"""PostgreSQL + pgvector storage of chunks (Neon in dev), plain SQL."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from config import get_env
from rag.embeddings import DIM

SCHEMA_SQL = [
    "CREATE EXTENSION IF NOT EXISTS vector",
    f"""CREATE TABLE IF NOT EXISTS chunks (
        id SERIAL PRIMARY KEY,
        embedding_model TEXT NOT NULL,
        page INTEGER NOT NULL,
        chapter INTEGER NOT NULL,
        section TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        text TEXT NOT NULL,
        embedding vector({DIM}) NOT NULL
    )""",
]
INSERT_SQL = text(
    "INSERT INTO chunks (embedding_model, page, chapter, section, chunk_index, text, "
    "embedding) VALUES (:embedding_model, :page, :chapter, :section, :chunk_index, "
    ":text, CAST(:embedding AS vector))"
)
# <=> is the pgvector cosine distance: 0 = same direction. Exact scan, no index:
# a few hundred rows are searched in milliseconds and the result is exact.
SEARCH_SQL = text(
    "SELECT page, chapter, section, chunk_index, text, "
    "1 - (embedding <=> CAST(:query AS vector)) AS score "
    "FROM chunks WHERE embedding_model = :model "
    "ORDER BY embedding <=> CAST(:query AS vector) LIMIT :k"
)


def get_engine(url: str | None = None) -> AsyncEngine:
    """Create the async engine (asyncpg driver); pre-ping wakes a sleeping Neon."""
    return create_async_engine(url or get_env("DATABASE_URL"), pool_pre_ping=True)


def to_pgvector(vector: list[float]) -> str:
    """Format a vector as pgvector text input: "[0.1,0.2,...]"."""
    return "[" + ",".join(f"{value:.7g}" for value in vector) + "]"


async def create_schema(engine: AsyncEngine) -> None:
    """Enable pgvector and create the chunks table if needed."""
    async with engine.begin() as conn:
        for statement in SCHEMA_SQL:
            await conn.execute(text(statement))


async def replace_chunks(
    engine: AsyncEngine, model: str, chunks: list[dict], vectors: list[list[float]]
) -> int:
    """Replace all chunks of one embedding model in a single transaction."""
    rows = [
        {**chunk, "embedding_model": model, "embedding": to_pgvector(vector)}
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    async with engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM chunks WHERE embedding_model = :model"), {"model": model}
        )
        if rows:  # executing an INSERT with an empty list is an error
            await conn.execute(INSERT_SQL, rows)
    return len(rows)


async def count_chunks(engine: AsyncEngine, model: str) -> int:
    """Return how many chunks are stored for one embedding model."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT count(*) FROM chunks WHERE embedding_model = :model"),
            {"model": model},
        )
        return result.scalar_one()


async def search(
    engine: AsyncEngine, query_vector: list[float], model: str, k: int
) -> list[dict]:
    """Return the k chunks closest to the query (cosine), best first."""
    params = {"query": to_pgvector(query_vector), "model": model, "k": k}
    async with engine.connect() as conn:
        result = await conn.execute(SEARCH_SQL, params)
        return [dict(row) for row in result.mappings()]
