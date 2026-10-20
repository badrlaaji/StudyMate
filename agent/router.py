"""Router: choose the branch (answer, quiz, plan) and the language of a message."""

import logging
import re
from typing import Literal

from pydantic import BaseModel

from agent.answer import LANGUAGES
from agent.llm import invoke_structured

logger = logging.getLogger(__name__)

ROUTER_PROMPT = """Classify a student's message sent to a study assistant for a
textbook.
route:
- "quiz": the student wants to be quizzed or tested (multiple-choice questions).
- "plan": the student asks what to review, a revision plan, or their weak topics.
- "answer": anything else (a question about the course, or any other question).
lang: "fr" if the message is written in French, otherwise "en".
search_query: the message rewritten as one short {book_language} question to search
the {book_language} textbook (translate if needed, keep the technical terms, add
nothing).

Message: {message}"""

# Fallback rules, used only when the LLM router fails.
QUIZ_RULE = re.compile(
    r"\b(quiz+|qcm|test me|teste-moi|interroge-moi)\b", re.IGNORECASE
)
PLAN_RULE = re.compile(
    r"\b(plan de révision|study plan|revision plan|what should i (review|study)|"
    r"quoi réviser|que dois-je réviser|weak topics|notions faibles)\b",
    re.IGNORECASE,
)
FRENCH_RULE = re.compile(
    r"[éèêàùçôîû]|\b(le|la|les|des|est|une|quoi|comment|pourquoi|quel|quelle|qu'est)\b",
    re.IGNORECASE,
)


class Route(BaseModel):
    """Router decision."""

    route: Literal["answer", "quiz", "plan"]
    lang: Literal["en", "fr"]
    search_query: str  # in the book's language (cross-lingual retrieval)


def fallback_route(message: str) -> Route:
    """Keyword rules: quiz, then plan, else answer; French if French hints."""
    lang = "fr" if FRENCH_RULE.search(message) else "en"
    route = "answer"
    if QUIZ_RULE.search(message):
        route = "quiz"
    elif PLAN_RULE.search(message):
        route = "plan"
    return Route(route=route, lang=lang, search_query=message)  # no translation


def route_message(message: str, book_lang: str = "en", llm=None) -> Route:
    """Ask the LLM router; on any failure use the keyword rules."""
    prompt = ROUTER_PROMPT.format(book_language=LANGUAGES[book_lang], message=message)
    try:
        return invoke_structured(Route, prompt, llm=llm)
    except Exception as error:  # LLM down, quota reached, invalid output
        logger.warning("router fallback (%s): %s", type(error).__name__, error)
        return fallback_route(message)
