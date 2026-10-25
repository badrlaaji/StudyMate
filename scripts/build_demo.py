"""Build the public demo data (frontend/demo/data.json): real answers, computed once.

Usage: uv run python -m scripts.build_demo   (courses indexed, GOOGLE_API_KEY set)
The demo then runs with DEMO_MODE=1 in the Next.js app: no API, no database, no LLM.
"""

import asyncio
import json
import os
import random

from agent.feynman import evaluate_explanation
from agent.graph import build_graph, to_response
from agent.quiz import build_quiz
from agent.spring import make_client
from config import ROOT
from course.courses import Course, get_course, load_registry, notions_path
from course.notions import Catalog, load_catalog
from rag.embeddings import model_name
from rag.store import count_chunks, get_engine

DEMO_PATH = ROOT / "frontend" / "demo" / "data.json"
PAUSE_S = float(os.environ.get("LLM_PAUSE_S", "6"))  # stay under the per-minute quota
QUIZ_SETS = 3  # quizzes of 3 questions per course and language
SEED = 42
QUESTIONS = {
    "data-science": [
        ("en", "How does a random forest combine many decision trees?"),
        ("en", "What is the difference between overfitting and underfitting?"),
        ("en", "How does the k-means algorithm assign points to clusters?"),
        ("en", "What does a convolutional layer do in a CNN?"),
        ("en", "What is the capital of Morocco?"),  # out of the course: refused
        ("fr", "Qu'est-ce que le surapprentissage et comment le détecter ?"),
        ("fr", "Comment fonctionne la rétropropagation du gradient ?"),
    ],
    "statistics": [
        ("en", "What does the correlation coefficient r measure?"),
        ("en", "What is the least-squares regression line?"),
        ("en", "How do you predict a value with the regression line?"),
        ("fr", "Comment repérer une valeur aberrante avec la droite de régression ?"),
    ],
}
FEYNMAN = {
    "data-science": [
        (
            "k_means_clustering",
            "en",
            "K-means groups unlabeled points into k clusters chosen in advance. It"
            " places k centroids, assigns each point to the nearest centroid, then"
            " moves each centroid to the mean of its points, and repeats until nothing"
            " changes.",
        ),
        (
            "overfitting_and_underfitting",
            "fr",
            "Le surapprentissage, c'est quand le modèle apprend par cœur les données"
            " d'entraînement, même le bruit : il est très bon sur ces données mais"
            " mauvais sur de nouvelles. Le sous-apprentissage, c'est l'inverse : le"
            " modèle est trop simple et rate même les données d'entraînement.",
        ),
    ],
    "statistics": [
        (
            "correlation_coefficient",
            "en",
            "The correlation coefficient r goes from -1 to 1. It tells how strong the"
            " straight-line relationship between x and y is, and its sign tells the"
            " direction: positive when y grows with x, negative otherwise.",
        ),
    ],
}


def notion_entries(catalog: Catalog) -> list[dict]:
    """Notions in both languages (the demo serves /notions without the API)."""
    return [notion.model_dump() for notion in catalog.notions]


async def chat_answers(app, course_id: str) -> list[dict]:
    """Run the real agent on the demo questions of a course."""
    answers = []
    for lang, question in QUESTIONS[course_id]:
        state = await app.ainvoke({"message": question, "course": course_id})
        response = to_response(state)
        answers.append({"question": question, "lang": lang, "response": response})
        print(f"  {course_id} {response['status']:9} {question}")
        await asyncio.sleep(PAUSE_S)
    return answers


async def quiz_pool(engine, http, course_id: str, catalog: Catalog) -> dict:
    """A few real quizzes per language, generated from the book pages."""
    rng = random.Random(SEED)
    pool = {}
    for lang in ("en", "fr"):
        questions, seen = [], set()
        for _ in range(QUIZ_SETS):
            batch, _ = await build_quiz(
                engine, http, course_id, catalog, 3, lang, rng=rng
            )
            for question in batch:
                if question.question not in seen:
                    seen.add(question.question)
                    questions.append(question.model_dump())
            await asyncio.sleep(PAUSE_S)
        pool[lang] = questions
        print(f"  {course_id} quiz {lang}: {len(questions)} questions")
    return pool


def feynman_examples(course_id: str, catalog: Catalog) -> list[dict]:
    """Example explanations judged by the real Feynman judge (score by code)."""
    notions = {notion.id: notion for notion in catalog.notions}
    examples = []
    for notion_id, lang, text in FEYNMAN[course_id]:
        result = evaluate_explanation(notions[notion_id], text, lang)
        examples.append(
            {
                "notion_id": notion_id,
                "lang": lang,
                "explanation": text,
                "result": result,
            }
        )
        print(f"  {course_id} feynman {notion_id}: {result['score']}/5")
    return examples


def course_entry(course: Course, catalog: Catalog, chunks: int) -> dict:
    """What the library and the reader need to know about a course."""
    keys = (
        "id",
        "title",
        "scope_en",
        "scope_fr",
        "book_lang",
        "license",
        "attribution",
    )
    entry = {key: getattr(course, key) for key in keys}
    entry |= {"book_url": course.book_url, "pdf_url": course.pdf_url, "chunks": chunks}
    entry["notions"] = notion_entries(catalog)
    return entry


async def build() -> dict:
    """Compute every demo answer with the real pipeline."""
    registry = load_registry()
    engine, http = get_engine(), make_client()
    catalogs = {cid: load_catalog(notions_path(cid)) for cid in QUESTIONS}
    app = build_graph(engine, http, registry, catalogs)
    data = {"default": registry.default, "courses": []}
    try:
        for course_id, catalog in catalogs.items():
            course = get_course(registry, course_id)
            chunks = await count_chunks(engine, course_id, model_name())
            entry = course_entry(course, catalog, chunks)
            entry["answers"] = await chat_answers(app, course_id)
            entry["quiz"] = await quiz_pool(engine, http, course_id, catalog)
            entry["feynman"] = await asyncio.to_thread(
                feynman_examples, course_id, catalog
            )
            data["courses"].append(entry)
    finally:
        await http.aclose()
        await engine.dispose()
    return data


def main() -> None:
    """Build and save the demo data."""
    data = asyncio.run(build())
    DEMO_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=1)
    DEMO_PATH.write_text(text + "\n", encoding="utf-8")
    print(f"{DEMO_PATH} ({len(text) // 1024} KB)")


if __name__ == "__main__":
    main()
