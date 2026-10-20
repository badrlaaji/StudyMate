"""Course PDF -> clean pages (pages.jsonl) -> chunks -> e5 vectors -> chunks table.

Usage: uv run python -m rag.ingest [course_id]   (default course if omitted)
"""

import asyncio
import json
import re
import time
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

from course.courses import Course, course_from_argv, pages_path, pdf_path
from rag.chunking import chunk_pages
from rag.embeddings import embed_passages, model_name
from rag.store import count_chunks, create_schema, get_engine, replace_chunks

# D8: a line found on more than 50 % of the pages is a header or footer.
REPEAT_THRESHOLD = 0.5
# Footers: "266     6 • Chapter title" (even), "6.1 • Section title     267" (odd).
EVEN_FOOTER = re.compile(r"^\d+\s+\d+ • .+$")
ODD_FOOTER = re.compile(r"^\d+(\.\d+)? • .+\s\d+$")
CHAPTER_TITLE = re.compile(r"^Chapter (\d+)\b")


def normalize_line(line: str) -> str:
    """Collapse spaces and replace digits with '#' to compare repeated lines."""
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", line)).strip()


def repeated_lines(texts: list[str], threshold: float = REPEAT_THRESHOLD) -> set[str]:
    """Return normalized lines found on more than `threshold` of the pages."""
    counts = Counter()
    for text in texts:
        counts.update({normalize_line(line) for line in text.splitlines()})
    limit = threshold * len(texts)
    return {line for line, count in counts.items() if line and count > limit}


def is_running_footer(line: str) -> bool:
    """Return True for the book's page footers (chapter or section + page number)."""
    line = line.strip()
    return bool(EVEN_FOOTER.match(line) or ODD_FOOTER.match(line))


def clean_page(text: str, repeated: set[str]) -> str:
    """Drop headers/footers, collapse spaces, rejoin lines split after a hyphen."""
    kept = []
    for line in text.splitlines():
        if normalize_line(line) in repeated or is_running_footer(line):
            continue
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            kept.append(line)
    # "k-\nmeans" -> "k-means": the book uses real hyphens, so keep them.
    return re.sub(r"(\w)-\n(\w)", r"\1-\2", "\n".join(kept))


def chapter_bounds(
    chapters: list[tuple[int, str]], number: int, book_pages: int
) -> tuple[int, int]:
    """Return (first, last) PDF pages of a chapter from top-level (page, title)."""
    for i, (page, title) in enumerate(chapters):
        match = CHAPTER_TITLE.match(title)
        if match and int(match.group(1)) == number:
            # The last outline entry runs to the end of the book.
            last = chapters[i + 1][0] - 1 if i + 1 < len(chapters) else book_pages
            return page, last
    raise ValueError(f"Chapter {number} not found in the outline")


def section_for_page(sections: list[tuple[int, str]], page: int) -> str:
    """Return the title of the last section starting on or before `page`."""
    title = ""
    for start, name in sections:
        if start <= page:
            title = name
    return title


def read_outline(reader: PdfReader) -> tuple[list, list]:
    """Return top-level (page, title) entries and their sub-entries, 1-based pages."""
    top, subs = [], []
    for item in reader.outline:
        if isinstance(item, list):
            subs.extend(
                (reader.get_destination_page_number(s) + 1, s.title) for s in item
            )
        else:
            top.append((reader.get_destination_page_number(item) + 1, item.title))
    # Stable sort on the page only: keeps the outline order within a page.
    return top, sorted(subs, key=lambda entry: entry[0])


def page_ranges(
    course: Course, top: list, book_pages: int
) -> list[tuple[int, int, int]]:
    """Return (chapter, first, last) ranges; chapter 0 for a plain page range."""
    if course.pages:
        return [(0, course.pages[0], min(course.pages[1], book_pages))]
    return [(n, *chapter_bounds(top, n, book_pages)) for n in course.chapters]


def chapter_records(
    reader: PdfReader, number: int, first: int, last: int, subs: list
) -> list[dict]:
    """Extract and clean every page of one range; skip empty pages."""
    pages = list(range(first, last + 1))
    texts = {page: reader.pages[page - 1].extract_text() for page in pages}
    # Headers alternate between even and odd pages: count each parity apart.
    repeated = set()
    for parity in (0, 1):
        repeated |= repeated_lines([texts[p] for p in pages if p % 2 == parity])
    records = [
        {
            "page": page,
            "chapter": number,
            "section": section_for_page(subs, page),
            "text": clean_page(texts[page], repeated),
        }
        for page in pages
    ]
    return [record for record in records if record["text"]]


def write_jsonl(records: list[dict], path: Path) -> None:
    """Write one JSON object per line (UTF-8)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    """Read one JSON object per line (UTF-8)."""
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def build_pages(course: Course) -> list[dict]:
    """Build pages.jsonl for the studied part of a course, print counts."""
    reader = PdfReader(pdf_path(course.id))
    top, subs = read_outline(reader)
    records = []
    for number, first, last in page_ranges(course, top, len(reader.pages)):
        chapter = chapter_records(reader, number, first, last, subs)
        chars = sum(len(r["text"]) for r in chapter)
        print(
            f"chapter {number}: pages {first}-{last}, {len(chapter)} non-empty "
            f"pages, {chars} chars"
        )
        records.extend(chapter)
    path = pages_path(course.id)
    write_jsonl(records, path)
    total = sum(len(r["text"]) for r in records)
    print(f"total: {len(records)} pages, {total} chars -> {path}")
    return records


async def index_pages(course_id: str, records: list[dict]) -> None:
    """Chunk, embed ("passage: ") and store the pages, then print the counts."""
    start = time.perf_counter()
    chunks = chunk_pages(records)
    vectors = embed_passages([chunk["text"] for chunk in chunks])
    print(f"{len(chunks)} chunks embedded in {time.perf_counter() - start:.0f} s")
    engine = get_engine()
    try:
        await create_schema(engine)
        await replace_chunks(engine, course_id, model_name(), chunks, vectors)
        stored = await count_chunks(engine, course_id, model_name())
        print(f"{stored} chunks stored for {course_id} ({model_name()})")
    finally:
        await engine.dispose()


def main() -> None:
    """Run the whole offline pipeline for one course."""
    course = course_from_argv()
    asyncio.run(index_pages(course.id, build_pages(course)))


if __name__ == "__main__":
    main()
