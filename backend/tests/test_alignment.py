"""
tests/test_alignment.py
Comprehensive test suite for Phase 7: Job-Candidate Behavioral Alignment.

Coverage:
  A. Calculator Unit Tests (pure Python, 0 mocks, deterministic math)
  B. AlignmentService Helper Unit Tests
  C. API Integration Tests (POST/GET /api/sessions/{id}/alignment, GET /api/jobs/{id}/alignments)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.alignment.calculator import calculate_alignment
from app.schemas.alignment import DimensionAlignmentItem, SessionAlignmentRead
from app.services.alignment_service import AlignmentService

# ── Fixtures & Mock Data ───────────────────────────────────────────────────────

JOB_ID = str(uuid4())
SESSION_ID = str(uuid4())
RECRUITER_ID = "11111111-1111-1111-1111-111111111111"

MOCK_JOB = {
    "id": JOB_ID,
    "recruiter_id": RECRUITER_ID,
    "title": "Senior Software Engineer",
    "status": "active",
}

MOCK_SESSION_COMPLETED = {
    "id": SESSION_ID,
    "job_id": JOB_ID,
    "candidate_name": "Jane Doe",
    "candidate_email": "jane@example.com",
    "status": "completed",
    "submitted_at": "2026-09-27T00:00:00Z",
}

MOCK_SESSION_PENDING = {
    **MOCK_SESSION_COMPLETED,
    "status": "pending",
}

MOCK_REQUIREMENTS = [
    {
        "dimension_name": "communication",
        "importance": 80,
        "confirmed": True,
        "reason": "Clear technical discussion required",
    },
    {
        "dimension_name": "teamwork",
        "importance": 60,
        "confirmed": True,
        "reason": "Cross-functional collaboration",
    },
    {
        "dimension_name": "decision_making",
        "importance": 60,
        "confirmed": True,
        "reason": "Autonomous architectural choices",
    },
]

MOCK_RESPONSE_SCORES = [
    {
        "id": str(uuid4()),
        "dimension_name": "communication",
        "normalized_score": 85,
        "confidence": 0.88,
        "status": "scored",
    },
    {
        "id": str(uuid4()),
        "dimension_name": "teamwork",
        "normalized_score": 75,
        "confidence": 0.82,
        "status": "scored",
    },
    {
        "id": str(uuid4()),
        "dimension_name": "decision_making",
        "normalized_score": 65,
        "confidence": 0.79,
        "status": "scored",
    },
]


# ===============================================================================
# A. CALCULATOR UNIT TESTS (Pure Python, Deterministic Math)
# ===============================================================================

class TestAlignmentCalculator:
    """Unit tests for calculate_alignment math and rules."""

    def test_formula_weighted_overall_score(self):
        """
        Verify: sum(candidate_score * weight) / sum(weight)
        Weights:
          communication: 80, score: 85 -> product: 6800
          teamwork:      60, score: 75 -> product: 4500
          decision_making: 60, score: 65 -> product: 3900
        Total weight = 200
        Sum products = 15200
        Overall = 15200 / 200 = 76.0
        """
        result = calculate_alignment(MOCK_REQUIREMENTS, MOCK_RESPONSE_SCORES)
        assert result["overall_score"] == 76.0
        assert result["total_weight"] == 200

    def test_contribution_sums_to_overall_score(self):
        """
        Each dimension's point contribution must sum to the overall score.
        contribution_i = score_i * (weight_i / total_weight)
        comm: 85 * (80/200) = 34.0
        team: 75 * (60/200) = 22.5
        dec:  65 * (60/200) = 19.5
        Total = 34.0 + 22.5 + 19.5 = 76.0
        """
        result = calculate_alignment(MOCK_REQUIREMENTS, MOCK_RESPONSE_SCORES)
        contrib_sum = sum(d["contribution"] for d in result["dimension_alignments"] if d["status"] == "assessed")
        assert pytest.approx(contrib_sum, 0.1) == result["overall_score"]

    def test_weight_percentages_sum_to_100(self):
        """Dimension weight percentages should sum to 100%."""
        result = calculate_alignment(MOCK_REQUIREMENTS, MOCK_RESPONSE_SCORES)
        weight_pct_sum = sum(d["weight_percentage"] for d in result["dimension_alignments"] if d["status"] == "assessed")
        assert pytest.approx(weight_pct_sum, 0.1) == 100.0

    def test_missing_dimension_handled_safely(self):
        """
        If a job requires a dimension that candidate did not answer,
        candidate_score is 0.0, status is 'missing', and contribution is 0.0.
        Overall score is penalized proportionally by the unassessed weight.
        """
        # Candidate only answered communication & teamwork (decision_making missing)
        partial_scores = [MOCK_RESPONSE_SCORES[0], MOCK_RESPONSE_SCORES[1]]
        result = calculate_alignment(MOCK_REQUIREMENTS, partial_scores)

        # Expected:
        # comm: 85 * 80 = 6800
        # team: 75 * 60 = 4500
        # dec:   0 * 60 =    0
        # Total weight = 200 -> overall = 11300 / 200 = 56.5
        assert result["overall_score"] == 56.5

        dec_dim = next(d for d in result["dimension_alignments"] if d["dimension_name"] == "decision_making")
        assert dec_dim["status"] == "missing"
        assert dec_dim["candidate_score"] == 0.0
        assert dec_dim["contribution"] == 0.0

        # Should be flagged in areas for review
        assert any("decision making" in area.lower() and "missing" in area.lower() for area in result["areas_for_review"])

    def test_unweighted_dimension_handled(self):
        """
        Candidate answered an extra dimension not in job requirements.
        Included with status='unweighted', weight=0, contribution=0.
        """
        extra_scores = MOCK_RESPONSE_SCORES + [
            {"dimension_name": "adaptability", "normalized_score": 90, "confidence": 0.85, "status": "scored"}
        ]
        result = calculate_alignment(MOCK_REQUIREMENTS, extra_scores)

        # Overall score still based on the required dimensions
        assert result["overall_score"] == 76.0

        adapt = next(d for d in result["dimension_alignments"] if d["dimension_name"] == "adaptability")
        assert adapt["status"] == "unweighted"
        assert adapt["job_weight"] == 0.0
        assert adapt["contribution"] == 0.0
        assert adapt["candidate_score"] == 90.0

    def test_multiple_responses_for_same_dimension_averaged(self):
        """Multiple candidate answers for the same dimension should be averaged."""
        multi_scores = [
            {"dimension_name": "communication", "normalized_score": 70, "confidence": 0.8, "status": "scored"},
            {"dimension_name": "communication", "normalized_score": 90, "confidence": 0.9, "status": "scored"},
        ]
        single_req = [{"dimension_name": "communication", "importance": 100, "confirmed": True}]
        result = calculate_alignment(single_req, multi_scores)

        comm = result["dimension_alignments"][0]
        assert comm["candidate_score"] == 80.0
        assert comm["response_count"] == 2
        assert comm["confidence"] == 0.85
        assert result["overall_score"] == 80.0

    def test_zero_total_weight_prevents_division_by_zero(self):
        """All weights 0 should not raise ZeroDivisionError and return clean score."""
        zero_reqs = [{"dimension_name": "communication", "importance": 0, "confirmed": True}]
        result = calculate_alignment(zero_reqs, MOCK_RESPONSE_SCORES)
        assert result["overall_score"] >= 0.0
        assert result["total_weight"] == 0

    def test_empty_requirements_and_scores_safe(self):
        """Empty inputs should return safe empty structure with 0.0 overall score."""
        result = calculate_alignment([], [])
        assert result["overall_score"] == 0.0
        assert result["total_weight"] == 0
        assert result["dimension_alignments"] == []
        assert isinstance(result["strengths"], list)
        assert isinstance(result["areas_for_review"], list)

    def test_strengths_detection(self):
        """High score on important dimension should generate positive strength note."""
        strong_scores = [
            {"dimension_name": "communication", "normalized_score": 95, "confidence": 0.95, "status": "scored"},
            {"dimension_name": "teamwork", "normalized_score": 70, "confidence": 0.80, "status": "scored"},
        ]
        reqs = [
            {"dimension_name": "communication", "importance": 90, "confirmed": True},
            {"dimension_name": "teamwork", "importance": 50, "confirmed": True},
        ]
        result = calculate_alignment(reqs, strong_scores)
        assert any("communication" in s.lower() and "strong" in s.lower() for s in result["strengths"])

    def test_areas_for_review_priority_gap(self):
        """Low score on high-priority requirement should generate review item."""
        weak_scores = [
            {"dimension_name": "communication", "normalized_score": 40, "confidence": 0.85, "status": "scored"},
        ]
        reqs = [
            {"dimension_name": "communication", "importance": 85, "confirmed": True},
        ]
        result = calculate_alignment(reqs, weak_scores)
        assert any("communication" in a.lower() and "gap" in a.lower() for a in result["areas_for_review"])

    def test_areas_for_review_low_confidence(self):
        """Low confidence score (<0.45) should be noted in areas for review."""
        low_conf_scores = [
            {"dimension_name": "communication", "normalized_score": 80, "confidence": 0.30, "status": "scored"},
        ]
        reqs = [
            {"dimension_name": "communication", "importance": 60, "confirmed": True},
        ]
        result = calculate_alignment(reqs, low_conf_scores)
        assert any("confidence" in a.lower() for a in result["areas_for_review"])

    def test_prioritizes_confirmed_requirements_when_present(self):
        """When confirmed requirements exist, unconfirmed draft ones should be excluded."""
        mixed_reqs = [
            {"dimension_name": "communication", "importance": 90, "confirmed": True},
            {"dimension_name": "leadership", "importance": 20, "confirmed": False},
        ]
        scores = [
            {"dimension_name": "communication", "normalized_score": 80, "confidence": 0.8, "status": "scored"}
        ]
        result = calculate_alignment(mixed_reqs, scores)
        # Leadership was not confirmed, so total weight should only reflect communication
        assert result["total_weight"] == 90
        assert result["overall_score"] == 80.0

    def test_no_employment_recommendations_output(self):
        """
        Verify strict compliance with rule:
        NO Hire / Reject / Selected recommendations output.
        """
        result = calculate_alignment(MOCK_REQUIREMENTS, MOCK_RESPONSE_SCORES)
        combined_text = " ".join(result["strengths"] + result["areas_for_review"]).lower()
        forbidden_terms = ["hire", "reject", "do not hire", "selected", "unfit", "terminate"]
        for term in forbidden_terms:
            assert f" {term} " not in f" {combined_text} "


# ===============================================================================
# B. ALIGNMENT SERVICE HELPER TESTS
# ===============================================================================

class TestAlignmentServiceHelpers:
    """Unit tests for AlignmentService static helpers."""

    def test_parse_json_field_variations(self):
        assert AlignmentService._parse_json_field([1, 2, 3]) == [1, 2, 3]
        assert AlignmentService._parse_json_field('["a", "b"]') == ["a", "b"]
        assert AlignmentService._parse_json_field("invalid json") == []
        assert AlignmentService._parse_json_field(None) == []

    def test_raise_if_error(self):
        mock_ok = MagicMock(error=None)
        AlignmentService._raise_if_error(mock_ok)  # should not raise

        mock_err = MagicMock(error="DB connection refused")
        with pytest.raises(RuntimeError, match="DB connection refused"):
            AlignmentService._raise_if_error(mock_err)


# ===============================================================================
# C. API ENDPOINTS INTEGRATION TESTS
# ===============================================================================

class TestAlignmentEndpoints:
    """Tests for POST / GET alignment endpoints."""

    def test_calculate_alignment_success(self, client):
        """Happy path — calculates and returns 200 with SessionAlignmentRead."""
        with patch("app.api.alignment.AlignmentService") as MockSvc, \
             patch("app.api.alignment.JobService") as MockJobSvc:

            mock_job_svc = MagicMock()
            mock_job_svc.get_job.return_value = MOCK_JOB
            MockJobSvc.return_value = mock_job_svc

            mock_svc = MagicMock()
            mock_svc.get_session.return_value = MOCK_SESSION_COMPLETED
            mock_svc.get_response_scores.return_value = MOCK_RESPONSE_SCORES
            mock_svc.calculate_and_save_alignment.return_value = {
                "id": str(uuid4()),
                "session_id": SESSION_ID,
                "job_id": JOB_ID,
                "candidate_name": "Jane Doe",
                "job_title": "Senior Software Engineer",
                "overall_score": 76.0,
                "total_weight": 200,
                "total_dimensions_count": 3,
                "assessed_dimensions_count": 3,
                "average_confidence": 0.83,
                "dimension_alignments": [
                    {
                        "dimension_name": "communication",
                        "dimension_label": "Communication",
                        "job_weight": 80.0,
                        "weight_percentage": 40.0,
                        "candidate_score": 85.0,
                        "contribution": 34.0,
                        "status": "assessed",
                        "confidence": 0.88,
                        "response_count": 1,
                    }
                ],
                "strengths": ["Strong communication"],
                "areas_for_review": ["No critical gaps"],
                "metadata": {},
                "calculated_at": "2026-09-27T00:00:00Z",
            }
            MockSvc.return_value = mock_svc

            resp = client.post(f"/api/sessions/{SESSION_ID}/alignment")

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["overall_score"] == 76.0
        assert body["data"]["candidate_name"] == "Jane Doe"

    def test_calculate_alignment_uncompleted_session_fails(self, client):
        """Cannot calculate alignment for uncompleted session -> 422."""
        with patch("app.api.alignment.AlignmentService") as MockSvc, \
             patch("app.api.alignment.JobService") as MockJobSvc:

            mock_job_svc = MagicMock()
            mock_job_svc.get_job.return_value = MOCK_JOB
            MockJobSvc.return_value = mock_job_svc

            mock_svc = MagicMock()
            mock_svc.get_session.return_value = MOCK_SESSION_PENDING
            MockSvc.return_value = mock_svc

            resp = client.post(f"/api/sessions/{SESSION_ID}/alignment")

        assert resp.status_code == 422

    def test_calculate_alignment_unscored_session_fails(self, client):
        """Cannot calculate alignment if responses have not been scored -> 422."""
        with patch("app.api.alignment.AlignmentService") as MockSvc, \
             patch("app.api.alignment.JobService") as MockJobSvc:

            mock_job_svc = MagicMock()
            mock_job_svc.get_job.return_value = MOCK_JOB
            MockJobSvc.return_value = mock_job_svc

            mock_svc = MagicMock()
            mock_svc.get_session.return_value = MOCK_SESSION_COMPLETED
            mock_svc.get_response_scores.return_value = []  # No scores
            MockSvc.return_value = mock_svc

            resp = client.post(f"/api/sessions/{SESSION_ID}/alignment")

        assert resp.status_code == 422

    def test_calculate_alignment_requires_auth(self):
        """Unauthenticated request must receive 401."""
        from fastapi.testclient import TestClient
        from app.main import app as _app

        saved = dict(_app.dependency_overrides)
        _app.dependency_overrides.clear()
        try:
            with TestClient(_app) as raw_client:
                resp = raw_client.post(f"/api/sessions/{SESSION_ID}/alignment")
            assert resp.status_code in (401, 403, 422)
        finally:
            _app.dependency_overrides.update(saved)

    def test_calculate_alignment_wrong_recruiter_forbidden(self, client):
        """403 if session belongs to another recruiter's job."""
        other_job = {**MOCK_JOB, "recruiter_id": str(uuid4())}
        with patch("app.api.alignment.AlignmentService") as MockSvc, \
             patch("app.api.alignment.JobService") as MockJobSvc:

            mock_job_svc = MagicMock()
            mock_job_svc.get_job.return_value = other_job
            MockJobSvc.return_value = mock_job_svc

            mock_svc = MagicMock()
            mock_svc.get_session.return_value = MOCK_SESSION_COMPLETED
            MockSvc.return_value = mock_svc

            resp = client.post(f"/api/sessions/{SESSION_ID}/alignment")

        assert resp.status_code == 403

    def test_get_alignment_success(self, client):
        """GET /api/sessions/{id}/alignment returns 200 with saved record."""
        with patch("app.api.alignment.AlignmentService") as MockSvc, \
             patch("app.api.alignment.JobService") as MockJobSvc:

            mock_job_svc = MagicMock()
            mock_job_svc.get_job.return_value = MOCK_JOB
            MockJobSvc.return_value = mock_job_svc

            mock_svc = MagicMock()
            mock_svc.get_session.return_value = MOCK_SESSION_COMPLETED
            mock_svc.get_alignment.return_value = {
                "id": str(uuid4()),
                "session_id": SESSION_ID,
                "job_id": JOB_ID,
                "candidate_name": "Jane Doe",
                "job_title": "Senior Software Engineer",
                "overall_score": 76.0,
                "total_weight": 200,
                "total_dimensions_count": 3,
                "assessed_dimensions_count": 3,
                "average_confidence": 0.83,
                "dimension_alignments": [],
                "strengths": ["Strong skills"],
                "areas_for_review": [],
                "metadata": {},
                "calculated_at": "2026-09-27T00:00:00Z",
            }
            MockSvc.return_value = mock_svc

            resp = client.get(f"/api/sessions/{SESSION_ID}/alignment")

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["overall_score"] == 76.0

    def test_get_alignment_not_found(self, client):
        """GET /api/sessions/{id}/alignment returns 404 when uncalculated and unscored."""
        with patch("app.api.alignment.AlignmentService") as MockSvc, \
             patch("app.api.alignment.JobService") as MockJobSvc:

            mock_job_svc = MagicMock()
            mock_job_svc.get_job.return_value = MOCK_JOB
            MockJobSvc.return_value = mock_job_svc

            mock_svc = MagicMock()
            mock_svc.get_session.return_value = MOCK_SESSION_COMPLETED
            mock_svc.get_alignment.return_value = None
            mock_svc.get_response_scores.return_value = []
            MockSvc.return_value = mock_svc

            resp = client.get(f"/api/sessions/{SESSION_ID}/alignment")

        assert resp.status_code == 404

    def test_list_job_alignments_success(self, client):
        """GET /api/jobs/{id}/alignments returns 200 with list of session alignments."""
        with patch("app.api.alignment.AlignmentService") as MockSvc, \
             patch("app.api.alignment.JobService") as MockJobSvc:

            mock_job_svc = MagicMock()
            mock_job_svc.get_job.return_value = MOCK_JOB
            MockJobSvc.return_value = mock_job_svc

            mock_svc = MagicMock()
            mock_svc.list_alignments_for_job.return_value = [
                {
                    "id": str(uuid4()),
                    "session_id": SESSION_ID,
                    "job_id": JOB_ID,
                    "candidate_name": "Jane Doe",
                    "job_title": "Senior Software Engineer",
                    "overall_score": 76.0,
                    "total_weight": 200,
                    "total_dimensions_count": 3,
                    "assessed_dimensions_count": 3,
                    "average_confidence": 0.83,
                    "dimension_alignments": [],
                    "strengths": ["Strong skills"],
                    "areas_for_review": [],
                    "metadata": {},
                    "calculated_at": "2026-09-27T00:00:00Z",
                }
            ]
            MockSvc.return_value = mock_svc

            resp = client.get(f"/api/jobs/{JOB_ID}/alignments")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["overall_score"] == 76.0
