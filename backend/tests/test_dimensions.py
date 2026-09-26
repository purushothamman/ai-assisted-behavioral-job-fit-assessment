"""
tests/test_dimensions.py
Tests for GET /api/dimensions and GET /api/dimensions/{dimension_id}.

Strategy: patch DimensionService at the API layer (same pattern as test_jobs.py).
Auth is bypassed via conftest.py dependency override.
"""
from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest

DIM_ID = str(uuid4())
IND_ID_1 = str(uuid4())
IND_ID_2 = str(uuid4())

SAMPLE_DIM = {
    "id": DIM_ID,
    "name": "communication",
    "description": "Ability to clearly convey information and actively listen",
    "is_active": True,
    "created_at": "2026-01-01T00:00:00+00:00",
}

SAMPLE_INDICATOR_1 = {
    "id": IND_ID_1,
    "dimension_id": DIM_ID,
    "name": "clarity",
    "description": "Expresses ideas clearly and concisely",
    "example_behaviors": None,
    "created_at": "2026-01-01T00:00:00+00:00",
}

SAMPLE_INDICATOR_2 = {
    "id": IND_ID_2,
    "dimension_id": DIM_ID,
    "name": "active_listening",
    "description": "Demonstrates attentiveness and understanding",
    "example_behaviors": None,
    "created_at": "2026-01-01T00:00:00+00:00",
}

SAMPLE_DIM_DETAIL = {
    **SAMPLE_DIM,
    "indicators": [SAMPLE_INDICATOR_1, SAMPLE_INDICATOR_2],
}


# ── GET /api/dimensions ────────────────────────────────────────────────────

def test_list_dimensions_success(client):
    """Should return a list of DimensionRead objects."""
    with patch("app.api.dimensions.DimensionService") as MockSvc:
        instance = MockSvc.return_value
        instance.list_dimensions.return_value = [SAMPLE_DIM]

        response = client.get("/api/dimensions")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert len(body["data"]) == 1
    assert body["data"][0]["name"] == "communication"
    assert body["data"][0]["is_active"] is True


def test_list_dimensions_empty(client):
    """Should return an empty list when no dimensions exist."""
    with patch("app.api.dimensions.DimensionService") as MockSvc:
        instance = MockSvc.return_value
        instance.list_dimensions.return_value = []

        response = client.get("/api/dimensions")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == []


def test_list_dimensions_multiple(client):
    """Should return all six dimensions from seed data."""
    six_dims = [
        {**SAMPLE_DIM, "id": str(uuid4()), "name": n}
        for n in [
            "communication", "teamwork", "adaptability",
            "decision_making", "leadership", "stress_management",
        ]
    ]
    with patch("app.api.dimensions.DimensionService") as MockSvc:
        instance = MockSvc.return_value
        instance.list_dimensions.return_value = six_dims

        response = client.get("/api/dimensions")

    assert response.status_code == 200
    assert len(response.json()["data"]) == 6


def test_list_dimensions_service_error(client):
    """Should return 500 when the service raises an exception."""
    with patch("app.api.dimensions.DimensionService") as MockSvc:
        instance = MockSvc.return_value
        instance.list_dimensions.side_effect = RuntimeError("DB unavailable")

        response = client.get("/api/dimensions")

    assert response.status_code == 500


# ── GET /api/dimensions/{dimension_id} ────────────────────────────────────

def test_get_dimension_success(client):
    """Should return a DimensionDetail with nested indicators."""
    with patch("app.api.dimensions.DimensionService") as MockSvc:
        instance = MockSvc.return_value
        instance.get_dimension.return_value = SAMPLE_DIM_DETAIL

        response = client.get(f"/api/dimensions/{DIM_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["id"] == DIM_ID
    assert data["name"] == "communication"
    assert isinstance(data["indicators"], list)
    assert len(data["indicators"]) == 2


def test_get_dimension_indicators_content(client):
    """Indicators within the detail response should have correct fields."""
    with patch("app.api.dimensions.DimensionService") as MockSvc:
        instance = MockSvc.return_value
        instance.get_dimension.return_value = SAMPLE_DIM_DETAIL

        response = client.get(f"/api/dimensions/{DIM_ID}")

    indicators = response.json()["data"]["indicators"]
    names = {ind["name"] for ind in indicators}
    assert "clarity" in names
    assert "active_listening" in names


def test_get_dimension_not_found(client):
    """Should return 404 when the dimension does not exist."""
    with patch("app.api.dimensions.DimensionService") as MockSvc:
        instance = MockSvc.return_value
        instance.get_dimension.return_value = None

        response = client.get(f"/api/dimensions/{DIM_ID}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_dimension_invalid_uuid(client):
    """Should return 422 when the UUID path param is malformed."""
    response = client.get("/api/dimensions/not-a-valid-uuid")
    assert response.status_code == 422


def test_get_dimension_service_error(client):
    """Should return 500 when the service raises an exception."""
    with patch("app.api.dimensions.DimensionService") as MockSvc:
        instance = MockSvc.return_value
        instance.get_dimension.side_effect = RuntimeError("Timeout")

        response = client.get(f"/api/dimensions/{DIM_ID}")

    assert response.status_code == 500


def test_get_dimension_no_indicators(client):
    """Should return an empty indicators list if the dimension has none."""
    dim_no_indicators = {**SAMPLE_DIM, "indicators": []}
    with patch("app.api.dimensions.DimensionService") as MockSvc:
        instance = MockSvc.return_value
        instance.get_dimension.return_value = dim_no_indicators

        response = client.get(f"/api/dimensions/{DIM_ID}")

    assert response.status_code == 200
    assert response.json()["data"]["indicators"] == []
