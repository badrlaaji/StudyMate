"""Regression gate (CI): retrieval and replayed answers must stay above the thresholds.

Usage:
  uv run python -m eval.regression          check, offline: no LLM call (CI)
  uv run python -m eval.regression record   re-record the answers with Gemini (quota)
Both use the app's default model (base e5, public, so CI can download it) and the
test split.
"""

import asyncio
import json
import os
import sys

from config import ROOT
from eval import eval_answers, eval_retrieval
from rag.embeddings import BASE_MODEL

THRESHOLDS = ROOT / "eval" / "thresholds.json"
REPLAY_DIR = ROOT / "eval" / "replay"
REPORT = ROOT / "eval" / "results" / "regression.json"
CI = os.environ.get("GITHUB_ACTIONS") == "true"
RECORD_HINT = (
    "Prompts changed: re-record with `uv run python -m eval.regression record`."
)


def flatten(retrieval: dict, answers: dict) -> dict[str, float]:
    """One flat dict of the gated metrics, e.g. {"retrieval.en.hit@4": 0.85}."""
    metrics = {}
    for lang in eval_retrieval.LANGS:
        for name in ("hit@4", "mrr@10"):
            metrics[f"retrieval.{lang}.{name}"] = retrieval[lang][name]
        for name in ("correct", "refused", "replay_misses"):
            metrics[f"answers.{lang}.{name}"] = answers[lang]["summary"][name]
    return metrics


def failures(metrics: dict[str, float], thresholds: dict[str, float]) -> list[str]:
    """Every metric below its minimum (a missing metric fails too)."""
    return [
        f"{key}: {metrics.get(key)} < {minimum}"
        for key, minimum in thresholds.items()
        if metrics.get(key, float("-inf")) < minimum
    ]


def markdown(metrics: dict[str, float], thresholds: dict[str, float]) -> str:
    """Table for the CI job summary."""
    lines = ["| Metric | Value | Minimum |", "| --- | --- | --- |"]
    for key, value in metrics.items():
        below = key in thresholds and value < thresholds[key]
        mark = " ❌" if below else ""
        lines.append(f"| {key} | {value}{mark} | {thresholds.get(key, '-')} |")
    return "\n".join(lines) + "\n"


def one_line(metrics: dict[str, float]) -> str:
    """Metrics as "key=value" pairs on one line."""
    return " ".join(f"{key}={value}" for key, value in metrics.items())


def use_settings(record: bool) -> None:
    """Same settings locally and in CI: base model, replay folder, offline check."""
    os.environ["EMBEDDING_MODEL"] = BASE_MODEL
    os.environ["LLM_CACHE_DIR"] = str(REPLAY_DIR)
    os.environ["LLM_OFFLINE"] = "0" if record else "1"


async def measure(pause_s: float) -> dict[str, float]:
    """Run the retrieval eval and the answer eval on the test split."""
    retrieval = await eval_retrieval.evaluate("test", "all-pages")
    answers = await eval_answers.evaluate(pause_s)
    return flatten(retrieval, answers)


def record() -> None:
    """Replace the recorded answers with fresh Gemini answers, then save the metrics."""
    for path in REPLAY_DIR.glob("*.json"):
        path.unlink()
    metrics = asyncio.run(measure(eval_answers.PAUSE_S))
    REPORT.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"{len(list(REPLAY_DIR.glob('*.json')))} answers recorded in {REPLAY_DIR}")


def check() -> int:
    """Measure offline and compare with the thresholds; return the exit code."""
    thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    metrics = asyncio.run(measure(0))
    table = markdown(metrics, thresholds)
    print(table)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as file:
            file.write("## Regression evaluation\n\n" + table)
    failed = failures(metrics, thresholds)
    # GitHub annotations: shown on the run page, readable through the API.
    prefix = "::error title=Regression::" if CI else "REGRESSION "
    for line in failed:
        print(f"{prefix}{line}")
    if CI:
        print(f"::notice title=Regression gate::{one_line(metrics)}")
    if any(metrics[f"answers.{lang}.replay_misses"] for lang in eval_retrieval.LANGS):
        print(RECORD_HINT)
    return 1 if failed else 0


def main(args: list[str]) -> None:
    """Record or check."""
    mode = args[0] if args else "check"
    if mode not in ("check", "record"):
        raise SystemExit(__doc__)
    use_settings(mode == "record")
    if mode == "record":
        record()
    else:
        sys.exit(check())


if __name__ == "__main__":
    main(sys.argv[1:])
