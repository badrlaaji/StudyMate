"""FastAPI service: agent, course library, Feynman, quiz and relays to Spring.

Run: uv run uvicorn api.main:app --reload --port 8000
Next.js is the only client of this API; this API is the only client of Spring.
Every endpoint takes an optional course id (course/courses.json); none = default.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from agent.feynman import evaluate_explanation
from agent.graph import build_graph, to_response
from agent.plan import PLAN_SIZE, build_plan
from agent.quiz import build_quiz, notion_scores
from agent.spring import fetch_mastery, fetch_weak_notions, make_client, post_score
from api.schemas import (
    ChatRequest,
    ChatResponse,
    CourseOut,
    FeynmanRequest,
    FeynmanResponse,
    Lang,
    NotionOut,
    QuizRequest,
    QuizResultRequest,
    QuizResultResponse,
)
from api.uploads import job_state
from api.uploads import router as uploads_router
from course.courses import (
    COURSE_ID_PATTERN,
    Course,
    Registry,
    get_course,
    load_registry,
    notions_path,
    pdf_path,
)
from course.notions import Catalog, Notion, load_catalog
from rag.embeddings import load_model, model_name
from rag.store import count_chunks, get_engine

logging.basicConfig(level=logging.INFO)
CourseQuery = Annotated[str | None, Query(pattern=COURSE_ID_PATTERN)]
INDEX_HINT = (
    "Database query failed: is the course indexed? Run python -m rag.ingest <course>."
)


def load_catalogs(registry: Registry) -> dict[str, Catalog]:
    """Notion catalogues of the courses that already have one."""
    return {
        course.id: load_catalog(notions_path(course.id, course.uploaded))
        for course in registry.courses
        if notions_path(course.id, course.uploaded).exists()
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the database pool and the Spring client, warm up the embedding model."""
    app.state.engine = get_engine()
    app.state.http = make_client()
    app.state.registry = load_registry()
    app.state.catalogs = load_catalogs(app.state.registry)
    app.state.graph = build_graph(
        app.state.engine, app.state.http, app.state.registry, app.state.catalogs
    )
    app.state.jobs = {}  # processing of uploaded courses
    app.state.job_lock = asyncio.Lock()
    app.state.tasks = set()
    await asyncio.to_thread(load_model, model_name())
    yield
    await app.state.http.aclose()
    await app.state.engine.dispose()


app = FastAPI(title="StudyMate API", version="1.2.0", lifespan=lifespan)
app.include_router(uploads_router)


@app.exception_handler(RuntimeError)
async def llm_unavailable(request: Request, error: RuntimeError) -> JSONResponse:
    """LLM down twice in a row (quota or overload): a clear 503, not a crash."""
    return JSONResponse(status_code=503, content={"detail": str(error)})


@app.exception_handler(ProgrammingError)
async def index_missing(request: Request, error: ProgrammingError) -> JSONResponse:
    """Missing table (book not indexed yet): a 503 with the fix, not a bare 500."""
    logging.error("SQL error: %s", error.orig)
    return JSONResponse(status_code=503, content={"detail": INDEX_HINT})


def find_course(request: Request, course_id: str | None) -> Course:
    """Return a course of the registry or a 404."""
    try:
        return get_course(request.app.state.registry, course_id)
    except KeyError as error:
        detail = f"Unknown course: {course_id}"
        raise HTTPException(status_code=404, detail=detail) from error


def find_catalog(request: Request, course: Course) -> Catalog:
    """Return the notion catalogue of a course or a 404 with the command to run."""
    catalog = request.app.state.catalogs.get(course.id)
    if catalog is None:
        detail = f"No notions yet for {course.id}: run python -m course.add {course.id}"
        raise HTTPException(status_code=404, detail=detail)
    return catalog


def find_notion(catalog: Catalog, notion_id: str) -> Notion:
    """Return a notion of the catalogue or a 404."""
    for notion in catalog.notions:
        if notion.id == notion_id:
            return notion
    raise HTTPException(status_code=404, detail=f"Unknown notion: {notion_id}")


async def indexed_chunks(request: Request, course_id: str) -> int | None:
    """Chunks stored for a course; None if the database cannot tell."""
    try:
        return await count_chunks(request.app.state.engine, course_id, model_name())
    except Exception:  # database down: the library still lists the courses
        return None


@app.get("/health")
async def health(request: Request) -> dict:
    """Wake the database (Neon sleeps when idle) and report the dependencies."""
    try:
        async with request.app.state.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        database = True
    except Exception:  # any connection problem means "down"
        database = False
    default = request.app.state.registry.default
    spring = await fetch_mastery(request.app.state.http, default) is not None
    return {
        "status": "ok" if database else "degraded",
        "database": database,
        "spring": spring,
    }


@app.get("/courses", response_model=list[CourseOut])
async def courses(request: Request, lang: Lang = "en") -> list[dict]:
    """The course library, with what is ready for each course."""
    registry = request.app.state.registry
    rows = []
    for course in registry.courses:
        catalog = request.app.state.catalogs.get(course.id)
        job = job_state(request.app, course)
        rows.append(
            {
                "id": course.id,
                "title": course.title,
                "scope": course.scope_fr if lang == "fr" else course.scope_en,
                "book_lang": course.book_lang,
                "license": course.license,
                "attribution": course.attribution,
                "book_url": course.book_url,
                "default": course.id == registry.default,
                "pdf": pdf_path(course.id).exists(),
                "chunks": await indexed_chunks(request, course.id),
                "notions": len(catalog.notions) if catalog else 0,
                "validated": bool(catalog and catalog.validated),
                "uploaded": course.uploaded,
                "job": job["state"] if course.uploaded else None,
                "job_detail": job["detail"] if course.uploaded else "",
            }
        )
    return rows


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> dict:
    """Route the message, then answer with verified citations, a quiz or a plan."""
    course = find_course(request, body.course)
    state = await request.app.state.graph.ainvoke(
        {"message": body.message, "course": course.id}
    )
    return to_response(state)


@app.get("/notions", response_model=list[NotionOut])
async def notions(
    request: Request, lang: Lang = "en", course: CourseQuery = None
) -> list[dict]:
    """The notion catalogue of a course in English or French."""
    catalog = find_catalog(request, find_course(request, course))
    return [
        {
            "id": n.id,
            "name": n.name_fr if lang == "fr" else n.name_en,
            "chapter": n.chapter,
            "section": n.section,
            "pages": n.pages,
            "key_ideas": [k.fr if lang == "fr" else k.en for k in n.key_ideas],
        }
        for n in catalog.notions
    ]


@app.post("/feynman", response_model=FeynmanResponse)
async def feynman(body: FeynmanRequest, request: Request) -> dict:
    """Judge an explanation, compute the score by code, record it in Spring."""
    course = find_course(request, body.course)
    notion = find_notion(find_catalog(request, course), body.notion_id)
    result = await asyncio.to_thread(
        evaluate_explanation, notion, body.explanation, body.lang
    )
    recorded = await post_score(
        request.app.state.http, course.id, notion.id, "FEYNMAN", result["score"]
    )
    return {**result, "recorded": recorded}


@app.post("/quiz")
async def quiz(body: QuizRequest, request: Request) -> dict:
    """Multiple-choice quiz on the weakest notions (random ones if Spring is down)."""
    course = find_course(request, body.course)
    catalog = find_catalog(request, course)
    state = request.app.state
    questions, degraded = await build_quiz(
        state.engine, state.http, course.id, catalog, body.n, body.lang
    )
    return {
        "questions": [q.model_dump() for q in questions],
        "status": "degraded" if degraded else "ok",
    }


@app.post("/quiz/result", response_model=QuizResultResponse)
async def quiz_result(body: QuizResultRequest, request: Request) -> dict:
    """Grade by code (no LLM) and record one score per notion in Spring."""
    course = find_course(request, body.course)
    results = [(a.notion_id, a.chosen_index == a.answer_index) for a in body.answers]
    scores = notion_scores(results)
    recorded = [
        await post_score(request.app.state.http, course.id, notion_id, "QUIZ", score)
        for notion_id, score in scores.items()
    ]
    return {"scores": scores, "recorded": all(recorded)}


@app.get("/mastery")
async def mastery(request: Request, course: CourseQuery = None) -> dict:
    """Relay the mastery of every scored notion of a course from Spring."""
    course_id = find_course(request, course).id
    data = await fetch_mastery(request.app.state.http, course_id)
    return {"notions": data or [], "status": "degraded" if data is None else "ok"}


@app.get("/plan")
async def plan(request: Request, lang: Lang = "en", course: CourseQuery = None) -> dict:
    """Revision plan without LLM: weakest notions first, with pages to re-read."""
    found = find_course(request, course)
    catalog = find_catalog(request, found)
    weak = await fetch_weak_notions(request.app.state.http, found.id, PLAN_SIZE)
    if weak is None:
        return {"plan": [], "status": "degraded"}
    return {"plan": build_plan(weak, catalog, lang), "status": "ok"}


@app.get("/book.pdf")
async def book_pdf(request: Request, course: CourseQuery = None) -> FileResponse:
    """Serve the local PDF of a course to the PDF panel (never stored in Git)."""
    found = find_course(request, course)
    path = pdf_path(found.id)
    if not path.exists():
        detail = f"Run python -m scripts.download_book {found.id} first."
        raise HTTPException(status_code=404, detail=detail)
    return FileResponse(path, media_type="application/pdf")
