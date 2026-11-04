# Maple Ridge Onboarding Assistant (CMSC 495 Group 6)

Starter application for T-2. A FastAPI server serves the question page (`static/`, from Alex's interface handoff) and the `POST /api/questions` endpoint from our submitted Interface Contracts. Search uses SQLite full-text search over the fictional HR documents in `data/documents/`.

## Setup

You need Python 3.11 or newer and Git.

```bash
git clone <repo URL>
cd onboarding-assistant

python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Create your local settings file:

```bash
# macOS/Linux
cp .env.example .env
# Windows
copy .env.example .env
```

Leave `AI_PROVIDER=fake` for now. Test mode makes no API call and needs no key.

## Run

```bash
python -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 and click **Try the orientation question**. In test mode, the answer starts with "[Test mode…]" and shows the top matching HR-01 passage.

The search database (`data/policies.db`) is built automatically on first start. After editing or adding a document in `data/documents/`, rebuild it:

```bash
python -m scripts.build_index
```

## Run the tests

```bash
python -m pytest -q
```

The tests check every status code and result type in the contract (200, 400, 405, 413, 415, 422, 502, 503, 504). They also check that answer sources come from storage, that unknown citations are rejected, and that question text never appears in the logs. They never call a real AI provider.

## Setup check (T-2)

On each teammate's machine, confirm:

- [ ] Setup steps above work as written (note any step that fails)
- [ ] The page loads and the orientation question returns a test-mode answer with an HR-01 source
- [ ] A question with no matches (e.g., "Is dental coverage included?") shows **Contact HR**
- [ ] A question with an email address is rejected beside the field
- [ ] `python -m pytest -q` passes
- [ ] `git status` does not list `.env` or `data/policies.db`
- [ ] The terminal log shows only `result=… status=… ms=…`, never the question text

## Connecting a real AI provider (SP-1)

`app/ai_adapter.py` supports `anthropic` and `openai`. To test one, set these in **your own `.env`** (never in code or a commit):

```
AI_PROVIDER=anthropic        # or openai
AI_MODEL=<model name from the provider's docs>
AI_API_KEY=<your key>
```

Then restart the server. If the key or model is missing, the page shows a service error (503) and the log says the provider isn't configured.

## Project layout

| Path | What it is |
| --- | --- |
| `app/main.py` | FastAPI app, `handle_question`, page routes, error handling, logging |
| `app/validation.py` | `validate_question`, `screen_question`, body/media-type checks |
| `app/search.py` | SQLite FTS5 index and `search_passages` (top 3, relevance then passage ID) |
| `app/ai_adapter.py` | `generate_answer`, the only code that calls the AI provider |
| `app/responses.py` | `build_response`: checks decisions and citations, builds sources from storage |
| `static/` | Alex's `index.html` and `app.js` |
| `data/documents/` | One JSON file per HR document (HR-01 now; HR-02 to HR-05 to come) |
| `tests/` | Contract tests |

## Known limitations

- Search ranks passages by word overlap. For "Where and when is new-hire orientation?", HR-01-P3 (what to bring) ranks above HR-01-P2 (where and when), though both are sent to the model. Review this during paraphrase testing.
- Some unsupported questions still match common words (e.g., "sick **days**" matches HR-01 passages), so they reach the model, which must decline. Test mode cannot decline, so use a real provider when testing US-4.

## Working agreement

- Branch from `main` for each backlog item (e.g., `t2-starter`, `us1-answer-flow`) and open a pull request.
- Another member reviews each pull request before it merges (definition of done).
- Note AI-assisted code in the pull request description so the reviewer checks it against the contract and runs the tests.
