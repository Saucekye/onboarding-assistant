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

Open http://127.0.0.1:8000. Choose an example topic to fill in a question, then click **Ask**. In test mode, the answer starts with "[Test mode…]" and quotes the top matching passage; this checks retrieval and the interface, not a real AI provider's answer accuracy.

The examples cover all five HR documents:

| Topic | Example question | Expected first passage |
| --- | --- | --- |
| Orientation | What room is orientation in? | HR-01-P2 |
| Benefits | What does the dental plan cover? | HR-02-P4 |
| Required forms | When must I complete Form I-9? | HR-03-P2 |
| Leave | How do I request paid time off? | HR-04-P4 |
| Workplace conduct | What is the dress code? | HR-05-P4 |

The search database (`data/policies.db`) is built automatically on first start. After editing or adding a document in `data/documents/`, rebuild it:

```bash
python -m scripts.build_index
```

## Run the tests

```bash
python -m pytest -q
```

The tests check every status code and result type in the contract (200, 400, 405, 413, 415, 422, 502, 503, 504). They also check that answer sources come from storage, that unknown citations are rejected, that question text never appears in the logs, that search ties sort in passage-number order, and that the 20 test questions meet the retrieval target. They never call a real AI provider.

### 20-question retrieval check

```bash
python -m scripts.run_test_questions
```

Prints where each of the 20 questions in `tests/test_questions.json` lands in the search results. It exits with an error if fewer than 14 of the 16 answerable questions find their expected passage, or if any of the 12 direct questions miss. This checks **retrieval only**. It cannot show whether the AI answers correctly or declines T17–T20; test that with a real provider (US-4).

### End-to-end check with a real AI provider (US-4)

With the server running and a provider set in `.env` (see below), run this in a second terminal:

```bash
python -m scripts.run_end_to_end
```

It sends all 20 questions to the running server and prints each answer. Targets: 14 of 16 answerable questions cite the expected passage, all 4 unsupported questions (T17–T20) return HR guidance with no sources, and every response takes 10 seconds or less. It only checks the cited passage, so read the printed answers and confirm each claim matches the passage. In test mode the unsupported questions always fail, because test mode never declines.

### Automated checks (GitHub Actions)

`.github/workflows/ci.yml` runs `python -m pytest -q` and the 20-question check on every pull request and every push to `main`. It runs in test mode and uses no API key or secret. Never add an API key to the workflow file.

## Setup check (T-2)

On each teammate's machine, confirm:

- [ ] Setup steps above work as written (note any step that fails)
- [ ] The page loads, each topic fills in its example, and **Ask** returns the expected source listed above
- [ ] A question with no matches (e.g., "Zebra xylophone quokka?") shows **Contact HR**
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
| `data/documents/` | Five JSON documents: orientation, benefits, required forms, leave, and workplace conduct (HR-01 to HR-05) |
| `tests/` | Contract tests |

## How search works and known limitations

Search returns up to 3 passages: SQLite FTS5 relevance first, then document and passage number for ties (HR-01-P2 before HR-01-P10).

**Synonym list.** `SYNONYMS` in `app/search.py` adds search terms when a question words things differently from the documents. The original word is always kept. The list is small and maintained by hand: "misplace/lose/computer" add "lost/laptop" (HR-05-P6), and "orientation" adds "room/arrive" so the first-day passage (HR-01-P2) outranks passages that only mention orientation in passing. Before changing it, rerun the 20-question check. Do not add a synonym just to make one question pass.

Results for the 20 test questions with all five documents loaded:

- **Answerable:** 15 of 16 find the expected passage in the top 3 (target 14). All 12 direct questions pass. T14, T15 and T16 pass.
- **T13 is a known limitation.** "Can I take a vacation during my first month on the job?" shares no words with HR-04-P9 ("Paid time off... introductory period"), so search misses it. A test in `tests/test_search.py` records this; if it starts passing, update this section.
- **Unanswerable (T17–T20):** all four match some passage, so none stop at search. The model must decline every one. Test mode cannot decline, so test these with a real provider.
- **Orientation examples:** the page's example, "What room is orientation in?", and the original demo question, "Where and when is new-hire orientation?", both return HR-01-P2 first. The original question needed the synonym list above; it was previously a known search limitation.
- **No relevance cutoff yet.** Without one, safety on unsupported questions depends on the model declining.
- **A timed-out search keeps running briefly** after the 15-second deadline. Acceptable at prototype scale.

## Documentation

| Document | What it covers |
| --- | --- |
| `docs/API.md` | The `POST /api/questions` request, responses, status codes, and limits |
| `docs/USER_MANUAL.md` | How new hires use the page, and how to run, configure, and update the assistant |
| `docs/ci-cd-evidence.md` | What the GitHub Actions pipeline checks and how to see its runs |
| `docs/code-quality.md` | Test count, coverage, performance numbers, review evidence, and technical debt |
| `docs/alpha-results.md` | Real-provider results for the 20 test questions and the API feasibility notes |

Performance benchmark (our own code, test mode):

```bash
python -m scripts.benchmark
```

## Team and contributions

| Member | Contributions |
| --- | --- |
| Ceth Solwazi (Integration Lead) | Starter application and API server, search and synonym handling, AI provider integration and its feasibility check (SP-1), GitHub Actions pipeline, 20-question test and results documentation, written peer review of pull request #2 |
| Alex Luna | Web interface (`static/index.html`, `static/app.js`), expanded to all five HR documents in pull request #2; reviewed pull request #3 |
| Medlina Kanu | Testing and review of the search module, including finding the passage-ordering bug fixed in pull request #3; Unit 6 risk and impact statement |

Commit history and pull request reviews on GitHub show each member's work in detail.

## Working agreement

- Branch from `main` for each backlog item (e.g., `t2-starter`, `us1-answer-flow`) and open a pull request.
- Another member reviews each pull request before it merges (definition of done).
- Note AI-assisted code in the pull request description so the reviewer checks it against the contract and runs the tests.
