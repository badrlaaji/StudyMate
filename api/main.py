"""FastAPI service: agent, catalogue, Feynman, quiz and relays to Spring.

Run: uv run uvicorn api.main:app --reload --port 8000
Next.js is the only client of this API; this API is the only client of Spring.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text

from agent.feynman import evaluate_explanation
from agent.graph import build_graph, to_response
from agent.plan import PLAN_SIZE, build_plan
from agent.quiz import build_quiz, notion_scores
from agent.spring import fetch_mastery, fetch_weak_notions, make_client, post_score
from api.schemas import (
    ChatRequest,
    ChatResponse,
    FeynmanRequest,
    FeynmanResponse,
    Lang,
    NotionOut,
    QuizRequest,
    QuizResultRequest,
    QuizResultResponse,
)
from course.notions import Catalog, Notion, load_catalog
from rag.embeddings import load_model, model_name
from rag.store import get_engine
from scripts.download_book import BOOK_PATH

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the database pool and the Spring client, warm up the embedding model."""
    app.state.engine = get_engine()
    app.state.http = make_client()
    app.state.catalog = load_catalog()
    app.state.graph = build_graph(app.state.engine, app.state.http, app.state.catalog)
    await asyncio.to_thread(load_model, model_name())
    yield
    await app.state.http.aclose()
    await app.state.engine.dispose()


app = FastAPI(title="StudyMate API", version="1.0.0", lifespan=lifespan)


@app.exception_handler(RuntimeError)
async def llm_unavailable(request: Request, error: RuntimeError) -> JSONResponse:
    """LLM down twice in a row (quota or overload): a clear 503, not a crash."""
    return JSONResponse(status_code=503, content={"detail": str(error)})


def find_notion(catalog: Catalog, notion_id: str) -> Notion:
    """Return a notion of the catalogue or a 404."""
    for notion in catalog.notions:
        if notion.id == notion_id:
            return notion
    raise HTTPException(status_code=404, detail=f"Unknown notion: {notion_id}")


@app.get("/health")
async def health(request: Request) -> dict:
    """Wake the database (Neon sleeps when idle) and report the dependencies."""
    try:
        async with request.app.state.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        database = True
    except Exception:  # any connection problem means "down"
        database = False
    spring = await fetch_mastery(request.app.state.http) is not None
    return {
        "status": "ok" if database else "degraded",
        "database": database,
        "spring": spring,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> dict:
    """Route the message, then answer with verified citations, a quiz or a plan."""
    state = await request.app.state.graph.ainvoke({"message": body.message})
    return to_response(state)


@app.get("/notions", response_model=list[NotionOut])
async def notions(request: Request, lang: Lang = "en") -> list[dict]:
    """The notion catalogue in English or French."""
    return [
        {
            "id": n.id,
            "name": n.name_fr if lang == "fr" else n.name_en,
            "chapter": n.chapter,
            "section": n.section,
            "pages": n.pages,
            "key_ideas": [k.fr if lang == "fr" else k.en for k in n.key_ideas],
        }
        for n in request.app.state.catalog.notions
    ]


@app.post("/feynman", response_model=FeynmanResponse)
async def feynman(body: FeynmanRequest, request: Request) -> dict:
    """Judge an explanation, compute the score by code, record it in Spring."""
    notion = find_notion(request.app.state.catalog, body.notion_id)
    result = await asyncio.to_thread(
        evaluate_explanation, notion, body.explanation, body.lang
    )
    recorded = await post_score(
        request.app.state.http, notion.id, "FEYNMAN", result["score"]
    )
    return {**result, "recorded": recorded}


@app.post("/quiz")
async def quiz(body: QuizRequest, request: Request) -> dict:
    """Multiple-choice quiz on the weakest notions (random ones if Spring is down)."""
    state = request.app.state
    questions, degraded = await build_quiz(
        state.engine, state.http, state.catalog, body.n, body.lang
    )
    return {
        "questions": [q.model_dump() for q in questions],
        "status": "degraded" if degraded else "ok",
    }


@app.post("/quiz/result", response_model=QuizResultResponse)
async def quiz_result(body: QuizResultRequest, request: Request) -> dict:
    """Grade by code (no LLM) and record one score per notion in Spring."""
    results = [(a.notion_id, a.chosen_index == a.answer_index) for a in body.answers]
    scores = notion_scores(results)
    recorded = [
        await post_score(request.app.state.http, notion_id, "QUIZ", score)
        for notion_id, score in scores.items()
    ]
    return {"scores": scores, "recorded": all(recorded)}


@app.get("/mastery")
async def mastery(request: Request) -> dict:
    """Relay the mastery of every scored notion from Spring."""
    data = await fetch_mastery(request.app.state.http)
    return {"notions": data or [], "status": "degraded" if data is None else "ok"}


@app.get("/plan")
async def plan(request: Request, lang: Lang = "en") -> dict:
    """Revision plan without LLM: weakest notions first, with pages to re-read."""
    weak = await fetch_weak_notions(request.app.state.http, PLAN_SIZE)
    if weak is None:
        return {"plan": [], "status": "degraded"}
    return {"plan": build_plan(weak, request.app.state.catalog, lang), "status": "ok"}


@app.get("/book.pdf")
async def book_pdf() -> FileResponse:
    """Serve the local book PDF to the PDF panel (never stored in Git)."""
    if not BOOK_PATH.exists():
        raise HTTPException(status_code=404, detail="Run scripts.download_book first.")
    return FileResponse(BOOK_PATH, media_type="application/pdf")
