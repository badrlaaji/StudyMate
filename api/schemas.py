"""Request and response schemas of the FastAPI service (the API contract)."""

from typing import Literal

from pydantic import BaseModel, Field

Lang = Literal["en", "fr"]


class ChatRequest(BaseModel):
    """POST /chat body; lang is the interface language (the router detects the rest)."""

    message: str = Field(min_length=1, max_length=2000)
    lang: Lang = "en"


class Citation(BaseModel):
    """A verified citation: PDF page and the start of the chunk."""

    page: int
    excerpt: str


class ChatResponse(BaseModel):
    """POST /chat answer: route, verified citations, quiz or plan when routed."""

    route: str
    lang: Lang
    answer: str | None = None
    citations: list[Citation] = []
    status: str
    quiz: list[dict] | None = None
    plan: list[dict] | None = None


class NotionOut(BaseModel):
    """One notion of the catalogue in the requested language."""

    id: str
    name: str
    chapter: int
    section: str
    pages: list[int]
    key_ideas: list[str]


class FeynmanRequest(BaseModel):
    """POST /feynman body."""

    notion_id: str
    explanation: str = Field(min_length=20, max_length=4000)
    lang: Lang = "en"


class FeynmanResponse(BaseModel):
    """Feynman result: the score is computed by code (D2)."""

    covered: list[str]
    missing: list[str]
    errors: list[str]
    score: int = Field(ge=0, le=5)
    follow_up: str
    pages: list[int]
    recorded: bool  # False when Spring is down (degraded mode)


class QuizRequest(BaseModel):
    """POST /quiz body."""

    n: int = Field(default=3, ge=1, le=10)
    lang: Lang = "en"


class QuizAnswer(BaseModel):
    """One answered question, as shown and checked by the interface."""

    notion_id: str
    answer_index: int = Field(ge=0, le=3)
    chosen_index: int = Field(ge=0, le=3)


class QuizResultRequest(BaseModel):
    """POST /quiz/result body."""

    answers: list[QuizAnswer] = Field(min_length=1)


class QuizResultResponse(BaseModel):
    """Scores per notion (0-5) and whether Spring recorded them."""

    scores: dict[str, int]
    recorded: bool
