"""Local performance benchmark (test mode, no network).

Sends each of the 20 test questions through the full FastAPI app repeatedly and
reports latency percentiles. It measures our own code (validation, search,
response building) and not the AI provider. Provider timing is recorded in
docs/alpha-results.md.

Run:  python -m scripts.benchmark
"""

import json
import os
import statistics
import time
from pathlib import Path

os.environ["AI_PROVIDER"] = "fake"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

QUESTIONS = json.loads((Path(__file__).resolve().parent.parent / "tests" / "test_questions.json").read_text())
ROUNDS = 10


def main() -> None:
    texts = [q["question"] for q in QUESTIONS]
    times_ms: list[float] = []
    failures = 0
    with TestClient(app) as client:
        client.post("/api/questions", json={"question": texts[0]})  # warm-up
        for _ in range(ROUNDS):
            for text in texts:
                start = time.perf_counter()
                response = client.post("/api/questions", json={"question": text})
                times_ms.append((time.perf_counter() - start) * 1000)
                if response.status_code != 200:
                    failures += 1
    times_ms.sort()
    p95 = times_ms[int(len(times_ms) * 0.95) - 1]
    print(f"requests: {len(times_ms)}  non-200: {failures}")
    print(f"median: {statistics.median(times_ms):.1f} ms  p95: {p95:.1f} ms  max: {times_ms[-1]:.1f} ms")


if __name__ == "__main__":
    main()
