"""Draft the notion catalogue of a course with the LLM, one call per main section.

Usage: uv run python -m course.draft_notions [course_id]   (default course if omitted)
The draft (course/notions/<course_id>.json) must then be reviewed by hand (D1) and
"validated" set to true.
"""

import json
import os
import re
import time

from pydantic import BaseModel

from agent.cache import cache_get, cache_key
from agent.llm import invoke_structured
from config import get_env
from course.courses import Course, course_from_argv, notions_path, pages_path
from course.notions import Catalog, KeyIdea, Notion, load_catalog
from rag.ingest import read_jsonl

MAIN_SECTION = re.compile(r"^\d+\.\d+ ")  # "6.2 Classification ..." (not Key Terms)
# Numbered sections that recap or test, without new notions ("5.6 Chapter summary").
END_MATTER = re.compile(r"summary|review|exercises|key terms", re.IGNORECASE)
BLOCK_PAGES = 10  # no numbered sections in the outline: blocks of 10 pages
PAGES_PER_NOTION = 5  # about one notion per 5 pages of a section
MAX_PER_SECTION = 4
PAUSE_S = float(os.environ.get("LLM_PAUSE_S", "6"))  # stay under the per-minute quota
MAX_KEY_IDEAS = 5

PROMPT = """You are building a study catalogue for one section of a textbook.
Section: "{section}" (chapter {chapter}), PDF pages {first}-{last}.

List exactly {count} distinct core notion(s) that a student must master in this section.
For each notion give:
- id: short snake_case English identifier (example: "k_means_clustering")
- name_en: notion name in English; name_fr: the same name in French
- pages: the PDF page numbers where the notion is explained, taken only from the
  [page N] markers below
- key_ideas: 3 to 5 short sentences stating what a student must be able to explain,
  each in English (en) and in French (fr)

Rules:
- Use only the section text. Formulas were lost when the PDF was read: describe ideas
  in words.
- Each key idea is a factual statement, not an instruction ("Entropy measures...",
  not "Explain entropy").
- Names have no leading article. French names use sentence case
  ("Régression logistique", not "Régression Logistique").
- Write French with all its accents (é, è, à, ç...). Use these French terms:
  overfitting = surapprentissage, underfitting = sous-apprentissage,
  dataset = jeu de données, feature = caractéristique.

SECTION TEXT
{text}"""


class NotionDraft(BaseModel):
    """One notion as proposed by the LLM (chapter and section are added by code)."""

    id: str
    name_en: str
    name_fr: str
    pages: list[int]
    key_ideas: list[KeyIdea]


class SectionDraft(BaseModel):
    """LLM answer for one section."""

    notions: list[NotionDraft]


def group_sections(pages: list[dict]) -> dict[str, list[dict]]:
    """Group pages by main section ("6.1 ...", "7.2 ..."), else by blocks of pages."""
    sections: dict[str, list[dict]] = {}
    for page in pages:
        section = page["section"]
        if MAIN_SECTION.match(section) and not END_MATTER.search(section):
            sections.setdefault(page["section"], []).append(page)
    return sections or page_blocks(pages)


def page_blocks(pages: list[dict]) -> dict[str, list[dict]]:
    """Split pages into blocks of BLOCK_PAGES, named "Pages first-last"."""
    blocks = {}
    for start in range(0, len(pages), BLOCK_PAGES):
        block = pages[start : start + BLOCK_PAGES]
        blocks[f"Pages {block[0]['page']}-{block[-1]['page']}"] = block
    return blocks


def catalog_source(course: Course) -> str:
    """Source line of a catalogue: book, scope, authors and link."""
    parts = [course.title, course.scope_en, course.attribution, course.book_url]
    return ", ".join(part for part in parts if part)


def notion_count(section_pages: list[dict]) -> int:
    """Return how many notions to ask for: 1 per ~5 pages, between 1 and 4."""
    return min(MAX_PER_SECTION, max(1, round(len(section_pages) / PAGES_PER_NOTION)))


def build_prompt(section: str, section_pages: list[dict], count: int) -> str:
    """Fill the prompt with the section text and its [page N] markers."""
    text = "\n\n".join(f"[page {p['page']}]\n{p['text']}" for p in section_pages)
    return PROMPT.format(
        section=section,
        chapter=section_pages[0]["chapter"],
        first=section_pages[0]["page"],
        last=section_pages[-1]["page"],
        count=count,
        text=text,
    )


def to_notion(draft: NotionDraft, section: str, section_pages: list[dict]) -> Notion:
    """Keep only pages of the section and at most 5 key ideas, then validate."""
    allowed = {p["page"] for p in section_pages}
    pages = sorted({page for page in draft.pages if page in allowed})
    return Notion(
        id=draft.id,
        name_en=draft.name_en,
        name_fr=draft.name_fr,
        chapter=section_pages[0]["chapter"],
        section=section,
        pages=pages,
        key_ideas=draft.key_ideas[:MAX_KEY_IDEAS],
    )


def draft_section(section: str, section_pages: list[dict]) -> list[Notion]:
    """Ask the LLM for the notions of one section; pause after a real call."""
    prompt = build_prompt(section, section_pages, notion_count(section_pages))
    cached = cache_get(cache_key(get_env("LLM_MODEL"), prompt)) is not None
    answer = invoke_structured(SectionDraft, prompt)
    if not cached:
        time.sleep(PAUSE_S)
    notions = []
    for draft in answer.notions:
        try:
            notions.append(to_notion(draft, section, section_pages))
        except ValueError as error:  # pydantic.ValidationError is a ValueError
            print(f"  dropped {draft.id!r}: {error.errors()[0]['msg']}")
    return notions


def draft_catalog(course: Course) -> Catalog:
    """Draft the catalogue of a course and write it (validated = false)."""
    path = notions_path(course.id, course.uploaded)
    if path.exists() and load_catalog(path).validated:
        raise SystemExit(f"{path} is validated (D1): it is never overwritten.")
    notions = []
    for section, section_pages in group_sections(
        read_jsonl(pages_path(course.id))
    ).items():
        found = draft_section(section, section_pages)
        print(f"{section}: {[n.id for n in found]}")
        notions.extend(found)
    catalog = Catalog(
        source=catalog_source(course),
        license=course.license,
        validated=False,
        notions=notions,
    )
    text = json.dumps(catalog.model_dump(), ensure_ascii=False, indent=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")
    print(f"{len(notions)} notions -> {path}")
    return catalog


def main() -> None:
    """Draft the catalogue of the course named on the command line."""
    draft_catalog(course_from_argv())


if __name__ == "__main__":
    main()
