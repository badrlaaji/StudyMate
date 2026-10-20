"""Split each page into overlapping token windows (D9), e5 tokenizer."""

from functools import lru_cache

from transformers import AutoTokenizer

from rag.embeddings import BASE_MODEL, PASSAGE_PREFIX

MAX_TOKENS = 300  # D9: whole model input, prefix and special tokens included
OVERLAP = 50


@lru_cache(maxsize=1)
def get_tokenizer(name: str = BASE_MODEL):
    """Load the e5 tokenizer once (fine-tuned e5 keeps the same tokenizer)."""
    return AutoTokenizer.from_pretrained(name)


def text_budget(tokenizer) -> int:
    """Return the tokens left for the text after the prefix and special tokens."""
    prefix = len(tokenizer(PASSAGE_PREFIX, add_special_tokens=False)["input_ids"])
    return MAX_TOKENS - prefix - tokenizer.num_special_tokens_to_add()


def window_starts(n_tokens: int, size: int, overlap: int = OVERLAP) -> list[int]:
    """Return the first token of each window; consecutive windows share `overlap`."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than the window size")
    starts = [0]
    while starts[-1] + size < n_tokens:
        starts.append(starts[-1] + size - overlap)
    return starts


def input_length(tokenizer, text: str) -> int:
    """Return the real model input length: prefix + text + special tokens."""
    return len(tokenizer(PASSAGE_PREFIX + text)["input_ids"])


def chunk_page(record: dict, tokenizer, budget: int) -> list[dict]:
    """Cut one page into chunks; each chunk text is an exact slice of the page."""
    encoding = tokenizer(
        record["text"], add_special_tokens=False, return_offsets_mapping=True
    )
    offsets = encoding["offset_mapping"]
    chunks = []
    for index, start in enumerate(window_starts(len(offsets), budget)):
        end = min(start + budget, len(offsets))
        # Re-tokenizing a slice can add a token at its edge: shrink until it fits.
        while (
            end > start + 1
            and input_length(
                tokenizer, record["text"][offsets[start][0] : offsets[end - 1][1]]
            )
            > MAX_TOKENS
        ):
            end -= 1
        first_char, last_char = offsets[start][0], offsets[end - 1][1]
        chunks.append(
            {
                "page": record["page"],
                "chapter": record["chapter"],
                "section": record["section"],
                "chunk_index": index,
                "text": record["text"][first_char:last_char],
            }
        )
    return chunks


def chunk_pages(records: list[dict], tokenizer=None) -> list[dict]:
    """Chunk every page; a chunk never spans two pages."""
    tokenizer = tokenizer or get_tokenizer()
    budget = text_budget(tokenizer)
    return [
        chunk for record in records for chunk in chunk_page(record, tokenizer, budget)
    ]
