"""Courses uploaded from the interface: PDF checks, chapters, course id and scope.

The PDF waits in data/uploads/<upload_id>.pdf until the form is sent, then moves to
data/raw/<course_id>.pdf. Nothing uploaded ever goes to Git.
"""

import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

from config import ROOT
from rag.ingest import CHAPTER_TITLE, read_outline

MAX_UPLOAD_MB = 100
MAX_STUDY_PAGES = 150  # bounds the indexing time and the Gemini quota of one course
UPLOAD_ID_PATTERN = r"^[0-9a-f]{32}$"
MAX_ID_CHARS = 40


def upload_path(upload_id: str) -> Path:
    """Temporary place of an uploaded PDF."""
    return ROOT / "data" / "uploads" / f"{upload_id}.pdf"


def slugify(title: str) -> str:
    """Course id from a title: "Probabilités 101!" -> "probabilites-101"."""
    ascii_title = (
        unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")
    return slug[:MAX_ID_CHARS].strip("-") or "course"


def unique_id(base: str, taken: set[str]) -> str:
    """Add -2, -3... until the id is free."""
    course_id, n = base, 2
    while course_id in taken:
        course_id, n = f"{base}-{n}", n + 1
    return course_id


def read_chapters(path: Path) -> tuple[int, list[dict]]:
    """Page count and the "Chapter N" entries of the outline, with their pages."""
    reader = PdfReader(path)
    book_pages = len(reader.pages)
    top, _ = read_outline(reader)
    chapters = []
    for i, (first, title) in enumerate(top):
        match = CHAPTER_TITLE.match(title)
        if match:
            last = top[i + 1][0] - 1 if i + 1 < len(top) else book_pages
            chapters.append(
                {
                    "number": int(match.group(1)),
                    "title": title,
                    "first": first,
                    "last": last,
                }
            )
    return book_pages, chapters


def pdf_title(path: Path) -> str:
    """Title stored in the PDF metadata, or "" if there is none."""
    metadata = PdfReader(path).metadata
    return (metadata.title or "").strip() if metadata else ""


def selected_pages(chapters: list[dict], numbers: list[int], pages: list[int]) -> int:
    """How many pages the chosen chapters (or the [first, last] range) cover."""
    if pages:
        return pages[1] - pages[0] + 1
    return sum(c["last"] - c["first"] + 1 for c in chapters if c["number"] in numbers)


def default_scope(numbers: list[int], pages: list[int]) -> tuple[str, str]:
    """Short description of the studied part, in English and French."""
    if pages:
        text = f"Pages {pages[0]}-{pages[1]}"
        return text, text
    listed = ", ".join(str(n) for n in sorted(numbers))
    if len(numbers) == 1:
        return f"Chapter {listed}", f"Chapitre {listed}"
    return f"Chapters {listed}", f"Chapitres {listed}"
