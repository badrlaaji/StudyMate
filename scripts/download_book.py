"""Download the official OpenStax PDF of Principles of Data Science.

Usage: uv run python -m scripts.download_book
"""

from pathlib import Path

import httpx

from config import ROOT

# From the OpenStax CMS API: book "principles-data-science", high_resolution_pdf_url.
BOOK_URL = (
    "https://assets.openstax.org/oscms-prodcms/media/documents/"
    "Principles-of-Data-Science-WEB.pdf"
)
BOOK_PATH = ROOT / "data" / "raw" / "book.pdf"
TIMEOUT_S = 120.0


def is_pdf(path: Path) -> bool:
    """Return True if the file starts with the PDF magic bytes."""
    with path.open("rb") as file:
        return file.read(5) == b"%PDF-"


def download(url: str, path: Path) -> None:
    """Stream the file to disk through a temporary .part file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".part")
    with httpx.stream("GET", url, follow_redirects=True, timeout=TIMEOUT_S) as resp:
        resp.raise_for_status()
        with part.open("wb") as file:
            for chunk in resp.iter_bytes():
                file.write(chunk)
    part.replace(path)


def main() -> None:
    """Download the book once and check it is a real PDF."""
    if BOOK_PATH.exists() and is_pdf(BOOK_PATH):
        print(f"Already downloaded: {BOOK_PATH}")
        return
    download(BOOK_URL, BOOK_PATH)
    if not is_pdf(BOOK_PATH):
        raise RuntimeError(f"Not a PDF: {BOOK_PATH}")
    size_mb = BOOK_PATH.stat().st_size / 1e6
    print(f"Downloaded {BOOK_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
