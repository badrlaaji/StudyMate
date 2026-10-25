"""Tests for the LLM factory, the disk cache and the 429 policy (no network)."""

from types import SimpleNamespace

import pytest
from langchain_core.exceptions import ModelAPIError, ModelRateLimitError
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from agent.cache import cache_get, cache_key, cache_put
from agent.llm import DEFAULT_WAIT_S, get_llm, invoke_structured, retry_delay


class Answer(BaseModel):
    """Tiny schema for the fake LLM."""

    text: str


def fake_llm(outcomes: list):
    """Return a fake chat model whose invoke() replays `outcomes` (value or error)."""
    calls = []

    def invoke(prompt):
        calls.append(prompt)
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    runnable = SimpleNamespace(invoke=invoke)
    return SimpleNamespace(with_structured_output=lambda schema, **_: runnable), calls


@pytest.fixture(autouse=True)
def gemini_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-test-model")
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")


def test_get_llm_builds_gemini_from_env():
    llm = get_llm()
    assert isinstance(llm, ChatGoogleGenerativeAI)
    assert llm.model.endswith("gemini-test-model")
    assert llm.max_retries == 1


def test_get_llm_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "other")
    with pytest.raises(ValueError, match="other"):
        get_llm()


def test_cache_key_depends_on_model_and_prompt():
    assert cache_key("m", "p") == cache_key("m", "p")
    assert cache_key("m1", "p") != cache_key("m2", "p")


def test_cache_roundtrip_and_miss(tmp_path):
    assert cache_get("missing", tmp_path) is None
    cache_put("k", {"text": "réponse"}, tmp_path)
    assert cache_get("k", tmp_path) == {"text": "réponse"}


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("429 RESOURCE_EXHAUSTED {'retryDelay': '37s'}", 37.0),
        ("429 [retry_delay { seconds: 12 }]", 12.0),
        ("429 RESOURCE_EXHAUSTED", DEFAULT_WAIT_S),
    ],
)
def test_retry_delay_reads_both_formats(message, expected):
    assert retry_delay(Exception(message)) == expected


def test_invoke_structured_second_call_comes_from_cache(tmp_path):
    llm, calls = fake_llm([Answer(text="hi")])
    first = invoke_structured(Answer, "q", llm=llm, cache_dir=tmp_path)
    second = invoke_structured(Answer, "q", llm=llm, cache_dir=tmp_path)
    assert first == second == Answer(text="hi")
    assert len(calls) == 1


def test_invoke_structured_waits_then_retries_once_after_429(tmp_path):
    error = ModelRateLimitError("429 {'retryDelay': '5s'}")
    llm, calls = fake_llm([error, Answer(text="ok")])
    waits = []
    result = invoke_structured(
        Answer, "q", llm=llm, cache_dir=tmp_path, sleep=waits.append
    )
    assert result == Answer(text="ok")
    assert waits == [5.0]
    assert len(calls) == 2


def test_invoke_structured_two_429_give_a_clear_error(tmp_path):
    error = ModelRateLimitError("429")
    llm, _ = fake_llm([error, error])
    with pytest.raises(RuntimeError, match="twice"):
        invoke_structured(
            Answer, "q", llm=llm, cache_dir=tmp_path, sleep=lambda s: None
        )


def test_invoke_structured_retries_once_after_503_overload(tmp_path):
    llm, calls = fake_llm(
        [ModelAPIError("503 UNAVAILABLE high demand"), Answer(text="ok")]
    )
    waits = []
    result = invoke_structured(
        Answer, "q", llm=llm, cache_dir=tmp_path, sleep=waits.append
    )
    assert result == Answer(text="ok")
    assert waits == [DEFAULT_WAIT_S]
    assert len(calls) == 2
