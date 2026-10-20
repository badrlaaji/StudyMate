"""Fine-tune e5 on the generated pairs with MultipleNegativesRankingLoss (F1), on CPU.

Usage: uv run python -m finetune.train
Uses old_fit (plain PyTorch loop): the Trainer needs `accelerate` (not in our stack).
"""

import json
import random
import time

import torch
from sentence_transformers import InputExample, SentenceTransformer
from sentence_transformers.sentence_transformer.datasets import NoDuplicatesDataLoader
from sentence_transformers.sentence_transformer.losses import (
    MultipleNegativesRankingLoss,
)

from config import ROOT
from eval.questions import load_questions
from finetune.make_pairs import PAIRS_PATH
from rag.embeddings import BASE_MODEL, PASSAGE_PREFIX, QUERY_PREFIX
from rag.ingest import read_jsonl

MODEL_DIR = ROOT / "models" / "e5-small-studymate"
INFO_PATH = MODEL_DIR / "training_info.json"
EPOCHS = 2
BATCH_SIZE = 16  # fits in 8 GB of RAM; more in-batch negatives would need more
LEARNING_RATE = 2e-5
WARMUP_RATIO = 0.1
SEED = 42
# A training question this close to an eval question is removed (decontamination).
NEAR_DUPLICATE = 0.95


def eval_texts() -> list[str]:
    """Return every dev and test question, in both languages."""
    questions = load_questions()
    return [
        getattr(q, lang)
        for q in questions.dev + questions.test
        for lang in ("en", "fr")
    ]


def decontaminate(
    pairs: list[dict], forbidden: list[str], model, threshold: float = NEAR_DUPLICATE
) -> list[dict]:
    """Drop pairs whose question is a near-duplicate of an evaluation question."""

    def embed(texts: list[str]):
        return model.encode(
            [QUERY_PREFIX + t for t in texts], normalize_embeddings=True
        )

    similarity = embed([p["question"] for p in pairs]) @ embed(forbidden).T
    return [
        pair
        for pair, row in zip(pairs, similarity, strict=True)
        if row.max() < threshold
    ]


def to_examples(pairs: list[dict]) -> list[InputExample]:
    """Turn pairs into (query, passage) examples with the e5 prefixes."""
    return [
        InputExample(
            texts=[QUERY_PREFIX + p["question"], PASSAGE_PREFIX + p["passage"]]
        )
        for p in pairs
    ]


def main() -> None:
    """Decontaminate, train and save the fine-tuned model."""
    random.seed(SEED)
    torch.manual_seed(SEED)
    model = SentenceTransformer(BASE_MODEL, device="cpu")
    pairs = read_jsonl(PAIRS_PATH)
    kept = decontaminate(pairs, eval_texts(), model)
    removed = len(pairs) - len(kept)
    print(f"pairs: {len(pairs)} generated, {removed} removed, {len(kept)} kept")
    loader = NoDuplicatesDataLoader(to_examples(kept), batch_size=BATCH_SIZE)
    loss = MultipleNegativesRankingLoss(model)
    steps = len(loader) * EPOCHS
    start = time.perf_counter()
    model.old_fit(
        train_objectives=[(loader, loss)],
        epochs=EPOCHS,
        warmup_steps=int(steps * WARMUP_RATIO),
        optimizer_params={"lr": LEARNING_RATE},
        show_progress_bar=False,
    )
    seconds = round(time.perf_counter() - start)
    print(f"trained {steps} steps in {seconds} s")
    model.save(str(MODEL_DIR))
    info = {"pairs_generated": len(pairs), "pairs_removed": removed}
    info |= {"pairs_kept": len(kept), "steps": steps, "seconds": seconds}
    INFO_PATH.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(f"saved to {MODEL_DIR}")


if __name__ == "__main__":
    main()
