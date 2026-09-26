"""
tests/test_sessions.py
Tests for the Phase 5 candidate session pipeline:
  - POST /api/jobs/{id}/sessions           (recruiter: create session)
  - GET  /api/jobs/{id}/sessions           (recruiter: list sessions)
  - GET  /api/sessions/{token}             (public: candidate fetches assessment)
  - POST /api/sessions/{token}/responses   (public: candidate submits answers)

Strategy:
  - JobService and SessionService are patched at the API layer.
  - Auth bypassed via conftest.py dependency override for recruiter routes.
  - Public endpoints require no auth — tested without override.
  - No real Supabase calls are made.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

JOB_ID     = str(uuid4())
SESSION_ID = str(uuid4())
TOKEN      = str(uuid4())
Q_ID_1     = str(uuid4())
Q_ID_2     = str(uuid4())

FUTURE_EXPIRY = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
PAST_EXPIRY   = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

SAMPLE_JOB = {
    "id":               JOB_ID,
    "recruiter_id":     "11111111-1111-1111-1111-111111111111",
    "title":            "Senior Data Scientist",
    "description":      "Lead ML initiatives across the organisation.",
    "responsibilities": "Build models, mentor junior data scientists.",
    "requirements":     "5+ years ML, Python, strong communication.",
    "status":           "questions_generated",
    "created_at":       "2026-01-01T00:00:00+00:00",
    "updated_at":       "2026-01-01T00:00:00+00:00",
}

SAMPLE_SESSION = {
    "id":              SESSION_ID,
    "job_id":          JOB_ID,
    "token":           TOKEN,
    "candidate_name":  "Alice Smith",
    "candidate_email": "alice@example.com",
    "status":          "pending",
    "expires_at":      FUTURE_EXPIRY,
    "submitted_at":    None,
    "created_at":      "2026-01-01T00:00:00+00:00",
}

SAMPLE_SESSION_COMPLETED = {
    **SAMPLE_SESSION,
    "status":       "completed",
    "submitted_at": "2026-01-02T12:00:00+00:00",
}

SAMPLE_SESSION_EXPIRED = {
    **SAMPLE_SESSION,
    "status":     "pending",
    "expires_at": PAST_EXPIRY,
}

SAMPLE_QUESTION = {
    "id":             Q_ID_1,
    "job_id":         JOB_ID,
    "dimension_id":   str(uuid4()),
    "dimension_name": "communication",
    "question":       "Tell me about a time you explained a complex ML model to non-technical stakeholders.",
    "type":           "behavioral",
    "difficulty":     "medium",
    "indicators":     ["Clear explanation", "Adapted language", "Measurable outcome"],
}

SAMPLE_RESPONSE = {
    "id":          str(uuid4()),
    "session_id":  SESSION_ID,
    "question_id": Q_ID_1,
    "answer":      "In my previous role, I was tasked with presenting a recommendation system to a C-suite audience.",
    "created_at":  "2026-01-02T12:00:00+00:00",
}

SAMPLE_PUBLIC_JOB = {
    "id":          JOB_ID,
    "title":       "Senior Data Scientist",
    "description": "Lead ML initiatives across the organisation.",
}


# ── POST /api/jobs/{job_id}/sessions ─────────────────────────────────────────

def test_create_session_success(client):
    """Should create a session and return token + session details."""
    with patch("app.api.sessions.JobService") as MockJobSvc, \
         patch("app.api.sessions.SessionService") as MockSsnSvc:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockSsnSvc.return_value.get_approved_questions.return_value = [SAMPLE_QUESTION]
        MockSsnSvc.return_value.create_session.return_value = SAMPLE_SESSION

        response = client.post(
            f"/api/jobs/{JOB_ID}/sessions",
            json={
                "candidate_name":  "Alice Smith",
                "candidate_email": "alice@example.com",
                "expires_in_days": 7,
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["token"] == TOKEN
    assert body["data"]["candidate_name"] == "Alice Smith"
    assert body["data"]["status"] == "pending"


def test_create_session_job_not_found(client):
    """Should return 404 when the job doesn't belong to the recruiter."""
    with patch("app.api.sessions.JobService") as MockJobSvc, \
         patch("app.api.sessions.SessionService"):

        MockJobSvc.return_value.get_job.return_value = None

        response = client.post(
            f"/api/jobs/{JOB_ID}/sessions",
            json={
                "candidate_name":  "Alice Smith",
                "candidate_email": "alice@example.com",
            },
        )

    assert response.status_code == 404


def test_create_session_no_approved_questions(client):
    """Should return 422 when job has no approved questions."""
    with patch("app.api.sessions.JobService") as MockJobSvc, \
         patch("app.api.sessions.SessionService") as MockSsnSvc:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockSsnSvc.return_value.get_approved_questions.return_value = []

        response = client.post(
            f"/api/jobs/{JOB_ID}/sessions",
            json={
                "candidate_name":  "Alice Smith",
                "candidate_email": "alice@example.com",
            },
        )

    assert response.status_code == 422
    assert "approved" in response.json()["detail"].lower()


def test_create_session_invalid_payload(client):
    """Should return 422 when required fields are missing."""
    response = client.post(
        f"/api/jobs/{JOB_ID}/sessions",
        json={},  # missing candidate_name and candidate_email
    )
    assert response.status_code == 422


# ── GET /api/jobs/{job_id}/sessions ──────────────────────────────────────────

def test_list_sessions_success(client):
    """Should return all sessions for a job."""
    with patch("app.api.sessions.JobService") as MockJobSvc, \
         patch("app.api.sessions.SessionService") as MockSsnSvc:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockSsnSvc.return_value.list_sessions.return_value = [SAMPLE_SESSION]

        response = client.get(f"/api/jobs/{JOB_ID}/sessions")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["candidate_email"] == "alice@example.com"


def test_list_sessions_empty(client):
    """Should return empty list when no sessions exist."""
    with patch("app.api.sessions.JobService") as MockJobSvc, \
         patch("app.api.sessions.SessionService") as MockSsnSvc:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockSsnSvc.return_value.list_sessions.return_value = []

        response = client.get(f"/api/jobs/{JOB_ID}/sessions")

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_list_sessions_job_not_found(client):
    """Should return 404 when the job doesn't exist."""
    with patch("app.api.sessions.JobService") as MockJobSvc, \
         patch("app.api.sessions.SessionService"):

        MockJobSvc.return_value.get_job.return_value = None

        response = client.get(f"/api/jobs/{JOB_ID}/sessions")

    assert response.status_code == 404


# ── GET /api/sessions/{token} ────────────────────────────────────────────────

def test_get_session_success(client):
    """Candidate should receive job info + approved questions."""
    in_progress_session = {**SAMPLE_SESSION, "status": "in_progress"}
    with patch("app.api.sessions.SessionService") as MockSsnSvc:

        MockSsnSvc.return_value.get_session_by_token.return_value = SAMPLE_SESSION
        MockSsnSvc.return_value.get_job_public.return_value = SAMPLE_PUBLIC_JOB
        MockSsnSvc.return_value.get_approved_questions.return_value = [SAMPLE_QUESTION]
        MockSsnSvc.return_value.mark_in_progress.return_value = None

        response = client.get(f"/api/sessions/{TOKEN}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["job_title"] == "Senior Data Scientist"
    assert data["candidate_name"] == "Alice Smith"
    assert len(data["questions"]) == 1
    assert data["questions"][0]["type"] == "behavioral"


def test_get_session_not_found(client):
    """Should return 404 for an invalid token."""
    with patch("app.api.sessions.SessionService") as MockSsnSvc:
        MockSsnSvc.return_value.get_session_by_token.return_value = None

        response = client.get(f"/api/sessions/{TOKEN}")

    assert response.status_code == 404


def test_get_session_already_completed(client):
    """Should return 403 when session is already completed."""
    with patch("app.api.sessions.SessionService") as MockSsnSvc:
        MockSsnSvc.return_value.get_session_by_token.return_value = SAMPLE_SESSION_COMPLETED

        response = client.get(f"/api/sessions/{TOKEN}")

    assert response.status_code == 403
    assert "submitted" in response.json()["detail"].lower()


def test_get_session_expired(client):
    """Should return 403 when session link has expired."""
    with patch("app.api.sessions.SessionService") as MockSsnSvc:
        MockSsnSvc.return_value.get_session_by_token.return_value = SAMPLE_SESSION_EXPIRED

        response = client.get(f"/api/sessions/{TOKEN}")

    assert response.status_code == 403
    assert "expired" in response.json()["detail"].lower()


def test_get_session_no_approved_questions(client):
    """Should still succeed even with zero approved questions (edge case)."""
    with patch("app.api.sessions.SessionService") as MockSsnSvc:

        MockSsnSvc.return_value.get_session_by_token.return_value = SAMPLE_SESSION
        MockSsnSvc.return_value.get_job_public.return_value = SAMPLE_PUBLIC_JOB
        MockSsnSvc.return_value.get_approved_questions.return_value = []
        MockSsnSvc.return_value.mark_in_progress.return_value = None

        response = client.get(f"/api/sessions/{TOKEN}")

    assert response.status_code == 200
    assert response.json()["data"]["questions"] == []


# ── POST /api/sessions/{token}/responses ─────────────────────────────────────

def test_submit_responses_success(client):
    """Candidate should be able to submit responses and get 201."""
    with patch("app.api.sessions.SessionService") as MockSsnSvc:

        MockSsnSvc.return_value.get_session_by_token.return_value = SAMPLE_SESSION
        MockSsnSvc.return_value.get_approved_questions.return_value = [SAMPLE_QUESTION]
        MockSsnSvc.return_value.submit_responses.return_value = [SAMPLE_RESPONSE]

        response = client.post(
            f"/api/sessions/{TOKEN}/responses",
            json={
                "responses": [
                    {
                        "question_id": Q_ID_1,
                        "answer": "In my previous role, I presented complex ML results to executives clearly.",
                    }
                ]
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert "submitted" in body["message"].lower()
    assert len(body["data"]) == 1


def test_submit_responses_invalid_question_id(client):
    """Should return 422 when a question_id doesn't belong to this assessment."""
    foreign_q_id = str(uuid4())  # a question from another job
    with patch("app.api.sessions.SessionService") as MockSsnSvc:

        MockSsnSvc.return_value.get_session_by_token.return_value = SAMPLE_SESSION
        # Only Q_ID_1 is approved
        MockSsnSvc.return_value.get_approved_questions.return_value = [SAMPLE_QUESTION]

        response = client.post(
            f"/api/sessions/{TOKEN}/responses",
            json={
                "responses": [
                    {
                        "question_id": foreign_q_id,
                        "answer": "Some answer to a question that doesn't belong here.",
                    }
                ]
            },
        )

    assert response.status_code == 422


def test_submit_responses_session_not_found(client):
    """Should return 404 for invalid token."""
    with patch("app.api.sessions.SessionService") as MockSsnSvc:
        MockSsnSvc.return_value.get_session_by_token.return_value = None

        response = client.post(
            f"/api/sessions/{TOKEN}/responses",
            json={
                "responses": [
                    {"question_id": Q_ID_1, "answer": "My detailed STAR answer here."}
                ]
            },
        )

    assert response.status_code == 404


def test_submit_responses_already_completed(client):
    """Should return 403 when session is already completed."""
    with patch("app.api.sessions.SessionService") as MockSsnSvc:
        MockSsnSvc.return_value.get_session_by_token.return_value = SAMPLE_SESSION_COMPLETED

        response = client.post(
            f"/api/sessions/{TOKEN}/responses",
            json={
                "responses": [
                    {"question_id": Q_ID_1, "answer": "My detailed STAR answer here."}
                ]
            },
        )

    assert response.status_code == 403


def test_submit_responses_empty_payload(client):
    """Should return 422 for an empty responses array."""
    with patch("app.api.sessions.SessionService") as MockSsnSvc:
        MockSsnSvc.return_value.get_session_by_token.return_value = SAMPLE_SESSION

        response = client.post(
            f"/api/sessions/{TOKEN}/responses",
            json={"responses": []},
        )

    assert response.status_code == 422


def test_submit_responses_short_answer(client):
    """Should return 422 when answer is too short (min_length=10)."""
    with patch("app.api.sessions.SessionService") as MockSsnSvc:
        MockSsnSvc.return_value.get_session_by_token.return_value = SAMPLE_SESSION
        MockSsnSvc.return_value.get_approved_questions.return_value = [SAMPLE_QUESTION]

        response = client.post(
            f"/api/sessions/{TOKEN}/responses",
            json={
                "responses": [
                    {"question_id": Q_ID_1, "answer": "short"},
                ]
            },
        )

    assert response.status_code == 422


# ── Pydantic schema tests ─────────────────────────────────────────────────────

def test_session_schemas():
    """SessionRead, PublicSessionRead, ResponseCreate should all parse correctly."""
    import uuid
    from app.schemas.sessions import (
        PublicQuestion,
        PublicSessionRead,
        ResponseCreate,
        ResponseRead,
        SessionCreate,
        SessionRead,
        SubmitResponsesPayload,
    )

    # SessionCreate validates expires_in_days range
    sc = SessionCreate(
        candidate_name="Alice",
        candidate_email="alice@example.com",
        expires_in_days=14,
    )
    assert sc.expires_in_days == 14

    # SessionRead
    sr = SessionRead(**SAMPLE_SESSION)
    assert sr.status == "pending"
    assert str(sr.token) == TOKEN

    # PublicQuestion
    pq = PublicQuestion(**SAMPLE_QUESTION)
    assert pq.type == "behavioral"
    assert len(pq.indicators) == 3

    # PublicSessionRead
    psr = PublicSessionRead(
        session_id=SESSION_ID,
        job_title="Senior Data Scientist",
        job_description="Lead ML...",
        candidate_name="Alice Smith",
        status="in_progress",
        questions=[pq],
    )
    assert len(psr.questions) == 1

    # ResponseCreate enforces min_length
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ResponseCreate(question_id=uuid.uuid4(), answer="hi")  # too short

    # SubmitResponsesPayload enforces non-empty
    with pytest.raises(ValidationError):
        SubmitResponsesPayload(responses=[])

    # Valid submission
    sp = SubmitResponsesPayload(
        responses=[ResponseCreate(question_id=uuid.uuid4(), answer="A" * 20)]
    )
    assert len(sp.responses) == 1
