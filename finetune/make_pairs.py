"""Generate (question, passage) training pairs with the LLM, in English and French (F1).

Usage: uv run python -m finetune.make_pairs
About 5 chunks per LLM call; answers are cached, so a rerun costs no quota.
"""

import os
import time

from pydantic import BaseModel

from agent.cache import cache_get, cache_key
from agent.llm import invoke_structured
from config import ROOT, get_env
from course.courses import pages_path
from eval.questions import EVAL_COURSE
from rag.chunking import chunk_pages
from rag.ingest import read_jsonl, write_jsonl

PAIRS_PATH = ROOT / "data" / "pairs" / "pairs.jsonl"
CHUNKS_PER_CALL = 5
PAUSE_S = float(os.environ.get("LLM_PAUSE_S", "6"))
MIN_QUESTION_CHARS = 15

PROMPT = """You write study questions for passages of a data science textbook.
For EACH passage below, write one question a student could ask whose answer is in
that passage: one in English (en) and the same question in French (fr).

Rules:
- Paraphrase like a real student; do not copy phrases from the passage.
- The question must make sense alone (no "this passage", no "the example above").
- If a passage is only code, a table of numbers or a reference list, ask about the
  idea it illustrates.
- French with all its accents. Answer with the passage numbers as given.

{passages}"""


class PairDraft(BaseModel):
    """Questions written by the LLM for one passage."""

    passage: int
    en: str
    fr: str


class PairBatch(BaseModel):
    """LLM answer for one batch of passages."""

    pairs: list[PairDraft]


def batches(items: list, size: int) -> list[list]:
    """Split a list into consecutive batches of `size`."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def build_prompt(chunks: list[dict]) -> str:
    """Number the passages of one batch, starting at 1."""
    text = "\n\n".join(
        f"[passage {n}]\n{chunk['text']}" for n, chunk in enumerate(chunks, start=1)
    )
    return PROMPT.format(passages=text)


def to_records(answer: PairBatch, chunks: list[dict]) -> list[dict]:
    """Keep valid answers (known passage, real question) as one record per language."""
    records = []
    for pair in answer.pairs:
        if not 1 <= pair.passage <= len(chunks):
            continue  # the LLM cited a passage that was not sent
        chunk = chunks[pair.passage - 1]
        for lang in ("en", "fr"):
            question = getattr(pair, lang).strip()
            if len(question) >= MIN_QUESTION_CHARS:
                records.append(
                    {
                        "page": chunk["page"],
                        "chunk_index": chunk["chunk_index"],
                        "lang": lang,
                        "question": question,
                        "passage": chunk["text"],
                    }
                )
    return records


def main() -> None:
    """Generate pairs for every chunk and write data/pairs/pairs.jsonl."""
    chunks = chunk_pages(read_jsonl(pages_path(EVAL_COURSE)))  # the reference course
    records, calls = [], 0
    for batch in batches(chunks, CHUNKS_PER_CALL):
        prompt = build_prompt(batch)
        cached = cache_get(cache_key(get_env("LLM_MODEL"), prompt)) is not None
        records.extend(to_records(invoke_structured(PairBatch, prompt), batch))
        if not cached:
            calls += 1
            time.sleep(PAUSE_S)
    write_jsonl(records, PAIRS_PATH)
    covered = len({(r["page"], r["chunk_index"]) for r in records})
    print(
        f"{len(records)} pairs for {covered}/{len(chunks)} chunks ({calls} LLM calls)"
    )


if __name__ == "__main__":
    main()
