"""Download the official PDF of a course (URL from course/courses.json).

Usage: uv run python -m scripts.download_book [course_id]   (default course if omitted)
"""

from pathlib import Path

import httpx

from course.courses import Course, course_from_argv, pdf_path

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


def download_course(course: Course) -> Path:
    """Download the PDF of a course once and check it is a real PDF."""
    path = pdf_path(course.id)
    if path.exists() and is_pdf(path):
        print(f"Already downloaded: {path}")
        return path
    download(course.pdf_url, path)
    if not is_pdf(path):
        raise RuntimeError(f"Not a PDF: {path}")
    print(f"Downloaded {path} ({path.stat().st_size / 1e6:.1f} MB)")
    return path


def main() -> None:
    """Download the PDF of the course named on the command line."""
    download_course(course_from_argv())


if __name__ == "__main__":
    main()
