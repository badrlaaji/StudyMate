"""Tests for the agent: router, citation check, quiz, plan, Spring client, graph.

No network: fake LLM, fake retrieval, httpx.MockTransport for Spring.
"""

import asyncio
import random
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError

import agent.graph as graph_module
from agent.answer import (
    NOT_FOUND,
    AnswerDraft,
    answer_prompt,
    build_citations,
    verify_citations,
)
from agent.graph import build_graph, to_response
from agent.plan import build_plan
from agent.quiz import (
    QuizDraft,
    QuizQuestion,
    keep_valid,
    notion_scores,
    pick_notions,
)
from agent.router import Route, fallback_route, route_message
from agent.spring import fetch_weak_notions, post_score
from course.notions import Catalog, KeyIdea, Notion

HITS = [
    {
        "page": 281,
        "text": "Overfitting happens when the model fits noise.",
        "score": 0.9,
    },
    {"page": 282, "text": "The cubic curve overfits the training data.", "score": 0.8},
]


@pytest.fixture(autouse=True)
def isolated_llm_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.llm.CACHE_DIR", tmp_path)
    monkeypatch.setenv("LLM_MODEL", "gemini-test-model")


def fake_llm(answers: dict):
    """Fake chat model: answers[schema] is a list of results (or errors) to replay."""

    def with_structured_output(schema):
        def invoke(prompt):
            outcome = answers[schema].pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        return SimpleNamespace(invoke=invoke)

    return SimpleNamespace(with_structured_output=with_structured_output)


def notion(notion_id: str, pages: list[int]) -> Notion:
    """Build a small valid notion."""
    idea = KeyIdea(en="An idea in English.", fr="Une idée en français.")
    return Notion(
        id=notion_id,
        name_en=f"{notion_id} en",
        name_fr=f"{notion_id} fr",
        chapter=6,
        section="6.1 ML",
        pages=pages,
        key_ideas=[idea] * 3,
    )


CATALOG = Catalog.model_construct(
    source="book",
    license="CC",
    validated=False,
    notions=[notion("overfitting", [281, 282]), notion("k_means", [290, 291])]
    + [notion(f"other_{i}", [300 + i]) for i in range(3)],
)


def spring(handler) -> httpx.AsyncClient:
    """Async client whose requests are answered by `handler` (no network)."""
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://s"
    )


def spring_down(request):
    raise httpx.ConnectError("connection refused")


# --- router -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("message", "route", "lang"),
    [
        ("Quiz me on chapter 6", "quiz", "en"),
        ("Fais-moi un QCM sur les arbres", "quiz", "fr"),
        ("What should I review this week?", "plan", "en"),
        ("Quel est mon plan de révision ?", "plan", "fr"),
        ("What is a regression plane?", "answer", "en"),
        ("Qu'est-ce que le surapprentissage ?", "answer", "fr"),
    ],
)
def test_fallback_route(message, route, lang):
    assert fallback_route(message) == Route(
        route=route, lang=lang, search_query=message
    )


def test_route_message_uses_rules_when_llm_fails():
    llm = fake_llm({Route: [RuntimeError("quota")]})
    assert route_message("Quiz me please", llm=llm).route == "quiz"


def test_route_message_trusts_the_llm_when_it_works():
    llm = fake_llm({Route: [Route(route="plan", lang="fr", search_query="q")]})
    assert route_message("anything", llm=llm) == Route(
        route="plan", lang="fr", search_query="q"
    )


# --- answer and citation check (D5) --------------------------------------------


@pytest.mark.parametrize(
    ("answer", "pages", "ok"),
    [
        ("Overfitting is...", [281], True),
        ("Overfitting is...", [281, 282], True),
        ("Overfitting is...", [], False),  # no citation
        ("Overfitting is...", [281, 999], False),  # page not retrieved
        ("", [281], False),  # empty answer
    ],
)
def test_verify_citations(answer, pages, ok):
    draft = AnswerDraft(found=True, answer=answer, cited_pages=pages)
    assert verify_citations(draft, HITS) is ok


def test_verify_citations_rejects_not_found_flag_even_with_pages():
    draft = AnswerDraft(found=False, answer="The text does not say.", cited_pages=[281])
    assert verify_citations(draft, HITS) is False


def test_build_citations_one_excerpt_per_page_in_page_order():
    citations = build_citations([282, 281, 281], HITS)
    assert [c["page"] for c in citations] == [281, 282]
    assert citations[0]["excerpt"].startswith("Overfitting happens")


def test_answer_prompt_language_markers_and_retry_reminder():
    first = answer_prompt("Q?", "fr", HITS, retry=False)
    second = answer_prompt("Q?", "fr", HITS, retry=True)
    assert "in French" in first and "[page 281]" in first
    assert "rejected" not in first and "rejected" in second


# --- quiz and plan ------------------------------------------------------------


def question(notion_id: str, page: int, answer_index: int = 0) -> QuizQuestion:
    """Build a valid quiz question."""
    return QuizQuestion(
        notion_id=notion_id,
        question="Which one?",
        options=["a", "b", "c", "d"],
        answer_index=answer_index,
        page=page,
        explanation="Because.",
    )


def test_quiz_question_needs_exactly_four_options():
    with pytest.raises(ValidationError):
        QuizQuestion(**{**question("x", 1).model_dump(), "options": ["a", "b", "c"]})


def test_pick_notions_weak_first_then_random_others():
    picked = pick_notions(["k_means", "unknown"], CATALOG, 3, random.Random(0))
    assert picked[0].id == "k_means"
    assert len(picked) == 3 and len({n.id for n in picked}) == 3


def test_keep_valid_drops_questions_on_foreign_pages_or_notions():
    notions = [CATALOG.notions[0]]
    draft = QuizDraft(
        questions=[
            question("overfitting", 281),
            question("overfitting", 300),
            question("k_means", 290),
        ]
    )
    assert [q.page for q in keep_valid(draft, notions)] == [281]


def test_notion_scores_graded_by_code():
    results = [("a", True), ("a", False), ("b", True)]
    # a: 1 correct out of 2 -> 5 x 1/2 = 2.5 -> 3 (half up, not Python's round)
    assert notion_scores(results) == {"a": 3, "b": 5}


def test_build_plan_sorted_by_score_and_localized():
    weak = [
        {"notionId": "k_means", "average": 2.5},
        {"notionId": "overfitting", "average": 1.333},
        {"notionId": "ghost", "average": 0.0},
    ]
    plan = build_plan(weak, CATALOG, "fr")
    assert [row["notion_id"] for row in plan] == ["overfitting", "k_means"]
    assert plan[0] == {
        "notion_id": "overfitting",
        "name": "overfitting fr",
        "score": 1.33,
        "pages": [281, 282],
        "action": "quiz",
    }


# --- Spring client --------------------------------------------------------------


def test_fetch_weak_notions_returns_json_or_none_when_down():
    def ok(request):
        assert request.url.path == "/api/notions/weak"
        assert request.url.params["limit"] == "5"
        return httpx.Response(200, json=[{"notionId": "k_means", "average": 2.0}])

    assert asyncio.run(fetch_weak_notions(spring(ok), 5)) == [
        {"notionId": "k_means", "average": 2.0}
    ]
    assert asyncio.run(fetch_weak_notions(spring(spring_down), 5)) is None


def test_post_score_false_on_server_error():
    def error(request):
        return httpx.Response(500)

    assert asyncio.run(post_score(spring(error), "k_means", "QUIZ", 4)) is False


# --- whole graph ----------------------------------------------------------------


SEARCHED: list[str] = []


def run_graph(message: str, answers: dict, http=None, monkeypatch=None) -> dict:
    """Run the compiled graph with fakes and return the /chat response."""

    async def fake_retrieve(question, engine, k, embedder):
        SEARCHED.append(question)
        return HITS

    async def fake_chunks(engine, pages, model):
        return [
            {"page": p, "chunk_index": 0, "text": f"text of page {p}"} for p in pages
        ]

    monkeypatch.setattr(graph_module, "retrieve", fake_retrieve)
    monkeypatch.setattr("agent.quiz.chunks_for_pages", fake_chunks)
    monkeypatch.setattr("agent.quiz.model_name", lambda: "test-model")
    app = build_graph(
        engine=None,
        http=http or spring(spring_down),
        catalog=CATALOG,
        llm=fake_llm(answers),
        rng=random.Random(0),
    )
    return to_response(asyncio.run(app.ainvoke({"message": message})))


def test_graph_answer_verified_on_first_try(monkeypatch):
    answers = {
        Route: [Route(route="answer", lang="en", search_query="q")],
        AnswerDraft: [
            AnswerDraft(found=True, answer="It fits noise.", cited_pages=[281])
        ],
    }
    SEARCHED.clear()
    response = run_graph("What is overfitting?", answers, monkeypatch=monkeypatch)
    assert SEARCHED == ["q"]  # the router's English search_query, not the raw message
    assert response["status"] == "ok"
    assert response["answer"] == "It fits noise."
    assert [c["page"] for c in response["citations"]] == [281]


def test_graph_retries_once_then_answers(monkeypatch):
    answers = {
        Route: [Route(route="answer", lang="en", search_query="q")],
        AnswerDraft: [
            AnswerDraft(found=True, answer="Wrong page.", cited_pages=[999]),
            AnswerDraft(found=True, answer="Right page.", cited_pages=[282]),
        ],
    }
    response = run_graph("What is overfitting?", answers, monkeypatch=monkeypatch)
    assert response["status"] == "ok" and response["answer"] == "Right page."


def test_graph_not_found_after_two_invalid_answers(monkeypatch):
    answers = {
        Route: [Route(route="answer", lang="fr", search_query="q")],
        AnswerDraft: [AnswerDraft(found=False, answer="", cited_pages=[])] * 2,
    }
    response = run_graph("Recette du couscous ?", answers, monkeypatch=monkeypatch)
    assert response["status"] == "not_found"
    assert response["answer"] == NOT_FOUND["fr"]
    assert response["citations"] == []


def test_graph_quiz_in_degraded_mode_when_spring_is_down(monkeypatch):
    answers = {
        Route: [Route(route="quiz", lang="en", search_query="q")],
        QuizDraft: [QuizDraft(questions=[question("overfitting", 281)])],
    }
    response = run_graph("Quiz me", answers, monkeypatch=monkeypatch)
    assert response["route"] == "quiz" and response["status"] == "degraded"
    assert isinstance(response["quiz"], list)


def test_graph_plan_from_spring(monkeypatch):
    def weak(request):
        return httpx.Response(200, json=[{"notionId": "k_means", "average": 2.0}])

    answers = {Route: [Route(route="plan", lang="en", search_query="q")]}
    response = run_graph("What should I review?", answers, spring(weak), monkeypatch)
    assert response["status"] == "ok"
    assert [row["notion_id"] for row in response["plan"]] == ["k_means"]
