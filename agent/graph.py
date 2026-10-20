"""LangGraph agent: route -> answer (retrieve, generate, verify) | quiz | plan."""

import asyncio
import random

import httpx
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine

from agent.answer import (
    NOT_FOUND,
    TOP_K,
    AnswerDraft,
    build_citations,
    generate,
    verify_citations,
)
from agent.plan import PLAN_SIZE, build_plan
from agent.quiz import QUIZ_SIZE, build_quiz
from agent.router import route_message
from agent.spring import fetch_weak_notions
from course.courses import Registry, get_course
from course.notions import Catalog
from rag.retrieve import retrieve

MAX_ATTEMPTS = 2  # first answer + 1 retry, then not_found (D5)


class ChatState(BaseModel):
    """Everything the graph knows about one message."""

    message: str
    course: str = ""  # course id; empty = the default course
    route: str = "answer"
    lang: str = "en"
    search_query: str = ""
    hits: list[dict] = []
    draft: AnswerDraft | None = None
    attempts: int = 0
    answer: str | None = None
    citations: list[dict] = []
    status: str = ""
    quiz: list[dict] | None = None
    plan: list[dict] | None = None


def after_generate(state: ChatState) -> str:
    """Verified -> answered; otherwise retry once, then not_found."""
    if state.draft is not None and verify_citations(state.draft, state.hits):
        return "verified"
    return "retry" if state.attempts < MAX_ATTEMPTS else "not_found"


def build_graph(
    engine: AsyncEngine,
    http: httpx.AsyncClient,
    registry: Registry,
    catalogs: dict[str, Catalog],
    llm=None,
    embedder=None,
    rng: random.Random | None = None,
):
    """Compile the agent; dependencies are injected so tests can pass fakes."""
    rng = rng or random.Random()

    async def route_node(state: ChatState) -> dict:
        course = get_course(registry, state.course or None)
        decision = await asyncio.to_thread(
            route_message, state.message, course.book_lang, llm
        )
        # Rewrite only to translate: in the book's language, the student's own words
        # are searched (a rewrite dropped words and missed a page, see DECISIONS S11-7).
        same = decision.lang == course.book_lang
        query = state.message if same else decision.search_query
        return {**decision.model_dump(), "search_query": query, "course": course.id}

    async def retrieve_node(state: ChatState) -> dict:
        query = state.search_query or state.message
        return {"hits": await retrieve(query, engine, state.course, TOP_K, embedder)}

    async def generate_node(state: ChatState) -> dict:
        retry = state.attempts > 0
        book = get_course(registry, state.course).title
        draft = await asyncio.to_thread(
            generate, state.message, state.lang, state.hits, retry, book, llm
        )
        return {"draft": draft, "attempts": state.attempts + 1}

    def answered_node(state: ChatState) -> dict:
        citations = build_citations(state.draft.cited_pages, state.hits)
        return {"answer": state.draft.answer, "citations": citations, "status": "ok"}

    def not_found_node(state: ChatState) -> dict:
        return {"answer": NOT_FOUND[state.lang], "citations": [], "status": "not_found"}

    async def quiz_node(state: ChatState) -> dict:
        catalog = catalogs.get(state.course)
        if catalog is None:  # notions not drafted yet for this course
            return {"quiz": [], "status": "no_notions"}
        questions, degraded = await build_quiz(
            engine, http, state.course, catalog, QUIZ_SIZE, state.lang, llm, rng
        )
        status = "degraded" if degraded else "ok"
        return {"quiz": [q.model_dump() for q in questions], "status": status}

    async def plan_node(state: ChatState) -> dict:
        catalog = catalogs.get(state.course)
        if catalog is None:
            return {"plan": [], "status": "no_notions"}
        weak = await fetch_weak_notions(http, state.course, PLAN_SIZE)
        if weak is None:
            return {"plan": [], "status": "degraded"}
        return {"plan": build_plan(weak, catalog, state.lang), "status": "ok"}

    graph = StateGraph(ChatState)
    graph.add_node("route", route_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("answered", answered_node)
    graph.add_node("not_found", not_found_node)
    graph.add_node("quiz", quiz_node)
    graph.add_node("plan", plan_node)
    graph.add_edge(START, "route")
    graph.add_conditional_edges(
        "route",
        lambda state: state.route,
        {"answer": "retrieve", "quiz": "quiz", "plan": "plan"},
    )
    graph.add_edge("retrieve", "generate")
    graph.add_conditional_edges(
        "generate",
        after_generate,
        {"verified": "answered", "retry": "generate", "not_found": "not_found"},
    )
    for node in ("answered", "not_found", "quiz", "plan"):
        graph.add_edge(node, END)
    return graph.compile()


def to_response(state: dict) -> dict:
    """Shape the final state as the /chat contract."""
    return {
        "course": state["course"],
        "route": state["route"],
        "lang": state["lang"],
        "answer": state.get("answer"),
        "citations": state.get("citations", []),
        "status": state["status"],
        "quiz": state.get("quiz"),
        "plan": state.get("plan"),
    }
