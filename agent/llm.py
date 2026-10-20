"""LLM provider factory: the only place that builds the chat model."""

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from config import get_env

# Lowest thinking level, for speed (values listed by langchain-google-genai 4.4.2).
THINKING_LEVEL = "minimal"
# 1 = a single request, no SDK retry: 429 handling is done by our own code.
MAX_RETRIES = 1
TIMEOUT_S = 60.0


def get_llm() -> BaseChatModel:
    """Return the chat model set by LLM_PROVIDER and LLM_MODEL in .env."""
    provider = get_env("LLM_PROVIDER")
    if provider != "gemini":
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
    return ChatGoogleGenerativeAI(
        model=get_env("LLM_MODEL"),
        thinking_level=THINKING_LEVEL,
        max_retries=MAX_RETRIES,
        timeout=TIMEOUT_S,
    )
