"""Search tests: tie-break order, synonyms, and the 20-question retrieval target."""

import json
import tempfile
from pathlib import Path

from app.search import SYNONYMS, _search_sync, build_index, to_fts_query
from scripts.run_test_questions import TARGET, run


def _write_doc(directory: Path, passages: dict[str, str]) -> None:
    doc = {
        "document_id": "HR-09",
        "document_title": "HR-09 Test Document",
        "passages": [{"passage_id": pid, "heading": "Heading", "passage_text": text} for pid, text in passages.items()],
    }
    (directory / "HR-09.json").write_text(json.dumps(doc), encoding="utf-8")


def test_ties_sort_by_passage_number_not_text():
    """With equal relevance, HR-09-P2 must come before HR-09-P10 (contract: ascending passage ID)."""
    with tempfile.TemporaryDirectory() as d:
        docs = Path(d) / "docs"
        docs.mkdir()
        same = "Employees receive a zebra badge on arrival."
        _write_doc(docs, {"HR-09-P10": same, "HR-09-P2": same, "HR-09-P1": same})
        db = Path(d) / "t.db"
        build_index(docs, db)
        ids = [p.passage_id for p in _search_sync(db, "zebra badge", 3)]
    assert ids == ["HR-09-P1", "HR-09-P2", "HR-09-P10"]


def test_synonyms_added_next_to_original_words():
    query = to_fts_query("What should I do if I misplace my work computer?")
    for term in ("misplace", "lost", "computer", "laptop"):
        assert f'"{term}"' in query


def test_stopwords_are_dropped_but_not_their_synonyms():
    assert to_fts_query("What is the") == ""
    assert '"room"' in to_fts_query("Where is orientation?")


def test_synonym_values_are_plain_lowercase_words():
    """Synonyms go into a quoted FTS query, so keep them simple."""
    for expansions in SYNONYMS.values():
        assert all(t.isalpha() and t == t.lower() for t in expansions)


def test_twenty_question_retrieval_meets_target():
    result = run()
    assert result["hits"] >= TARGET, f"only {result['hits']} of {result['answerable']} answerable questions found their passage"
    assert result["direct_hits"] == result["direct"]


def test_reworded_lost_laptop_question_finds_hr05_p6_first():
    rows = {r["id"]: r for r in run()["rows"]}
    assert rows["T16"]["found"][0] == "HR-05-P6"


def test_t13_is_still_a_known_limitation():
    """T13 (vacation) shares no words with HR-04-P9. If this starts passing, update the README."""
    rows = {r["id"]: r for r in run()["rows"]}
    assert rows["T13"]["status"] == "MISS"


# The five example questions on the page (see the README table). If search changes,
# each must still return its expected passage first.
PAGE_EXAMPLES = [
    ("What room is orientation in?", "HR-01-P2"),
    ("What does the dental plan cover?", "HR-02-P4"),
    ("When must I complete Form I-9?", "HR-03-P2"),
    ("How do I request paid time off?", "HR-04-P4"),
    ("What is the dress code?", "HR-05-P4"),
]


def test_page_example_questions_return_expected_passage_first():
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "t.db"
        build_index(Path(__file__).parent.parent / "data" / "documents", db)
        for question, expected in PAGE_EXAMPLES:
            ids = [p.passage_id for p in _search_sync(db, question, 3)]
            assert ids[0] == expected, f"{question!r} returned {ids}"
