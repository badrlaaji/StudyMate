"""Tests for chunking, e5 prefixes and the pgvector store (fake tokenizer and model)."""

import asyncio
import os
import re
from types import SimpleNamespace

import numpy as np
import pytest

from rag.chunking import chunk_page, chunk_pages, text_budget, window_starts
from rag.embeddings import (
    PASSAGE_PREFIX,
    QUERY_PREFIX,
    embed_passages,
    embed_query,
    with_prefix,
)
from rag.store import (
    count_chunks,
    create_schema,
    get_engine,
    replace_chunks,
    search,
    to_pgvector,
)


def fake_tokenizer(text, add_special_tokens=True, return_offsets_mapping=False):
    """One token per word, with character offsets, like a fast tokenizer."""
    spans = [match.span() for match in re.finditer(r"\S+", text)]
    ids = list(range(len(spans)))
    if add_special_tokens:
        ids = [0, *ids, 0]
    encoding = {"input_ids": ids}
    if return_offsets_mapping:
        encoding["offset_mapping"] = spans
    return encoding


fake_tokenizer.num_special_tokens_to_add = lambda: 2


def page(number: int, words: int) -> dict:
    """Build a page record with `words` numbered words."""
    text = " ".join(f"w{number}_{i}" for i in range(words))
    return {"page": number, "chapter": 6, "section": "6.1 ML", "text": text}


# --- chunking ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("n_tokens", "expected"),
    [(10, [0]), (296, [0]), (297, [0, 246]), (550, [0, 246, 492])],
)
def test_window_starts_step_is_size_minus_overlap(n_tokens, expected):
    assert window_starts(n_tokens, size=296, overlap=50) == expected


def test_window_starts_rejects_overlap_bigger_than_window():
    with pytest.raises(ValueError):
        window_starts(100, size=40, overlap=50)


def test_text_budget_counts_prefix_and_special_tokens():
    # "passage:" = 1 word token, plus 2 special tokens -> 300 - 3
    assert text_budget(fake_tokenizer) == 297


def test_chunk_page_overlaps_by_50_tokens_and_slices_exactly():
    record = page(276, 110)  # windows of 80, step 80 - 50 = 30: starts 0 and 30
    chunks = chunk_page(record, fake_tokenizer, budget=80)
    words = [chunk["text"].split() for chunk in chunks]
    assert [len(w) for w in words] == [80, 80]
    assert words[0][-50:] == words[1][:50]  # overlap of 50 tokens
    assert all(chunk["text"] in record["text"] for chunk in chunks)
    assert [chunk["chunk_index"] for chunk in chunks] == [0, 1]


def test_chunk_pages_never_mixes_two_pages():
    chunks = chunk_pages([page(276, 30), page(277, 400)], tokenizer=fake_tokenizer)
    for chunk in chunks:
        assert {word.split("_")[0] for word in chunk["text"].split()} == {
            f"w{chunk['page']}"
        }
    assert [c["page"] for c in chunks].count(276) == 1


# --- e5 prefixes ------------------------------------------------------------


def fake_model(calls: list):
    """Fake sentence-transformers model that records what it encodes."""

    def encode(texts, normalize_embeddings=False, **kwargs):
        calls.append((list(texts), normalize_embeddings))
        return np.ones((len(texts), 3))

    return SimpleNamespace(encode=encode)


def test_with_prefix():
    assert with_prefix(["a", "b"], "query: ") == ["query: a", "query: b"]


def test_embed_query_uses_query_prefix_and_normalizes():
    calls = []
    vector = embed_query("What is k-means?", model=fake_model(calls))
    assert calls == [([QUERY_PREFIX + "What is k-means?"], True)]
    assert vector == [1.0, 1.0, 1.0]


def test_embed_passages_uses_passage_prefix_and_normalizes():
    calls = []
    vectors = embed_passages(["p1", "p2"], model=fake_model(calls))
    assert calls == [([PASSAGE_PREFIX + "p1", PASSAGE_PREFIX + "p2"], True)]
    assert len(vectors) == 2


# --- store ------------------------------------------------------------------


def test_to_pgvector_format():
    assert to_pgvector([0.5, -0.25, 1e-8]) == "[0.5,-0.25,1e-08]"


TEST_DB = os.environ.get("TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(not TEST_DB, reason="TEST_DATABASE_URL not set")


def unit(index: int) -> list[float]:
    """Return the 384-d unit vector along axis `index`."""
    vector = [0.0] * 384
    vector[index] = 1.0
    return vector


async def store_roundtrip() -> tuple[int, list[dict]]:
    """Store 3 chunks for a test model, search near the second one, clean up."""
    engine = get_engine(TEST_DB)
    try:
        await create_schema(engine)
        await create_schema(engine)  # idempotent
        chunks = [{**page(300 + i, 3), "chunk_index": 0} for i in range(3)]
        await replace_chunks(engine, "test-model", chunks, [unit(0), unit(1), unit(2)])
        await replace_chunks(engine, "test-model", chunks, [unit(0), unit(1), unit(2)])
        stored = await count_chunks(engine, "test-model")
        hits = await search(engine, unit(1), "test-model", k=2)
        await replace_chunks(engine, "test-model", [], [])
        return stored, hits
    finally:
        await engine.dispose()


@needs_db
def test_store_replaces_and_returns_nearest_first():
    stored, hits = asyncio.run(store_roundtrip())
    assert stored == 3  # replace, not append
    assert hits[0]["page"] == 301
    assert hits[0]["score"] == pytest.approx(1.0)
    assert hits[1]["score"] == pytest.approx(0.0)
