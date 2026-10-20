"""Add a course in one command: download its PDF, index it, draft its notions.

1. Write the course entry in course/courses.json (id, title, PDF URL, license,
   chapters or pages).
2. uv run python -m course.add <course_id>
3. Review course/notions/<course_id>.json by hand, then set "validated" to true.
An existing catalogue is kept (re-draft on purpose with course.draft_notions).
"""

import asyncio

from course.courses import course_from_argv, notions_path
from course.draft_notions import draft_catalog
from rag.ingest import build_pages, index_pages
from scripts.download_book import download_course


def main() -> None:
    """Run the three offline steps for the course named on the command line."""
    course = course_from_argv()
    download_course(course)
    asyncio.run(index_pages(course.id, build_pages(course)))
    path = notions_path(course.id)
    if path.exists():
        print(f"Keeping the existing notions: {path}")
    else:
        draft_catalog(course)
    print(f"Done: review {path}, then restart the API.")


if __name__ == "__main__":
    main()
