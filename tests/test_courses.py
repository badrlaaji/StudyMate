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
    save_uploaded,
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
        path = notions_path(course.id, course.uploaded)
        if path.exists() and not course.uploaded:
            assert load_catalog(path).license == course.license


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
    # The last chapter of the outline ends with the book (here 386 pages).
    assert page_ranges(chapters, TOP, 386) == [(6, 275, 340), (7, 341, 386)]
    pages = make_course(chapters=[], pages=[12, 40])
    assert page_ranges(pages, [], 30) == [(0, 12, 30)]  # clipped to the book


def test_uploaded_course_needs_no_link_but_a_repository_course_does():
    assert make_course(pdf_url=None, uploaded=True).uploaded
    with pytest.raises(ValidationError, match="pdf_url"):
        make_course(pdf_url=None)


def test_registry_adds_uploaded_courses_and_saves_only_them(tmp_path):
    local = tmp_path / "courses.local.json"
    registry = load_registry(local=local)  # no local file yet
    registry.courses.append(make_course(id="my-notes", pdf_url=None, uploaded=True))
    save_uploaded(registry, local)
    assert "data-science" not in local.read_text(encoding="utf-8")
    again = load_registry(local=local)
    assert [c.id for c in again.courses][-1] == "my-notes"


def test_uploaded_notions_stay_in_data():
    assert notions_path("my-notes", uploaded=True).parent.parent.name == "data"
    assert notions_path("statistics").parent.parent.name == "course"
