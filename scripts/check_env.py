"""Step 0 checks: torch CPU, e5, Postgres + pgvector, Gemini structured output.

Usage: uv run python -m scripts.check_env [torch|e5|db|gemini|all]
"""

import asyncio
import sys
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from pydantic import BaseModel

from config import get_env

E5_MODEL = "intfloat/multilingual-e5-small"
E5_QUERY = "query: What is overfitting in machine learning?"
E5_PASSAGES = [
    "passage: Overfitting happens when a model learns the noise of the training data "
    "and performs poorly on new data.",
    "passage: A bar chart displays categorical data with rectangular bars.",
]
GEMINI_PROMPT = "Give the capital city of Morocco and one short fact about it."


class CapitalFact(BaseModel):
    """Expected shape of the Gemini check answer."""

    country: str
    capital: str
    fact: str


def asyncpg_args(url: str) -> tuple[str, str | None]:
    """Split a SQLAlchemy URL into a plain asyncpg DSN and its ssl mode."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    dsn = urlunsplit(("postgresql", parts.netloc, parts.path, "", ""))
    return dsn, query.get("ssl")


def check_torch() -> None:
    """Print torch version and confirm the CPU-only build."""
    import torch

    print("torch", torch.__version__, "| cuda available:", torch.cuda.is_available())


def check_e5() -> None:
    """Embed one query and two passages with e5, print cosine similarities."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(E5_MODEL, device="cpu")
    query = model.encode([E5_QUERY], normalize_embeddings=True)
    passages = model.encode(E5_PASSAGES, normalize_embeddings=True)
    scores = (query @ passages.T)[0]
    print("e5 dim:", query.shape[1])
    for text, score in zip(E5_PASSAGES, scores, strict=True):
        print(f"  {score:.4f}  {text[:60]}")


async def db_check(url: str) -> None:
    """Connect with asyncpg, enable pgvector, print versions."""
    import asyncpg

    dsn, ssl = asyncpg_args(url)
    conn = await asyncpg.connect(dsn, ssl=ssl)
    try:
        print(await conn.fetchval("SELECT version()"))
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        version = await conn.fetchval(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        )
        print("CREATE EXTENSION vector: OK | pgvector", version)
        ssl_on = await conn.fetchval(
            "SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()"
        )
        print("ssl in use:", ssl_on)
    finally:
        await conn.close()


def check_db() -> None:
    """Run the database check (Neon or local) in an event loop."""
    asyncio.run(db_check(get_env("DATABASE_URL")))


def check_gemini() -> None:
    """Ask Gemini for a Pydantic-validated answer; fall back to another method."""
    from agent.llm import get_llm

    llm = get_llm()
    for method in ("json_schema", "function_calling"):
        try:
            result = llm.with_structured_output(CapitalFact, method=method).invoke(
                GEMINI_PROMPT
            )
            print(f"method={method} -> {type(result).__name__}: {result.model_dump()}")
            return
        except Exception as error:  # report and try the next method
            print(f"method={method} failed: {type(error).__name__}: {error}")
    raise RuntimeError("Structured output failed with every method.")


CHECKS = {"torch": check_torch, "e5": check_e5, "db": check_db, "gemini": check_gemini}


def main(names: list[str]) -> None:
    """Run the requested checks (all by default)."""
    selected = list(CHECKS) if not names or names == ["all"] else names
    for name in selected:
        print(f"== {name}")
        CHECKS[name]()


if __name__ == "__main__":
    main(sys.argv[1:])
