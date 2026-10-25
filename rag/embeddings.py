"""e5 embeddings: the only place that adds the "query: " / "passage: " prefixes."""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from config import get_env

BASE_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DIM = 384
QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "
BATCH_SIZE = 32


def model_name() -> str:
    """Return EMBEDDING_MODEL from .env (base e5 by default)."""
    return get_env("EMBEDDING_MODEL", BASE_MODEL)


def with_prefix(texts: list[str], prefix: str) -> list[str]:
    """Prepend the e5 prefix to every text."""
    return [prefix + text for text in texts]


@lru_cache(maxsize=2)
def load_model(name: str) -> SentenceTransformer:
    """Load a sentence-transformers model on CPU, once per process."""
    return SentenceTransformer(name, device="cpu")


def embed_passages(texts: list[str], model=None) -> list[list[float]]:
    """Embed book passages ("passage: " prefix), unit-length vectors."""
    model = model or load_model(model_name())
    vectors = model.encode(
        with_prefix(texts, PASSAGE_PREFIX),
        normalize_embeddings=True,
        batch_size=BATCH_SIZE,
    )
    return vectors.tolist()


def embed_query(question: str, model=None) -> list[float]:
    """Embed one user question ("query: " prefix), unit-length vector."""
    model = model or load_model(model_name())
    vectors = model.encode(
        with_prefix([question], QUERY_PREFIX), normalize_embeddings=True
    )
    return vectors[0].tolist()
