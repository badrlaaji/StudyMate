"""Tests for the presence relays: study sessions, goal, summary, trophies (offline)."""

import json

import pytest
from fastapi.testclient import TestClient

import api.main as main
from tests.test_api import (
    STUDY_CALLS,
    client,  # noqa: F401 (fixture)
)


def sent(index: int) -> dict:
    """JSON body of the n-th call that reached the fake Spring."""
    return json.loads(STUDY_CALLS[index][2])


def test_start_names_the_course_and_mode(client):  # noqa: F811
    response = client.post("/study/sessions", json={"mode": "CAMERA"})
    assert response.status_code == 201
    assert sent(0) == {"courseId": "data-science", "mode": "CAMERA"}


def test_update_sends_active_seconds_only(client):  # noqa: F811
    assert (
        client.patch("/study/sessions/3", json={"active_seconds": 120}).status_code
        == 200
    )
    method, path, _ = STUDY_CALLS[0]
    assert (method, path, sent(0)) == (
        "PATCH",
        "/api/study/sessions/3",
        {"activeSeconds": 120},
    )


@pytest.mark.parametrize("minutes", [4, 481])
def test_goal_out_of_range_is_refused_before_spring(client, minutes):  # noqa: F811
    body = {"minutes": minutes, "timezone": "Africa/Casablanca"}
    assert client.put("/study/goal", json=body).status_code == 422
    assert STUDY_CALLS == []


def test_goal_summary_and_trophies_are_relayed(client):  # noqa: F811
    body = {"minutes": 45, "timezone": "Africa/Casablanca"}
    assert client.put("/study/goal", json=body).status_code == 200
    assert client.get("/study/summary").status_code == 200
    assert client.get("/trophies").status_code == 200
    assert [call[1] for call in STUDY_CALLS] == [
        "/api/study/goal",
        "/api/study/summary",
        "/api/trophies",
    ]


@pytest.mark.parametrize("path", ["/study/summary", "/trophies"])
def test_presence_routes_need_an_account(client, path):  # noqa: F811
    assert TestClient(main.app).get(path).status_code == 401
    assert STUDY_CALLS == []
