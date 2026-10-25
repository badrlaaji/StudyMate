"""HTTP client for the Spring Boot mastery service; None means "Spring is down".

Every data route of Spring needs the user's JWT (Authorization: Bearer <token>): the
browser's token is relayed as is, and Spring answers with that user's data only.
Contract: GET /api/notions/weak?course=C&limit=N and GET /api/mastery?course=C return
[{"notionId": str, "average": float, "count": int, ...}]; GET /api/scores?course=C
returns [{"notionId", "source", "score", "createdAt"}] oldest first; POST /api/scores
takes {"courseId", "notionId", "source": "FEYNMAN" | "QUIZ", "score": 0-5}; POST
/api/quiz-answers takes {"courseId", "quizId", "answers": [{"notionId", "status"}]}.
Public: GET /api/health, POST /api/auth/register and /api/auth/login.
"""

import logging

import httpx

from config import get_env

logger = logging.getLogger(__name__)

TIMEOUT_S = 3.0
DOWN = {"detail": "The account service is unavailable. Try again in a moment."}


def make_client() -> httpx.AsyncClient:
    """Create the async client for SPRING_URL (default http://localhost:8080)."""
    base_url = get_env("SPRING_URL", "http://localhost:8080")
    return httpx.AsyncClient(base_url=base_url, timeout=TIMEOUT_S)


def auth(token: str | None) -> dict[str, str]:
    """The Authorization header carrying the user's JWT, or no header."""
    return {"Authorization": f"Bearer {token}"} if token else {}


async def get_json(
    http: httpx.AsyncClient, path: str, params: dict | None, token: str | None
):
    """GET a JSON body; log and return None if Spring does not answer correctly."""
    try:
        response = await http.get(path, params=params, headers=auth(token))
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as error:
        logger.warning("spring unavailable (degraded mode): %s %s", path, error)
        return None


async def spring_alive(http: httpx.AsyncClient) -> bool:
    """True if Spring answers its public health route."""
    return await get_json(http, "/api/health", None, None) is not None


async def fetch_weak_notions(
    http: httpx.AsyncClient, course: str, limit: int, token: str | None
) -> list[dict] | None:
    """Return the user's weak notions of a course (average of last 3 < 3)."""
    params = {"course": course, "limit": limit}
    return await get_json(http, "/api/notions/weak", params, token)


async def fetch_mastery(
    http: httpx.AsyncClient, course: str, token: str | None
) -> list[dict] | None:
    """Return the mastery of every notion the user scored in a course."""
    return await get_json(http, "/api/mastery", {"course": course}, token)


async def fetch_history(
    http: httpx.AsyncClient, course: str, token: str | None
) -> list[dict] | None:
    """Return every score of the user in a course with its time (for FSRS)."""
    return await get_json(http, "/api/scores", {"course": course}, token)


async def post_json(
    http: httpx.AsyncClient, path: str, body: dict, token: str | None
) -> bool:
    """POST a JSON body; return False (and log) if Spring refuses it or is down."""
    try:
        response = await http.post(path, json=body, headers=auth(token))
        response.raise_for_status()
        return True
    except httpx.HTTPError as error:
        logger.warning("not recorded (degraded mode): %s %s", path, error)
        return False


async def post_score(
    http: httpx.AsyncClient,
    course: str,
    notion_id: str,
    source: str,
    score: int,
    token: str | None,
) -> bool:
    """Record a 0-5 score for the user; False if Spring is down."""
    body = {"courseId": course, "notionId": notion_id, "source": source, "score": score}
    return await post_json(http, "/api/scores", body, token)


async def post_quiz_answers(
    http: httpx.AsyncClient,
    course: str,
    quiz_id: str,
    answers: list[dict],
    token: str | None,
) -> bool:
    """Log every question of a quiz (CORRECT, INCORRECT or SKIPPED); False if down."""
    body = {"courseId": course, "quizId": quiz_id, "answers": answers}
    return await post_json(http, "/api/quiz-answers", body, token)


async def relay(
    http: httpx.AsyncClient,
    method: str,
    path: str,
    body: dict | None = None,
    token: str | None = None,
) -> tuple[int, dict]:
    """Pass an account request to Spring as is: (status code, JSON body)."""
    try:
        response = await http.request(method, path, json=body, headers=auth(token))
    except httpx.HTTPError as error:
        logger.warning("account service unavailable: %s %s", path, error)
        return 503, DOWN
    try:
        return response.status_code, response.json()
    except ValueError:  # an empty or non-JSON error body
        return response.status_code, {"detail": response.reason_phrase}
