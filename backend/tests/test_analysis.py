"""
tests/test_analysis.py
Tests for the Groq job analysis pipeline:
  - POST /api/jobs/{id}/analyze
  - GET  /api/jobs/{id}/requirements
  - PATCH /api/jobs/{id}/requirements/{req_id}

Strategy:
  - JobService, JobRequirementService, and analyze_job are all patched at the
    API layer so no real Supabase or Groq calls are made.
  - Auth bypassed via conftest.py dependency override.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

JOB_ID  = str(uuid4())
REQ_ID  = str(uuid4())
DIM_ID  = str(uuid4())

SAMPLE_JOB = {
    "id":               JOB_ID,
    "recruiter_id":     "11111111-1111-1111-1111-111111111111",
    "title":            "Senior Data Scientist",
    "description":      "Lead ML initiatives across the organisation.",
    "responsibilities": "Build models, mentor junior data scientists.",
    "requirements":     "5+ years ML, Python, strong communication.",
    "status":           "draft",
    "created_at":       "2026-01-01T00:00:00+00:00",
    "updated_at":       "2026-01-01T00:00:00+00:00",
}

SAMPLE_REQ = {
    "id":             REQ_ID,
    "job_id":         JOB_ID,
    "dimension_id":   DIM_ID,
    "dimension_name": "communication",
    "importance":     85,
    "reason":         "The role requires presenting complex findings to non-technical stakeholders.",
    "confirmed":      False,
    "created_at":     "2026-01-01T00:00:00+00:00",
}

SAMPLE_REQ_CONFIRMED = {**SAMPLE_REQ, "confirmed": True, "importance": 90}


# ── POST /api/jobs/{job_id}/analyze ────────────────────────────────────────

def test_analyze_job_success(client):
    """Should return a list of saved requirements on success."""
    with patch("app.api.analysis.JobService") as MockJobSvc, \
         patch("app.api.analysis.JobRequirementService") as MockReqSvc, \
         patch("app.api.analysis.analyze_job") as mock_analyze:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockJobSvc.return_value.update_job.return_value = {**SAMPLE_JOB, "status": "analyzed"}
        mock_analyze.return_value = [MagicMock()]
        MockReqSvc.return_value.save_requirements.return_value = [SAMPLE_REQ]

        response = client.post(f"/api/jobs/{JOB_ID}/analyze")

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["dimension_name"] == "communication"
    assert body["data"][0]["importance"] == 85


def test_analyze_job_not_found(client):
    """Should return 404 when the job doesn't belong to the recruiter."""
    with patch("app.api.analysis.JobService") as MockJobSvc, \
         patch("app.api.analysis.JobRequirementService"), \
         patch("app.api.analysis.analyze_job"):

        MockJobSvc.return_value.get_job.return_value = None

        response = client.post(f"/api/jobs/{JOB_ID}/analyze")

    assert response.status_code == 404


def test_analyze_job_no_description(client):
    """Should return 422 when the job has no description."""
    job_no_desc = {**SAMPLE_JOB, "description": ""}
    with patch("app.api.analysis.JobService") as MockJobSvc, \
         patch("app.api.analysis.JobRequirementService"), \
         patch("app.api.analysis.analyze_job"):

        MockJobSvc.return_value.get_job.return_value = job_no_desc

        response = client.post(f"/api/jobs/{JOB_ID}/analyze")

    assert response.status_code == 422
    assert "description" in response.json()["detail"].lower()


def test_analyze_job_groq_unavailable(client):
    """Should return 503 when Groq is unavailable."""
    from app.ai.groq_client import GroqError

    with patch("app.api.analysis.JobService") as MockJobSvc, \
         patch("app.api.analysis.JobRequirementService"), \
         patch("app.api.analysis.analyze_job") as mock_analyze:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        mock_analyze.side_effect = GroqError("API key not set")

        response = client.post(f"/api/jobs/{JOB_ID}/analyze")

    assert response.status_code == 503


def test_analyze_job_groq_validation_error(client):
    """Should return 422 when Groq output fails Pydantic validation."""
    with patch("app.api.analysis.JobService") as MockJobSvc, \
         patch("app.api.analysis.JobRequirementService"), \
         patch("app.api.analysis.analyze_job") as mock_analyze:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        mock_analyze.side_effect = ValueError("Groq returned invalid structure")

        response = client.post(f"/api/jobs/{JOB_ID}/analyze")

    assert response.status_code == 422


def test_analyze_job_multiple_requirements(client):
    """Should handle multiple dimensions returned by Groq."""
    reqs = [
        {**SAMPLE_REQ, "id": str(uuid4()), "dimension_name": name, "importance": imp}
        for name, imp in [("communication", 85), ("leadership", 70), ("teamwork", 60)]
    ]
    with patch("app.api.analysis.JobService") as MockJobSvc, \
         patch("app.api.analysis.JobRequirementService") as MockReqSvc, \
         patch("app.api.analysis.analyze_job") as mock_analyze:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockJobSvc.return_value.update_job.return_value = SAMPLE_JOB
        mock_analyze.return_value = [MagicMock() for _ in reqs]
        MockReqSvc.return_value.save_requirements.return_value = reqs

        response = client.post(f"/api/jobs/{JOB_ID}/analyze")

    assert response.status_code == 201
    assert len(response.json()["data"]) == 3


# ── GET /api/jobs/{job_id}/requirements ───────────────────────────────────

def test_list_requirements_success(client):
    """Should return the list of requirements ordered by importance."""
    with patch("app.api.analysis.JobService") as MockJobSvc, \
         patch("app.api.analysis.JobRequirementService") as MockReqSvc:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockReqSvc.return_value.list_requirements.return_value = [SAMPLE_REQ]

        response = client.get(f"/api/jobs/{JOB_ID}/requirements")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"][0]["importance"] == 85
    assert body["data"][0]["confirmed"] is False


def test_list_requirements_empty(client):
    """Should return an empty list when no requirements have been generated yet."""
    with patch("app.api.analysis.JobService") as MockJobSvc, \
         patch("app.api.analysis.JobRequirementService") as MockReqSvc:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockReqSvc.return_value.list_requirements.return_value = []

        response = client.get(f"/api/jobs/{JOB_ID}/requirements")

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_list_requirements_job_not_found(client):
    """Should return 404 when the job doesn't exist."""
    with patch("app.api.analysis.JobService") as MockJobSvc, \
         patch("app.api.analysis.JobRequirementService"):

        MockJobSvc.return_value.get_job.return_value = None

        response = client.get(f"/api/jobs/{JOB_ID}/requirements")

    assert response.status_code == 404


# ── PATCH /api/jobs/{job_id}/requirements/{req_id} ────────────────────────

def test_update_requirement_confirm(client):
    """Should confirm a requirement and return the updated row."""
    with patch("app.api.analysis.JobService") as MockJobSvc, \
         patch("app.api.analysis.JobRequirementService") as MockReqSvc:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockReqSvc.return_value.update_requirement.return_value = SAMPLE_REQ_CONFIRMED

        response = client.patch(
            f"/api/jobs/{JOB_ID}/requirements/{REQ_ID}",
            json={"confirmed": True, "importance": 90},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["confirmed"] is True
    assert body["data"]["importance"] == 90


def test_update_requirement_not_found(client):
    """Should return 404 when the requirement doesn't exist."""
    with patch("app.api.analysis.JobService") as MockJobSvc, \
         patch("app.api.analysis.JobRequirementService") as MockReqSvc:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockReqSvc.return_value.update_requirement.return_value = None

        response = client.patch(
            f"/api/jobs/{JOB_ID}/requirements/{REQ_ID}",
            json={"confirmed": True},
        )

    assert response.status_code == 404


def test_update_requirement_invalid_importance(client):
    """Should return 422 when importance is out of 0-100 range."""
    with patch("app.api.analysis.JobService") as MockJobSvc, \
         patch("app.api.analysis.JobRequirementService"):

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB

        response = client.patch(
            f"/api/jobs/{JOB_ID}/requirements/{REQ_ID}",
            json={"importance": 150},
        )

    assert response.status_code == 422


def test_update_requirement_job_not_found(client):
    """Should return 404 when the job doesn't belong to the recruiter."""
    with patch("app.api.analysis.JobService") as MockJobSvc, \
         patch("app.api.analysis.JobRequirementService"):

        MockJobSvc.return_value.get_job.return_value = None

        response = client.patch(
            f"/api/jobs/{JOB_ID}/requirements/{REQ_ID}",
            json={"confirmed": True},
        )

    assert response.status_code == 404
