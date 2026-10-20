"""Tests for the retrieval metrics and the question set (no network)."""

import json

import pytest

from course.notions import load_catalog
from eval.eval_retrieval import (
    first_relevant_rank,
    hit_at,
    reciprocal_rank,
    summarize,
)
from eval.questions import load_questions


def test_first_relevant_rank_is_one_based_and_none_when_missing():
    assert first_relevant_rank([300, 281, 281], [281, 282]) == 2
    assert first_relevant_rank([300, 301], [281]) is None


@pytest.mark.parametrize(
    ("rank", "hit", "rr"),
    [(1, 1.0, 1.0), (4, 1.0, 0.25), (5, 0.0, 0.2), (11, 0.0, 0.0), (None, 0.0, 0.0)],
)
def test_hit_at_4_and_reciprocal_rank_at_10(rank, hit, rr):
    assert hit_at(rank) == hit
    assert reciprocal_rank(rank) == pytest.approx(rr)


def test_summarize_by_hand():
    # ranks 1, 2, None, 5 -> hit@4 = 2/4 ; MRR = (1 + 0.5 + 0 + 0.2) / 4 = 0.425
    assert summarize([1, 2, None, 5]) == {"n": 4, "hit@4": 0.5, "mrr@10": 0.425}


def test_question_set_follows_d3():
    questions = load_questions()
    ids = [q.id for q in questions.dev + questions.test] + [
        t.id for t in questions.traps
    ]
    assert len(ids) == len(set(ids)) == 35
    assert all(q.en and q.fr for q in questions.dev + questions.test)


def test_question_notions_and_pages_exist():
    questions = load_questions()
    notion_ids = {notion.id for notion in load_catalog().notions}
    for question in questions.dev + questions.test:
        assert question.notion is None or question.notion in notion_ids
        assert all(275 <= page <= 386 for page in question.pages)


def test_saved_reports_are_valid_json():
    from eval.eval_retrieval import RESULTS_DIR

    for path in RESULTS_DIR.glob("*.json"):
        report = json.loads(path.read_text(encoding="utf-8"))
        assert {"en", "fr", "split", "setting"} <= report.keys()
