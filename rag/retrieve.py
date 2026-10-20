"""Retrieve the top-k book chunks for a question (EN or FR).

Usage: uv run python -m rag.retrieve "What is overfitting?"   (default course)
"""

import asyncio
import sys

from sqlalchemy.ext.asyncio import AsyncEngine

from course.courses import load_registry
from rag.embeddings import embed_query, model_name
from rag.store import get_engine, search

TOP_K = 4


async def retrieve(
    question: str, engine: AsyncEngine, course: str, k: int = TOP_K, model=None
) -> list[dict]:
    """Embed the question ("query: ") and return the k closest chunks of a course."""
    vector = embed_query(question, model)
    return await search(engine, vector, course, model_name(), k)


async def print_results(question: str) -> None:
    """Run one search and print page, score and the start of each chunk."""
    engine = get_engine()
    try:
        course = load_registry().default
        for hit in await retrieve(question, engine, course):
            preview = hit["text"][:90].replace("\n", " ")
            print(
                f"p.{hit['page']}  {hit['score']:.4f}  {hit['section']}\n    {preview}"
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(print_results(" ".join(sys.argv[1:])))
