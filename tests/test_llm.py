"""Tests for the LLM factory (builds the client, never calls the API)."""

import pytest
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.llm import get_llm


def test_get_llm_builds_gemini_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-test-model")
    monkeypatch.setenv("GOOGLE_API_KEY", "fake-key")
    llm = get_llm()
    assert isinstance(llm, ChatGoogleGenerativeAI)
    assert llm.model.endswith("gemini-test-model")
    assert llm.max_retries == 1


def test_get_llm_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "other")
    with pytest.raises(ValueError, match="other"):
        get_llm()
