"""Notion catalogue: Pydantic schema, loading, and checks against the book pages."""

from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from config import ROOT

NOTIONS_PATH = ROOT / "course" / "notions.json"
MIN_NOTIONS = 15
MAX_NOTIONS = 25
ID_PATTERN = r"^[a-z0-9]+(_[a-z0-9]+)*$"


class KeyIdea(BaseModel):
    """One idea the learner must be able to explain, in both languages."""

    en: str = Field(min_length=10)
    fr: str = Field(min_length=10)


class Notion(BaseModel):
    """One course notion with the PDF pages that explain it."""

    id: str = Field(pattern=ID_PATTERN)
    name_en: str = Field(min_length=3)
    name_fr: str = Field(min_length=3)
    chapter: int
    section: str
    pages: list[int] = Field(min_length=1)
    key_ideas: list[KeyIdea] = Field(min_length=3, max_length=5)


class Catalog(BaseModel):
    """The frozen notion catalogue, single source of truth (D1)."""

    source: str
    license: str
    validated: bool = False
    notions: list[Notion] = Field(min_length=MIN_NOTIONS, max_length=MAX_NOTIONS)

    @model_validator(mode="after")
    def check_unique_ids(self) -> "Catalog":
        """Reject duplicate notion ids."""
        ids = [notion.id for notion in self.notions]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"Duplicate notion ids: {duplicates}")
        return self


def load_catalog(path: Path = NOTIONS_PATH) -> Catalog:
    """Read and validate notions.json."""
    return Catalog.model_validate_json(path.read_text(encoding="utf-8"))


def unknown_pages(catalog: Catalog, book_pages: set[int]) -> dict[str, list[int]]:
    """Return, per notion id, the cited pages missing from pages.jsonl."""
    missing = {}
    for notion in catalog.notions:
        bad = [page for page in notion.pages if page not in book_pages]
        if bad:
            missing[notion.id] = bad
    return missing
