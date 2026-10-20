"""Evaluation question set: Pydantic schema and loading (D3)."""

from pathlib import Path

from pydantic import BaseModel, Field

from config import ROOT

QUESTIONS_PATH = ROOT / "eval" / "questions.json"


class EvalQuestion(BaseModel):
    """One bilingual question with the PDF pages that answer it."""

    id: str
    notion: str | None
    pages: list[int] = Field(min_length=1)
    en: str
    fr: str


class Trap(BaseModel):
    """One out-of-course question (the agent must refuse it)."""

    id: str
    en: str
    fr: str


class QuestionSet(BaseModel):
    """D3: 10 dev, 20 frozen test, 5 traps."""

    source: str
    license: str
    validated: bool = False
    note: str
    dev: list[EvalQuestion] = Field(min_length=10, max_length=10)
    test: list[EvalQuestion] = Field(min_length=20, max_length=20)
    traps: list[Trap] = Field(min_length=5, max_length=5)


def load_questions(path: Path = QUESTIONS_PATH) -> QuestionSet:
    """Read and validate questions.json."""
    return QuestionSet.model_validate_json(path.read_text(encoding="utf-8"))
