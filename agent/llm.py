"""LLM provider factory and the single structured-call helper."""

import re
import time
from collections.abc import Callable
from pathlib import Path

from langchain_core.exceptions import ModelRateLimitError
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from agent.cache import CACHE_DIR, cache_get, cache_key, cache_put
from config import get_env

# Lowest thinking level, for speed (values listed by langchain-google-genai 4.4.2).
THINKING_LEVEL = "minimal"
# 1 = a single request, no SDK retry: 429 handling is done below.
MAX_RETRIES = 1
TIMEOUT_S = 60.0
# 429 without a suggested delay: wait this long before the single retry.
DEFAULT_WAIT_S = 60.0
# REST errors say "'retryDelay': '37s'", gRPC ones "retry_delay { seconds: 37".
RETRY_DELAY = re.compile(r"retry_?delay\D{0,20}?(\d+(?:\.\d+)?)", re.IGNORECASE)
QUOTA_MESSAGE = (
    "LLM quota reached (429) twice in a row. Wait a minute, or until the daily "
    "quota resets (midnight Pacific time), then run again: cached answers are kept."
)


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


def retry_delay(error: Exception) -> float:
    """Return the server's suggested wait from a 429 error, else 60 s."""
    match = RETRY_DELAY.search(str(error))
    return float(match.group(1)) if match else DEFAULT_WAIT_S


def invoke_structured[T: BaseModel](
    schema: type[T],
    prompt: str,
    llm: BaseChatModel | None = None,
    cache_dir: Path = CACHE_DIR,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Ask the LLM for a `schema` object: disk cache first, one retry after a 429."""
    key = cache_key(get_env("LLM_MODEL"), prompt)
    cached = cache_get(key, cache_dir)
    if cached is not None:
        return schema.model_validate(cached)
    runnable = (llm or get_llm()).with_structured_output(schema)
    try:
        result = runnable.invoke(prompt)
    except ModelRateLimitError as error:
        sleep(retry_delay(error))
        try:
            result = runnable.invoke(prompt)
        except ModelRateLimitError as second_error:
            raise RuntimeError(QUOTA_MESSAGE) from second_error
    cache_put(key, result.model_dump(), cache_dir)
    return result
