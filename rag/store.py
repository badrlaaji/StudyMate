"""PostgreSQL + pgvector storage of chunks (Neon in dev), plain SQL."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from config import get_env
from course.courses import load_registry
from rag.embeddings import DIM

SCHEMA_SQL = [
    "CREATE EXTENSION IF NOT EXISTS vector",
    f"""CREATE TABLE IF NOT EXISTS chunks (
        id SERIAL PRIMARY KEY,
        course_id TEXT NOT NULL,
        embedding_model TEXT NOT NULL,
        page INTEGER NOT NULL,
        chapter INTEGER NOT NULL,
        section TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        text TEXT NOT NULL,
        embedding vector({DIM}) NOT NULL
    )""",
]
# Tables created before multi-course support held the default course only.
MIGRATION_SQL = (
    "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS course_id TEXT NOT NULL "
    "DEFAULT '{default}'"
)
INSERT_SQL = text(
    "INSERT INTO chunks (course_id, embedding_model, page, chapter, section, "
    "chunk_index, text, embedding) VALUES (:course_id, :embedding_model, :page, "
    ":chapter, :section, :chunk_index, :text, CAST(:embedding AS vector))"
)
# <=> is the pgvector cosine distance: 0 = same direction. Exact scan, no index:
# a few hundred rows are searched in milliseconds and the result is exact.
SEARCH_SQL = text(
    "SELECT page, chapter, section, chunk_index, text, "
    "1 - (embedding <=> CAST(:query AS vector)) AS score "
    "FROM chunks WHERE course_id = :course AND embedding_model = :model "
    "AND section <> ALL(:excluded) "
    "ORDER BY embedding <=> CAST(:query AS vector) LIMIT :k"
)


def get_engine(url: str | None = None) -> AsyncEngine:
    """Create the async engine (asyncpg driver); pre-ping wakes a sleeping Neon."""
    return create_async_engine(url or get_env("DATABASE_URL"), pool_pre_ping=True)


def to_pgvector(vector: list[float]) -> str:
    """Format a vector as pgvector text input: "[0.1,0.2,...]"."""
    return "[" + ",".join(f"{value:.7g}" for value in vector) + "]"


async def create_schema(engine: AsyncEngine) -> None:
    """Enable pgvector, create the chunks table, add course_id to an old table."""
    migration = MIGRATION_SQL.format(default=load_registry().default)
    async with engine.begin() as conn:
        for statement in [*SCHEMA_SQL, migration]:
            await conn.execute(text(statement))


async def replace_chunks(
    engine: AsyncEngine,
    course: str,
    model: str,
    chunks: list[dict],
    vectors: list[list[float]],
) -> int:
    """Replace the chunks of one course and model in a single transaction."""
    rows = [
        {
            **chunk,
            "course_id": course,
            "embedding_model": model,
            "embedding": to_pgvector(vector),
        }
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "DELETE FROM chunks WHERE course_id = :course "
                "AND embedding_model = :model"
            ),
            {"course": course, "model": model},
        )
        if rows:  # executing an INSERT with an empty list is an error
            await conn.execute(INSERT_SQL, rows)
    return len(rows)


async def count_chunks(engine: AsyncEngine, course: str, model: str) -> int:
    """Return how many chunks are stored for one course and embedding model."""
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT count(*) FROM chunks WHERE course_id = :course "
                "AND embedding_model = :model"
            ),
            {"course": course, "model": model},
        )
        return result.scalar_one()


async def search(
    engine: AsyncEngine,
    query_vector: list[float],
    course: str,
    model: str,
    k: int,
    excluded: tuple[str, ...] = (),
) -> list[dict]:
    """Return the k chunks of a course closest to the query (cosine), best first."""
    params = {
        "query": to_pgvector(query_vector),
        "course": course,
        "model": model,
        "k": k,
        "excluded": list(excluded),  # sections to skip (empty = keep all)
    }
    async with engine.connect() as conn:
        result = await conn.execute(SEARCH_SQL, params)
        return [dict(row) for row in result.mappings()]


async def chunks_for_pages(
    engine: AsyncEngine, course: str, pages: list[int], model: str
) -> list[dict]:
    """Return the chunks of the given pages, in page order (texts for the quiz)."""
    query = text(
        "SELECT page, chunk_index, text FROM chunks WHERE course_id = :course "
        "AND embedding_model = :model AND page = ANY(:pages) "
        "ORDER BY page, chunk_index"
    )
    params = {"course": course, "model": model, "pages": pages}
    async with engine.connect() as conn:
        result = await conn.execute(query, params)
        return [dict(row) for row in result.mappings()]
