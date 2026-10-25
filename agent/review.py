"""Spaced repetition with FSRS (py-fsrs): a review date per notion, from its scores."""

from datetime import datetime

from fsrs import Card, Rating, Scheduler

from course.notions import Catalog

# Notions are reviewed over days: no minute-long learning steps; no random fuzz, so the
# same scores always give the same dates (tests at fixed dates).
SCHEDULER = Scheduler(learning_steps=(), relearning_steps=(), enable_fuzzing=False)


def to_rating(score: int) -> Rating:
    """0-5 score -> FSRS rating: 0-2 forgotten, 3 hard, 4-5 good (never Easy)."""
    if score <= 2:
        return Rating.Again
    return Rating.Hard if score == 3 else Rating.Good


def notion_card(reviews: list[tuple[datetime, int]]) -> Card:
    """Replay the (time, score) reviews of one notion, oldest first."""
    card = Card()
    for when, score in sorted(reviews):
        card, _ = SCHEDULER.review_card(card, to_rating(score), review_datetime=when)
    return card


def group_reviews(history: list[dict]) -> dict[str, list[tuple[datetime, int]]]:
    """Spring history rows -> notion id -> [(time, score)]."""
    reviews: dict[str, list[tuple[datetime, int]]] = {}
    for row in history:
        when = datetime.fromisoformat(row["createdAt"])
        reviews.setdefault(row["notionId"], []).append((when, row["score"]))
    return reviews


def review_schedule(
    history: list[dict], catalog: Catalog, lang: str, now: datetime
) -> list[dict]:
    """Every scored notion with its next review date, the most urgent first."""
    names = {n.id: n.name_fr if lang == "fr" else n.name_en for n in catalog.notions}
    pages = {n.id: n.pages for n in catalog.notions}
    rows = []
    for notion_id, reviews in group_reviews(history).items():
        if notion_id not in names:
            continue  # unknown id: the catalogue is the single source of truth
        card = notion_card(reviews)
        rows.append(
            {
                "notion_id": notion_id,
                "name": names[notion_id],
                "due": card.due.isoformat(),
                "days_left": (card.due.date() - now.date()).days,
                "reviews": len(reviews),
                "pages": pages[notion_id],
            }
        )
    return sorted(rows, key=lambda row: row["due"])


def due_ids(schedule: list[dict]) -> list[str]:
    """Notions due today or overdue, the most overdue first."""
    return [row["notion_id"] for row in schedule if row["days_left"] <= 0]
