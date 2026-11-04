"""Contract tests for POST /api/questions. They never call a real AI provider."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app import ai_adapter, main
from app.models import HR_GUIDANCE_MESSAGE, ModelAnswer

URL = "/api/questions"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "fake")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    with TestClient(main.app) as c:
        yield c


def ask(client, question):
    return client.post(URL, json={"question": question})


def assert_shape(r, status, result_type):
    assert r.status_code == status
    assert r.headers["cache-control"] == "no-store"
    body = r.json()
    assert set(body) == {"result_type", "message", "sources"}
    assert body["result_type"] == result_type
    assert body["message"].strip()
    return body


def fake_model(answer: ModelAnswer):
    async def _gen(question, passages, deadline, settings):
        return answer
    return _gen


# --- Pages ---

def test_serves_page_and_script(client):
    assert "Onboarding Assistant" in client.get("/").text
    r = client.get("/app.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]


# --- Supported answer path (fake provider) ---

def test_orientation_question_retrieves_hr01_p2():
    """HR-01-P2 must be among the top 3 passages sent to the model."""
    import tempfile
    from pathlib import Path
    from app.search import _search_sync, build_index
    with tempfile.TemporaryDirectory() as d:
        db = Path(d) / "t.db"
        build_index(Path(__file__).parent.parent / "data" / "documents", db)
        ids = [p.passage_id for p in _search_sync(db, "Where and when is new-hire orientation?", 3)]
    assert "HR-01-P2" in ids


def test_fake_provider_cites_a_retrieved_passage(client):
    body = assert_shape(ask(client, "Where and when is new-hire orientation?"), 200, "answer")
    assert body["message"].startswith("[Test mode")
    assert len(body["sources"]) == 1


def test_answer_sources_come_from_storage(client, monkeypatch):
    monkeypatch.setattr(ai_adapter, "generate_answer", fake_model(ModelAnswer("answer", "Room 204, 9 to noon.", ["HR-01-P2"])))
    body = assert_shape(ask(client, "Where and when is new-hire orientation?"), 200, "answer")
    src = body["sources"][0]
    assert src["passage_id"] == "HR-01-P2"
    assert src["document_id"] == "HR-01"
    assert src["document_title"] == "HR-01 New-Hire Orientation"
    assert "Room 204" in src["passage_text"]


def test_no_matches_gives_hr_guidance_without_ai_call(client, monkeypatch):
    called = False

    async def should_not_run(*args):
        nonlocal called
        called = True

    monkeypatch.setattr(ai_adapter, "generate_answer", should_not_run)
    body = assert_shape(ask(client, "Zebra xylophone quokka?"), 200, "hr_guidance")
    assert body["message"] == HR_GUIDANCE_MESSAGE and body["sources"] == []
    assert not called


# --- Model output checks (build_response) ---

def test_model_decline_uses_standard_hr_message(client, monkeypatch):
    monkeypatch.setattr(ai_adapter, "generate_answer", fake_model(ModelAnswer("hr_guidance", "anything", [])))
    body = assert_shape(ask(client, "What should I bring to orientation?"), 200, "hr_guidance")
    assert body["message"] == HR_GUIDANCE_MESSAGE


def test_unknown_citation_is_502(client, monkeypatch):
    monkeypatch.setattr(ai_adapter, "generate_answer", fake_model(ModelAnswer("answer", "Room 9.", ["HR-05-P9"])))
    body = assert_shape(ask(client, "Where is orientation?"), 502, "service_error")
    assert body["sources"] == []


def test_answer_without_citation_is_502(client, monkeypatch):
    monkeypatch.setattr(ai_adapter, "generate_answer", fake_model(ModelAnswer("answer", "Room 204.", [])))
    assert_shape(ask(client, "Where is orientation?"), 502, "service_error")


def test_duplicate_citations_removed_in_order(client, monkeypatch):
    ids = ["HR-01-P2", "HR-01-P2"]
    monkeypatch.setattr(ai_adapter, "generate_answer", fake_model(ModelAnswer("answer", "Room 204.", ids)))
    body = assert_shape(ask(client, "Where is new-hire orientation?"), 200, "answer")
    assert [s["passage_id"] for s in body["sources"]] == ["HR-01-P2"]


def test_malformed_model_json_is_502():
    from app.models import ContractError
    with pytest.raises(ContractError) as exc:
        ai_adapter.parse_model_json("Sure! Orientation is in Room 204.")
    assert exc.value.status_code == 502


def test_model_timeout_is_504(client, monkeypatch):
    """A provider call that outlasts the shared deadline returns 504 and is discarded."""
    import dataclasses

    async def slow_provider(http_client, settings, prompt):
        await asyncio.sleep(5)
        return '{"decision": "answer", "message": "late", "passage_ids": ["HR-01-P2"]}'

    monkeypatch.setitem(ai_adapter.PROVIDERS, "anthropic", slow_provider)
    main.app.state.settings = dataclasses.replace(
        main.app.state.settings, ai_provider="anthropic", ai_model="test", ai_api_key="test", deadline_seconds=0.3
    )
    body = assert_shape(ask(client, "Where is orientation?"), 504, "service_error")
    assert "late" not in body["message"]


def test_real_provider_without_key_is_503(client):
    import dataclasses
    main.app.state.settings = dataclasses.replace(main.app.state.settings, ai_provider="anthropic", ai_api_key="")
    assert_shape(ask(client, "Where is orientation?"), 503, "service_error")


# --- Input errors ---

@pytest.mark.parametrize(
    "payload",
    [{"question": ""}, {"question": "   "}, {"question": 5}, {}, {"question": "hi", "extra": 1}, ["question"],
     {"question": "x" * 1001}],
)
def test_invalid_questions_are_422(client, payload):
    body = assert_shape(client.post(URL, json=payload), 422, "input_error")
    assert body["sources"] == []


def test_blank_question_message(client):
    assert ask(client, "  ").json()["message"] == "Please enter a question."


def test_1000_code_points_accepted(client):
    assert ask(client, "é" * 1000).status_code == 200  # 1,000 code points, 2,000 bytes


@pytest.mark.parametrize(
    "question",
    ["My email is jo.doe@example.com, when is orientation?", "Call me at (555) 123-4567",
     "My SSN is 123-45-6789"],
)
def test_personal_info_rejected_without_echo(client, question):
    body = assert_shape(ask(client, question), 422, "input_error")
    for fragment in ("example.com", "4567", "6789"):
        assert fragment not in body["message"]


def test_malformed_json_is_400(client):
    r = client.post(URL, content=b"{not json", headers={"Content-Type": "application/json"})
    assert_shape(r, 400, "input_error")


def test_wrong_media_type_is_415(client):
    r = client.post(URL, content=b'{"question":"hi"}', headers={"Content-Type": "text/plain"})
    assert_shape(r, 415, "input_error")


def test_body_over_16_kib_is_413(client):
    r = client.post(URL, content=b"x" * (16 * 1024 + 1), headers={"Content-Type": "application/json"})
    assert_shape(r, 413, "input_error")


def test_wrong_method_is_405_with_allow_header(client):
    r = client.get(URL)
    assert_shape(r, 405, "input_error")
    assert r.headers["allow"] == "POST"


# --- Privacy: no raw questions in logs ---

def test_question_text_not_logged(client, caplog):
    caplog.set_level("DEBUG")
    ask(client, "Where is the purple-unicorn orientation room?")
    assert "purple-unicorn" not in caplog.text
