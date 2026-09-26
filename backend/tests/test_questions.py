"""
tests/test_questions.py
Tests for the Phase 4 question generation pipeline:
  - POST /api/jobs/{id}/questions/generate
  - GET  /api/jobs/{id}/questions
  - PATCH /api/questions/{id}?job_id={job_id}
  - DELETE /api/questions/{id}?job_id={job_id}

Strategy:
  - JobService, JobRequirementService, QuestionService, and generate_questions
    are all patched at the API layer.
  - Auth bypassed via conftest.py dependency override.
  - No real Supabase or Groq calls are made.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

JOB_ID   = str(uuid4())
Q_ID     = str(uuid4())
DIM_ID   = str(uuid4())

SAMPLE_JOB = {
    "id":               JOB_ID,
    "recruiter_id":     "11111111-1111-1111-1111-111111111111",
    "title":            "Senior Data Scientist",
    "description":      "Lead ML initiatives across the organisation.",
    "responsibilities": "Build models, mentor junior data scientists.",
    "requirements":     "5+ years ML, Python, strong communication.",
    "status":           "analyzed",
    "created_at":       "2026-01-01T00:00:00+00:00",
    "updated_at":       "2026-01-01T00:00:00+00:00",
}

SAMPLE_CONFIRMED_REQ = {
    "id":             str(uuid4()),
    "job_id":         JOB_ID,
    "dimension_id":   DIM_ID,
    "dimension_name": "communication",
    "importance":     85,
    "reason":         "The role requires presenting complex findings to stakeholders.",
    "confirmed":      True,
    "created_at":     "2026-01-01T00:00:00+00:00",
}

SAMPLE_QUESTION = {
    "id":             Q_ID,
    "job_id":         JOB_ID,
    "dimension_id":   DIM_ID,
    "dimension_name": "communication",
    "question":       "Tell me about a time you explained a complex ML model to non-technical stakeholders.",
    "type":           "behavioral",
    "difficulty":     "medium",
    "indicators":     ["Clear explanation", "Adapted language to audience", "Measurable outcome"],
    "approved":       False,
    "created_at":     "2026-01-01T00:00:00+00:00",
}

SAMPLE_QUESTION_APPROVED = {**SAMPLE_QUESTION, "approved": True}


# ── POST /api/jobs/{job_id}/questions/generate ────────────────────────────

def test_generate_questions_success(client):
    """Should return a list of questions on success."""
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.JobRequirementService") as MockReqSvc, \
         patch("app.api.questions.QuestionService") as MockQSvc, \
         patch("app.api.questions.generate_questions") as mock_gen:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockJobSvc.return_value.update_job.return_value = {**SAMPLE_JOB, "status": "questions_generated"}
        MockReqSvc.return_value.list_requirements.return_value = [SAMPLE_CONFIRMED_REQ]
        mock_gen.return_value = [MagicMock()]
        MockQSvc.return_value.save_questions.return_value = [SAMPLE_QUESTION]

        response = client.post(f"/api/jobs/{JOB_ID}/questions/generate")

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["dimension_name"] == "communication"
    assert body["data"][0]["type"] == "behavioral"
    assert body["data"][0]["difficulty"] == "medium"


def test_generate_questions_job_not_found(client):
    """Should return 404 when the job doesn't belong to the recruiter."""
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.JobRequirementService"), \
         patch("app.api.questions.QuestionService"), \
         patch("app.api.questions.generate_questions"):

        MockJobSvc.return_value.get_job.return_value = None

        response = client.post(f"/api/jobs/{JOB_ID}/questions/generate")

    assert response.status_code == 404


def test_generate_questions_no_description(client):
    """Should return 422 when the job has no description."""
    job_no_desc = {**SAMPLE_JOB, "description": ""}
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.JobRequirementService"), \
         patch("app.api.questions.QuestionService"), \
         patch("app.api.questions.generate_questions"):

        MockJobSvc.return_value.get_job.return_value = job_no_desc

        response = client.post(f"/api/jobs/{JOB_ID}/questions/generate")

    assert response.status_code == 422
    assert "description" in response.json()["detail"].lower()


def test_generate_questions_no_confirmed_requirements(client):
    """Should return 422 when there are no confirmed requirements."""
    unconfirmed_req = {**SAMPLE_CONFIRMED_REQ, "confirmed": False}
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.JobRequirementService") as MockReqSvc, \
         patch("app.api.questions.QuestionService"), \
         patch("app.api.questions.generate_questions"):

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockReqSvc.return_value.list_requirements.return_value = [unconfirmed_req]

        response = client.post(f"/api/jobs/{JOB_ID}/questions/generate")

    assert response.status_code == 422
    assert "confirmed" in response.json()["detail"].lower()


def test_generate_questions_groq_unavailable(client):
    """Should return 503 when Groq is unavailable."""
    from app.ai.groq_client import GroqError

    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.JobRequirementService") as MockReqSvc, \
         patch("app.api.questions.QuestionService"), \
         patch("app.api.questions.generate_questions") as mock_gen:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockReqSvc.return_value.list_requirements.return_value = [SAMPLE_CONFIRMED_REQ]
        mock_gen.side_effect = GroqError("API key not set")

        response = client.post(f"/api/jobs/{JOB_ID}/questions/generate")

    assert response.status_code == 503


def test_generate_questions_groq_validation_error(client):
    """Should return 422 when Groq output fails Pydantic validation."""
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.JobRequirementService") as MockReqSvc, \
         patch("app.api.questions.QuestionService"), \
         patch("app.api.questions.generate_questions") as mock_gen:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockReqSvc.return_value.list_requirements.return_value = [SAMPLE_CONFIRMED_REQ]
        mock_gen.side_effect = ValueError("Groq returned invalid structure")

        response = client.post(f"/api/jobs/{JOB_ID}/questions/generate")

    assert response.status_code == 422


def test_generate_questions_multiple(client):
    """Should handle multiple questions across multiple dimensions."""
    extra_req = {
        **SAMPLE_CONFIRMED_REQ,
        "id": str(uuid4()),
        "dimension_name": "leadership",
        "importance": 70,
    }
    questions = [
        {**SAMPLE_QUESTION, "id": str(uuid4()), "dimension_name": "communication"},
        {**SAMPLE_QUESTION, "id": str(uuid4()), "dimension_name": "communication"},
        {**SAMPLE_QUESTION, "id": str(uuid4()), "dimension_name": "leadership", "type": "situational"},
        {**SAMPLE_QUESTION, "id": str(uuid4()), "dimension_name": "leadership", "type": "behavioral"},
    ]
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.JobRequirementService") as MockReqSvc, \
         patch("app.api.questions.QuestionService") as MockQSvc, \
         patch("app.api.questions.generate_questions") as mock_gen:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockJobSvc.return_value.update_job.return_value = SAMPLE_JOB
        MockReqSvc.return_value.list_requirements.return_value = [SAMPLE_CONFIRMED_REQ, extra_req]
        mock_gen.return_value = [MagicMock() for _ in questions]
        MockQSvc.return_value.save_questions.return_value = questions

        response = client.post(f"/api/jobs/{JOB_ID}/questions/generate")

    assert response.status_code == 201
    assert len(response.json()["data"]) == 4


# ── GET /api/jobs/{job_id}/questions ─────────────────────────────────────

def test_list_questions_success(client):
    """Should return list of questions for a job."""
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.QuestionService") as MockQSvc:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockQSvc.return_value.list_questions.return_value = [SAMPLE_QUESTION]

        response = client.get(f"/api/jobs/{JOB_ID}/questions")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["approved"] is False
    assert isinstance(body["data"][0]["indicators"], list)


def test_list_questions_empty(client):
    """Should return empty list when no questions generated yet."""
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.QuestionService") as MockQSvc:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockQSvc.return_value.list_questions.return_value = []

        response = client.get(f"/api/jobs/{JOB_ID}/questions")

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_list_questions_job_not_found(client):
    """Should return 404 when the job doesn't exist."""
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.QuestionService"):

        MockJobSvc.return_value.get_job.return_value = None

        response = client.get(f"/api/jobs/{JOB_ID}/questions")

    assert response.status_code == 404


# ── PATCH /api/questions/{question_id}?job_id={job_id} ───────────────────

def test_update_question_approve(client):
    """Should approve a question and return the updated row."""
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.QuestionService") as MockQSvc:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockQSvc.return_value.update_question.return_value = SAMPLE_QUESTION_APPROVED

        response = client.patch(
            f"/api/questions/{Q_ID}?job_id={JOB_ID}",
            json={"approved": True},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["approved"] is True


def test_update_question_edit_text(client):
    """Should update the question text."""
    updated_q = {**SAMPLE_QUESTION, "question": "Describe a time you led a cross-functional team."}
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.QuestionService") as MockQSvc:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockQSvc.return_value.update_question.return_value = updated_q

        response = client.patch(
            f"/api/questions/{Q_ID}?job_id={JOB_ID}",
            json={"question": "Describe a time you led a cross-functional team."},
        )

    assert response.status_code == 200
    assert "cross-functional" in response.json()["data"]["question"]


def test_update_question_not_found(client):
    """Should return 404 when the question doesn't exist."""
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.QuestionService") as MockQSvc:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockQSvc.return_value.update_question.return_value = None

        response = client.patch(
            f"/api/questions/{Q_ID}?job_id={JOB_ID}",
            json={"approved": True},
        )

    assert response.status_code == 404


def test_update_question_job_not_found(client):
    """Should return 404 when the job doesn't exist."""
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.QuestionService"):

        MockJobSvc.return_value.get_job.return_value = None

        response = client.patch(
            f"/api/questions/{Q_ID}?job_id={JOB_ID}",
            json={"approved": True},
        )

    assert response.status_code == 404


def test_update_question_invalid_type(client):
    """Should return 422 when type is invalid."""
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.QuestionService"):

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB

        response = client.patch(
            f"/api/questions/{Q_ID}?job_id={JOB_ID}",
            json={"type": "technical"},  # not a valid type
        )

    assert response.status_code == 422


# ── DELETE /api/questions/{question_id}?job_id={job_id} ──────────────────

def test_delete_question_success(client):
    """Should delete a question and return success."""
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.QuestionService") as MockQSvc:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockQSvc.return_value.delete_question.return_value = True

        response = client.delete(f"/api/questions/{Q_ID}?job_id={JOB_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "deleted" in body["message"].lower()


def test_delete_question_not_found(client):
    """Should return 404 when the question doesn't exist."""
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.QuestionService") as MockQSvc:

        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockQSvc.return_value.delete_question.return_value = False

        response = client.delete(f"/api/questions/{Q_ID}?job_id={JOB_ID}")

    assert response.status_code == 404


def test_delete_question_job_not_found(client):
    """Should return 404 when the job doesn't belong to recruiter."""
    with patch("app.api.questions.JobService") as MockJobSvc, \
         patch("app.api.questions.QuestionService"):

        MockJobSvc.return_value.get_job.return_value = None

        response = client.delete(f"/api/questions/{Q_ID}?job_id={JOB_ID}")

    assert response.status_code == 404


# ── Pydantic schema tests ─────────────────────────────────────────────────

def test_question_schemas():
    """QuestionRead should parse the SAMPLE_QUESTION dict correctly."""
    from app.schemas.questions import QuestionRead, QuestionUpdate
    import uuid

    q = QuestionRead(**{**SAMPLE_QUESTION, "id": str(uuid.uuid4())})
    assert q.type == "behavioral"
    assert q.difficulty == "medium"
    assert len(q.indicators) == 3
    assert q.approved is False

    # QuestionUpdate accepts partial data
    upd = QuestionUpdate(approved=True)
    assert upd.approved is True
    assert upd.question is None

    # QuestionUpdate rejects invalid type
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        QuestionUpdate(type="technical")
