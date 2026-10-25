"""Tests for spaced repetition (FSRS) at fixed dates and skipped questions (offline)."""

import asyncio
import random
from datetime import UTC, datetime

import httpx
import pytest
from fsrs import Rating, State

from agent.quiz import answer_status, build_quiz, quiz_order
from agent.review import (
    due_ids,
    group_reviews,
    notion_card,
    review_schedule,
    to_rating,
)
from agent.spring import fetch_history
from tests.test_agent import CATALOG, spring, spring_down
from tests.test_api import (
    QUIZ_LOGS,
    SCORES,
    client,  # noqa: F401 (fixture)
)


def at(day: int) -> datetime:
    """9:00 UTC on a day of January 2026."""
    return datetime(2026, 1, day, 9, tzinfo=UTC)


def row(notion_id: str, day: int, score: int) -> dict:
    """One row of the Spring history, as JSON."""
    return {
        "notionId": notion_id,
        "source": "QUIZ",
        "score": score,
        "createdAt": f"2026-01-{day:02d}T09:00:00Z",
    }


@pytest.mark.parametrize(
    ("score", "rating"),
    [(0, Rating.Again), (2, Rating.Again), (3, Rating.Hard), (4, Rating.Good)]
    + [(5, Rating.Good)],
)
def test_score_to_rating(score, rating):
    assert to_rating(score) == rating


def test_first_good_score_is_reviewed_two_days_later():
    card = notion_card([(at(1), 4)])
    assert card.state == State.Review
    assert card.due == at(3)


def test_intervals_grow_then_shrink_after_a_failure():
    assert notion_card([(at(1), 4), (at(3), 4)]).due == at(14)
    assert notion_card([(at(1), 4), (at(3), 4), (at(14), 1)]).due == at(16)


def test_reviews_are_replayed_in_time_order():
    assert notion_card([(at(3), 4), (at(1), 4)]).due == at(14)


def test_history_rows_are_grouped_by_notion_with_aware_times():
    grouped = group_reviews([row("k_means", 1, 4), row("overfitting", 2, 1)])
    assert grouped["k_means"] == [(at(1), 4)]
    assert grouped["overfitting"][0][0].tzinfo is not None


def test_schedule_most_urgent_first_with_days_left():
    history = [row("k_means", 1, 4), row("k_means", 3, 4), row("overfitting", 2, 1)]
    history.append(row("unknown_notion", 1, 4))  # not in the catalogue: ignored
    schedule = review_schedule(history, CATALOG, "fr", now=at(5))
    assert [r["notion_id"] for r in schedule] == ["overfitting", "k_means"]
    assert schedule[0]["name"] == "overfitting fr"
    assert schedule[0]["days_left"] == -2  # failed on the 2nd: due the 3rd, 2 days late
    assert schedule[1]["days_left"] == 9  # due on the 14th
    assert schedule[1]["reviews"] == 2
    assert due_ids(schedule) == ["overfitting"]


def test_due_notions_come_first_in_the_quiz():
    assert quiz_order(["b"], ["a", "b", "c"]) == ["b", "a", "c"]
    assert quiz_order([], ["a"]) == ["a"]


def test_fetch_history_returns_json_or_none_when_down():
    def ok(request):
        assert request.url.path == "/api/scores"
        assert request.method == "GET"
        return httpx.Response(200, json=[row("k_means", 1, 4)])

    assert asyncio.run(fetch_history(spring(ok), "data-science", "t"))[0]["score"] == 4
    assert asyncio.run(fetch_history(spring(spring_down), "data-science", "t")) is None


def test_review_endpoint_gives_a_date_per_notion(client):  # noqa: F811
    body = client.get("/review", params={"lang": "en"}).json()
    assert body["status"] == "ok"
    assert body["reviews"][0]["notion_id"] == "k_means"
    assert body["reviews"][0]["due"] == "2026-01-03T09:00:00+00:00"


def test_a_skipped_question_creates_no_review(client):  # noqa: F811
    skipped = [{"notion_id": "k_means", "answer_index": 1, "chosen_index": None}]
    body = client.post("/quiz/result", json={"answers": skipped}).json()
    assert body == {"scores": {}, "recorded": True, "skipped": 1}
    assert SCORES == []  # no score sent to Spring: neither mastery nor FSRS moves
    assert QUIZ_LOGS[0]["answers"] == [{"notionId": "k_means", "status": "SKIPPED"}]


def test_only_answered_questions_are_graded(client):  # noqa: F811
    answers = [
        {"notion_id": "k_means", "answer_index": 1, "chosen_index": 1},
        {"notion_id": "k_means", "answer_index": 0},  # skipped (no chosen_index)
    ]
    body = client.post("/quiz/result", json={"answers": answers}).json()
    assert body["scores"] == {"k_means": 5}  # 1 correct out of 1 answered
    assert len(SCORES) == 1


def test_build_quiz_asks_due_notions_before_weak_ones(monkeypatch):
    def fake_spring(request):
        if request.url.path == "/api/notions/weak":
            return httpx.Response(200, json=[{"notionId": "overfitting"}])
        return httpx.Response(200, json=[row("k_means", 1, 1)])  # due long ago

    asked = []

    async def no_pages(engine, course, notions):
        return {}

    def fake_make_quiz(notions, texts, lang, llm):
        asked.extend(notion.id for notion in notions)
        return []

    monkeypatch.setattr("agent.quiz.page_texts", no_pages)
    monkeypatch.setattr("agent.quiz.make_quiz", fake_make_quiz)
    http = spring(fake_spring)
    questions, degraded = asyncio.run(
        build_quiz(
            None,
            http,
            "data-science",
            CATALOG,
            3,
            "en",
            rng=random.Random(0),
            token="t",
        )
    )
    assert asked[:2] == ["k_means", "overfitting"] and len(asked) == 3
    assert questions == [] and degraded is False


@pytest.mark.parametrize(
    ("chosen", "status"), [(None, "SKIPPED"), (2, "CORRECT"), (0, "INCORRECT")]
)
def test_answer_status(chosen, status):
    assert answer_status(chosen, 2) == status
