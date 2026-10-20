"""One test per endpoint, plus the Feynman formula (fakes only, no network)."""

from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import ProgrammingError

import api.main as main
from agent.feynman import IdeaVerdict, Judgement, feynman_score, grade, round_half_up
from agent.quiz import QuizQuestion
from course.courses import Course, Registry
from course.notions import Catalog, KeyIdea, Notion

IDEAS = [KeyIdea(en=f"Idea number {i}.", fr=f"Idée numéro {i}.") for i in range(4)]
NOTION = Notion(
    id="k_means",
    name_en="k-means clustering",
    name_fr="Clustering k-means",
    chapter=6,
    section="6.2 Classification",
    pages=[290, 291],
    key_ideas=IDEAS,
)
CATALOG = Catalog.model_construct(
    source="b", license="c", validated=False, notions=[NOTION]
)
SCORES: list[dict] = []


def make_course(course_id: str) -> Course:
    """Build a course entry of the registry."""
    return Course(
        id=course_id,
        title=f"Book {course_id}",
        scope_en="Chapter 1",
        scope_fr="Chapitre 1",
        pdf_url="https://example.org/book.pdf",
        book_url="https://example.org",
        attribution="Authors",
        license="CC BY-NC-SA 4.0",
        chapters=[1],
    )


REGISTRY = Registry(
    default="data-science",
    courses=[make_course("data-science"), make_course("statistics")],
)


def spring_handler(request: httpx.Request) -> httpx.Response:
    """Fake Spring: weak notions, mastery and score recording (course required)."""
    if request.url.path == "/api/scores":
        SCORES.append(request.content)
        return httpx.Response(201)
    assert request.url.params["course"] in {"data-science", "statistics"}
    if request.url.path == "/api/notions/weak":
        return httpx.Response(200, json=[{"notionId": "k_means", "average": 2.0}])
    return httpx.Response(
        200, json=[{"notionId": "k_means", "average": 2.0, "count": 3}]
    )


def fake_engine(ok: bool = True):
    """Engine whose connect() works (or fails) without a database."""

    @asynccontextmanager
    async def connect():
        if not ok:
            raise OSError("database down")

        async def execute(statement):
            return None

        yield SimpleNamespace(execute=execute)

    return SimpleNamespace(connect=connect)


@pytest.fixture
def client():
    """TestClient without lifespan: the app state is filled with fakes."""
    SCORES.clear()

    async def ainvoke(state):
        return {
            "course": state["course"],
            "route": "answer",
            "lang": "en",
            "answer": "Centroids move to the mean.",
            "citations": [{"page": 290, "excerpt": "k-Means Clustering Fundamentals"}],
            "status": "ok",
        }

    main.app.state.engine = fake_engine()
    main.app.state.http = httpx.AsyncClient(
        transport=httpx.MockTransport(spring_handler), base_url="http://spring"
    )
    main.app.state.registry = REGISTRY
    main.app.state.catalogs = {"data-science": CATALOG}
    main.app.state.graph = SimpleNamespace(ainvoke=ainvoke)
    return TestClient(main.app)


# --- Feynman formula (D2) -------------------------------------------------------


@pytest.mark.parametrize(
    ("covered", "total", "errors", "score"),
    [
        (4, 4, 0, 5),
        (2, 4, 0, 3),
        (2, 4, 1, 2),
        (1, 4, 3, 0),
        (0, 4, 0, 0),
        (3, 3, 5, 3),
    ],
)
def test_feynman_score_formula(covered, total, errors, score):
    assert feynman_score(covered, total, errors) == score


def test_round_half_up_differs_from_python_round():
    assert round(2.5) == 2 and round_half_up(2.5) == 3


def test_grade_ignores_unknown_indexes_and_uses_the_language():
    judgement = Judgement(
        ideas=[IdeaVerdict(index=0, covered=True), IdeaVerdict(index=9, covered=True)],
        errors=["Wrong claim."],
        follow_up="Why?",
    )
    result = grade(NOTION, judgement, "fr")
    assert result["covered"] == ["Idée numéro 0."]
    assert len(result["missing"]) == 3
    assert result["score"] == 0  # round_half_up(5 x 1/4 = 1.25) = 1, minus 1 error


# --- endpoints ------------------------------------------------------------------


def test_health_reports_database_and_spring(client):
    assert client.get("/health").json() == {
        "status": "ok",
        "database": True,
        "spring": True,
    }
    main.app.state.engine = fake_engine(ok=False)
    assert client.get("/health").json()["status"] == "degraded"


def test_chat_returns_the_contract(client):
    response = client.post("/chat", json={"message": "How does k-means work?"})
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "answer" and body["status"] == "ok"
    assert body["citations"][0]["page"] == 290


def test_chat_without_index_is_a_clear_503(client):
    async def ainvoke(state):
        raise ProgrammingError("SELECT ...", {}, Exception('"chunks" does not exist'))

    main.app.state.graph = SimpleNamespace(ainvoke=ainvoke)
    response = client.post("/chat", json={"message": "What is k-means?"})
    assert response.status_code == 503
    assert "rag.ingest" in response.json()["detail"]


def test_chat_rejects_an_empty_message(client):
    assert client.post("/chat", json={"message": ""}).status_code == 422


def test_chat_uses_the_chosen_course_or_the_default(client):
    message = {"message": "What is a regression line?"}
    assert client.post("/chat", json=message).json()["course"] == "data-science"
    body = client.post("/chat", json={**message, "course": "statistics"}).json()
    assert body["course"] == "statistics"


def test_unknown_course_is_404_and_bad_id_is_422(client):
    message = {"message": "Hello there"}
    assert (
        client.post("/chat", json={**message, "course": "biology"}).status_code == 404
    )
    assert client.post("/chat", json={**message, "course": "../x"}).status_code == 422
    assert client.get("/notions", params={"course": "biology"}).status_code == 404


def test_courses_lists_the_library(client, monkeypatch):
    async def fake_count(engine, course, model):
        return {"data-science": 284, "statistics": 0}[course]

    monkeypatch.setattr(main, "count_chunks", fake_count)
    body = client.get("/courses", params={"lang": "fr"}).json()
    assert [c["id"] for c in body] == ["data-science", "statistics"]
    assert body[0]["default"] and body[0]["chunks"] == 284 and body[0]["notions"] == 1
    assert body[1]["notions"] == 0 and body[1]["scope"] == "Chapitre 1"


def test_course_without_notions_says_how_to_add_them(client):
    response = client.get("/notions", params={"course": "statistics"})
    assert response.status_code == 404
    assert "course.add statistics" in response.json()["detail"]


def test_notions_in_french(client):
    body = client.get("/notions", params={"lang": "fr"}).json()
    assert body[0]["name"] == "Clustering k-means"
    assert body[0]["key_ideas"][0] == "Idée numéro 0."


def test_feynman_scores_by_code_and_records(client, monkeypatch):
    def fake_evaluate(notion, explanation, lang):
        return {
            "covered": ["a"],
            "missing": ["b"],
            "errors": [],
            "score": 3,
            "follow_up": "Why?",
            "pages": notion.pages,
        }

    monkeypatch.setattr(main, "evaluate_explanation", fake_evaluate)
    body = {"notion_id": "k_means", "explanation": "k-means moves centroids to means."}
    result = client.post("/feynman", json=body).json()
    assert result["score"] == 3 and result["recorded"] is True
    assert b'"source":"FEYNMAN"' in SCORES[0]
    assert b'"courseId":"data-science"' in SCORES[0]


def test_feynman_unknown_notion_is_404(client):
    body = {"notion_id": "nope", "explanation": "An explanation long enough to pass."}
    assert client.post("/feynman", json=body).status_code == 404


def test_quiz_returns_questions(client, monkeypatch):
    async def fake_build_quiz(engine, http, course, catalog, n, lang):
        question = QuizQuestion(
            notion_id="k_means",
            question="What is a centroid?",
            options=["mean", "median", "mode", "max"],
            answer_index=0,
            page=290,
            explanation="The mean of the cluster.",
        )
        return [question], False

    monkeypatch.setattr(main, "build_quiz", fake_build_quiz)
    body = client.post("/quiz", json={"n": 1, "lang": "en"}).json()
    assert body["status"] == "ok" and body["questions"][0]["page"] == 290


def test_quiz_result_grades_by_code_and_records(client):
    answers = [
        {"notion_id": "k_means", "answer_index": 0, "chosen_index": 0},
        {"notion_id": "k_means", "answer_index": 1, "chosen_index": 2},
    ]
    body = client.post("/quiz/result", json={"answers": answers}).json()
    assert body == {"scores": {"k_means": 3}, "recorded": True}


def test_mastery_relays_spring(client):
    body = client.get("/mastery").json()
    assert body["status"] == "ok" and body["notions"][0]["notionId"] == "k_means"


def test_plan_without_llm(client):
    body = client.get("/plan", params={"lang": "en"}).json()
    assert body["plan"][0]["notion_id"] == "k_means" and body["plan"][0]["score"] == 2.0


def test_book_pdf_served_per_course_or_404(client, monkeypatch, tmp_path):
    monkeypatch.setattr(
        main, "pdf_path", lambda course_id: tmp_path / f"{course_id}.pdf"
    )
    assert client.get("/book.pdf").status_code == 404
    (tmp_path / "statistics.pdf").write_bytes(b"%PDF-1.7 test")
    assert client.get("/book.pdf").status_code == 404  # default course: no PDF
    response = client.get("/book.pdf", params={"course": "statistics"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
