"""Plan branch, without LLM: weak notions sorted by score, with pages to review."""

from course.notions import Catalog

PLAN_SIZE = 5


def build_plan(weak: list[dict], catalog: Catalog, lang: str) -> list[dict]:
    """Weakest first: notion, score, pages to re-read and a quiz action."""
    by_id = {notion.id: notion for notion in catalog.notions}
    rows = []
    for item in weak:
        notion = by_id.get(item["notionId"])
        if notion is None:
            continue  # unknown id: the catalogue is the single source of truth
        rows.append(
            {
                "notion_id": notion.id,
                "name": notion.name_fr if lang == "fr" else notion.name_en,
                "score": round(item["average"], 2),
                "pages": notion.pages,
                "action": "quiz",
            }
        )
    return sorted(rows, key=lambda row: row["score"])
