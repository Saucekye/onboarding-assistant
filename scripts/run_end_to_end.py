"""Send the 20 test questions to a RUNNING server and compare with the expected results.

1. Start the server in another terminal:   python -m uvicorn app.main:app
2. Run this:                               python -m scripts.run_end_to_end

With a real AI provider in .env this is the US-4 check: T17-T20 must return HR guidance
with no sources. In test mode (AI_PROVIDER=fake) the unsupported questions cannot pass,
because test mode never declines.

The script prints each answer so a person can read it. It checks that the right passage
is cited, but only a human can judge whether every claim in the answer matches that
passage (the backlog's definition of a correct answer). Read the printed answers.

Exits with status 1 if a target is missed: 14 of 16 answerable questions cited correctly,
4 of 4 unsupported questions declined, and every response within 10 seconds.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

QUESTIONS = Path(__file__).resolve().parent.parent / "tests" / "test_questions.json"
ANSWER_TARGET, SECONDS_TARGET = 14, 10.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    url = parser.parse_args().url.rstrip("/") + "/api/questions"

    answerable_ok = unsupported_ok = 0
    slowest = 0.0
    for q in json.loads(QUESTIONS.read_text(encoding="utf-8")):
        start = time.monotonic()
        try:
            response = httpx.post(url, json={"question": q["question"]}, timeout=25)
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            print(f"{q['id']}  ERROR  could not get a response ({type(exc).__name__}). Is the server running?")
            continue
        seconds = time.monotonic() - start
        slowest = max(slowest, seconds)
        cited = [s["passage_id"] for s in body.get("sources", [])]
        expected = q["expected_passage"]
        if expected:
            ok = body.get("result_type") == "answer" and expected in cited
            answerable_ok += ok
        else:
            ok = body.get("result_type") == "hr_guidance" and not cited
            unsupported_ok += ok
        print(f"{q['id']}  {'PASS' if ok else 'FAIL'}  {body.get('result_type')} (HTTP {response.status_code}, {seconds:.1f}s)  cited={cited}  expected={expected}")
        print(f"      {body.get('message', '')}")

    print(f"\nAnswerable questions answered with the expected passage cited: {answerable_ok} of 16 (target {ANSWER_TARGET})")
    print(f"Unsupported questions that returned HR guidance with no sources: {unsupported_ok} of 4 (target 4)")
    print(f"Slowest response: {slowest:.1f}s (target {SECONDS_TARGET:.0f}s)")
    print("Read the printed answers: a cited passage does not prove every claim in the answer is supported.")
    ok = answerable_ok >= ANSWER_TARGET and unsupported_ok == 4 and slowest <= SECONDS_TARGET
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
