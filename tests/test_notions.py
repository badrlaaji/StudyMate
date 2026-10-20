"""Tests for the notion catalogue schema and the draft helpers (no network)."""

import pytest
from pydantic import ValidationError

from course.draft_notions import (
    NotionDraft,
    build_prompt,
    group_sections,
    notion_count,
    to_notion,
)
from course.notions import (
    NOTIONS_PATH,
    Catalog,
    KeyIdea,
    Notion,
    load_catalog,
    unknown_pages,
)

IDEA = KeyIdea(en="Entropy measures disorder.", fr="L'entropie mesure le désordre.")


def make_notion(notion_id: str = "entropy", pages: list[int] | None = None) -> Notion:
    """Build a valid notion for the tests."""
    return Notion(
        id=notion_id,
        name_en="Entropy",
        name_fr="Entropie",
        chapter=6,
        section="6.4 Decision Trees",
        pages=pages or [317],
        key_ideas=[IDEA] * 3,
    )


def make_catalog(count: int = 15) -> Catalog:
    """Build a valid catalogue with `count` distinct notions."""
    notions = [make_notion(f"notion_{i}") for i in range(count)]
    return Catalog(source="book", license="CC BY-NC-SA 4.0", notions=notions)


def test_notion_rejects_bad_id_and_too_few_ideas():
    with pytest.raises(ValidationError):
        make_notion("Bad Id")
    with pytest.raises(ValidationError):
        Notion(**{**make_notion().model_dump(), "key_ideas": [IDEA.model_dump()] * 2})


@pytest.mark.parametrize("count", [14, 26])
def test_catalog_needs_15_to_25_notions(count):
    with pytest.raises(ValidationError):
        make_catalog(count)


def test_catalog_rejects_duplicate_ids():
    notions = [make_notion("same")] * 15
    with pytest.raises(ValidationError, match="Duplicate"):
        Catalog(source="book", license="CC", notions=notions)


def test_unknown_pages_lists_pages_missing_from_the_book():
    catalog = make_catalog()
    catalog.notions[0].pages = [317, 999]
    assert unknown_pages(catalog, {317}) == {"notion_0": [999]}


def test_committed_catalog_is_valid_and_cites_chapter_6_7_pages():
    catalog = load_catalog(NOTIONS_PATH)
    pages = {page for notion in catalog.notions for page in notion.pages}
    assert 15 <= len(catalog.notions) <= 25
    assert all(275 <= page <= 386 for page in pages)


PAGES = [
    {"page": 275, "chapter": 6, "section": "Introduction", "text": "intro"},
    {"page": 276, "chapter": 6, "section": "6.1 What Is ML?", "text": "a"},
    {"page": 277, "chapter": 6, "section": "6.1 What Is ML?", "text": "b"},
    {"page": 336, "chapter": 6, "section": "Key Terms", "text": "terms"},
]


def test_group_sections_keeps_only_numbered_sections():
    groups = group_sections(PAGES)
    assert list(groups) == ["6.1 What Is ML?"]
    assert [p["page"] for p in groups["6.1 What Is ML?"]] == [276, 277]


@pytest.mark.parametrize(
    ("pages", "expected"), [(2, 1), (8, 2), (13, 3), (19, 4), (40, 4)]
)
def test_notion_count_is_one_per_five_pages_between_1_and_4(pages, expected):
    assert notion_count([{}] * pages) == expected


def test_build_prompt_contains_page_markers_and_count():
    prompt = build_prompt("6.1 What Is ML?", PAGES[1:3], 2)
    assert "[page 276]\na" in prompt and "[page 277]\nb" in prompt
    assert "exactly 2 distinct" in prompt


def test_to_notion_drops_pages_outside_the_section():
    draft = NotionDraft(
        id="ml_basics",
        name_en="Machine learning",
        name_fr="Apprentissage automatique",
        pages=[277, 276, 999],
        key_ideas=[IDEA] * 6,
    )
    notion = to_notion(draft, "6.1 What Is ML?", PAGES[1:3])
    assert notion.pages == [276, 277]
    assert len(notion.key_ideas) == 5
    assert (notion.chapter, notion.section) == (6, "6.1 What Is ML?")


def test_to_notion_without_valid_page_is_rejected():
    draft = NotionDraft(
        id="x_y", name_en="XYZ", name_fr="XYZ", pages=[999], key_ideas=[IDEA] * 3
    )
    with pytest.raises(ValidationError):
        to_notion(draft, "6.1 What Is ML?", PAGES[1:3])
