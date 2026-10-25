"""Tests for the public demo data (no network): shape, agreement with the catalogues."""

import json

import pytest

from agent.quiz import QuizQuestion
from course.courses import get_course, load_registry, notions_path
from course.notions import load_catalog
from scripts.build_demo import DEMO_PATH, FEYNMAN, QUESTIONS, course_entry

DEMO = json.loads(DEMO_PATH.read_text(encoding="utf-8"))
COURSES = {course["id"]: course for course in DEMO["courses"]}


def test_course_entry_has_what_the_web_app_reads():
    registry = load_registry()
    course = get_course(registry, "data-science")
    entry = course_entry(course, load_catalog(notions_path("data-science")), 12)
    assert entry["chunks"] == 12
    assert entry["pdf_url"].startswith("https://")
    assert {"scope_en", "scope_fr", "license", "attribution", "notions"} <= set(entry)


def test_demo_covers_every_question_and_example():
    assert DEMO["default"] in COURSES
    for course_id, questions in QUESTIONS.items():
        stored = [(a["lang"], a["question"]) for a in COURSES[course_id]["answers"]]
        assert stored == questions
        examples = [(f["notion_id"], f["lang"]) for f in COURSES[course_id]["feynman"]]
        assert examples == [
            (notion_id, lang) for notion_id, lang, _ in FEYNMAN[course_id]
        ]


@pytest.mark.parametrize("course_id", sorted(QUESTIONS))
def test_demo_notions_match_the_catalogue(course_id):
    # A failure means the catalogue changed: rebuild with scripts.build_demo.
    catalog = load_catalog(notions_path(course_id))
    assert COURSES[course_id]["notions"] == [n.model_dump() for n in catalog.notions]


@pytest.mark.parametrize("course_id", sorted(QUESTIONS))
def test_demo_answers_and_quizzes_are_valid(course_id):
    course = COURSES[course_id]
    ids = {notion["id"] for notion in course["notions"]}
    for item in course["answers"]:
        response = item["response"]
        assert response["course"] == course_id
        if response["status"] == "ok":  # verified answers only, as in the API
            assert response["answer"] and response["citations"]
    for lang in ("en", "fr"):
        assert course["quiz"][lang], f"no {lang} quiz"
        for question in course["quiz"][lang]:
            assert QuizQuestion.model_validate(question).notion_id in ids
    for example in course["feynman"]:
        assert 0 <= example["result"]["score"] <= 5
