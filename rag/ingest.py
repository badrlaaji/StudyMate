"""Book PDF -> clean pages (pages.jsonl) -> chunks -> e5 vectors -> chunks table.

Usage: uv run python -m rag.ingest
"""

import asyncio
import json
import re
import time
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

from config import ROOT
from rag.chunking import chunk_pages
from rag.embeddings import embed_passages, model_name
from rag.store import count_chunks, create_schema, get_engine, replace_chunks

BOOK_PATH = ROOT / "data" / "raw" / "book.pdf"
PAGES_PATH = ROOT / "data" / "interim" / "pages.jsonl"
CHAPTERS = (6, 7)
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


def chapter_bounds(chapters: list[tuple[int, str]], number: int) -> tuple[int, int]:
    """Return (first, last) PDF pages of a chapter from top-level (page, title)."""
    for i, (page, title) in enumerate(chapters):
        match = CHAPTER_TITLE.match(title)
        if match and int(match.group(1)) == number:
            last = chapters[i + 1][0] - 1 if i + 1 < len(chapters) else page
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


def chapter_records(
    reader: PdfReader, number: int, top: list, subs: list
) -> list[dict]:
    """Extract and clean every page of one chapter; skip empty pages."""
    first, last = chapter_bounds(top, number)
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


def read_jsonl(path: Path = PAGES_PATH) -> list[dict]:
    """Read one JSON object per line (UTF-8)."""
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def build_pages() -> list[dict]:
    """Build pages.jsonl for the selected chapters, print counts, return the pages."""
    reader = PdfReader(BOOK_PATH)
    top, subs = read_outline(reader)
    records = []
    for number in CHAPTERS:
        chapter = chapter_records(reader, number, top, subs)
        chars = sum(len(r["text"]) for r in chapter)
        first, last = chapter_bounds(top, number)
        print(
            f"chapter {number}: pages {first}-{last}, {len(chapter)} non-empty "
            f"pages, {chars} chars"
        )
        records.extend(chapter)
    write_jsonl(records, PAGES_PATH)
    total = sum(len(r["text"]) for r in records)
    print(f"total: {len(records)} pages, {total} chars -> {PAGES_PATH}")
    return records


async def index_pages(records: list[dict]) -> None:
    """Chunk, embed ("passage: ") and store the pages, then print the counts."""
    start = time.perf_counter()
    chunks = chunk_pages(records)
    vectors = embed_passages([chunk["text"] for chunk in chunks])
    print(f"{len(chunks)} chunks embedded in {time.perf_counter() - start:.0f} s")
    engine = get_engine()
    try:
        await create_schema(engine)
        await replace_chunks(engine, model_name(), chunks, vectors)
        stored = await count_chunks(engine, model_name())
        print(f"{stored} chunks stored for {model_name()}")
    finally:
        await engine.dispose()


def main() -> None:
    """Run the whole offline pipeline."""
    asyncio.run(index_pages(build_pages()))


if __name__ == "__main__":
    main()
