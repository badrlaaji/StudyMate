"""Courses uploaded from the interface: receive the PDF, create the course, process it.

Processing (indexing, then drafting the notions) runs in the background, one course
at a time; the interface polls GET /courses/{id}/status.
"""

import asyncio
import logging
import shutil
import uuid
from typing import Annotated

from fastapi import APIRouter, FastAPI, HTTPException, Path, Request, Response
from pydantic import ValidationError

from api.schemas import NewCourse
from course.add import index_course
from course.courses import (
    COURSE_ID_PATTERN,
    Course,
    get_course,
    notions_path,
    pages_path,
    pdf_path,
    save_uploaded,
)
from course.draft_notions import draft_catalog
from course.upload import (
    MAX_STUDY_PAGES,
    MAX_UPLOAD_MB,
    default_scope,
    pdf_title,
    read_chapters,
    selected_pages,
    slugify,
    unique_id,
    upload_path,
)
from rag.embeddings import model_name
from rag.store import count_chunks, create_schema, delete_course_chunks

router = APIRouter()
logger = logging.getLogger(__name__)
RUNNING = {"queued", "indexing", "drafting"}
CourseId = Annotated[str, Path(pattern=COURSE_ID_PATTERN)]


def job_state(app: FastAPI, course: Course) -> dict:
    """Processing state of a course; after a restart, deduced from its notions."""
    if course.id in app.state.jobs:
        return app.state.jobs[course.id]
    if course.id in app.state.catalogs or not course.uploaded:
        return {"state": "ready", "detail": ""}
    return {"state": "failed", "detail": "Processing was interrupted: retry."}


def course_or_404(request: Request, course_id: str) -> Course:
    """Return a course or a 404."""
    try:
        return get_course(request.app.state.registry, course_id)
    except KeyError as error:
        raise HTTPException(404, f"Unknown course: {course_id}") from error


def start_job(app: FastAPI, course: Course, index: bool) -> None:
    """Queue the processing of a course (the task is kept so it is not lost)."""
    app.state.jobs[course.id] = {"state": "queued", "detail": ""}
    task = asyncio.create_task(run_job(app, course, index))
    app.state.tasks.add(task)
    task.add_done_callback(app.state.tasks.discard)


async def run_job(app: FastAPI, course: Course, index: bool) -> None:
    """Index the course (CPU), then draft its notions (Gemini); one course at a time."""
    jobs = app.state.jobs
    async with app.state.job_lock:
        try:
            if index:
                jobs[course.id] = {"state": "indexing", "detail": ""}
                await asyncio.to_thread(index_course, course)
            jobs[course.id] = {"state": "drafting", "detail": ""}
            app.state.catalogs[course.id] = await asyncio.to_thread(
                draft_catalog, course
            )
            jobs[course.id] = {"state": "ready", "detail": ""}
        except (Exception, SystemExit) as error:  # quota, unreadable pages...
            logger.exception("processing of course %s failed", course.id)
            jobs[course.id] = {"state": "failed", "detail": str(error)[:300]}


@router.post("/uploads")
async def upload_pdf(request: Request) -> dict:
    """Receive a PDF as the raw request body; return its pages and outline chapters."""
    body = await request.body()
    if len(body) > MAX_UPLOAD_MB * 1_000_000:
        raise HTTPException(413, f"The PDF is larger than {MAX_UPLOAD_MB} MB.")
    if not body.startswith(b"%PDF-"):
        raise HTTPException(400, "This file is not a PDF.")
    upload_id = uuid.uuid4().hex
    path = upload_path(upload_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    try:
        pages, chapters = await asyncio.to_thread(read_chapters, path)
        title = await asyncio.to_thread(pdf_title, path)
    except Exception as error:  # damaged or encrypted PDF
        path.unlink(missing_ok=True)
        raise HTTPException(400, "This PDF cannot be read.") from error
    return {
        "upload_id": upload_id,
        "pages": pages,
        "chapters": chapters,
        "title": title,
    }


@router.post("/courses", status_code=202)
async def add_course(body: NewCourse, request: Request) -> dict:
    """Create a course from an uploaded PDF, then process it in the background."""
    if not body.rights:
        raise HTTPException(422, "Confirm that you may use this document.")
    upload = upload_path(body.upload_id)
    if not upload.exists():
        raise HTTPException(404, "Unknown upload: send the PDF again.")
    book_pages, chapters = await asyncio.to_thread(read_chapters, upload)
    if not set(body.chapters) <= {c["number"] for c in chapters}:
        raise HTTPException(422, "Unknown chapter number.")
    if body.pages and not 1 <= body.pages[0] <= body.pages[-1] <= book_pages:
        raise HTTPException(422, f"Pages must be between 1 and {book_pages}.")
    count = selected_pages(chapters, body.chapters, body.pages)
    if not 1 <= count <= MAX_STUDY_PAGES:
        detail = f"Choose 1 to {MAX_STUDY_PAGES} pages ({count} selected)."
        raise HTTPException(422, detail)
    registry = request.app.state.registry
    scope_en, scope_fr = default_scope(body.chapters, body.pages)
    try:
        course = Course(
            id=unique_id(slugify(body.title), {c.id for c in registry.courses}),
            title=body.title,
            scope_en=scope_en,
            scope_fr=scope_fr,
            book_lang=body.book_lang,
            attribution=body.attribution,
            license=body.license,
            chapters=body.chapters,
            pages=body.pages,
            uploaded=True,
        )
    except ValidationError as error:
        raise HTTPException(422, error.errors()[0]["msg"]) from error
    pdf_path(course.id).parent.mkdir(parents=True, exist_ok=True)
    upload.replace(pdf_path(course.id))
    registry.courses.append(course)
    save_uploaded(registry)
    start_job(request.app, course, index=True)
    return {"id": course.id, "state": "queued"}


@router.get("/courses/{course_id}/status")
async def course_status(course_id: CourseId, request: Request) -> dict:
    """Processing state of a course: queued, indexing, drafting, ready or failed."""
    return job_state(request.app, course_or_404(request, course_id))


@router.post("/courses/{course_id}/retry", status_code=202)
async def retry_course(course_id: CourseId, request: Request) -> dict:
    """Run the failed steps again (indexing only if nothing is stored yet)."""
    course = course_or_404(request, course_id)
    if job_state(request.app, course)["state"] in RUNNING:
        raise HTTPException(409, "This course is already being processed.")
    try:
        stored = await count_chunks(request.app.state.engine, course.id, model_name())
    except Exception:  # no chunks table yet
        stored = 0
    start_job(request.app, course, index=stored == 0)
    return {"id": course.id, "state": "queued"}


@router.delete("/courses/{course_id}", status_code=204)
async def delete_course(course_id: CourseId, request: Request) -> Response:
    """Remove an uploaded course: its passages, files and registry entry."""
    course = course_or_404(request, course_id)
    state = request.app.state
    if not course.uploaded:
        raise HTTPException(
            403, "Only courses uploaded from the interface can be deleted."
        )
    if job_state(request.app, course)["state"] in RUNNING:
        raise HTTPException(409, "Wait until the processing ends.")
    await create_schema(state.engine)
    await delete_course_chunks(state.engine, course.id)
    pdf_path(course.id).unlink(missing_ok=True)
    notions_path(course.id, uploaded=True).unlink(missing_ok=True)
    shutil.rmtree(pages_path(course.id).parent, ignore_errors=True)
    state.registry.courses.remove(course)
    state.catalogs.pop(course.id, None)
    state.jobs.pop(course.id, None)
    save_uploaded(state.registry)
    return Response(status_code=204)
