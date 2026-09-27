"""
tests/test_email_service.py
Comprehensive test suite for Resend email invitations in the Candidate Sessions flow:
- EmailService: success, failure handling, missing key, key redaction
- Session creation: email success, email failure resilience (session preserved), send_email=False
- Retry email endpoint: success, failure, 404 for unknown session, 403 cross-tenant isolation
- Security: RESEND_API_KEY is never exposed in any API response or error string
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.services.email_service import EmailService

JOB_ID = str(uuid4())
SESSION_ID = str(uuid4())
TOKEN = str(uuid4())
CANDIDATE_EMAIL = "candidate@example.com"
CANDIDATE_NAME = "Jane Doe"
SECRET_TEST_KEY = "re_test_secret_1234567890abcdef"

SAMPLE_JOB = {
    "id": JOB_ID,
    "recruiter_id": "11111111-1111-1111-1111-111111111111",
    "title": "Staff Backend Engineer",
    "description": "Design distributed microservices.",
    "status": "questions_generated",
}

SAMPLE_APPROVED_QUESTIONS = [
    {
        "id": str(uuid4()),
        "job_id": JOB_ID,
        "question": "Describe an incident where a distributed system experienced a split-brain condition.",
        "type": "behavioral",
        "difficulty": "hard",
        "approved": True,
        "indicators": ["Root-cause analysis", "Incident command", "Remediation"],
    }
]

SAMPLE_SESSION = {
    "id": SESSION_ID,
    "job_id": JOB_ID,
    "token": TOKEN,
    "candidate_name": CANDIDATE_NAME,
    "candidate_email": CANDIDATE_EMAIL,
    "status": "pending",
    "email_status": "pending",
    "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    "submitted_at": None,
    "created_at": "2026-01-01T00:00:00+00:00",
}


# ==============================================================================
# 1. Unit Tests: EmailService
# ==============================================================================

class TestEmailServiceUnit:
    """Direct unit tests for EmailService methods."""

    def test_send_invitation_smtp_success(self):
        """When SMTP is configured, send email via smtplib.SMTP."""
        service = EmailService()
        service._settings = Settings(
            supabase_url="https://fake.supabase.co",
            supabase_anon_key="fake-anon",
            supabase_service_role_key="fake-service",
            email_provider="smtp",
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            smtp_user="recruiter@gmail.com",
            smtp_password="app_password_1234",
        )

        with patch("smtplib.SMTP") as mock_smtp_cls:
            mock_server = mock_smtp_cls.return_value.__enter__.return_value
            res = service.send_assessment_invitation(
                to_email=CANDIDATE_EMAIL,
                candidate_name=CANDIDATE_NAME,
                job_title="Staff Backend Engineer",
                assessment_url="http://localhost:3000/assess/test-token",
            )
            assert res["success"] is True
            assert res["id"] == "smtp_success"
            assert res["error"] is None
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("recruiter@gmail.com", "app_password_1234")
            mock_server.send_message.assert_called_once()

    def test_send_invitation_smtp_missing_credentials(self):
        """When SMTP credentials are missing, return failure gracefully."""
        service = EmailService()
        service._settings = Settings(
            supabase_url="https://fake.supabase.co",
            supabase_anon_key="fake-anon",
            supabase_service_role_key="fake-service",
            email_provider="smtp",
            smtp_user="",
            smtp_password="",
            resend_api_key="",
        )

        res = service.send_assessment_invitation(
            to_email=CANDIDATE_EMAIL,
            candidate_name=CANDIDATE_NAME,
            job_title="Staff Backend Engineer",
            assessment_url="http://localhost:3000/assess/test-token",
        )
        assert res["success"] is False
        assert "not configured" in res["error"].lower()

    def test_send_invitation_smtp_redacts_password(self):
        """If SMTP throws an exception containing the password, mask it."""
        service = EmailService()
        service._settings = Settings(
            supabase_url="https://fake.supabase.co",
            supabase_anon_key="fake-anon",
            supabase_service_role_key="fake-service",
            email_provider="smtp",
            smtp_user="recruiter@gmail.com",
            smtp_password="secret_pass_9999",
        )

        with patch("smtplib.SMTP", side_effect=RuntimeError("Auth failed for secret_pass_9999")):
            res = service.send_assessment_invitation(
                to_email=CANDIDATE_EMAIL,
                candidate_name=CANDIDATE_NAME,
                job_title="Staff Backend Engineer",
                assessment_url="http://localhost:3000/assess/test-token",
            )
            assert res["success"] is False
            assert "secret_pass_9999" not in res["error"]
            assert "[REDACTED]" in res["error"]

    def test_send_invitation_success(self):
        """When Resend succeeds, return success=True and email id."""
        service = EmailService()
        service._settings = Settings(
            supabase_url="https://fake.supabase.co",
            supabase_anon_key="fake-anon",
            supabase_service_role_key="fake-service",
            email_provider="resend",
            resend_api_key=SECRET_TEST_KEY,
            email_from="Assessments <no-reply@resend.dev>",
        )

        with patch("resend.Emails.send", return_value={"id": "msg_abc123"}) as mock_send:
            res = service.send_assessment_invitation(
                to_email=CANDIDATE_EMAIL,
                candidate_name=CANDIDATE_NAME,
                job_title="Staff Backend Engineer",
                assessment_url="http://localhost:3000/assess/test-token",
            )
            assert res["success"] is True
            assert res["id"] == "msg_abc123"
            assert res["error"] is None
            mock_send.assert_called_once()

    def test_send_invitation_missing_key(self):
        """When Resend API key is unconfigured, return success=False gracefully without raising."""
        service = EmailService()
        service._settings = Settings(
            supabase_url="https://fake.supabase.co",
            supabase_anon_key="fake-anon",
            supabase_service_role_key="fake-service",
            email_provider="resend",
            resend_api_key="",
        )

        with patch("resend.Emails.send") as mock_send:
            res = service.send_assessment_invitation(
                to_email=CANDIDATE_EMAIL,
                candidate_name=CANDIDATE_NAME,
                job_title="Staff Backend Engineer",
                assessment_url="http://localhost:3000/assess/test-token",
            )
            assert res["success"] is False
            assert "not configured" in res["error"].lower()
            mock_send.assert_not_called()

    def test_send_invitation_exception_handled(self):
        """When Resend API throws an exception, catch it and return success=False."""
        service = EmailService()
        service._settings = Settings(
            supabase_url="https://fake.supabase.co",
            supabase_anon_key="fake-anon",
            supabase_service_role_key="fake-service",
            email_provider="resend",
            resend_api_key=SECRET_TEST_KEY,
        )

        with patch("resend.Emails.send", side_effect=RuntimeError("Resend API rate limit exceeded")):
            res = service.send_assessment_invitation(
                to_email=CANDIDATE_EMAIL,
                candidate_name=CANDIDATE_NAME,
                job_title="Staff Backend Engineer",
                assessment_url="http://localhost:3000/assess/test-token",
            )
            assert res["success"] is False
            assert "rate limit exceeded" in res["error"]

    def test_send_invitation_masks_secret_key(self):
        """If exception message includes the raw API key, it must be masked."""
        service = EmailService()
        service._settings = Settings(
            supabase_url="https://fake.supabase.co",
            supabase_anon_key="fake-anon",
            supabase_service_role_key="fake-service",
            email_provider="resend",
            resend_api_key=SECRET_TEST_KEY,
        )

        with patch("resend.Emails.send", side_effect=ValueError(f"Invalid key: {SECRET_TEST_KEY}")):
            res = service.send_assessment_invitation(
                to_email=CANDIDATE_EMAIL,
                candidate_name=CANDIDATE_NAME,
                job_title="Staff Backend Engineer",
                assessment_url="http://localhost:3000/assess/test-token",
            )
            assert res["success"] is False
            assert SECRET_TEST_KEY not in res["error"]
            assert "[REDACTED]" in res["error"]


# ==============================================================================
# 2. Integration Tests: POST /api/jobs/{id}/sessions with Email
# ==============================================================================

class TestSessionCreationWithEmail:
    """Tests for POST /api/jobs/{id}/sessions with Resend email delivery."""

    @patch("app.api.sessions.EmailService.send_assessment_invitation")
    @patch("app.api.sessions.SessionService")
    @patch("app.api.sessions.JobService")
    def test_create_session_email_success(self, MockJobSvc, MockSessionSvc, mock_send_email, client: TestClient):
        """When recruiter generates link with send_email=True and Resend succeeds, return email_status='sent'."""
        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockSessionSvc.return_value.get_approved_questions.return_value = SAMPLE_APPROVED_QUESTIONS
        MockSessionSvc.return_value.create_session.return_value = dict(SAMPLE_SESSION)
        MockSessionSvc.return_value.update_email_status.return_value = True

        mock_send_email.return_value = {"success": True, "id": "resend_123", "error": None}

        payload = {
            "candidate_name": CANDIDATE_NAME,
            "candidate_email": CANDIDATE_EMAIL,
            "expires_in_days": 7,
            "send_email": True,
        }

        resp = client.post(f"/api/jobs/{JOB_ID}/sessions", json=payload)
        assert resp.status_code == 201
        data = resp.json()["data"]

        assert data["email_status"] == "sent"
        assert data["email_error"] is None
        assert f"/assess/{TOKEN}" in data["assessment_url"]
        mock_send_email.assert_called_once()

    @patch("app.api.sessions.EmailService.send_assessment_invitation")
    @patch("app.api.sessions.SessionService")
    @patch("app.api.sessions.JobService")
    def test_create_session_email_failure_preserves_session(
        self, MockJobSvc, MockSessionSvc, mock_send_email, client: TestClient
    ):
        """CRITICAL: If Resend fails, session must NOT be deleted. Link must still be returned."""
        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockSessionSvc.return_value.get_approved_questions.return_value = SAMPLE_APPROVED_QUESTIONS
        MockSessionSvc.return_value.create_session.return_value = dict(SAMPLE_SESSION)
        MockSessionSvc.return_value.update_email_status.return_value = True

        # Simulate Resend failure (e.g. domain verification error or network timeout)
        mock_send_email.return_value = {
            "success": False,
            "id": None,
            "error": "Domain not verified. Visit resend.com/domains",
        }

        payload = {
            "candidate_name": CANDIDATE_NAME,
            "candidate_email": CANDIDATE_EMAIL,
            "expires_in_days": 7,
            "send_email": True,
        }

        resp = client.post(f"/api/jobs/{JOB_ID}/sessions", json=payload)
        # Must return 201 Created — not 500!
        assert resp.status_code == 201
        data = resp.json()["data"]

        # Session and token are preserved for manual copy
        assert data["id"] == SESSION_ID
        assert data["token"] == TOKEN
        assert f"/assess/{TOKEN}" in data["assessment_url"]
        assert data["email_status"] == "failed"
        assert "Domain not verified" in data["email_error"]

    @patch("app.api.sessions.EmailService.send_assessment_invitation")
    @patch("app.api.sessions.SessionService")
    @patch("app.api.sessions.JobService")
    def test_create_session_with_send_email_false(
        self, MockJobSvc, MockSessionSvc, mock_send_email, client: TestClient
    ):
        """When send_email=False, no email should be dispatched and email_status='pending'."""
        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockSessionSvc.return_value.get_approved_questions.return_value = SAMPLE_APPROVED_QUESTIONS
        MockSessionSvc.return_value.create_session.return_value = dict(SAMPLE_SESSION)

        payload = {
            "candidate_name": CANDIDATE_NAME,
            "candidate_email": CANDIDATE_EMAIL,
            "expires_in_days": 7,
            "send_email": False,
        }

        resp = client.post(f"/api/jobs/{JOB_ID}/sessions", json=payload)
        assert resp.status_code == 201
        data = resp.json()["data"]

        assert data["email_status"] == "pending"
        mock_send_email.assert_not_called()


# ==============================================================================
# 3. Integration Tests: POST /api/sessions/{session_id}/retry-email
# ==============================================================================

class TestRetryEmailEndpoint:
    """Tests for the recruiter retry-email endpoint."""

    @patch("app.api.sessions.EmailService.send_assessment_invitation")
    @patch("app.api.sessions.SessionService")
    @patch("app.api.sessions.JobService")
    def test_retry_email_success(self, MockJobSvc, MockSessionSvc, mock_send_email, client: TestClient):
        """Recruiter successfully retries email invitation."""
        MockSessionSvc.return_value.get_session.return_value = dict(SAMPLE_SESSION)
        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        mock_send_email.return_value = {"success": True, "id": "resend_retry_999", "error": None}

        resp = client.post(f"/api/sessions/{SESSION_ID}/retry-email")
        assert resp.status_code == 200
        body = resp.json()

        assert body["success"] is True
        assert body["email_status"] == "sent"
        assert body["email_error"] is None
        assert "successfully sent" in body["message"]
        MockSessionSvc.return_value.update_email_status.assert_called_with(SESSION_ID, "sent")

    @patch("app.api.sessions.EmailService.send_assessment_invitation")
    @patch("app.api.sessions.SessionService")
    @patch("app.api.sessions.JobService")
    def test_retry_email_failure_handled(self, MockJobSvc, MockSessionSvc, mock_send_email, client: TestClient):
        """When retry email delivery fails, return success=False with email_status='failed'."""
        MockSessionSvc.return_value.get_session.return_value = dict(SAMPLE_SESSION)
        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        mock_send_email.return_value = {"success": False, "id": None, "error": "SMTP rejection"}

        resp = client.post(f"/api/sessions/{SESSION_ID}/retry-email")
        assert resp.status_code == 200
        body = resp.json()

        assert body["success"] is False
        assert body["email_status"] == "failed"
        assert "SMTP rejection" in body["email_error"]
        MockSessionSvc.return_value.update_email_status.assert_called_with(SESSION_ID, "failed")

    @patch("app.api.sessions.SessionService")
    def test_retry_email_session_not_found(self, MockSessionSvc, client: TestClient):
        """Retrying an unknown session returns 404 Not Found."""
        MockSessionSvc.return_value.get_session.return_value = None

        resp = client.post(f"/api/sessions/{str(uuid4())}/retry-email")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @patch("app.api.sessions.SessionService")
    @patch("app.api.sessions.JobService")
    def test_retry_email_cross_tenant_forbidden(self, MockJobSvc, MockSessionSvc, client: TestClient):
        """Recruiter cannot retry email for a session belonging to another recruiter's job (403 Forbidden)."""
        MockSessionSvc.return_value.get_session.return_value = dict(SAMPLE_SESSION)
        # MockJobSvc returns None when requested by current recruiter because it belongs to another recruiter
        MockJobSvc.return_value.get_job.return_value = None

        resp = client.post(f"/api/sessions/{SESSION_ID}/retry-email")
        assert resp.status_code == 403
        assert "permission" in resp.json()["detail"].lower()


# ==============================================================================
# 4. Security & Isolation Tests: Zero API Key Exposure
# ==============================================================================

class TestApiKeySecurity:
    """Ensure RESEND_API_KEY is strictly confidential and never returned to clients."""

    @patch("app.api.sessions.EmailService.send_assessment_invitation")
    @patch("app.api.sessions.SessionService")
    @patch("app.api.sessions.JobService")
    def test_api_responses_never_leak_resend_key(
        self, MockJobSvc, MockSessionSvc, mock_send_email, client: TestClient
    ):
        """Verify session creation response does not contain the Resend API key."""
        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockSessionSvc.return_value.get_approved_questions.return_value = SAMPLE_APPROVED_QUESTIONS
        MockSessionSvc.return_value.create_session.return_value = dict(SAMPLE_SESSION)
        mock_send_email.return_value = {"success": True, "id": "msg_123", "error": None}

        resp = client.post(
            f"/api/jobs/{JOB_ID}/sessions",
            json={
                "candidate_name": CANDIDATE_NAME,
                "candidate_email": CANDIDATE_EMAIL,
                "send_email": True,
            },
        )
        assert resp.status_code == 201
        text = resp.text
        assert "resend_api_key" not in text
        assert "re_" not in text or "re_test" not in text

    @patch("app.api.sessions.SessionService")
    @patch("app.api.sessions.JobService")
    def test_list_sessions_never_leaks_resend_key(self, MockJobSvc, MockSessionSvc, client: TestClient):
        """Verify list sessions response does not contain the Resend API key."""
        MockJobSvc.return_value.get_job.return_value = SAMPLE_JOB
        MockSessionSvc.return_value.list_sessions.return_value = [dict(SAMPLE_SESSION)]

        resp = client.get(f"/api/jobs/{JOB_ID}/sessions")
        assert resp.status_code == 200
        text = resp.text
        assert "resend_api_key" not in text
        assert "re_test" not in text
