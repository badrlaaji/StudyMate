"""Tests for PDF page cleaning (synthetic pages, no PDF needed)."""

import json

import pytest

from rag.ingest import (
    chapter_bounds,
    clean_page,
    is_running_footer,
    normalize_line,
    repeated_lines,
    section_for_page,
    write_jsonl,
)

EVEN = "266     6 • Decision-Making Using Machine Learning Basics"
ODD = "6.1 • What Is Machine Learning?     267"
ACCESS = "Access for free at openstax.org"


def test_normalize_line_ignores_digits_and_spaces():
    assert normalize_line("  266     6 • Basics ") == "# # • Basics"


def test_repeated_lines_needs_strictly_more_than_half():
    pages = [f"{ACCESS}\nbody {i}" for i in range(2)] + ["other", "other 2"]
    assert repeated_lines(pages) == set()  # 2 of 4 pages = 50 %, not more
    assert normalize_line(ACCESS) in repeated_lines(pages[:3])  # 2 of 3 pages


def test_repeated_lines_matches_page_numbers_that_change():
    pages = ["266  6 • Title\nA", "268  6 • Title\nB", "270  6 • Title\nC"]
    assert "# # • Title" in repeated_lines(pages)


@pytest.mark.parametrize("line", [EVEN, ODD, "6 • Group Project     327"])
def test_is_running_footer_true_for_book_footers(line):
    assert is_running_footer(line)


@pytest.mark.parametrize(
    "line",
    ["• 6.1.1 Summarize the differences", "6.1 What Is Machine Learning?", "k = 3"],
)
def test_is_running_footer_false_for_body_lines(line):
    assert not is_running_footer(line)


def test_clean_page_removes_footers_and_rejoins_hyphenated_words():
    text = f"The  k-\nmeans   method\n\n{EVEN}\n{ACCESS}"
    repeated = {normalize_line(ACCESS)}
    assert clean_page(text, repeated) == "The k-means method"


def test_chapter_bounds_ends_before_next_top_level_entry():
    top = [(7, "Contents"), (275, "Chapter 6 ML"), (341, "Chapter 7 DL"), (387, "C8")]
    assert chapter_bounds(top, 6, 900) == (275, 340)
    assert chapter_bounds(top, 7, 900) == (341, 386)


def test_chapter_bounds_unknown_chapter_raises():
    with pytest.raises(ValueError):
        chapter_bounds([(275, "Chapter 6 ML")], 9, 900)


def test_section_for_page_takes_last_section_started():
    sections = [(275, "Chapter Outline"), (275, "Introduction"), (276, "6.1 ML")]
    assert section_for_page(sections, 275) == "Introduction"
    assert section_for_page(sections, 283) == "6.1 ML"


def test_write_jsonl_keeps_accents(tmp_path):
    path = tmp_path / "pages.jsonl"
    write_jsonl([{"page": 1, "text": "naïve Bayes"}], path)
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "page": 1,
        "text": "naïve Bayes",
    }
