"""Tests for LLM tracing (MLflow in a temporary SQLite file: no server, no network)."""

from types import SimpleNamespace

import pytest
from langchain_core.exceptions import ModelRateLimitError
from langchain_core.messages import AIMessage

from agent import tracing
from agent.llm import invoke_structured, parse_output
from eval.llm_traces import markdown, summarize, to_request
from tests.test_llm import Answer


def flaky_llm():
    """A fake model: 429 first, then an answer with token counts."""
    calls = []

    def invoke(prompt):
        calls.append(prompt)
        if len(calls) == 1:
            raise ModelRateLimitError("429 RESOURCE_EXHAUSTED {'retryDelay': '0s'}")
        usage = {"input_tokens": 120, "output_tokens": 30, "total_tokens": 150}
        raw = AIMessage(content="{}", usage_metadata=usage)
        return {"raw": raw, "parsed": Answer(text="ok"), "parsing_error": None}

    runnable = SimpleNamespace(invoke=invoke)
    return SimpleNamespace(with_structured_output=lambda schema, **_: runnable)


def test_tracing_is_off_without_a_tracking_uri(monkeypatch):
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    monkeypatch.setattr(tracing, "load_env", lambda: None)  # ignore a local .env
    assert tracing.setup() is False
    with tracing.span("POST /chat", "CHAIN") as current:
        assert current is None
    tracing.set_attributes(current, {"ignored": True})


def test_parse_output_reads_tokens_and_refuses_bad_output():
    raw = AIMessage(
        content="{}",
        usage_metadata={"input_tokens": 5, "output_tokens": 2, "total_tokens": 7},
    )
    parsed, tokens = parse_output(
        {"raw": raw, "parsed": Answer(text="a"), "parsing_error": None}
    )
    assert parsed.text == "a" and tokens == {"input_tokens": 5, "output_tokens": 2}
    with pytest.raises(ValueError):
        parse_output({"raw": raw, "parsed": None, "parsing_error": None})


def test_a_request_trace_keeps_latency_tokens_and_429(tmp_path, monkeypatch):
    mlflow = pytest.importorskip("mlflow")  # dev dependency: the local store needs it
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"sqlite:///{tmp_path / 'mlflow.db'}")
    monkeypatch.setenv("LLM_MODEL", "fake-model")
    assert tracing.setup() is True
    llm, cache = flaky_llm(), tmp_path / "cache"
    with tracing.span("POST /chat", "CHAIN", {"course": "data-science"}):
        invoke_structured(Answer, "q", llm=llm, cache_dir=cache, sleep=lambda s: None)
        invoke_structured(Answer, "q", llm=llm, cache_dir=cache)  # from the disk cache
    traces = mlflow.search_traces(return_type="list", flush=True)
    request = to_request(traces[0])
    assert request["name"] == "POST /chat"
    live, cached = request["calls"]
    assert live["errors_429"] == 1 and live["outcome"] == "ok"
    assert (live["input_tokens"], live["output_tokens"]) == (120, 30)
    assert cached["cached"] is True
    mlflow.set_tracking_uri("")  # leave no global state for the other tests


def test_summary_counts_429_per_call_and_per_request():
    calls = [
        {
            "seconds": 1.0,
            "cached": False,
            "errors_429": 1,
            "input_tokens": 100,
            "output_tokens": 10,
        },
        {
            "seconds": 3.0,
            "cached": False,
            "errors_429": 0,
            "input_tokens": 300,
            "output_tokens": 30,
        },
        {"seconds": 0.0, "cached": True},
    ]
    requests = [
        {"name": "POST /chat", "seconds": 4.0, "calls": calls},
        {"name": "POST /chat", "seconds": 2.0, "calls": [calls[1]]},
    ]
    summary = summarize(requests)
    assert summary["live_calls"] == 3 and summary["cached_calls"] == 1
    assert summary["calls_with_429_pct"] == 33.3  # 1 of 3 live calls
    assert summary["requests_with_429_pct"] == 50.0  # 1 of 2 requests
    assert summary["input_tokens"] == 700
    assert "| LLM calls hit by a 429 | 33.3 % |" in markdown(summary)


def test_an_empty_store_gives_zeros():
    assert summarize([])["calls_with_429_pct"] == 0.0
