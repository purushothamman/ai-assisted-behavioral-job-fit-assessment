"""
tests/test_scoring.py
Comprehensive tests for Phase 6 response analysis and scoring pipeline.

Coverage:
  A. Preprocessor (unit — pure Python, no mocks needed)
  B. Rubric (unit — pure Python, no mocks needed)
  C. Analyzer (integration — embedder mocked with deterministic numpy arrays)
  D. Scoring API — POST /api/sessions/{id}/score
  E. Scoring API — GET  /api/sessions/{id}/scores
  F. Authorization + edge cases

Strategy:
  - embed() is patched in tests that touch the NLP pipeline so the 90 MB
    all-MiniLM-L6-v2 model is never loaded during CI.
  - ScoringService is patched at the API layer (same pattern as Phase 5 tests).
  - No real Supabase calls are made.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Shared test IDs
# ---------------------------------------------------------------------------

SESSION_ID  = str(uuid4())
JOB_ID      = str(uuid4())
Q_ID_1      = str(uuid4())
Q_ID_2      = str(uuid4())
RESP_ID_1   = str(uuid4())
RESP_ID_2   = str(uuid4())
SCORE_ID_1  = str(uuid4())
SCORE_ID_2  = str(uuid4())
DIM_ID      = str(uuid4())

MOCK_SESSION_COMPLETED = {
    "id":              SESSION_ID,
    "job_id":          JOB_ID,
    "candidate_name":  "Jane Doe",
    "candidate_email": "jane@example.com",
    "status":          "completed",
    "submitted_at":    "2026-01-02T12:00:00+00:00",
}

MOCK_SESSION_PENDING = {
    **MOCK_SESSION_COMPLETED,
    "status": "pending",
    "submitted_at": None,
}

MOCK_JOB = {
    "id":           JOB_ID,
    "recruiter_id": "11111111-1111-1111-1111-111111111111",
    "title":        "Senior Engineer",
    "description":  "Lead engineering teams.",
}

MOCK_RESPONSE_1 = {
    "id":          RESP_ID_1,
    "session_id":  SESSION_ID,
    "question_id": Q_ID_1,
    "answer":      "In my previous role I led the team through a major restructuring. "
                   "I organized weekly syncs, kept stakeholders informed, and resolved conflicts swiftly.",
    "created_at":  "2026-01-02T10:00:00+00:00",
}

MOCK_RESPONSE_2 = {
    "id":          RESP_ID_2,
    "session_id":  SESSION_ID,
    "question_id": Q_ID_2,
    "answer":      "When our project deadline moved up by two weeks I reprioritized tasks "
                   "and reallocated resources to meet the new timeline without dropping quality.",
    "created_at":  "2026-01-02T10:05:00+00:00",
}

MOCK_SCORE_ROW = {
    "id":                SCORE_ID_1,
    "session_id":        SESSION_ID,
    "question_id":       Q_ID_1,
    "response_id":       RESP_ID_1,
    "dimension_name":    "communication",
    "normalized_score":  75,
    "raw_score":         0.75,
    "confidence":        0.68,
    "indicators_matched": 2,
    "total_indicators":   3,
    "status":            "scored",
    "evidence":          [
        {"indicator_name": "clarity", "similarity": 0.61, "score": 2, "matched": True,  "level": "strong"},
        {"indicator_name": "listening", "similarity": 0.35, "score": 1, "matched": True, "level": "partial"},
        {"indicator_name": "sharing",  "similarity": 0.12, "score": 0, "matched": False, "level": "none"},
    ],
    "scored_at": "2026-01-02T12:30:00+00:00",
}


# ===========================================================================
# A. PREPROCESSOR UNIT TESTS
# ===========================================================================

class TestPreprocessor:
    """Pure-Python text preprocessing — no mocking needed."""

    def test_clean_strips_whitespace(self):
        from app.nlp.preprocessor import clean
        assert clean("  hello world  ") == "hello world"

    def test_clean_collapses_internal_whitespace(self):
        from app.nlp.preprocessor import clean
        assert clean("hello\n\n  world\t!") == "hello world !"

    def test_clean_empty_string(self):
        from app.nlp.preprocessor import clean
        assert clean("") == ""

    def test_clean_non_string_returns_empty(self):
        from app.nlp.preprocessor import clean
        assert clean(None) == ""    # type: ignore[arg-type]

    def test_quality_gate_valid_response(self):
        from app.nlp.preprocessor import quality_gate
        long_answer = "I led the team through a major product launch last quarter."
        result = quality_gate(long_answer)
        assert result.is_valid is True
        assert result.flag == ""

    def test_quality_gate_empty_response(self):
        from app.nlp.preprocessor import quality_gate
        result = quality_gate("")
        assert result.is_valid is False
        assert result.flag == "empty"
        assert result.char_count == 0

    def test_quality_gate_whitespace_only(self):
        from app.nlp.preprocessor import quality_gate
        result = quality_gate("   \n\t  ")
        assert result.is_valid is False
        assert result.flag == "empty"

    def test_quality_gate_too_short_chars(self):
        from app.nlp.preprocessor import quality_gate
        result = quality_gate("Hi")     # < MIN_CHARS (10)
        assert result.is_valid is False
        assert result.flag == "too_short"

    def test_quality_gate_too_few_words(self):
        from app.nlp.preprocessor import quality_gate
        result = quality_gate("1234567890")   # 10 chars but only 1 word
        assert result.is_valid is False
        assert result.flag == "too_short"

    def test_quality_gate_garbled_input(self):
        from app.nlp.preprocessor import quality_gate
        result = quality_gate("!!! ??? ### !!! ???")
        assert result.is_valid is False
        assert result.flag == "garbled"

    def test_quality_gate_returns_word_count(self):
        from app.nlp.preprocessor import quality_gate
        result = quality_gate("The quick brown fox jumped over the lazy dog today.")
        assert result.word_count == 10
        assert result.is_valid is True


# ===========================================================================
# B. RUBRIC UNIT TESTS
# ===========================================================================

class TestRubric:
    """Pure-Python scoring rubric — no mocking needed."""

    def test_score_indicator_strong(self):
        from app.scoring.rubric import score_indicator
        assert score_indicator(0.50) == 2

    def test_score_indicator_partial(self):
        from app.scoring.rubric import score_indicator
        assert score_indicator(0.35) == 1

    def test_score_indicator_none(self):
        from app.scoring.rubric import score_indicator
        assert score_indicator(0.10) == 0

    def test_score_indicator_boundary_strong(self):
        from app.scoring.rubric import score_indicator, STRONG_THRESHOLD
        assert score_indicator(STRONG_THRESHOLD) == 2

    def test_score_indicator_boundary_partial(self):
        from app.scoring.rubric import score_indicator, PARTIAL_THRESHOLD
        assert score_indicator(PARTIAL_THRESHOLD) == 1

    def test_normalize_score_full(self):
        from app.scoring.rubric import normalize_score
        assert normalize_score(6, 3) == 100   # 3 indicators, all score 2

    def test_normalize_score_zero(self):
        from app.scoring.rubric import normalize_score
        assert normalize_score(0, 3) == 0

    def test_normalize_score_half(self):
        from app.scoring.rubric import normalize_score
        assert normalize_score(3, 3) == 50   # 3 indicators, all score 1

    def test_normalize_score_no_indicators(self):
        from app.scoring.rubric import normalize_score
        assert normalize_score(0, 0) == 0    # safe guard

    def test_compute_confidence(self):
        from app.scoring.rubric import compute_confidence
        sims = [0.6, 0.4, 0.2]
        conf = compute_confidence(sims)
        assert abs(conf - round(0.4, 4)) < 1e-6

    def test_compute_confidence_empty(self):
        from app.scoring.rubric import compute_confidence
        assert compute_confidence([]) == 0.0

    def test_compute_confidence_clips_negatives(self):
        from app.scoring.rubric import compute_confidence
        conf = compute_confidence([-0.1, 0.5])
        assert conf >= 0.0

    def test_build_evidence_length(self):
        from app.scoring.rubric import build_evidence
        ev = build_evidence(["clarity", "listening"], [0.6, 0.3])
        assert len(ev) == 2

    def test_build_evidence_matched_flag(self):
        from app.scoring.rubric import build_evidence
        ev = build_evidence(["clarity", "noise"], [0.6, 0.1])
        assert ev[0].matched is True
        assert ev[1].matched is False

    def test_build_evidence_level_labels(self):
        from app.scoring.rubric import build_evidence
        ev = build_evidence(["a", "b", "c"], [0.55, 0.35, 0.10])
        assert ev[0].level == "strong"
        assert ev[1].level == "partial"
        assert ev[2].level == "none"

    def test_build_evidence_mismatch_raises(self):
        from app.scoring.rubric import build_evidence
        with pytest.raises(ValueError):
            build_evidence(["only_one"], [0.5, 0.3])

    def test_aggregate_dimension_score_full_pipeline(self):
        from app.scoring.rubric import aggregate_dimension_score
        score = aggregate_dimension_score(
            "communication",
            ["clarity", "listening", "sharing"],
            [0.60, 0.40, 0.10],
        )
        assert score.dimension_name == "communication"
        assert 0 <= score.normalized_score <= 100
        assert score.total_indicators == 3
        assert score.indicators_matched == 2   # 0.60 (strong), 0.40 (partial), 0.10 (none)
        assert score.status == "scored"

    def test_aggregate_dimension_score_no_indicators(self):
        from app.scoring.rubric import aggregate_dimension_score
        score = aggregate_dimension_score("communication", [], [])
        assert score.normalized_score == 0
        assert score.status == "no_indicators"


# ===========================================================================
# C. ANALYZER INTEGRATION TESTS (embedder mocked)
# ===========================================================================

def _make_embedding(sim_with_first: float, dim: int = 8) -> np.ndarray:
    """
    Return a unit-length embedding whose cosine similarity with the first
    returned embedding (the answer) is approximately sim_with_first.

    Used to control which thresholds are hit in rubric tests.
    """
    # Simple approach: answer vec = e_0; indicator vec = cos*e_0 + sin*e_1
    theta = np.arccos(np.clip(sim_with_first, 0.0, 1.0))
    vec   = np.zeros(dim, dtype=np.float32)
    vec[0] = np.cos(theta)
    vec[1] = np.sin(theta)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


class TestAnalyzer:
    """Analyzer integration tests — embed() is mocked."""

    def _run_analysis(self, sims, names=None, texts=None):
        """Helper: run analyze_response with mocked embeddings."""
        from app.scoring.analyzer import analyze_response

        n   = len(sims)
        dim = 8
        # Build answer embedding (e_0 unit vector)
        answer_emb = np.zeros((1, dim), dtype=np.float32)
        answer_emb[0, 0] = 1.0

        # Build indicator embeddings with desired cosine sims to answer
        ind_embs = np.array([_make_embedding(s, dim) for s in sims], dtype=np.float32)

        # Stack: first row = answer, rest = indicators
        all_embs = np.vstack([answer_emb, ind_embs])

        if names is None:
            names = [f"indicator_{i}" for i in range(n)]
        if texts is None:
            texts = [f"text for indicator {i}" for i in range(n)]

        with patch("app.scoring.analyzer.embed", return_value=all_embs):
            return analyze_response("A long enough valid candidate answer for testing.", "communication", names, texts)

    def test_analyze_response_valid(self):
        score = self._run_analysis([0.6, 0.4, 0.1])
        assert score.status == "scored"
        assert score.normalized_score > 0
        assert score.total_indicators == 3

    def test_analyze_response_all_strong(self):
        score = self._run_analysis([0.55, 0.60, 0.50])
        assert score.normalized_score == 100
        assert score.indicators_matched == 3

    def test_analyze_response_none_matched(self):
        score = self._run_analysis([0.1, 0.05, 0.15])
        assert score.normalized_score == 0
        assert score.indicators_matched == 0

    def test_analyze_response_empty_answer_returns_invalid(self):
        from app.scoring.analyzer import analyze_response
        score = analyze_response("", "communication", ["clarity"], ["Clarity of expression"])
        assert score.status.startswith("invalid")
        assert score.normalized_score == 0

    def test_analyze_response_too_short_answer(self):
        from app.scoring.analyzer import analyze_response
        score = analyze_response("Hi", "communication", ["clarity"], ["Clarity of expression"])
        assert score.status.startswith("invalid")

    def test_analyze_response_no_indicators(self):
        from app.scoring.analyzer import analyze_response
        score = analyze_response(
            "A long enough valid candidate answer for testing.",
            "communication", [], [],
        )
        assert score.status == "no_indicators"
        assert score.normalized_score == 0

    def test_analyze_response_mismatched_names_texts_raises(self):
        from app.scoring.analyzer import analyze_response
        with pytest.raises(ValueError):
            analyze_response(
                "A long enough answer for testing.",
                "communication",
                ["one_indicator"],
                ["text1", "text2"],   # mismatched length
            )

    def test_analyze_response_safe_never_raises(self):
        from app.scoring.analyzer import analyze_response_safe
        # Pass bad data that would normally raise — safe wrapper must absorb it
        with patch("app.scoring.analyzer.embed", side_effect=RuntimeError("model unavailable")):
            score = analyze_response_safe(
                "A valid long enough answer for testing.",
                "communication",
                ["clarity"],
                ["Clear and concise communication"],
            )
        assert score.status == "error"
        assert score.normalized_score == 0

    def test_evidence_records_present(self):
        score = self._run_analysis([0.6, 0.2], names=["alpha", "beta"])
        assert len(score.evidence) == 2
        names_in_evidence = [e.indicator_name for e in score.evidence]
        assert "alpha" in names_in_evidence
        assert "beta" in names_in_evidence

    def test_confidence_between_0_and_1(self):
        score = self._run_analysis([0.5, 0.3, 0.1])
        assert 0.0 <= score.confidence <= 1.0


# ===========================================================================
# D. SCORING API — POST /api/sessions/{id}/score
# ===========================================================================

class TestScoreEndpoint:
    """Tests for POST /api/sessions/{session_id}/score."""

    def test_score_session_success(self, client):
        """Happy path — completed session is scored, returns score list."""
        mock_score = {**MOCK_SCORE_ROW}

        with patch("app.api.scoring.ScoringService") as MockSvc, \
             patch("app.api.scoring.SessionService") as MockSsvc, \
             patch("app.services.job_service.JobService.get_job", return_value=MOCK_JOB):

            mock_instance = MagicMock()
            mock_instance.get_session.return_value = MOCK_SESSION_COMPLETED
            mock_instance.score_session.return_value = [mock_score]
            mock_instance.get_job_title.return_value = "Senior Engineer"
            MockSvc.return_value = mock_instance

            mock_session_svc = MagicMock()
            MockSsvc.return_value = mock_session_svc

            resp = client.post(f"/api/sessions/{SESSION_ID}/score")

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["scores"]) == 1
        assert body["scores"][0]["normalized_score"] == 75

    def test_score_session_not_found(self, client):
        """404 when session does not exist."""
        with patch("app.api.scoring.ScoringService") as MockSvc:
            mock_instance = MagicMock()
            mock_instance.get_session.return_value = None
            MockSvc.return_value = mock_instance

            resp = client.post(f"/api/sessions/{SESSION_ID}/score")

        assert resp.status_code == 404

    def test_score_session_not_completed(self, client):
        """422 when session is still pending."""
        with patch("app.api.scoring.ScoringService") as MockSvc, \
             patch("app.services.job_service.JobService.get_job", return_value=MOCK_JOB):

            mock_instance = MagicMock()
            mock_instance.get_session.return_value = MOCK_SESSION_PENDING
            MockSvc.return_value = mock_instance

            resp = client.post(f"/api/sessions/{SESSION_ID}/score")

        assert resp.status_code in (422, 400)

    def test_score_session_pipeline_error_returns_503(self, client):
        """503 when NLP pipeline raises an unexpected exception."""
        with patch("app.api.scoring.ScoringService") as MockSvc, \
             patch("app.services.job_service.JobService.get_job", return_value=MOCK_JOB):

            mock_instance = MagicMock()
            mock_instance.get_session.return_value = MOCK_SESSION_COMPLETED
            mock_instance.score_session.side_effect = RuntimeError("model crash")
            MockSvc.return_value = mock_instance

            resp = client.post(f"/api/sessions/{SESSION_ID}/score")

        assert resp.status_code == 503

    def test_score_session_requires_auth(self):
        """No auth header → 401/403 from require_recruiter."""
        from fastapi.testclient import TestClient
        from app.main import app as _app
        saved = dict(_app.dependency_overrides)
        _app.dependency_overrides.clear()
        try:
            with TestClient(_app) as raw_client:
                resp = raw_client.post(f"/api/sessions/{SESSION_ID}/score")
            assert resp.status_code in (401, 403, 422)
        finally:
            _app.dependency_overrides.update(saved)

    def test_score_session_wrong_recruiter_forbidden(self, client):
        """403 when session belongs to a different recruiter's job."""
        other_job = {**MOCK_JOB, "recruiter_id": str(uuid4())}   # different recruiter

        with patch("app.api.scoring.ScoringService") as MockSvc, \
             patch("app.services.job_service.JobService.get_job", return_value=other_job):

            mock_instance = MagicMock()
            mock_instance.get_session.return_value = MOCK_SESSION_COMPLETED
            MockSvc.return_value = mock_instance

            resp = client.post(f"/api/sessions/{SESSION_ID}/score")

        assert resp.status_code == 403


# ===========================================================================
# E. SCORING API — GET /api/sessions/{id}/scores
# ===========================================================================

class TestGetScoresEndpoint:
    """Tests for GET /api/sessions/{session_id}/scores."""

    def test_get_scores_success(self, client):
        """Happy path — returns summary with scores list."""
        with patch("app.api.scoring.ScoringService") as MockSvc, \
             patch("app.services.job_service.JobService.get_job", return_value=MOCK_JOB):

            mock_instance = MagicMock()
            mock_instance.get_session.return_value = MOCK_SESSION_COMPLETED
            mock_instance.get_scores.return_value = [MOCK_SCORE_ROW]
            mock_instance.get_job_title.return_value = "Senior Engineer"
            MockSvc.return_value = mock_instance

            resp = client.get(f"/api/sessions/{SESSION_ID}/scores")

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["total_responses"] == 1
        assert data["candidate_name"] == "Jane Doe"
        assert data["average_score"] == 75.0

    def test_get_scores_empty(self, client):
        """Returns empty scores list if scoring not yet run."""
        with patch("app.api.scoring.ScoringService") as MockSvc, \
             patch("app.services.job_service.JobService.get_job", return_value=MOCK_JOB):

            mock_instance = MagicMock()
            mock_instance.get_session.return_value = MOCK_SESSION_COMPLETED
            mock_instance.get_scores.return_value = []
            mock_instance.get_job_title.return_value = "Senior Engineer"
            MockSvc.return_value = mock_instance

            resp = client.get(f"/api/sessions/{SESSION_ID}/scores")

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["scores"] == []
        assert body["data"]["average_score"] == 0.0

    def test_get_scores_not_found(self, client):
        """404 when session does not exist."""
        with patch("app.api.scoring.ScoringService") as MockSvc:
            mock_instance = MagicMock()
            mock_instance.get_session.return_value = None
            MockSvc.return_value = mock_instance

            resp = client.get(f"/api/sessions/{SESSION_ID}/scores")

        assert resp.status_code == 404

    def test_get_scores_requires_auth(self):
        """No auth header → 401/403."""
        from fastapi.testclient import TestClient
        from app.main import app as _app
        saved = dict(_app.dependency_overrides)
        _app.dependency_overrides.clear()
        try:
            with TestClient(_app) as raw_client:
                resp = raw_client.get(f"/api/sessions/{SESSION_ID}/scores")
            assert resp.status_code in (401, 403, 422)
        finally:
            _app.dependency_overrides.update(saved)


# ===========================================================================
# F. SCORING SERVICE UNIT TESTS (build_indicator_text, parse_json_field)
# ===========================================================================

class TestScoringServiceHelpers:
    """Unit tests for pure helper methods in ScoringService."""

    def test_build_indicator_text_all_fields(self):
        from app.services.scoring_service import ScoringService
        ind = {
            "name": "Clarity",
            "description": "Communicates ideas clearly.",
            "example_behaviors": "Uses plain language. Checks for understanding.",
        }
        text = ScoringService.build_indicator_text(ind)
        assert "Clarity" in text
        assert "Communicates ideas clearly" in text
        assert "Uses plain language" in text

    def test_build_indicator_text_missing_fields(self):
        from app.services.scoring_service import ScoringService
        ind = {"name": "Clarity"}
        text = ScoringService.build_indicator_text(ind)
        assert text == "Clarity"

    def test_parse_json_field_list(self):
        from app.services.scoring_service import ScoringService
        result = ScoringService._parse_json_field(["a", "b"])
        assert result == ["a", "b"]

    def test_parse_json_field_string(self):
        from app.services.scoring_service import ScoringService
        result = ScoringService._parse_json_field('["a", "b"]')
        assert result == ["a", "b"]

    def test_parse_json_field_invalid_string(self):
        from app.services.scoring_service import ScoringService
        result = ScoringService._parse_json_field("not json")
        assert result == []

    def test_parse_json_field_none(self):
        from app.services.scoring_service import ScoringService
        result = ScoringService._parse_json_field(None)
        assert result == []
