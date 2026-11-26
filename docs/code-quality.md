# Code quality metrics

Measured on the final code of the Alpha release plus the Unit 8 additions. Commands to reproduce each number are in the right-hand column.

## Summary

| Measure | Result | Reproduce with |
| --- | --- | --- |
| Automated tests | 37 passing | `python -m pytest -q` |
| Statement coverage of `app/` | 87% (261 of 299 statements) | `python -m pytest -q --cov=app --cov-report=term-missing` |
| Search quality on our 20 questions | 15 of 16 answerable questions find the expected passage; 12 of 12 direct questions | `python -m scripts.run_test_questions` |
| End to end with a real AI provider | 15 of 16 answered with the correct citation; 4 of 4 unsupported questions got HR guidance | `python -m scripts.run_end_to_end` (server running, provider set) |
| Response time, our own code | Median 1.5 to 1.7 ms and 95th percentile 1.9 to 2.2 ms across two runs of 200 requests each (test mode, no failures) | `python -m scripts.benchmark` |
| Response time, with a real AI provider | 1.2 to 2.9 seconds per question (target 10 s, hard deadline 15 s) | `alpha-results.md` |
| Sensitive data in logs | None. Logs hold only result type, status, source count, and milliseconds. | Read `app/main.py` |

The benchmark runs in one process in test mode, so it measures validation, search, and response building. It says nothing about the AI provider, which accounts for nearly all of the time users wait.

## Coverage by file

| File | Statements | Missed | Coverage | Why the gap |
| --- | --- | --- | --- | --- |
| `app/validation.py` | 39 | 0 | 100% | |
| `app/models.py` | 35 | 0 | 100% | |
| `app/config.py` | 17 | 0 | 100% | |
| `app/main.py` | 72 | 5 | 93% | Rare error branches |
| `app/search.py` | 57 | 7 | 88% | Timeout and database-error branches |
| `app/responses.py` | 16 | 2 | 88% | Two malformed-answer branches |
| `app/ai_adapter.py` | 63 | 24 | 62% | The real Anthropic and OpenAI request code. CI uses test mode, so these lines run only in our manual real-provider runs. |

The lowest coverage is in the one file that talks to an outside service. It is also the file where a bug would matter most, so it is the first place to add tests, using a mocked HTTP client.

## Code review evidence

- Every change goes through a branch and a pull request, and a teammate reviews it before merge (our definition of done).
- **Pull request #2** (interface expanded to all five HR documents): reviewed in writing against readability, security, performance, integration, and documentation. The review confirmed server text is inserted with `textContent` (no `innerHTML` anywhere in `static/app.js`) and that the page's limits match the server's.
- **Pull request #3** (search fix, tie-break fix, CI pipeline, results documentation): reviews by teammates found a text-versus-number sorting bug (HR-01-P10 sorted before HR-01-P2), asked for the expected-failure test marker to be removed, and asked for the fix to be documented. All three were addressed before merge.
- Where AI tools helped write code, the pull request description says so and the reviewer checks that code against the contract.

## Known technical debt

| Item | Impact | Planned fix |
| --- | --- | --- |
| Limits (1,000 characters, 3 sources, 20 s timeout) are copied between the server and the page | They can drift apart without any test noticing | Add a test that compares the page's constants with the server's |
| No automated test of the page's JavaScript | Response handling in the browser is checked by hand | A browser smoke test in CI that clicks the example topics |
| `app/ai_adapter.py` provider code at 62% coverage | A provider API change could break answers unnoticed | Tests with a mocked HTTP client |
| Hand-maintained synonym list; question T13 ("vacation") still misses | Reworded questions can get HR guidance even when an answer exists | Test with more plainly worded questions and extend the list from results; consider semantic search later |
| No relevance cutoff in search | For questions outside the documents, safety relies on the model declining | Add a minimum score, then recheck all 20 questions |
| No linter or type checker | Style and type mistakes are caught only by review | Add `ruff` and `mypy` to CI |
| Continuous integration only, no deployment | The app must be run locally | Container image and a hosted demo, if the project continues |
