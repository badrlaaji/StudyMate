"""Median latency of POST /chat (step 10), on the 10 dev questions in EN and FR.

Usage: start the API, then uv run python -m eval.chat_latency
Dev questions were never sent to the agent before, so the LLM cache does not help.
"""

import json
import os
import statistics
import time

import httpx

from eval.eval_answers import PAUSE_S
from eval.eval_retrieval import LANGS, RESULTS_DIR
from eval.questions import load_questions

API_URL = os.environ.get("API_URL", "http://localhost:8000")
TIMEOUT_S = 120.0


def percentile(values: list[float], share: float) -> float:
    """Nearest-rank percentile (share between 0 and 1)."""
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(share * len(ordered)) - 1))
    return ordered[index]


def main() -> None:
    """Time every /chat call and save the summary."""
    rows = []
    with httpx.Client(base_url=API_URL, timeout=TIMEOUT_S) as client:
        for question in load_questions().dev:
            for lang in LANGS:
                start = time.perf_counter()
                body = client.post(
                    "/chat", json={"message": getattr(question, lang)}
                ).json()
                seconds = round(time.perf_counter() - start, 2)
                cited = {c["page"] for c in body.get("citations", [])}
                correct = body.get("status") == "ok" and bool(
                    cited & set(question.pages)
                )
                rows.append(
                    {
                        "id": question.id,
                        "lang": lang,
                        "seconds": seconds,
                        "status": body.get("status"),
                        "correct": correct,
                    }
                )
                time.sleep(PAUSE_S)  # quota: the pause is not part of the latency
    seconds = [row["seconds"] for row in rows]
    report = {
        "calls": len(rows),
        "median_s": round(statistics.median(seconds), 2),
        "p90_s": percentile(seconds, 0.9),
        "min_s": min(seconds),
        "max_s": max(seconds),
        "dev_correct": sum(row["correct"] for row in rows),
        "rows": rows,
    }
    print({key: value for key, value in report.items() if key != "rows"})
    path = RESULTS_DIR / "latency_chat.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
