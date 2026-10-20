"""Tests for the course registry and per-course paths (no network)."""

import pytest
from pydantic import ValidationError

from course.courses import (
    Course,
    Registry,
    get_course,
    load_registry,
    notions_path,
    pages_path,
    pdf_path,
)
from course.notions import load_catalog
from rag.ingest import page_ranges

TOP = [(275, "Chapter 6 Decision-Making"), (341, "Chapter 7 Deep Learning")]


def make_course(**changes) -> Course:
    """Build a valid course entry, with some fields changed."""
    fields = {
        "id": "statistics",
        "title": "Introductory Statistics 2e",
        "scope_en": "Chapter 12",
        "scope_fr": "Chapitre 12",
        "pdf_url": "https://example.org/stats.pdf",
        "book_url": "https://example.org",
        "attribution": "Authors",
        "license": "CC BY-NC-SA 4.0",
        "chapters": [12],
    }
    return Course(**{**fields, **changes})


def test_committed_registry_is_valid_and_every_catalog_loads():
    registry = load_registry()
    assert registry.default == "data-science"
    for course in registry.courses:
        if notions_path(course.id).exists():
            assert load_catalog(notions_path(course.id)).license == course.license


@pytest.mark.parametrize(
    "changes",
    [
        {"id": "Bad Id"},
        {"pdf_url": "http://example.org/a.pdf"},  # https only
        {"chapters": [], "pages": []},  # nothing to study
        {"pages": [10, 20]},  # chapters and pages together
        {"chapters": [], "pages": [20, 10]},  # first > last
        {"chapters": [], "pages": [10]},
    ],
)
def test_course_rejects_bad_entries(changes):
    with pytest.raises(ValidationError):
        make_course(**changes)


def test_registry_rejects_duplicate_ids_and_unknown_default():
    with pytest.raises(ValidationError, match="Duplicate"):
        Registry(default="statistics", courses=[make_course(), make_course()])
    with pytest.raises(ValidationError, match="Unknown default"):
        Registry(default="missing", courses=[make_course()])


def test_get_course_by_id_or_default():
    registry = Registry(
        default="statistics", courses=[make_course(), make_course(id="biology")]
    )
    assert get_course(registry).id == "statistics"
    assert get_course(registry, "biology").id == "biology"
    with pytest.raises(KeyError):
        get_course(registry, "missing")


def test_paths_are_separate_per_course():
    assert pdf_path("statistics").name == "statistics.pdf"
    assert pages_path("statistics").parent.name == "statistics"
    assert notions_path("statistics").name == "statistics.json"
    assert pdf_path("statistics") != pdf_path("data-science")


def test_page_ranges_from_chapters_or_plain_pages():
    chapters = make_course(id="data-science", chapters=[6, 7])
    assert page_ranges(chapters, TOP) == [(6, 275, 340), (7, 341, 341)]
    pages = make_course(chapters=[], pages=[12, 40])
    assert page_ranges(pages, []) == [(0, 12, 40)]
