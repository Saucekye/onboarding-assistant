"""Run the 20 test questions through search and report retrieval results.

Usage:  python -m scripts.run_test_questions

This checks retrieval only (does the expected passage reach the model?). It does not
call an AI provider, so it cannot tell whether the model answers correctly or declines
the four unsupported questions (T17-T20). Test those with a real provider.

Exits with status 1 if fewer than TARGET of the 16 answerable questions find their
expected passage in the top 3, or if the 12 direct questions do not all find theirs.
"""

import json
import sys
import tempfile
from pathlib import Path

from app.search import _search_sync, build_index

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "tests" / "test_questions.json"
TARGET = 14  # at least 14 of 16 answerable questions (backlog target)


def run() -> dict:
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "eval.db"
        build_index(ROOT / "data" / "documents", db)
        for q in questions:
            ids = [p.passage_id for p in _search_sync(db, q["question"], 3)]
            expected = q["expected_passage"]
            if expected is None:
                status = "reaches model" if ids else "no match -> HR guidance"
            elif ids and ids[0] == expected:
                status = "FIRST"
            elif expected in ids:
                status = "in top 3"
            else:
                status = "MISS"
            rows.append({**q, "found": ids, "status": status})
    answerable = [r for r in rows if r["expected_passage"]]
    hits = [r for r in answerable if r["status"] in ("FIRST", "in top 3")]
    direct = [r for r in answerable if r["type"] == "direct"]
    direct_hits = [r for r in direct if r["status"] in ("FIRST", "in top 3")]
    return {"rows": rows, "hits": len(hits), "answerable": len(answerable),
            "direct_hits": len(direct_hits), "direct": len(direct)}


if __name__ == "__main__":
    result = run()
    for r in result["rows"]:
        print(f"{r['id']}  {r['status']:24} {r['found']}")
    print(f"\nAnswerable questions with the expected passage in the top 3: {result['hits']} of {result['answerable']} (target {TARGET})")
    print(f"Direct questions: {result['direct_hits']} of {result['direct']}")
    print("Unsupported questions (T17-T20) need a real AI provider to confirm the model declines.")
    ok = result["hits"] >= TARGET and result["direct_hits"] == result["direct"]
    sys.exit(0 if ok else 1)
