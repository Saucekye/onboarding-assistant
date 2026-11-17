"""Policy passage storage and search_passages, using SQLite full-text search (FTS5)."""

import asyncio
import json
import re
import sqlite3
import time
from pathlib import Path

from .models import SourcePassage, service_error

# Common words dropped from the search so they do not match every passage.
STOPWORDS = {
    "a", "about", "am", "an", "and", "any", "are", "as", "at", "be", "can", "could", "do",
    "does", "for", "from", "get", "have", "how", "i", "if", "in", "is", "it", "me", "my",
    "of", "on", "or", "our", "should", "so", "that", "the", "there", "this", "to", "uh",
    "was", "we", "what", "when", "where", "which", "who", "why", "will", "with", "would",
    "you", "your",
}


def build_index(documents_dir: Path, database_path: Path) -> int:
    """(Re)build the SQLite database from the JSON documents. Returns the passage count."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = database_path.with_suffix(".tmp")
    tmp_path.unlink(missing_ok=True)
    conn = sqlite3.connect(tmp_path)
    count = 0
    try:
        conn.executescript(
            """
            CREATE TABLE passages (
                passage_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                document_title TEXT NOT NULL,
                heading TEXT NOT NULL,
                passage_text TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE passages_fts USING fts5(
                passage_id UNINDEXED, heading, passage_text, tokenize = 'porter unicode61'
            );
            """
        )
        for path in sorted(documents_dir.glob("*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            for p in doc["passages"]:
                conn.execute(
                    "INSERT INTO passages VALUES (?, ?, ?, ?, ?)",
                    (p["passage_id"], doc["document_id"], doc["document_title"], p["heading"], p["passage_text"]),
                )
                conn.execute(
                    "INSERT INTO passages_fts (passage_id, heading, passage_text) VALUES (?, ?, ?)",
                    (p["passage_id"], p["heading"], p["passage_text"]),
                )
                count += 1
        conn.commit()
    finally:
        conn.close()
    tmp_path.replace(database_path)
    return count


def to_fts_query(question: str) -> str:
    """Turn a question into an OR query of its meaningful words, each quoted."""
    words = re.findall(r"[^\W_]+", question.lower())
    terms = []
    for w in words:
        if w not in STOPWORDS and w not in terms:
            terms.append(w)
    return " OR ".join(f'"{t}"' for t in terms)


def _search_sync(database_path: Path, question: str, limit: int) -> list[SourcePassage]:
    query = to_fts_query(question)
    if not query:
        return []
    if not database_path.exists():
        raise service_error(503)
    try:
        conn = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                """
                SELECT p.document_id, p.passage_id, p.document_title, p.passage_text
                FROM passages_fts f JOIN passages p ON p.passage_id = f.passage_id
                WHERE passages_fts MATCH ?
                ORDER BY bm25(passages_fts) ASC, p.passage_id ASC
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        raise service_error(503)
    return [SourcePassage(*row) for row in rows]


async def search_passages(question: str, limit: int, deadline: float, database_path: Path) -> list[SourcePassage]:
    """Return up to `limit` passages by relevance, then ascending passage ID for ties."""
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise service_error(500)
    try:
        return await asyncio.wait_for(asyncio.to_thread(_search_sync, database_path, question, limit), remaining)
    except TimeoutError:
        raise service_error(500)  # deadline reached in local processing
