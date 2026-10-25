"""Request and response schemas of the FastAPI service (the API contract)."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from course.courses import COURSE_ID_PATTERN
from course.upload import UPLOAD_ID_PATTERN

Lang = Literal["en", "fr"]
# Course id (see course/courses.json); None = the default course.
CourseId = Annotated[str, Field(pattern=COURSE_ID_PATTERN)] | None


class ChatRequest(BaseModel):
    """POST /chat body; lang is the interface language (the router detects the rest)."""

    message: str = Field(min_length=1, max_length=2000)
    lang: Lang = "en"
    course: CourseId = None


class Citation(BaseModel):
    """A verified citation: PDF page and the start of the chunk."""

    page: int
    excerpt: str


class ChatResponse(BaseModel):
    """POST /chat answer: route, verified citations, quiz or plan when routed."""

    course: str
    route: str
    lang: Lang
    answer: str | None = None
    citations: list[Citation] = []
    status: str
    quiz: list[dict] | None = None
    plan: list[dict] | None = None


class CourseOut(BaseModel):
    """One course of the library, with what is ready for it."""

    id: str
    title: str
    scope: str
    book_lang: Lang
    license: str
    attribution: str
    book_url: str
    default: bool
    pdf: bool  # PDF downloaded
    chunks: int | None  # indexed chunks (None: database unavailable)
    notions: int  # 0 until the catalogue is drafted
    validated: bool  # catalogue reviewed by hand (D1)
    uploaded: bool  # added from the interface (files in data/, deletable)
    job: str | None  # uploaded course: queued, indexing, drafting, ready or failed
    job_detail: str = ""


class NewCourse(BaseModel):
    """POST /courses body: a course built from an uploaded PDF."""

    upload_id: str = Field(pattern=UPLOAD_ID_PATTERN)
    title: str = Field(min_length=3, max_length=120)
    book_lang: Lang = "en"
    license: str = Field(min_length=2, max_length=80)
    attribution: str = Field(min_length=2, max_length=300)
    chapters: list[int] = []
    pages: list[int] = []  # [first, last] when no chapter is chosen
    rights: bool = False  # "I may use this document; it holds no personal data"


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
    course: CourseId = None


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
    course: CourseId = None


class QuizAnswer(BaseModel):
    """One answered question, as shown and checked by the interface."""

    notion_id: str
    answer_index: int = Field(ge=0, le=3)
    # None = skipped ("passée"): no score, so no review date and no mastery change.
    chosen_index: int | None = Field(default=None, ge=0, le=3)


class QuizResultRequest(BaseModel):
    """POST /quiz/result body."""

    answers: list[QuizAnswer] = Field(min_length=1)
    course: CourseId = None


class QuizResultResponse(BaseModel):
    """Scores per notion (0-5) and whether Spring recorded them."""

    scores: dict[str, int]
    recorded: bool
    skipped: int = 0  # questions passed without an answer (not graded)


class AuthRequest(BaseModel):
    """Sign-up or login body, checked again by Spring (which hashes the password)."""

    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+$")
    password: str = Field(min_length=8, max_length=72)  # BCrypt reads 72 bytes at most


class StudyStart(BaseModel):
    """POST /study/sessions: start measuring the estimated study time."""

    course: CourseId = None
    mode: Literal["CAMERA", "MANUAL"] = "MANUAL"


class StudyUpdate(BaseModel):
    """PATCH /study/sessions/{id}: the new total of active seconds (never an image)."""

    active_seconds: int = Field(ge=0, le=86_400)


class StudyGoal(BaseModel):
    """PUT /study/goal: 5 to 480 minutes a day, in an IANA time zone."""

    minutes: int = Field(ge=5, le=480)
    timezone: str = Field(min_length=1, max_length=64)
