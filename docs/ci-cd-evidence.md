# CI/CD evidence

## What our pipeline is

We use **continuous integration** with GitHub Actions. We do **not** have automated deployment: the assistant runs locally from the repository (see `README.md`), and nothing is published to a server. We chose this on purpose for the course project, because there is no hosting environment and the AI provider needs a private key that must never be stored in the repository.

The workflow is `.github/workflows/ci.yml`.

| Item | Setting |
| --- | --- |
| Runs on | Every pull request, and every push to `main` |
| Environment | Ubuntu, Python 3.12, pip cache |
| AI provider | `AI_PROVIDER=fake` (test mode). The pipeline never calls a real AI service and uses no secrets. |

### Steps and gates

| Step | Command | Fails the run when |
| --- | --- | --- |
| Install | `pip install -r requirements.txt` | A dependency cannot be installed |
| Tests with coverage | `python -m pytest -q --cov=app --cov-report=term-missing --cov-fail-under=80` | Any test fails, or coverage of `app/` drops below 80% |
| 20-question retrieval check | `python -m scripts.run_test_questions` | Fewer than 14 of the 16 answerable questions find the right passage in the top 3 |

### What each gate protects

- **Contract tests** (`tests/test_api.py`) check the status codes, result types, limits, privacy screening, and headers from our Interface Contracts.
- **Search tests** (`tests/test_search.py`) check ranking, the numeric tie-break (HR-01-P2 before HR-01-P10), the synonym list, and the example questions on the page.
- **The 20-question check** catches search regressions that unit tests miss, such as a synonym change that fixes one question and breaks another.

### What the pipeline cannot check

- Whether a real AI model declines the four unsupported questions (T17 to T20). Test mode cannot decline, so we run `python -m scripts.run_end_to_end` by hand with a real provider. Results are in `alpha-results.md`.
- The web page's JavaScript. There is no automated browser test yet (listed as technical debt in `code-quality.md`).

## How the pipeline was used

- Pull request #3 (search fix, tie-break fix, removal of an expected-failure test marker, this pipeline, and the results document) ran the workflow on its branch (two passing runs on 2026-11-17) before merging.
- A pull request is not merged until the checks pass and a teammate has reviewed it. This is our definition of done in `README.md`.

## Where to see the evidence

1. Open the repository on GitHub and click the **Actions** tab.
2. Each row is one run. Click a run, then the **test** job, to see every step and its output, including the coverage table.
3. Pull requests show the same result under **Checks** at the bottom of the conversation tab.
