"""
tests/test_jobs.py
Tests for the Job CRUD API (/api/jobs).
The Supabase service layer is mocked so tests are purely in-process.
Auth is bypassed via the conftest.py dependency override.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

RECRUITER_ID = "11111111-1111-1111-1111-111111111111"
JOB_ID = str(uuid4())

SAMPLE_JOB = {
    "id": JOB_ID,
    "recruiter_id": RECRUITER_ID,
    "title": "Senior Data Scientist",
    "description": "Lead data science initiatives.",
    "responsibilities": "Model development, team mentoring.",
    "requirements": "5+ years ML experience.",
    "status": "draft",
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}

SAMPLE_LIST_ITEM = {
    "id": JOB_ID,
    "title": "Senior Data Scientist",
    "status": "draft",
    "created_at": "2026-01-01T00:00:00+00:00",
}


# ── POST /api/jobs ─────────────────────────────────────────────────────────

def test_create_job_success(client):
    with patch("app.api.jobs.JobService") as MockSvc:
        instance = MockSvc.return_value
        instance.create_job.return_value = SAMPLE_JOB

        response = client.post(
            "/api/jobs",
            json={
                "title": "Senior Data Scientist",
                "description": "Lead data science initiatives.",
                "responsibilities": "Model development, team mentoring.",
                "requirements": "5+ years ML experience.",
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["title"] == "Senior Data Scientist"
    assert body["data"]["status"] == "draft"


def test_create_job_validation_fails(client):
    """Title too short should trigger 422 Unprocessable Entity."""
    response = client.post(
        "/api/jobs",
        json={"title": "X", "description": "short"},  # title min_length=2 ok, desc min_length=10 fail
    )
    assert response.status_code == 422


def test_create_job_missing_required_field(client):
    """Missing 'title' should trigger 422."""
    response = client.post(
        "/api/jobs",
        json={"description": "A description with enough characters."},
    )
    assert response.status_code == 422


# ── GET /api/jobs ──────────────────────────────────────────────────────────

def test_list_jobs_success(client):
    with patch("app.api.jobs.JobService") as MockSvc:
        instance = MockSvc.return_value
        instance.list_jobs.return_value = [SAMPLE_LIST_ITEM]

        response = client.get("/api/jobs")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["title"] == "Senior Data Scientist"


def test_list_jobs_empty(client):
    with patch("app.api.jobs.JobService") as MockSvc:
        instance = MockSvc.return_value
        instance.list_jobs.return_value = []

        response = client.get("/api/jobs")

    assert response.status_code == 200
    assert response.json()["data"] == []


# ── GET /api/jobs/{job_id} ─────────────────────────────────────────────────

def test_get_job_success(client):
    with patch("app.api.jobs.JobService") as MockSvc:
        instance = MockSvc.return_value
        instance.get_job.return_value = SAMPLE_JOB

        response = client.get(f"/api/jobs/{JOB_ID}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == JOB_ID


def test_get_job_not_found(client):
    with patch("app.api.jobs.JobService") as MockSvc:
        instance = MockSvc.return_value
        instance.get_job.return_value = None

        response = client.get(f"/api/jobs/{JOB_ID}")

    assert response.status_code == 404


# ── PATCH /api/jobs/{job_id} ───────────────────────────────────────────────

def test_update_job_success(client):
    updated = {**SAMPLE_JOB, "title": "Principal Data Scientist"}
    with patch("app.api.jobs.JobService") as MockSvc:
        instance = MockSvc.return_value
        instance.update_job.return_value = updated

        response = client.patch(
            f"/api/jobs/{JOB_ID}",
            json={"title": "Principal Data Scientist"},
        )

    assert response.status_code == 200
    assert response.json()["data"]["title"] == "Principal Data Scientist"


def test_update_job_not_found(client):
    with patch("app.api.jobs.JobService") as MockSvc:
        instance = MockSvc.return_value
        instance.update_job.return_value = None

        response = client.patch(
            f"/api/jobs/{JOB_ID}",
            json={"title": "New Title Here"},
        )

    assert response.status_code == 404


# ── DELETE /api/jobs/{job_id} ──────────────────────────────────────────────

def test_delete_job_success(client):
    with patch("app.api.jobs.JobService") as MockSvc:
        instance = MockSvc.return_value
        instance.delete_job.return_value = True

        response = client.delete(f"/api/jobs/{JOB_ID}")

    assert response.status_code == 204


def test_delete_job_not_found(client):
    with patch("app.api.jobs.JobService") as MockSvc:
        instance = MockSvc.return_value
        instance.delete_job.return_value = False

        response = client.delete(f"/api/jobs/{JOB_ID}")

    assert response.status_code == 404
