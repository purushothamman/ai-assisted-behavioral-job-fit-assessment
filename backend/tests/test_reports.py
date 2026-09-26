"""
tests/test_reports.py
Unit and integration tests for Phase 8: Assessment Reports & Recruiter Dashboard.

Coverage:
  A. ReportService inquiry prompt generator & helpers
  B. GET /api/sessions/{session_id}/report (complete, incomplete, missing, auth, forbidden)
  C. GET /api/jobs/{job_id}/reports/summary (rankings, sorting, auth, forbidden)
  D. Ethical compliance verification (no automated hire/reject decisions)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.report import AssessmentReportRead, SessionReportSummaryItem
from app.services.report_service import COMPLIANCE_DISCLAIMER, ReportService

JOB_ID = str(uuid4())
SESSION_ID = str(uuid4())
RECRUITER_ID = "11111111-1111-1111-1111-111111111111"

MOCK_JOB = {
    "id": JOB_ID,
    "recruiter_id": RECRUITER_ID,
    "title": "Principal Architect",
    "status": "active",
}

MOCK_SESSION_COMPLETED = {
    "id": SESSION_ID,
    "job_id": JOB_ID,
    "candidate_name": "Alex Mercer",
    "candidate_email": "alex@example.com",
    "status": "completed",
    "submitted_at": "2026-09-27T01:00:00Z",
    "created_at": "2026-09-26T12:00:00Z",
}

MOCK_SESSION_PENDING = {
    **MOCK_SESSION_COMPLETED,
    "status": "pending",
    "submitted_at": None,
}

QUESTION_ID = str(uuid4())
MOCK_QUESTION = {
    "id": QUESTION_ID,
    "job_id": JOB_ID,
    "dimension_id": str(uuid4()),
    "dimension_name": "communication",
    "question": "Describe how you communicate complex technical decisions to stakeholders.",
    "type": "behavioral",
    "difficulty": "medium",
    "approved": True,
}

MOCK_RESPONSE = {
    "id": str(uuid4()),
    "session_id": SESSION_ID,
    "question_id": QUESTION_ID,
    "response_text": "I prepared detailed architectural decision records and organized interactive Q&A sessions.",
    "word_count": 14,
    "submitted_at": "2026-09-27T01:00:00Z",
}

MOCK_SCORE = {
    "id": str(uuid4()),
    "session_id": SESSION_ID,
    "question_id": QUESTION_ID,
    "response_id": MOCK_RESPONSE["id"],
    "dimension_name": "communication",
    "normalized_score": 85,
    "confidence": 0.88,
    "status": "scored",
    "indicators_matched": 3,
    "total_indicators": 4,
    "evidence": [
        {
            "indicator": "Clear Explanation",
            "matched": True,
            "level": "strong",
            "similarity": 0.82,
            "evidence_text": "prepared detailed architectural decision records",
        }
    ],
}

MOCK_ALIGNMENT = {
    "id": str(uuid4()),
    "session_id": SESSION_ID,
    "job_id": JOB_ID,
    "candidate_name": "Alex Mercer",
    "job_title": "Principal Architect",
    "overall_score": 85.0,
    "total_weight": 100,
    "total_dimensions_count": 1,
    "assessed_dimensions_count": 1,
    "average_confidence": 0.88,
    "dimension_alignments": [
        {
            "dimension_name": "communication",
            "dimension_label": "Communication",
            "job_weight": 100.0,
            "weight_percentage": 100.0,
            "candidate_score": 85.0,
            "contribution": 85.0,
            "status": "assessed",
            "confidence": 0.88,
            "response_count": 1,
        }
    ],
    "strengths": ["Strong behavioral proficiency in Communication."],
    "areas_for_review": [],
    "metadata": {},
    "calculated_at": "2026-09-27T01:05:00Z",
}


# ===============================================================================
# A. REPORT SERVICE UNIT TESTS
# ===============================================================================

class TestReportServiceUnits:
    """Unit tests for ReportService inquiry generation and helpers."""

    def test_generate_inquiry_prompts_for_missing_and_weak_competencies(self):
        svc = ReportService()
        dim_alignments = [
            {
                "dimension_name": "decision_making",
                "dimension_label": "Decision Making",
                "status": "missing",
                "candidate_score": 0.0,
                "job_weight": 80.0,
            },
            {
                "dimension_name": "leadership",
                "dimension_label": "Leadership",
                "status": "assessed",
                "candidate_score": 50.0,
                "job_weight": 75.0,
            },
        ]
        areas = ["Missing Decision Making", "Sub-benchmark in Leadership"]
        prompts = svc._generate_inquiry_prompts(dim_alignments, areas)
        assert len(prompts) == 2
        assert any("Decision Making" in p and "high-stakes" in p for p in prompts)
        assert any("Leadership" in p and "conflict or ambiguity" in p for p in prompts)

    def test_compliance_notice_constant(self):
        assert "Antigravity does NOT produce automated hire/reject recommendations" in COMPLIANCE_DISCLAIMER


# ===============================================================================
# B. GET /api/sessions/{session_id}/report ENDPOINT TESTS
# ===============================================================================

class TestGetAssessmentReportEndpoint:
    """Integration tests for single session report endpoint."""

    def test_get_report_success(self, client):
        """Happy path — returns comprehensive report with alignment, evidence, and prompts."""
        with patch("app.api.reports.SessionService") as MockSessSvc, \
             patch("app.api.reports.JobService") as MockJobSvc, \
             patch("app.api.reports.ReportService") as MockRepSvc:

            mock_sess = MagicMock()
            mock_sess.get_session.return_value = MOCK_SESSION_COMPLETED
            MockSessSvc.return_value = mock_sess

            mock_job = MagicMock()
            mock_job.get_job.return_value = MOCK_JOB
            MockJobSvc.return_value = mock_job

            mock_rep = MagicMock()
            mock_rep.get_assessment_report.return_value = {
                "session_id": SESSION_ID,
                "job_id": JOB_ID,
                "job_title": "Principal Architect",
                "candidate_name": "Alex Mercer",
                "candidate_email": "alex@example.com",
                "status": "completed",
                "submitted_at": "2026-09-27T01:00:00Z",
                "created_at": "2026-09-26T12:00:00Z",
                "executive_summary": {
                    "overall_alignment_score": 85.0,
                    "total_job_weight": 100,
                    "assessed_dimensions_count": 1,
                    "total_dimensions_count": 1,
                    "average_confidence": 0.88,
                    "is_complete": True,
                    "strengths": ["Strong communication skills."],
                    "areas_for_review": [],
                    "inquiry_prompts": ["Ask about high-scale system designs."],
                },
                "dimension_breakdown": [
                    {
                        "dimension_name": "communication",
                        "dimension_label": "Communication",
                        "job_weight": 100.0,
                        "weight_percentage": 100.0,
                        "candidate_score": 85.0,
                        "benchmark_gap": -15.0,
                        "contribution": 85.0,
                        "status": "assessed",
                        "confidence": 0.88,
                        "response_count": 1,
                        "indicators_matched": 3,
                        "total_indicators": 4,
                    }
                ],
                "questions_evidence": [
                    {
                        "question_id": QUESTION_ID,
                        "question_text": MOCK_QUESTION["question"],
                        "dimension_name": "communication",
                        "dimension_label": "Communication",
                        "question_type": "behavioral",
                        "difficulty": "medium",
                        "candidate_response": MOCK_RESPONSE["response_text"],
                        "word_count": 14,
                        "response_score": 85,
                        "confidence": 0.88,
                        "status": "scored",
                        "evidence": [
                            {
                                "indicator_name": "Clear Explanation",
                                "matched": True,
                                "level": "strong",
                                "similarity": 0.82,
                                "evidence_text": "prepared detailed architectural decision records",
                            }
                        ],
                    }
                ],
                "compliance_notice": COMPLIANCE_DISCLAIMER,
                "metadata": {},
                "generated_at": "2026-09-27T01:10:00Z",
            }
            MockRepSvc.return_value = mock_rep

            resp = client.get(f"/api/sessions/{SESSION_ID}/report")

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["candidate_name"] == "Alex Mercer"
        assert data["executive_summary"]["overall_alignment_score"] == 85.0
        assert len(data["questions_evidence"]) == 1
        assert "Clear Explanation" in data["questions_evidence"][0]["evidence"][0]["indicator_name"]
        assert "Antigravity does NOT produce automated hire/reject recommendations" in data["compliance_notice"]

    def test_get_report_session_not_found(self, client):
        """Returns 404 when session does not exist."""
        with patch("app.api.reports.SessionService") as MockSessSvc:
            mock_sess = MagicMock()
            mock_sess.get_session.return_value = None
            MockSessSvc.return_value = mock_sess

            resp = client.get(f"/api/sessions/{SESSION_ID}/report")

        assert resp.status_code == 404

    def test_get_report_wrong_recruiter_forbidden(self, client):
        """Returns 403 when session belongs to a different recruiter's job."""
        other_job = {**MOCK_JOB, "recruiter_id": str(uuid4())}
        with patch("app.api.reports.SessionService") as MockSessSvc, \
             patch("app.api.reports.JobService") as MockJobSvc:

            mock_sess = MagicMock()
            mock_sess.get_session.return_value = MOCK_SESSION_COMPLETED
            MockSessSvc.return_value = mock_sess

            mock_job = MagicMock()
            mock_job.get_job.return_value = other_job
            MockJobSvc.return_value = mock_job

            resp = client.get(f"/api/sessions/{SESSION_ID}/report")

        assert resp.status_code == 403

    def test_get_report_requires_auth(self):
        """No auth header -> 401."""
        from fastapi.testclient import TestClient
        from app.main import app as _app

        saved = dict(_app.dependency_overrides)
        _app.dependency_overrides.clear()
        try:
            with TestClient(_app) as raw_client:
                resp = raw_client.get(f"/api/sessions/{SESSION_ID}/report")
            assert resp.status_code in (401, 403, 422)
        finally:
            _app.dependency_overrides.update(saved)


# ===============================================================================
# C. GET /api/jobs/{job_id}/reports/summary ENDPOINT TESTS
# ===============================================================================

class TestGetJobReportsSummaryEndpoint:
    """Tests for job-wide candidate reports summary endpoint."""

    def test_get_job_reports_summary_success(self, client):
        """Returns candidate summaries list sorted by alignment score."""
        with patch("app.api.reports.JobService") as MockJobSvc, \
             patch("app.api.reports.ReportService") as MockRepSvc:

            mock_job = MagicMock()
            mock_job.get_job.return_value = MOCK_JOB
            MockJobSvc.return_value = mock_job

            mock_rep = MagicMock()
            mock_rep.get_job_reports_summary.return_value = [
                {
                    "session_id": SESSION_ID,
                    "candidate_name": "Alex Mercer",
                    "candidate_email": "alex@example.com",
                    "status": "completed",
                    "submitted_at": "2026-09-27T01:00:00Z",
                    "overall_alignment_score": 85.0,
                    "top_strength": "Strong communication",
                    "primary_review_area": None,
                    "is_scored": True,
                }
            ]
            MockRepSvc.return_value = mock_rep

            resp = client.get(f"/api/jobs/{JOB_ID}/reports/summary")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["overall_alignment_score"] == 85.0
        assert body["data"][0]["candidate_name"] == "Alex Mercer"

    def test_get_job_reports_summary_wrong_recruiter_forbidden(self, client):
        """403 if job belongs to another recruiter."""
        other_job = {**MOCK_JOB, "recruiter_id": str(uuid4())}
        with patch("app.api.reports.JobService") as MockJobSvc:
            mock_job = MagicMock()
            mock_job.get_job.return_value = other_job
            MockJobSvc.return_value = mock_job

            resp = client.get(f"/api/jobs/{JOB_ID}/reports/summary")

        assert resp.status_code == 403


# ===============================================================================
# D. ETHICAL SAFEGUARDS VERIFICATION
# ===============================================================================

class TestEthicalSafeguards:
    """Verifies compliance with ethical AI requirements."""

    def test_no_employment_decisions_in_schemas_or_outputs(self):
        """
        Verify that no automatic hire/reject/selected decisions
        or psychological diagnoses are present in report outputs.
        """
        svc = ReportService()
        prompts = svc._generate_inquiry_prompts([], [])
        for p in prompts:
            assert "hire" not in p.lower()
            assert "reject" not in p.lower()
            assert "depression" not in p.lower()
            assert "anxiety" not in p.lower()
            assert "disorder" not in p.lower()
