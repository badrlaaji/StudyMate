"""Course registry: one entry per book, and its file paths.

Two sources: course/courses.json (in Git, added with uv run python -m course.add <id>)
and data/courses.local.json (courses uploaded from the interface, never in Git).
"""

import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from config import ROOT

COURSES_PATH = ROOT / "course" / "courses.json"
LOCAL_COURSES_PATH = ROOT / "data" / "courses.local.json"
COURSE_ID_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class Course(BaseModel):
    """One course: a public PDF and the part of it that is studied."""

    id: str = Field(pattern=COURSE_ID_PATTERN)
    title: str = Field(min_length=3)
    scope_en: str
    scope_fr: str
    book_lang: Literal["en", "fr"] = "en"
    pdf_url: str | None = Field(default=None, pattern=r"^https://")
    book_url: str = ""
    attribution: str
    license: str
    chapters: list[int] = []  # "Chapter N" entries of the PDF outline
    pages: list[int] = []  # or [first, last] PDF pages when there is no such outline
    uploaded: bool = False  # added from the interface: its files stay in data/

    @model_validator(mode="after")
    def check_scope(self) -> "Course":
        """A PDF link for repository courses; exactly one of chapters / pages."""
        if not self.uploaded and not self.pdf_url:
            raise ValueError("A course of course/courses.json needs a pdf_url")
        if bool(self.chapters) == bool(self.pages):
            raise ValueError("Give either chapters or pages [first, last], not both")
        if self.pages and (len(self.pages) != 2 or self.pages[0] > self.pages[1]):
            raise ValueError("pages must be [first, last] with first <= last")
        return self


class Registry(BaseModel):
    """All courses and the one opened by default."""

    default: str
    courses: list[Course] = Field(min_length=1)

    @model_validator(mode="after")
    def check_ids(self) -> "Registry":
        """Unique ids, and the default course must exist."""
        ids = [course.id for course in self.courses]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate course ids: {ids}")
        if self.default not in ids:
            raise ValueError(f"Unknown default course: {self.default}")
        return self


def load_registry(path: Path = COURSES_PATH, local: Path | None = None) -> Registry:
    """Read courses.json, add the uploaded courses, validate the whole registry."""
    data = json.loads(path.read_text(encoding="utf-8"))
    local = local or LOCAL_COURSES_PATH
    if local.exists():
        data["courses"] += json.loads(local.read_text(encoding="utf-8"))["courses"]
    return Registry.model_validate(data)


def save_uploaded(registry: Registry, local: Path | None = None) -> None:
    """Write the uploaded courses of the registry to data/courses.local.json."""
    local = local or LOCAL_COURSES_PATH
    courses = [c.model_dump() for c in registry.courses if c.uploaded]
    local.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps({"courses": courses}, ensure_ascii=False, indent=2)
    local.write_text(text + "\n", encoding="utf-8")


def get_course(registry: Registry, course_id: str | None = None) -> Course:
    """Return a course by id (the default one if None); KeyError if unknown."""
    wanted = course_id or registry.default
    for course in registry.courses:
        if course.id == wanted:
            return course
    raise KeyError(f"Unknown course: {wanted}")


def course_from_argv(registry: Registry | None = None) -> Course:
    """Course named by the first command-line argument, or the default one."""
    registry = registry or load_registry()
    return get_course(registry, sys.argv[1] if len(sys.argv) > 1 else None)


def pdf_path(course_id: str) -> Path:
    """Local PDF of a course (never in Git)."""
    return ROOT / "data" / "raw" / f"{course_id}.pdf"


def pages_path(course_id: str) -> Path:
    """Clean pages of a course (one JSON object per page)."""
    return ROOT / "data" / "interim" / course_id / "pages.jsonl"


def notions_path(course_id: str, uploaded: bool = False) -> Path:
    """Notion catalogue of a course (in data/ for an uploaded course)."""
    folder = ROOT / "data" / "notions" if uploaded else ROOT / "course" / "notions"
    return folder / f"{course_id}.json"
