"""Tests for the offline replay and the regression gate (no network)."""

import asyncio
from types import SimpleNamespace

import pytest

from agent.cache import cache_key, cache_put
from agent.llm import OFFLINE_MESSAGE, cache_folder, invoke_structured
from config import ROOT
from eval import eval_answers
from eval.regression import failures, flatten, markdown, one_line
from tests.test_llm import Answer, fake_llm


@pytest.fixture(autouse=True)
def offline_env(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "gemini-test-model")
    monkeypatch.setenv("LLM_OFFLINE", "1")


def test_offline_replays_a_recorded_answer(tmp_path):
    cache_put(cache_key("gemini-test-model", "q"), {"text": "recorded"}, tmp_path)
    llm, calls = fake_llm([Answer(text="live")])
    assert (
        invoke_structured(Answer, "q", llm=llm, cache_dir=tmp_path).text == "recorded"
    )
    assert calls == []


def test_offline_never_calls_the_llm_on_a_miss(tmp_path):
    llm, calls = fake_llm([Answer(text="live")])
    with pytest.raises(RuntimeError, match="LLM_OFFLINE=1"):
        invoke_structured(Answer, "new prompt", llm=llm, cache_dir=tmp_path)
    assert calls == []


def test_cache_folder_follows_llm_cache_dir(monkeypatch):
    monkeypatch.setenv("LLM_CACHE_DIR", "eval/replay")
    assert cache_folder() == ROOT / "eval" / "replay"


def fake_app(error: Exception | None = None, state: dict | None = None):
    """An object with the graph's ainvoke(): raise `error` or return `state`."""

    async def ainvoke(message):
        if error:
            raise error
        return state

    return SimpleNamespace(ainvoke=ainvoke)


def test_replay_miss_counts_as_a_wrong_answer():
    app = fake_app(RuntimeError(OFFLINE_MESSAGE))
    row = asyncio.run(eval_answers.run_one(app, "test01", "q", [10], 0))
    assert row["status"] == "replay_miss"
    assert row["correct"] is False


def test_online_quota_error_still_stops_the_run(monkeypatch):
    monkeypatch.setenv("LLM_OFFLINE", "0")
    app = fake_app(RuntimeError("quota"))
    with pytest.raises(RuntimeError, match="quota"):
        asyncio.run(eval_answers.run_one(app, "test01", "q", [10], 0))


def reports(hit: float, correct: int) -> tuple[dict, dict]:
    """Minimal retrieval and answer reports, same values in both languages."""
    retrieval = {lang: {"hit@4": hit, "mrr@10": 0.7} for lang in ("en", "fr")}
    summary = {"correct": correct, "refused": 5, "replay_misses": 0}
    answers = {lang: {"summary": summary} for lang in ("en", "fr")}
    return retrieval, answers


def test_flatten_names_every_gated_metric():
    metrics = flatten(*reports(0.85, 18))
    assert metrics["retrieval.fr.hit@4"] == 0.85
    assert metrics["answers.en.correct"] == 18
    assert len(metrics) == 10


def test_failures_only_below_the_minimum():
    thresholds = {"retrieval.en.hit@4": 0.8, "answers.en.correct": 17}
    assert failures(flatten(*reports(0.8, 17)), thresholds) == []
    failed = failures(flatten(*reports(0.75, 17)), thresholds)
    assert failed == ["retrieval.en.hit@4: 0.75 < 0.8"]


def test_a_missing_metric_fails():
    assert failures({}, {"answers.fr.refused": 5}) == ["answers.fr.refused: None < 5"]


def test_markdown_marks_a_regression():
    table = markdown({"retrieval.en.hit@4": 0.5}, {"retrieval.en.hit@4": 0.8})
    assert "| retrieval.en.hit@4 | 0.5 ❌ | 0.8 |" in table


def test_one_line_keeps_every_metric():
    assert one_line({"a": 1, "b": 0.5}) == "a=1 b=0.5"
