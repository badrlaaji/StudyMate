"""Tests for accounts: the API relays sign-up, login and the user's token to Spring."""

import pytest
from fastapi.testclient import TestClient

import api.main as main
from tests.test_api import (
    SCORES,
    client,  # noqa: F401 (fixture)
)

ADA = {"email": "ada@example.org", "password": "correct horse"}


@pytest.fixture
def anonymous(client):  # noqa: F811
    """The same app, called without any token."""
    return TestClient(main.app)


def test_register_and_login_are_relayed(anonymous):
    assert anonymous.post("/auth/register", json=ADA).status_code == 201
    response = anonymous.post("/auth/login", json=ADA)
    assert response.status_code == 200 and response.json()["token"] == "a.b.c"


def test_wrong_password_keeps_springs_401(anonymous):
    wrong = ADA | {"password": "wrong password"}
    assert anonymous.post("/auth/login", json=wrong).status_code == 401


def test_bad_email_or_short_password_is_422_before_spring(anonymous):
    assert (
        anonymous.post("/auth/register", json=ADA | {"password": "short"}).status_code
        == 422
    )
    assert (
        anonymous.post("/auth/register", json=ADA | {"email": "nope"}).status_code
        == 422
    )


def test_me_needs_a_token(anonymous, client):  # noqa: F811
    assert anonymous.get("/me").status_code == 401
    assert client.get("/me").json()["email"] == "ada@example.org"


@pytest.mark.parametrize("path", ["/mastery", "/plan", "/review"])
def test_progress_without_token_is_signed_out(anonymous, path):
    assert anonymous.get(path).json()["status"] == "signed_out"


def test_quiz_result_without_token_is_graded_not_saved(anonymous):
    answers = [{"notion_id": "k_means", "answer_index": 0, "chosen_index": 0}]
    body = anonymous.post("/quiz/result", json={"answers": answers}).json()
    assert body["scores"] == {"k_means": 5} and body["recorded"] is False
    assert SCORES == []


def test_a_forged_bearer_header_is_not_trusted(client):  # noqa: F811
    # FastAPI only relays the token: Spring checks the signature (here: refuses it).
    body = client.get("/mastery", headers={"Authorization": "Bearer forged"}).json()
    assert body["status"] == "degraded" and body["notions"] == []


def test_bearer_parsing():
    def request(header: str):
        return type("R", (), {"headers": {"authorization": header}})()

    assert main.bearer(request("Bearer abc")) == "abc"
    assert main.bearer(request("Bearer ")) is None
    assert main.bearer(request("Basic abc")) is None
    assert main.bearer(request("")) is None
