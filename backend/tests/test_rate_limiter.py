"""
tests/test_rate_limiter.py
Tests for the sliding window in-memory rate limiter (Phase 10 Production Hardening).
"""
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, Request, status
from fastapi.testclient import TestClient

from app.core.rate_limiter import RateLimiter
from app.main import app


class TestRateLimiterUnit:
    """Unit tests for the RateLimiter class."""

    def test_requests_within_limit_pass(self):
        limiter = RateLimiter(requests_per_minute=5, name="test_limit", enable_in_test=True)
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client.host = "192.168.1.100"

        # 5 requests should succeed
        for _ in range(5):
            limiter(request)

    def test_requests_exceeding_limit_raise_429(self):
        limiter = RateLimiter(requests_per_minute=3, name="test_exceed", enable_in_test=True)
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client.host = "192.168.1.101"

        # First 3 succeed
        for _ in range(3):
            limiter(request)

        # 4th request must raise 429
        with pytest.raises(HTTPException) as exc_info:
            limiter(request)

        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Rate limit exceeded" in exc_info.value.detail
        assert "Retry-After" in exc_info.value.headers

    def test_separate_ips_have_independent_quotas(self):
        limiter = RateLimiter(requests_per_minute=2, name="test_ips", enable_in_test=True)

        req_ip1 = MagicMock(spec=Request)
        req_ip1.headers = {}
        req_ip1.client.host = "10.0.0.1"

        req_ip2 = MagicMock(spec=Request)
        req_ip2.headers = {}
        req_ip2.client.host = "10.0.0.2"

        # IP 1 uses all quota
        limiter(req_ip1)
        limiter(req_ip1)
        with pytest.raises(HTTPException):
            limiter(req_ip1)

        # IP 2 still has quota
        limiter(req_ip2)
        limiter(req_ip2)
        with pytest.raises(HTTPException):
            limiter(req_ip2)

    def test_x_forwarded_for_header_supported(self):
        limiter = RateLimiter(requests_per_minute=1, name="test_proxy", enable_in_test=True)

        req = MagicMock(spec=Request)
        req.headers = {"X-Forwarded-For": "203.0.113.195, 70.41.3.18"}
        req.client.host = "127.0.0.1"

        limiter(req)
        with pytest.raises(HTTPException):
            limiter(req)

    def test_reset_clears_records(self):
        limiter = RateLimiter(requests_per_minute=1, name="test_reset", enable_in_test=True)
        req = MagicMock(spec=Request)
        req.headers = {}
        req.client.host = "1.2.3.4"

        limiter(req)
        with pytest.raises(HTTPException):
            limiter(req)

        # Reset
        limiter.reset()
        # Should now succeed again
        limiter(req)


class TestRateLimiterIntegration:
    """Integration test with candidate API endpoint."""

    def test_candidate_endpoint_rate_limited_when_enabled(self):
        from app.api.sessions import candidate_view_limiter

        # Configure small limit and enable in test
        saved_limit = candidate_view_limiter.requests_per_minute
        saved_enable = candidate_view_limiter.enable_in_test
        candidate_view_limiter.requests_per_minute = 2
        candidate_view_limiter.enable_in_test = True
        candidate_view_limiter.reset()

        try:
            mock_session = {
                "id": "22222222-2222-2222-2222-222222222222",
                "job_id": "11111111-1111-1111-1111-111111111111",
                "candidate_name": "Test Candidate",
                "candidate_email": "candidate@example.com",
                "token": "rate-test-token",
                "status": "pending",
                "expires_at": None,
            }
            mock_job = {
                "id": "11111111-1111-1111-1111-111111111111",
                "title": "Software Engineer",
                "description": "Desc",
            }
            with patch("app.services.session_service.SessionService.get_session_by_token", return_value=mock_session), \
                 patch("app.services.session_service.SessionService.get_job_public", return_value=mock_job), \
                 patch("app.services.session_service.SessionService.get_approved_questions", return_value=[]), \
                 patch("app.services.session_service.SessionService.mark_in_progress"):

                with TestClient(app) as client:
                    # Request 1 & 2 succeed
                    r1 = client.get("/api/sessions/rate-test-token")
                    assert r1.status_code == 200

                    r2 = client.get("/api/sessions/rate-test-token")
                    assert r2.status_code == 200

                    # Request 3 should trigger 429
                    r3 = client.get("/api/sessions/rate-test-token")
                    assert r3.status_code == 429
                    assert "Rate limit exceeded" in r3.json()["detail"]
                    assert "retry-after" in r3.headers
        finally:
            candidate_view_limiter.requests_per_minute = saved_limit
            candidate_view_limiter.enable_in_test = saved_enable
            candidate_view_limiter.reset()
