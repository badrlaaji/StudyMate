"""Tests for pair generation, decontamination and the model card (no network)."""

from types import SimpleNamespace

import numpy as np

from finetune.make_pairs import PairBatch, PairDraft, batches, build_prompt, to_records
from finetune.publish import card_text, result_rows
from finetune.train import decontaminate, to_examples

CHUNKS = [
    {"page": 290, "chunk_index": 0, "text": "k-means groups points around centroids."},
    {"page": 297, "chunk_index": 1, "text": "DBScan finds dense regions."},
]


def test_batches_keeps_order_and_last_partial_batch():
    assert batches(list(range(7)), 3) == [[0, 1, 2], [3, 4, 5], [6]]


def test_build_prompt_numbers_passages_from_one():
    prompt = build_prompt(CHUNKS)
    assert "[passage 1]\nk-means" in prompt and "[passage 2]\nDBScan" in prompt


def test_to_records_drops_unknown_passages_and_too_short_questions():
    answer = PairBatch(
        pairs=[
            PairDraft(passage=1, en="How does k-means place its centers?", fr="Court"),
            PairDraft(
                passage=3, en="Unknown passage question?", fr="Question inconnue ?"
            ),
        ]
    )
    records = to_records(answer, CHUNKS)
    assert len(records) == 1  # FR too short, passage 3 does not exist
    assert records[0]["lang"] == "en"
    assert records[0]["page"] == 290
    assert records[0]["passage"] == CHUNKS[0]["text"]


def fake_encoder(vectors: dict[str, list[float]]):
    """Fake model: returns a fixed vector per text (prefix removed)."""

    def encode(texts, normalize_embeddings=True):
        return np.array([vectors[t.removeprefix("query: ")] for t in texts])

    return SimpleNamespace(encode=encode)


def test_decontaminate_removes_near_duplicates_of_eval_questions():
    vectors = {
        "eval question": [1.0, 0.0],
        "same idea": [0.99, 0.141],  # cosine 0.99 with the eval question
        "other idea": [0.0, 1.0],
    }
    pairs = [{"question": "same idea"}, {"question": "other idea"}]
    kept = decontaminate(pairs, ["eval question"], fake_encoder(vectors))
    assert kept == [{"question": "other idea"}]


def test_to_examples_adds_both_e5_prefixes():
    example = to_examples([{"question": "Q?", "passage": "P."}])[0]
    assert example.texts == ["query: Q?", "passage: P."]


def test_model_card_has_license_rows_and_attribution():
    report = {
        "en": {"hit@4": 0.95, "mrr@10": 0.722},
        "fr": {"hit@4": 0.8, "mrr@10": 0.611},
    }
    assert result_rows({"this model": report}).splitlines() == [
        "| this model | English | 0.950 | 0.722 |",
        "| this model | French | 0.800 | 0.611 |",
    ]
    card = card_text({"this model": report}, 560, "user/model")
    assert "license: cc-by-nc-sa-4.0" in card
    assert "560 synthetic" in card and "OpenStax" in card
    assert 'SentenceTransformer("user/model")' in card
