"""HTTP client for the Spring Boot mastery service; None means "Spring is down".

Contract: GET /api/notions/weak?course=C&limit=N and GET /api/mastery?course=C return
[{"notionId": str, "average": float, "count": int, ...}]; GET /api/scores?course=C
returns [{"notionId", "source", "score", "createdAt"}] oldest first; POST /api/scores
takes {"courseId", "notionId", "source": "FEYNMAN" | "QUIZ", "score": 0-5}.
"""

import logging

import httpx

from config import get_env

logger = logging.getLogger(__name__)

TIMEOUT_S = 3.0


def make_client() -> httpx.AsyncClient:
    """Create the async client for SPRING_URL (default http://localhost:8080)."""
    base_url = get_env("SPRING_URL", "http://localhost:8080")
    return httpx.AsyncClient(base_url=base_url, timeout=TIMEOUT_S)


async def get_json(http: httpx.AsyncClient, path: str, params: dict | None = None):
    """GET a JSON body; log and return None if Spring does not answer correctly."""
    try:
        response = await http.get(path, params=params)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as error:
        logger.warning("spring unavailable (degraded mode): %s %s", path, error)
        return None


async def fetch_weak_notions(
    http: httpx.AsyncClient, course: str, limit: int
) -> list[dict] | None:
    """Return the weak notions of a course (average of last 3 < 3), weakest first."""
    return await get_json(http, "/api/notions/weak", {"course": course, "limit": limit})


async def fetch_mastery(http: httpx.AsyncClient, course: str) -> list[dict] | None:
    """Return the mastery of every scored notion of a course."""
    return await get_json(http, "/api/mastery", {"course": course})


async def fetch_history(http: httpx.AsyncClient, course: str) -> list[dict] | None:
    """Return every score of a course with its time, oldest first (for FSRS)."""
    return await get_json(http, "/api/scores", {"course": course})


async def post_score(
    http: httpx.AsyncClient, course: str, notion_id: str, source: str, score: int
) -> bool:
    """Record a 0-5 score; return False (and log) if Spring is down."""
    body = {"courseId": course, "notionId": notion_id, "source": source, "score": score}
    try:
        response = await http.post("/api/scores", json=body)
        response.raise_for_status()
        return True
    except httpx.HTTPError as error:
        logger.warning("score not recorded (degraded mode): %s %s", body, error)
        return False
