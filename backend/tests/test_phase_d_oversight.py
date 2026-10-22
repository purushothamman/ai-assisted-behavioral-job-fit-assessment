"""
tests/test_phase_d_oversight.py
Phase D: Recruiter Oversight and Audit Trails (OV-1 to OV-6).

Coverage:
1. Audit log persistence and sensitive credential sanitization (OV-2)
2. Recruiter review submission and score override preservation (OV-3, OV-4, OV-5)
3. Tenant isolation and recruiter authorization vs admin bypass (OV-3, OV-5)
4. Repeated review submissions tracking (OV-5)
5. Report warnings (sample size, evidence quality, and research-backed fairness caveat) (OV-1)
6. Report recruiter review object presentation (OV-6)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.schemas.alignment import SessionReviewPayload
from app.services.audit_service import AuditService, sanitize_audit_details
from app.services.report_service import ReportService

JOB_ID = str(uuid4())
SESSION_ID = str(uuid4())
RECRUITER_ID = "11111111-1111-1111-1111-111111111111"
OTHER_RECRUITER_ID = "22222222-2222-2222-2222-222222222222"
ADMIN_ID = "99999999-9999-9999-9999-999999999999"

MOCK_JOB_OWNED = {
    "id": JOB_ID,
    "recruiter_id": RECRUITER_ID,
    "title": "Principal Architect",
    "status": "active",
}

MOCK_JOB_OTHER = {
    "id": JOB_ID,
    "recruiter_id": OTHER_RECRUITER_ID,
    "title": "Principal Architect",
    "status": "active",
}

MOCK_SESSION = {
    "id": SESSION_ID,
    "job_id": JOB_ID,
    "candidate_name": "Jordan Lee",
    "candidate_email": "jordan@example.com",
    "status": "completed",
    "submitted_at": "2026-10-20T10:00:00Z",
    "created_at": "2026-10-20T08:00:00Z",
}

MOCK_ALIGNMENT_INITIAL = {
    "id": str(uuid4()),
    "session_id": SESSION_ID,
    "job_id": JOB_ID,
    "overall_score": 82.5,
    "total_weight": 100,
    "total_dimensions_count": 2,
    "assessed_dimensions_count": 2,
    "average_confidence": 0.85,
    "dimension_alignments": [
        {
            "dimension_name": "communication",
            "dimension_label": "Communication",
            "job_weight": 50.0,
            "weight_percentage": 50.0,
            "candidate_score": 85.0,
            "benchmark_gap": 35.0,
            "contribution": 42.5,
            "status": "assessed",
            "confidence": 0.85,
            "response_count": 2,
        },
        {
            "dimension_name": "leadership",
            "dimension_label": "Leadership",
            "job_weight": 50.0,
            "weight_percentage": 50.0,
            "candidate_score": 80.0,
            "benchmark_gap": 30.0,
            "contribution": 40.0,
            "status": "assessed",
            "confidence": 0.85,
            "response_count": 2,
        },
    ],
    "strengths": ["Strong Communication"],
    "areas_for_review": [],
    "metadata": {},
    "calculated_at": "2026-10-20T10:05:00Z",
    "reviewed_at": None,
    "reviewed_by": None,
    "review_action": None,
    "recruiter_notes": None,
    "override_score": None,
}

MOCK_ALIGNMENT_ALREADY_REVIEWED = {
    **MOCK_ALIGNMENT_INITIAL,
    "reviewed_at": "2026-10-20T11:00:00Z",
    "reviewed_by": RECRUITER_ID,
    "review_action": "flagged_for_interview",
    "recruiter_notes": "Candidate should be invited for panel discussion.",
    "override_score": 85.0,
}


# ==============================================================================
# 1. AUDIT LOG PERSISTENCE & SANITIZATION (OV-2)
# ==============================================================================

class TestAuditService:
    def test_sanitize_audit_details_redacts_credentials(self):
        sensitive_data = {
            "password": "secret_password_123",
            "access_token": "eyJhbGciOi...",
            "api_key": "sk-proj-xyz...",
            "authorization": "Bearer token123",
            "safe_field": "valid_value",
            "nested": {
                "token": "nested_token",
                "normal": "nested_normal",
            },
            "items": [
                {"secret": "hidden_secret", "name": "item1"},
            ],
        }

        sanitized = sanitize_audit_details(sensitive_data)
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["access_token"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["authorization"] == "[REDACTED]"
        assert sanitized["safe_field"] == "valid_value"
        assert sanitized["nested"]["token"] == "[REDACTED]"
        assert sanitized["nested"]["normal"] == "nested_normal"
        assert sanitized["items"][0]["secret"] == "[REDACTED]"
        assert sanitized["items"][0]["name"] == "item1"

    def test_log_event_records_and_retrieves(self):
        svc = AuditService()
        event = svc.log_event(
            action="assessment.reviewed",
            entity_type="assessment_session",
            entity_id=SESSION_ID,
            user_id=RECRUITER_ID,
            user_role="recruiter",
            ip_address="127.0.0.1",
            user_agent="pytest/8.0",
            details={"review_action": "reviewed", "notes": "Solid performance."},
        )

        assert event is not None
        assert event["action"] == "assessment.reviewed"
        assert event["entity_id"] == SESSION_ID
        assert event["user_id"] == RECRUITER_ID

        history = svc.get_audit_history("assessment_session", SESSION_ID)
        assert len(history) >= 1
        actions = [e["action"] for e in history]
        assert "assessment.reviewed" in actions


# ==============================================================================
# 2. RECRUITER REVIEW API ENDPOINT (OV-3, OV-4, OV-5)
# ==============================================================================

class TestRecruiterReviewEndpoint:
    @patch("app.services.job_service.JobService.get_job")
    @patch("app.services.session_service.SessionService.get_session")
    @patch("app.services.alignment_service.AlignmentService.get_alignment")
    def test_review_session_success(self, mock_align, mock_sess, mock_job, client: TestClient):
        mock_sess.return_value = MOCK_SESSION
        mock_job.return_value = MOCK_JOB_OWNED
        mock_align.return_value = MOCK_ALIGNMENT_INITIAL

        payload = {
            "action": "reviewed",
            "notes": "Candidate demonstrated solid competence across all dimensions.",
            "override_score": 88.0,
        }

        resp = client.post(f"/api/sessions/{SESSION_ID}/review", json=payload)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["success"] is True
        review = data["data"]
        assert review["session_id"] == SESSION_ID
        assert review["review_action"] == "reviewed"
        assert review["recruiter_notes"] == payload["notes"]
        assert review["original_score"] == 82.5  # preserved authoritative score
        assert review["override_score"] == 88.0
        assert review["is_repeated_review"] is False

    @patch("app.services.job_service.JobService.get_job")
    @patch("app.services.session_service.SessionService.get_session")
    def test_review_session_tenant_isolation_forbidden(self, mock_sess, mock_job, client: TestClient):
        # Session belongs to job owned by OTHER_RECRUITER_ID
        mock_sess.return_value = MOCK_SESSION
        mock_job.return_value = MOCK_JOB_OTHER

        payload = {"action": "reviewed", "notes": "Trying to review someone else's candidate"}
        resp = client.post(f"/api/sessions/{SESSION_ID}/review", json=payload)
        assert resp.status_code == 403
        assert "permission" in resp.json()["detail"].lower()

    @patch("app.services.job_service.JobService.get_job")
    @patch("app.services.session_service.SessionService.get_session")
    @patch("app.services.alignment_service.AlignmentService.get_alignment")
    def test_review_session_admin_bypass_allowed(self, mock_align, mock_sess, mock_job, admin_client: TestClient):
        # Admin can review sessions even if job is owned by someone else
        mock_sess.return_value = MOCK_SESSION
        mock_job.return_value = MOCK_JOB_OTHER
        mock_align.return_value = MOCK_ALIGNMENT_INITIAL

        payload = {
            "action": "completed",
            "notes": "Admin audit oversight passed.",
        }
        resp = admin_client.post(f"/api/sessions/{SESSION_ID}/review", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["review_action"] == "completed"

    @patch("app.services.job_service.JobService.get_job")
    @patch("app.services.session_service.SessionService.get_session")
    @patch("app.services.alignment_service.AlignmentService.get_alignment")
    def test_review_session_repeated_submission(self, mock_align, mock_sess, mock_job, client: TestClient):
        mock_sess.return_value = MOCK_SESSION
        mock_job.return_value = MOCK_JOB_OWNED
        mock_align.return_value = MOCK_ALIGNMENT_ALREADY_REVIEWED

        payload = {
            "action": "overridden",
            "notes": "Updated review after secondary hiring manager review.",
            "override_score": 90.0,
        }

        resp = client.post(f"/api/sessions/{SESSION_ID}/review", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        review = data["data"]
        assert review["is_repeated_review"] is True
        assert review["review_action"] == "overridden"
        assert review["override_score"] == 90.0

    def test_review_session_invalid_action(self, client: TestClient):
        payload = {
            "action": "invalid_action_not_permitted",
            "notes": "Test notes",
        }
        resp = client.post(f"/api/sessions/{SESSION_ID}/review", json=payload)
        assert resp.status_code == 422

    @patch("app.services.session_service.SessionService.get_session")
    def test_review_session_not_found(self, mock_sess, client: TestClient):
        mock_sess.return_value = None
        payload = {"action": "reviewed"}
        resp = client.post(f"/api/sessions/{str(uuid4())}/review", json=payload)
        assert resp.status_code == 404


# ==============================================================================
# 3. REPORT WARNINGS & RESEARCH-BACKED FAIRNESS CAVEATS (OV-1, OV-6)
# ==============================================================================

class TestReportWarningsAndOversight:
    @patch("app.services.session_service.SessionService.get_session")
    @patch("app.services.job_service.JobService.get_job")
    @patch("app.services.report_service.ReportService._get_questions_by_job")
    @patch("app.services.report_service.ReportService._get_responses_by_session")
    @patch("app.services.report_service.ReportService._get_scores_by_session")
    @patch("app.services.alignment_service.AlignmentService.get_alignment")
    def test_report_includes_sample_size_and_fairness_caveat_warnings(
        self, mock_align, mock_scores, mock_resp, mock_qs, mock_job, mock_sess
    ):
        mock_sess.return_value = MOCK_SESSION
        mock_job.return_value = MOCK_JOB_OWNED
        # 5 questions in job, but candidate only answered 2
        mock_qs.return_value = [{"id": str(uuid4()), "question": f"Q{i}", "dimension_name": "communication"} for i in range(5)]
        mock_resp.return_value = [
            {"question_id": mock_qs.return_value[0]["id"], "answer": "Answer 1"},
            {"question_id": mock_qs.return_value[1]["id"], "answer": "Answer 2"},
        ]
        mock_scores.return_value = [
            {"question_id": mock_qs.return_value[0]["id"], "confidence": 0.40, "evidence": []},
            {"question_id": mock_qs.return_value[1]["id"], "confidence": 0.40, "evidence": []},
        ]
        mock_align.return_value = {
            **MOCK_ALIGNMENT_ALREADY_REVIEWED,
            "average_confidence": 0.40,
        }

        svc = ReportService()
        report = svc.get_assessment_report(SESSION_ID)

        assert report is not None
        assert "warnings" in report
        warnings = report["warnings"]
        assert len(warnings) >= 3

        # 1. Sample size warning
        sample_size_warnings = [w for w in warnings if "sample-size" in w.lower()]
        assert len(sample_size_warnings) >= 1

        # 2. Low confidence warning (<0.45)
        conf_warnings = [w for w in warnings if "confidence" in w.lower() or "similarity" in w.lower()]
        assert len(conf_warnings) >= 1

        # 3. Mandatory fairness caveat (OV-1: does NOT suggest thresholds prove fairness)
        fairness_caveats = [w for w in warnings if "fairness caveat" in w.lower()]
        assert len(fairness_caveats) >= 1
        assert "not prove absence of bias" in fairness_caveats[0].lower()

        # 4. Recruiter review object in report (OV-6)
        assert report["recruiter_review"] is not None
        assert report["recruiter_review"]["review_action"] == "flagged_for_interview"
        assert report["recruiter_review"]["override_score"] == 85.0
        assert report["recruiter_review"]["recruiter_notes"] == "Candidate should be invited for panel discussion."
