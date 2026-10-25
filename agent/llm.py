"""LLM provider factory and the single structured-call helper."""

import re
import time
from collections.abc import Callable
from pathlib import Path

from langchain_core.exceptions import ModelAPIError, ModelRateLimitError
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from agent.cache import CACHE_DIR, cache_get, cache_key, cache_put
from agent.tracing import set_attributes, span
from config import ROOT, get_env

# Lowest thinking level, for speed (values listed by langchain-google-genai 4.4.2).
THINKING_LEVEL = "minimal"
# 1 = a single request, no SDK retry: 429 handling is done below.
MAX_RETRIES = 1
TIMEOUT_S = 60.0
# 429 (quota) or 5xx (overloaded) without a suggested delay: wait, then 1 retry.
DEFAULT_WAIT_S = 60.0
RETRYABLE = (ModelRateLimitError, ModelAPIError)
# REST errors say "'retryDelay': '37s'", gRPC ones "retry_delay { seconds: 37".
RETRY_DELAY = re.compile(r"retry_?delay\D{0,20}?(\d+(?:\.\d+)?)", re.IGNORECASE)
QUOTA_MESSAGE = (
    "LLM unavailable twice in a row (429 quota or 5xx overload). Wait a minute, or "
    "until the daily quota resets (midnight Pacific time), then run again: cached "
    "answers are kept."
)
OFFLINE_MESSAGE = (
    "LLM_OFFLINE=1 and no recorded answer for this prompt: the prompt changed. "
    "Re-record the answers with: uv run python -m eval.regression record"
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


def cache_folder() -> Path:
    """LLM_CACHE_DIR (relative to the project) if set, else .cache/llm."""
    return ROOT / get_env("LLM_CACHE_DIR", str(CACHE_DIR))


def is_offline() -> bool:
    """True when LLM calls are forbidden (CI): only recorded answers are used."""
    return get_env("LLM_OFFLINE", "0") == "1"


def parse_output[T: BaseModel](output) -> tuple[T, dict]:
    """Structured output read with include_raw: the object, and the token counts."""
    if isinstance(output, BaseModel):  # test fakes return the object itself
        return output, {}
    if output.get("parsing_error") is not None or output.get("parsed") is None:
        raise output.get("parsing_error") or ValueError("No structured output.")
    usage = getattr(output.get("raw"), "usage_metadata", None) or {}
    tokens = {
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
    }
    return output["parsed"], tokens


def error_kind(error: Exception) -> str:
    """ "429" when the quota is reached, "5xx" when the server is overloaded."""
    return "429" if isinstance(error, ModelRateLimitError) else "5xx"


def call_attributes(errors: list[str], outcome: str, tokens: dict) -> dict:
    """What a trace keeps about one live LLM call (never the user's identity)."""
    counts = {"errors_429": errors.count("429"), "errors_5xx": errors.count("5xx")}
    return {"cached": False, "outcome": outcome, **counts, **tokens}


def invoke_structured[T: BaseModel](
    schema: type[T],
    prompt: str,
    llm: BaseChatModel | None = None,
    cache_dir: Path | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Ask the LLM for a `schema` object: disk cache, then one retry after 429/5xx.

    Traced when tracing is on: latency (span time), tokens, cache hit, 429/5xx errors.
    """
    cache_dir = cache_dir or cache_folder()
    model = get_env("LLM_MODEL")
    key = cache_key(model, prompt)
    info = {"model": model, "prompt_chars": len(prompt)}
    with span(schema.__name__, "CHAT_MODEL", info) as current:
        cached = cache_get(key, cache_dir)
        if cached is not None:
            set_attributes(current, {"cached": True})
            return schema.model_validate(cached)
        if is_offline():
            raise RuntimeError(OFFLINE_MESSAGE)
        runnable = (llm or get_llm()).with_structured_output(schema, include_raw=True)
        errors: list[str] = []
        try:
            output = runnable.invoke(prompt)
        except RETRYABLE as error:
            errors.append(error_kind(error))
            sleep(retry_delay(error))
            try:
                output = runnable.invoke(prompt)
            except RETRYABLE as second_error:
                errors.append(error_kind(second_error))
                set_attributes(current, call_attributes(errors, "failed", {}))
                raise RuntimeError(QUOTA_MESSAGE) from second_error
        result, tokens = parse_output(output)
        set_attributes(current, call_attributes(errors, "ok", tokens))
    cache_put(key, result.model_dump(), cache_dir)
    return result
