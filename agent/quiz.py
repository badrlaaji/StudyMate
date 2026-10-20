"""Quiz branch: weak notions from Spring (deterministic, D7), MCQ anchored on pages."""

import asyncio
import random

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncEngine

from agent.feynman import round_half_up
from agent.llm import invoke_structured
from agent.spring import fetch_weak_notions
from course.notions import Catalog, Notion
from rag.embeddings import model_name
from rag.store import chunks_for_pages

QUIZ_SIZE = 3
PAGES_PER_NOTION = 2  # text sent to the LLM: the first pages of each notion
LANGUAGES = {"en": "English", "fr": "French"}

QUIZ_PROMPT = """Write a multiple-choice quiz for a student, in {language}.
One question per notion below, based ONLY on the page text given for it.
Each question: 4 options, exactly one correct (answer_index from 0 to 3), the page
number it comes from (one of the [page N] markers of that notion), and a one-sentence
explanation of the correct answer.

{notions}"""


class QuizQuestion(BaseModel):
    """One multiple-choice question, graded by code."""

    notion_id: str
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    answer_index: int = Field(ge=0, le=3)
    page: int
    explanation: str


class QuizDraft(BaseModel):
    """LLM answer: the quiz questions."""

    questions: list[QuizQuestion]


def pick_notions(
    weak_ids: list[str], catalog: Catalog, n: int, rng: random.Random
) -> list[Notion]:
    """Weak notions first (Spring order), then random other notions, n in total."""
    by_id = {notion.id: notion for notion in catalog.notions}
    picked = [by_id[i] for i in weak_ids if i in by_id][:n]
    others = [notion for notion in catalog.notions if notion not in picked]
    return picked + rng.sample(others, max(0, n - len(picked)))


def quiz_prompt(notions: list[Notion], texts: dict[int, str], lang: str) -> str:
    """Give the LLM each notion with the text of its first pages."""
    blocks = []
    for notion in notions:
        pages = notion.pages[:PAGES_PER_NOTION]
        body = "\n".join(f"[page {p}]\n{texts.get(p, '')}" for p in pages)
        blocks.append(f"NOTION {notion.id}: {notion.name_en}\n{body}")
    return QUIZ_PROMPT.format(language=LANGUAGES[lang], notions="\n\n".join(blocks))


def keep_valid(draft: QuizDraft, notions: list[Notion]) -> list[QuizQuestion]:
    """Keep questions about a picked notion whose page belongs to that notion."""
    pages = {notion.id: set(notion.pages[:PAGES_PER_NOTION]) for notion in notions}
    return [q for q in draft.questions if q.page in pages.get(q.notion_id, set())]


def make_quiz(
    notions: list[Notion], texts: dict[int, str], lang: str, llm=None
) -> list[QuizQuestion]:
    """Generate the quiz with the LLM, then drop invalid questions."""
    draft = invoke_structured(QuizDraft, quiz_prompt(notions, texts, lang), llm=llm)
    return keep_valid(draft, notions)


def notion_scores(results: list[tuple[str, bool]]) -> dict[str, int]:
    """Grade by code: per notion, score 0-5 = round half up of 5 x correct / asked."""
    asked: dict[str, int] = {}
    correct: dict[str, int] = {}
    for notion_id, is_correct in results:
        asked[notion_id] = asked.get(notion_id, 0) + 1
        correct[notion_id] = correct.get(notion_id, 0) + int(is_correct)
    return {nid: round_half_up(5 * correct[nid] / asked[nid]) for nid in asked}


async def page_texts(
    engine: AsyncEngine, course: str, notions: list[Notion]
) -> dict[int, str]:
    """Rebuild the text of each page of the notions from the stored chunks."""
    pages = [page for notion in notions for page in notion.pages[:PAGES_PER_NOTION]]
    texts: dict[int, str] = {}
    for chunk in await chunks_for_pages(engine, course, pages, model_name()):
        texts[chunk["page"]] = texts.get(chunk["page"], "") + chunk["text"] + "\n"
    return texts


async def build_quiz(
    engine: AsyncEngine,
    http: httpx.AsyncClient,
    course: str,
    catalog: Catalog,
    n: int,
    lang: str,
    llm=None,
    rng: random.Random | None = None,
) -> tuple[list[QuizQuestion], bool]:
    """Weak notions from Spring, then the quiz; also say if Spring was down."""
    weak = await fetch_weak_notions(http, course, n)
    weak_ids = [item["notionId"] for item in weak or []]
    notions = pick_notions(weak_ids, catalog, n, rng or random.Random())
    texts = await page_texts(engine, course, notions)
    questions = await asyncio.to_thread(make_quiz, notions, texts, lang, llm)
    return questions, weak is None
