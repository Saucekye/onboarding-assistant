# Alpha test results and API feasibility (SP-1)

Run on 2026-11-17 at about 6:43 p.m. Eastern. All 20 questions in `tests/test_questions.json` were sent to the running server with `python -m scripts.run_end_to_end` and a real AI provider connected (`AI_PROVIDER=anthropic`, model `claude-haiku-5-5`). Code version: pull request #3.

## Results against our targets

| Measure | Target | Result |
| --- | --- | --- |
| Answerable questions answered with the expected passage cited | 14 of 16 | **15 of 16** |
| Unsupported questions (T17–T20) that returned HR guidance with no sources | 4 of 4 | **4 of 4** |
| Slowest response | 10 s (15 s timeout) | **2.9 s** |
| Credentials or question text in the server log | none | none (log shows only result type, status, sources, and milliseconds) |

These are results on our own 20-question set, not proof of accuracy beyond it.

## Question by question

| ID | Type | Outcome | Cited | Time |
| --- | --- | --- | --- | --- |
| T01 | direct | answer | HR-01-P2 | 2.2 s |
| T02 | direct | answer | HR-01-P6 | 1.3 s |
| T03 | direct | answer | HR-01-P9 | 1.3 s |
| T04 | direct | answer | HR-02-P2 | 1.3 s |
| T05 | direct | answer | HR-02-P5 | 1.4 s |
| T06 | direct | answer | HR-02-P7 | 1.2 s |
| T07 | direct | answer | HR-03-P4 | 1.7 s |
| T08 | direct | answer | HR-03-P2 | 2.4 s |
| T09 | direct | answer | HR-04-P2 | 1.9 s |
| T10 | direct | answer | HR-04-P5 | 1.7 s |
| T11 | direct | answer | HR-05-P4 | 2.0 s |
| T12 | direct | answer | HR-05-P3 | 2.0 s |
| T13 | reworded | **HR guidance (expected HR-04-P9)** | none | 2.2 s |
| T14 | reworded | answer | HR-01-P4 | 2.3 s |
| T15 | reworded | answer | HR-05-P5 | 2.2 s |
| T16 | reworded | answer | HR-05-P6 | 2.9 s |
| T17 | unsupported | HR guidance | none | 1.6 s |
| T18 | unsupported | HR guidance | none | 1.3 s |
| T19 | unsupported | HR guidance | none | 1.6 s |
| T20 | unsupported | HR guidance | none | 1.8 s |

## Answer check against the cited passages

The printed answers were compared with the text of the passages they cite.

- T01–T12, T14 and T15: every claim in the answer appears in the cited passage.
- **T13 (known limitation):** search did not retrieve HR-04-P9 because the question ("vacation") shares no words with the passage ("paid time off"). The model declined and returned HR guidance instead of guessing. This stays documented rather than fixed with a one-question rule.
- **T16 (borderline):** the cited passage (HR-05-P6) covers a laptop that is "lost or stolen." The answer also tells the employee to contact the Help Desk if they "can't find it." That reads "misplaced" as "lost," which is reasonable but goes slightly past the passage's wording.

Human review: this comparison still needs a teammate to read the answers and confirm.

## API feasibility (SP-1)

- **Provider tested:** Anthropic Claude API (Messages API), model `claude-haiku-5-5`.
- **Access requirements:** a Claude Console account, prepaid usage credits, and an API key created in the Console. The key is stored only in the server's `.env` file (ignored by Git) and never reaches the browser.
- **Response time:** 1.2–2.9 s per question through the full application, well inside the 10 s target and the 15 s deadline.
- **Failure behavior:** with an invalid key the provider returned HTTP 401. The application returned a 503 service error with a generic retry message, and the log recorded only the HTTP status.
- **Cost:** not yet measured. Check the Usage page in the Console and record it here.
- **Recommendation:** use this provider for the alpha. No blockers. Each tester supplies their own key, or runs in test mode (`AI_PROVIDER=fake`) without one.

## What is still open

- Reworded question T13 (see above).
- No relevance cutoff: safety on unsupported questions depends on the model declining. All four declined in this run.
- Repeat this run after any change to search, the synonym list, or the model instructions.
