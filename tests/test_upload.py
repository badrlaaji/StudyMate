"""Tests for the upload helpers: ids, outline chapters, scope (no network)."""

import io

from pypdf import PdfWriter

from course.upload import (
    default_scope,
    pdf_title,
    read_chapters,
    selected_pages,
    slugify,
    unique_id,
)


def write_pdf(path, outline: list[tuple[str, int]], pages: int = 12) -> None:
    """Blank PDF with top-level outline entries (title, 0-based page index)."""
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    for title, index in outline:
        writer.add_outline_item(title, index)
    writer.add_metadata({"/Title": "  A Book  "})
    buffer = io.BytesIO()
    writer.write(buffer)
    path.write_bytes(buffer.getvalue())


def test_slugify_keeps_letters_digits_and_drops_accents():
    assert (
        slugify("Introduction to Python Programming!")
        == "introduction-to-python-programming"
    )
    assert slugify("Probabilités 101") == "probabilites-101"
    assert slugify("???") == "course"
    assert len(slugify("x" * 80)) == 40


def test_unique_id_adds_a_number():
    assert unique_id("stats", {"stats", "stats-2"}) == "stats-3"
    assert unique_id("bio", {"stats"}) == "bio"


def test_read_chapters_keeps_chapter_entries_and_ends_the_last_with_the_book(tmp_path):
    path = tmp_path / "book.pdf"
    write_pdf(path, [("Preface", 0), ("Chapter 1 Data", 2), ("Chapter 2 Models", 6)])
    pages, chapters = read_chapters(path)
    assert pages == 12
    assert [(c["number"], c["first"], c["last"]) for c in chapters] == [
        (1, 3, 6),
        (2, 7, 12),
    ]
    assert pdf_title(path) == "A Book"


def test_read_chapters_without_outline(tmp_path):
    path = tmp_path / "notes.pdf"
    write_pdf(path, [], pages=3)
    assert read_chapters(path) == (3, [])


def test_selected_pages_and_default_scope():
    chapters = [
        {"number": 1, "first": 3, "last": 6},
        {"number": 2, "first": 7, "last": 12},
    ]
    assert selected_pages(chapters, [1, 2], []) == 10
    assert selected_pages(chapters, [], [5, 9]) == 5
    assert default_scope([2], []) == ("Chapter 2", "Chapitre 2")
    assert default_scope([2, 1], []) == ("Chapters 1, 2", "Chapitres 1, 2")
    assert default_scope([], [5, 9]) == ("Pages 5-9", "Pages 5-9")
