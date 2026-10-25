"""LLM tracing report (step 19): latency, tokens and 429 errors per request (MLflow).

Usage: MLFLOW_TRACKING_URI set (local MLflow server), API traced, then
  uv run python -m eval.llm_traces
"""

import json
import statistics

from agent.tracing import EXPERIMENT, load_mlflow, setup
from eval.chat_latency import percentile
from eval.eval_retrieval import RESULTS_DIR

REPORT = RESULTS_DIR / "llm_traces.json"
MAX_TRACES = 5000


def seconds(span) -> float:
    """Duration of an MLflow span in seconds."""
    return (span.end_time_ns - span.start_time_ns) / 1e9


def to_request(trace) -> dict:
    """One traced request as plain data: its name, duration and LLM calls."""
    root = next(s for s in trace.data.spans if s.parent_id is None)
    calls = [
        {"seconds": seconds(s), **s.attributes}
        for s in trace.data.spans
        if s.span_type == "CHAT_MODEL"
    ]
    return {"name": root.name, "seconds": seconds(root), "calls": calls}


def summarize(requests: list[dict]) -> dict:
    """Latency, tokens and 429 errors per request and per live LLM call."""
    calls = [call for request in requests for call in request["calls"]]
    live = [call for call in calls if not call.get("cached")]
    with_429 = [r for r in requests if any(c.get("errors_429") for c in r["calls"])]
    latency = [call["seconds"] for call in live] or [0.0]
    per_request = [sum(c.get("input_tokens", 0) for c in r["calls"]) for r in requests]
    return {
        "requests": len(requests),
        "llm_calls": len(calls),
        "live_calls": len(live),
        "cached_calls": len(calls) - len(live),
        "errors_429": sum(call.get("errors_429", 0) for call in live),
        "errors_5xx": sum(call.get("errors_5xx", 0) for call in live),
        "calls_with_429_pct": share(sum(1 for c in live if c.get("errors_429")), live),
        "requests_with_429_pct": share(len(with_429), requests),
        "failed_calls": sum(1 for call in live if call.get("outcome") == "failed"),
        "call_median_s": round(statistics.median(latency), 2),
        "call_p90_s": round(percentile(latency, 0.9), 2),
        "input_tokens": sum(call.get("input_tokens", 0) for call in live),
        "output_tokens": sum(call.get("output_tokens", 0) for call in live),
        "input_tokens_per_request": round(statistics.median(per_request or [0])),
    }


def share(part: int, whole: list) -> float:
    """Percentage with one decimal (0 when there is nothing to count)."""
    return round(100 * part / len(whole), 1) if whole else 0.0


def markdown(summary: dict) -> str:
    """The README table."""
    rows = [
        (
            "Requests traced (live LLM calls)",
            f"{summary['requests']} ({summary['live_calls']})",
        ),
        ("LLM calls hit by a 429", f"{summary['calls_with_429_pct']} %"),
        ("Requests with at least one 429", f"{summary['requests_with_429_pct']} %"),
        (
            "LLM call latency, median / p90",
            f"{summary['call_median_s']} s / {summary['call_p90_s']} s",
        ),
        (
            "Tokens in / out (live calls)",
            f"{summary['input_tokens']} / {summary['output_tokens']}",
        ),
        ("Input tokens per request (median)", str(summary["input_tokens_per_request"])),
    ]
    lines = ["| Measure | Value |", "| --- | --- |"]
    return "\n".join(lines + [f"| {name} | {value} |" for name, value in rows]) + "\n"


def main() -> None:
    """Read every trace of the experiment, print the table, save the report."""
    if not setup():
        raise SystemExit("Set MLFLOW_TRACKING_URI first (see agent/tracing.py).")
    mlflow = load_mlflow()
    experiment = mlflow.get_experiment_by_name(EXPERIMENT)
    traces = mlflow.search_traces(
        locations=[experiment.experiment_id],
        return_type="list",
        max_results=MAX_TRACES,
        flush=True,
    )
    summary = summarize([to_request(trace) for trace in traces])
    print(markdown(summary))
    REPORT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
