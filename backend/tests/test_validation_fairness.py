"""
tests/test_validation_fairness.py
Phase 9: Comprehensive Evaluation, Fairness, Security & System Validation Test Suite.

Audits and validates:
  1. Scoring determinism and mathematical boundaries
  2. Evidence integrity and indicator linkage
  3. Question validation, coverage, and dimension mapping
  4. Fairness, ethical safety, non-diagnostic constraints, no automated hire/reject
  5. Security, authorization, tenant isolation, and candidate information containment
  6. Data validation edge cases (short, garbled, incomplete, missing dimensions, duplicate submissions)
  7. End-to-end recruiter-to-candidate pipeline integration
"""
import copy
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.alignment.calculator import calculate_alignment
from app.core.security import require_recruiter
from app.main import app
from app.nlp.preprocessor import clean, quality_gate
from app.schemas.alignment import SessionAlignmentRead
from app.ai.question_schemas import GeneratedQuestion
from app.schemas.report import AssessmentReportRead
from app.schemas.sessions import PublicSessionRead, ResponseCreate, SubmitResponsesPayload
from app.scoring.analyzer import analyze_response, analyze_response_safe
from app.scoring.rubric import (
    MAX_PER_INDICATOR,
    aggregate_dimension_score,
    build_evidence,
    compute_confidence,
    normalize_score,
    score_indicator,
)
from app.services.report_service import COMPLIANCE_DISCLAIMER, ReportService
from app.services.scoring_service import ScoringService

# Fixed test fixtures
RECRUITER_A_ID = "00000000-0000-0000-0000-000000000001"
RECRUITER_B_ID = "00000000-0000-0000-0000-000000000002"
JOB_ID = "11111111-1111-1111-1111-111111111111"
SESSION_ID = "22222222-2222-2222-2222-222222222222"
QUESTION_1_ID = "33333333-3333-3333-3333-333333333331"
QUESTION_2_ID = "33333333-3333-3333-3333-333333333332"
TOKEN_VALID = "test-token-valid-uuid"


@pytest.fixture
def client_recruiter_a():
    """Client authenticated as Recruiter A."""
    app.dependency_overrides[require_recruiter] = lambda: {
        "id": RECRUITER_A_ID,
        "email": "recruiter_a@example.com",
        "role": "recruiter",
    }
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_recruiter_b():
    """Client authenticated as Recruiter B (unauthorized for Recruiter A's resources)."""
    app.dependency_overrides[require_recruiter] = lambda: {
        "id": RECRUITER_B_ID,
        "email": "recruiter_b@example.com",
        "role": "recruiter",
    }
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def unauth_client():
    """Unauthenticated client."""
    saved = dict(app.dependency_overrides)
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.update(saved)


import numpy as np

def _mock_embed_fn(texts):
    """Deterministic fast mock embedder for testing without loading torch weights."""
    dim = 16
    embs = []
    for idx, t in enumerate(texts):
        v = np.zeros(dim, dtype=np.float32)
        v[0] = 0.85
        v[1] = 0.15 * (idx + 1)
        norm = np.linalg.norm(v)
        embs.append(v / norm if norm > 0 else v)
    return np.array(embs, dtype=np.float32)


# ===========================================================================
# 1. SCORING VALIDATION & DETERMINISM
# ===========================================================================

class TestScoringDeterminismAndMath:
    """Verify that scoring is strictly deterministic, bounded, and mathematically sound."""

    def test_identical_input_produces_identical_score(self):
        """Rule: Scoring MUST be 100% deterministic — repeated runs return bit-for-bit identical outputs."""
        answer = (
            "In my previous project, we faced critical deadline pressure. I initiated daily standups, "
            "listened carefully to all team members' concerns, and clearly articulated the revised timeline "
            "to stakeholders to keep everyone aligned."
        )
        dim = "communication"
        indicators = ["Active listening", "Clarity in messaging"]
        indicator_texts = [
            "Demonstrates active listening and asks clarifying questions",
            "Communicates ideas clearly and concisely to stakeholders",
        ]

        # Run 5 consecutive iterations with mocked embedder
        with patch("app.scoring.analyzer.embed", side_effect=_mock_embed_fn):
            results = [analyze_response(answer, dim, indicators, indicator_texts) for _ in range(5)]

        first = results[0]
        for idx, res in enumerate(results[1:], 1):
            assert res.normalized_score == first.normalized_score, f"Run {idx} score mismatch"
            assert res.raw_score == first.raw_score, f"Run {idx} raw_score mismatch"
            assert res.confidence == first.confidence, f"Run {idx} confidence mismatch"
            assert len(res.evidence) == len(first.evidence)
            for e1, e2 in zip(first.evidence, res.evidence):
                assert e1.similarity == e2.similarity
                assert e1.score == e2.score
                assert e1.matched == e2.matched

    def test_normalization_bounds_and_extremes(self):
        """Verify normalization bounds [0, 100] across all point combinations."""
        # 0 points -> 0
        assert normalize_score(0, 3) == 0
        # Maximum points -> 100
        assert normalize_score(6, 3) == 100
        # Partial points: 1 out of 6 -> round(1/6 * 100) = 17
        assert normalize_score(1, 3) == 17
        # 0 indicators guard -> 0
        assert normalize_score(5, 0) == 0

    def test_weighted_alignment_formula_integrity(self):
        """
        Verify: Overall Alignment Score = sum(candidate_score_i * weight_i) / sum(weight_i)
        And sum of individual point contributions exactly matches overall score.
        """
        job_reqs = [
            {"dimension_name": "communication", "importance": 80, "confirmed": True},
            {"dimension_name": "teamwork", "importance": 40, "confirmed": True},
        ]
        candidate_scores = [
            {"dimension_name": "communication", "normalized_score": 90, "confidence": 0.85, "status": "scored"},
            {"dimension_name": "teamwork", "normalized_score": 60, "confidence": 0.70, "status": "scored"},
        ]

        res = calculate_alignment(job_reqs, candidate_scores)

        # Expected:
        # Total weight = 120
        # Comm weight pct = 80/120 = 66.7%
        # Team weight pct = 40/120 = 33.3%
        # Comm contrib = 90 * (80/120) = 60.0
        # Team contrib = 60 * (40/120) = 20.0
        # Overall = (90*80 + 60*40) / 120 = (7200 + 2400) / 120 = 9600 / 120 = 80.0
        assert res["overall_score"] == 80.0
        contrib_sum = sum(d["contribution"] for d in res["dimension_alignments"] if d["status"] == "assessed")
        assert round(contrib_sum, 1) == res["overall_score"]

    def test_zero_and_invalid_weights_handling(self):
        """Division by zero or invalid weights must not raise unhandled exceptions."""
        job_reqs = [
            {"dimension_name": "adaptability", "importance": 0, "confirmed": True},
            {"dimension_name": "leadership", "importance": -10, "confirmed": True},  # clamped to 0
        ]
        candidate_scores = [
            {"dimension_name": "adaptability", "normalized_score": 75, "confidence": 0.8, "status": "scored"},
        ]

        # Total weight becomes 0 -> falls back to unweighted mean safely
        res = calculate_alignment(job_reqs, candidate_scores)
        assert res["overall_score"] == 75.0
        assert res["total_weight"] == 0


# ===========================================================================
# 2. EVIDENCE VALIDATION
# ===========================================================================

class TestEvidenceIntegrity:
    """Verify that evidence is always linked to relevant indicators and handles missing data cleanly."""

    def test_every_score_has_supporting_evidence(self):
        """Scored response must include evidence item for each indicator with discrete level."""
        indicators = ["Collaboration", "Constructive feedback"]
        sims = [0.55, 0.32]

        evidence = build_evidence(indicators, sims)
        assert len(evidence) == 2
        # First: 0.55 >= 0.45 -> strong, score=2, matched=True
        assert evidence[0].indicator_name == "Collaboration"
        assert evidence[0].level == "strong"
        assert evidence[0].score == 2
        assert evidence[0].matched is True
        # Second: 0.32 >= 0.28 -> partial, score=1, matched=True
        assert evidence[1].indicator_name == "Constructive feedback"
        assert evidence[1].level == "partial"
        assert evidence[1].score == 1
        assert evidence[1].matched is True

    def test_quality_gate_failure_produces_no_false_evidence(self):
        """Garbled or too-short input must fail quality gate and produce status='invalid:*' with 0 score."""
        garbled_input = "$%#@!* 123456789 ???!!!"
        res = analyze_response(
            answer=garbled_input,
            dimension_name="decision_making",
            indicator_names=["Risk analysis"],
            indicator_texts=["Considers risks carefully before taking decisions"],
        )
        assert res.normalized_score == 0
        assert res.status.startswith("invalid")
        assert len(res.evidence) == 0

    def test_custom_indicators_fallback_preserves_evidence(self):
        """
        Verify that indicators defined on a question that do NOT exist in the seeded DB table
        are still embedded, evaluated, and returned as evidence instead of being dropped.
        """
        svc = ScoringService()
        mock_question_data = {
            "id": QUESTION_1_ID,
            "job_id": JOB_ID,
            "dimension_id": "dim-uuid-1",
            "question": "Tell me about a complex project",
            "type": "behavioral",
            "difficulty": "medium",
            "indicators": ["Custom project planning skill", "Unseeded cross-functional leadership"],
        }
        with patch.object(svc._db, "table") as mock_table:
            # Question fetch
            mock_table().select().eq().maybe_single().execute.side_effect = [
                MagicMock(data=mock_question_data, error=None),   # question
                MagicMock(data={"id": "dim-uuid-1", "name": "leadership"}, error=None),  # dimension
            ]
            # Indicators query returns empty data (unseeded)
            mock_table().select().eq().in_().execute.return_value = MagicMock(data=[], error=None)

            enriched = svc.get_question_with_indicators(QUESTION_1_ID)

            assert len(enriched["indicator_objects"]) == 2
            assert enriched["indicator_objects"][0]["name"] == "Custom project planning skill"
            assert enriched["indicator_objects"][1]["name"] == "Unseeded cross-functional leadership"


# ===========================================================================
# 3. QUESTION VALIDATION & COVERAGE
# ===========================================================================

class TestQuestionValidationAndCoverage:
    """Verify that interview questions adhere to approved dimensions, coverage, and schema constraints."""

    def test_valid_generated_question_schema(self):
        """Valid question parses cleanly with all required fields."""
        q = GeneratedQuestion(
            dimension="communication",
            question="Describe a situation where you had to explain a complex technical topic to non-technical stakeholders.",
            type="behavioral",
            difficulty="medium",
            indicators=["Uses analogies and plain language", "Confirms audience comprehension"],
        )
        assert q.dimension == "communication"
        assert len(q.indicators) == 2

    def test_invalid_dimension_rejected(self):
        """Question generator schema rejects dimensions outside the 6 core behavioral dimensions."""
        with pytest.raises(ValueError, match="Unknown dimension"):
            GeneratedQuestion(
                dimension="unsupported_dimension",
                question="Describe a situation where you had to lead a project from start to finish.",
                type="behavioral",
                difficulty="medium",
                indicators=["Clear goals", "Follow-up"],
            )

    def test_short_or_empty_question_rejected(self):
        """Questions shorter than 20 characters are rejected."""
        with pytest.raises(ValueError):
            GeneratedQuestion(
                dimension="teamwork",
                question="Too short?",
                type="behavioral",
                difficulty="easy",
                indicators=["Indicator 1", "Indicator 2"],
            )


# ===========================================================================
# 4. FAIRNESS, ETHICS & NON-DIAGNOSTIC COMPLIANCE
# ===========================================================================

class TestFairnessSafetyAndCompliance:
    """
    CRITICAL AUDIT:
      - Strictly NO automated hire/reject/select decisions
      - Strictly NO mental-health / clinical psychological diagnosis
      - Strict decision-support boundaries for recruiters
    """

    FORBIDDEN_AUTOMATED_DECISION_TERMS = [
        "hire candidate",
        "reject candidate",
        "candidate passed",
        "candidate failed",
        "automatically selected",
        "recommend rejection",
        "recommend hire",
    ]

    DIAGNOSTIC_PSYCHOLOGICAL_TERMS = [
        "clinical depression",
        "anxiety disorder",
        "bipolar",
        "neuroticism",
        "psychopathology",
        "personality disorder",
        "mental illness",
        "psychiatric",
    ]

    def test_alignment_contains_zero_automated_decisions(self):
        """Ensure alignment calculator output contains no hire/reject decision language."""
        job_reqs = [{"dimension_name": "communication", "importance": 100, "confirmed": True}]
        # Test extreme low score
        candidate_scores_low = [{"dimension_name": "communication", "normalized_score": 10, "status": "scored"}]
        low_res = calculate_alignment(job_reqs, candidate_scores_low)

        for text in low_res["strengths"] + low_res["areas_for_review"]:
            lower_text = text.lower()
            for term in self.FORBIDDEN_AUTOMATED_DECISION_TERMS:
                assert term not in lower_text, f"Forbidden decision term '{term}' found in: {text}"

        # Test extreme high score
        candidate_scores_high = [{"dimension_name": "communication", "normalized_score": 100, "status": "scored"}]
        high_res = calculate_alignment(job_reqs, candidate_scores_high)

        for text in high_res["strengths"] + high_res["areas_for_review"]:
            lower_text = text.lower()
            for term in self.FORBIDDEN_AUTOMATED_DECISION_TERMS:
                assert term not in lower_text, f"Forbidden decision term '{term}' found in: {text}"

    def test_report_service_compliance_disclaimer_mandatory(self):
        """Verify report service enforces non-decision ethical disclaimer."""
        assert "Antigravity does NOT produce automated hire/reject recommendations" in COMPLIANCE_DISCLAIMER
        assert "All hiring decisions must be made by qualified human recruiters" in COMPLIANCE_DISCLAIMER

    def test_zero_clinical_diagnostic_language(self):
        """Verify that alignment reasons and disclaimers contain zero mental-health diagnostic terms."""
        job_reqs = [{"dimension_name": "stress_management", "importance": 90, "confirmed": True}]
        candidate_scores = [{"dimension_name": "stress_management", "normalized_score": 25, "status": "scored"}]
        res = calculate_alignment(job_reqs, candidate_scores)

        all_text = " ".join(res["strengths"] + res["areas_for_review"]).lower()
        for diag in self.DIAGNOSTIC_PSYCHOLOGICAL_TERMS:
            assert diag not in all_text, f"Clinical diagnostic term '{diag}' leaked into report text"


# ===========================================================================
# 5. SECURITY & TENANT ISOLATION
# ===========================================================================

class TestSecurityTenantIsolation:
    """Audit authorization, recruiter tenant isolation, and candidate token isolation."""

    MOCK_JOB_A = {
        "id": JOB_ID,
        "recruiter_id": RECRUITER_A_ID,
        "title": "Software Engineer",
        "description": "Tech role",
        "status": "active",
    }

    MOCK_SESSION = {
        "id": SESSION_ID,
        "job_id": JOB_ID,
        "candidate_name": "Alice Candidate",
        "candidate_email": "alice@example.com",
        "token": TOKEN_VALID,
        "status": "completed",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }

    def test_candidate_endpoint_contains_zero_recruiter_secrets(self, unauth_client):
        """Candidate session endpoint MUST NOT expose recruiter_id, job weights, or internal scores."""
        mock_active = {**self.MOCK_SESSION, "status": "pending"}
        with patch("app.services.session_service.SessionService.get_session_by_token", return_value=mock_active), \
             patch("app.services.session_service.SessionService.get_job_public", return_value=self.MOCK_JOB_A), \
             patch("app.services.session_service.SessionService.get_approved_questions", return_value=[
                 {"id": QUESTION_1_ID, "question": "Tell me about a time...", "type": "behavioral", "difficulty": "medium", "indicators": ["Ind1"]}
             ]):

            resp = unauth_client.get(f"/api/sessions/{TOKEN_VALID}")

        assert resp.status_code == 200
        data = resp.json()["data"]
        # PublicSessionRead validated
        assert "recruiter_id" not in data
        assert "weights" not in data
        assert "scores" not in data
        assert "candidate_email" not in data  # Candidate's email hidden on public assessment page

    def test_recruiter_b_cannot_access_recruiter_a_report(self, client_recruiter_b):
        """Recruiter B accessing Recruiter A's candidate report MUST receive 403 Forbidden."""
        with patch("app.services.session_service.SessionService.get_session", return_value=self.MOCK_SESSION), \
             patch("app.services.job_service.JobService.get_job", return_value=self.MOCK_JOB_A):

            resp = client_recruiter_b.get(f"/api/sessions/{SESSION_ID}/report")

        assert resp.status_code == 403
        assert "access" in resp.json()["detail"].lower()

    def test_recruiter_b_cannot_access_recruiter_a_alignment(self, client_recruiter_b):
        """Recruiter B accessing Recruiter A's session alignment MUST receive 403 Forbidden."""
        with patch("app.services.alignment_service.AlignmentService.get_session", return_value=self.MOCK_SESSION), \
             patch("app.services.job_service.JobService.get_job", return_value=self.MOCK_JOB_A):

            resp = client_recruiter_b.get(f"/api/sessions/{SESSION_ID}/alignment")

        assert resp.status_code == 403

    def test_unauthenticated_recruiter_endpoints_return_401(self, unauth_client):
        """Unauthenticated requests to reports or alignment must be rejected."""
        resp1 = unauth_client.get(f"/api/sessions/{SESSION_ID}/report")
        assert resp1.status_code in (401, 403, 422)

        resp2 = unauth_client.get(f"/api/sessions/{SESSION_ID}/alignment")
        assert resp2.status_code in (401, 403, 422)


# ===========================================================================
# 6. DATA VALIDATION & EDGE CASES
# ===========================================================================

class TestDataValidationEdgeCases:
    """Test boundary conditions, malformed input, incomplete assessments, and duplicate submissions."""

    def test_duplicate_submission_blocked_with_403(self, unauth_client):
        """Submitting answers to an already-completed session returns 403 Forbidden."""
        completed_session = {
            "id": SESSION_ID,
            "job_id": JOB_ID,
            "token": TOKEN_VALID,
            "status": "completed",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }
        with patch("app.services.session_service.SessionService.get_session_by_token", return_value=completed_session):
            payload = {"responses": [{"question_id": QUESTION_1_ID, "answer": "Valid long answer text for submission."}]}
            resp = unauth_client.post(f"/api/sessions/{TOKEN_VALID}/responses", json=payload)

        assert resp.status_code == 403
        assert "already been submitted" in resp.json()["detail"].lower()

    def test_expired_session_blocked_with_403(self, unauth_client):
        """Submitting answers to an expired session returns 403 Forbidden."""
        expired_session = {
            "id": SESSION_ID,
            "job_id": JOB_ID,
            "token": TOKEN_VALID,
            "status": "pending",
            "expires_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        }
        with patch("app.services.session_service.SessionService.get_session_by_token", return_value=expired_session):
            payload = {"responses": [{"question_id": QUESTION_1_ID, "answer": "Valid long answer text for submission."}]}
            resp = unauth_client.post(f"/api/sessions/{TOKEN_VALID}/responses", json=payload)

        assert resp.status_code == 403
        assert "expired" in resp.json()["detail"].lower()

    def test_missing_dimension_handled_safely(self):
        """Candidate session missing responses for a required dimension is marked as missing."""
        job_reqs = [
            {"dimension_name": "communication", "importance": 70, "confirmed": True},
            {"dimension_name": "adaptability", "importance": 50, "confirmed": True},
        ]
        # Candidate only scored on communication
        candidate_scores = [
            {"dimension_name": "communication", "normalized_score": 85, "confidence": 0.8, "status": "scored"},
        ]

        res = calculate_alignment(job_reqs, candidate_scores)
        alignments = {d["dimension_name"]: d for d in res["dimension_alignments"]}

        assert alignments["communication"]["status"] == "assessed"
        assert alignments["adaptability"]["status"] == "missing"
        assert alignments["adaptability"]["candidate_score"] == 0.0
        assert alignments["adaptability"]["contribution"] == 0.0

        # Review area generated for missing dimension
        assert any("missing evaluation for 'adaptability'" in rev.lower() for rev in res["areas_for_review"])


# ===========================================================================
# 7. END-TO-END WORKFLOW INTEGRATION
# ===========================================================================

class TestEndToEndWorkflowSimulation:
    """Simulates the entire workflow from Job Creation through to Report Generation."""

    def test_full_pipeline_simulation(self):
        """
        End-to-end integration:
          Job -> Requirements -> Question -> Candidate Answer -> Scoring -> Alignment -> Report
        """
        # 1. Job Requirements
        requirements = [
            {"dimension_name": "communication", "importance": 70, "confirmed": True, "reason": "Team updates"},
            {"dimension_name": "teamwork", "importance": 60, "confirmed": True, "reason": "Cross-functional pair programming"},
        ]

        # 2. Approved Question
        q1_indicators = ["Active listening", "Clarity in updates"]
        q1_indicator_texts = [
            "Actively listens to colleague concerns during engineering syncs",
            "Communicates status and technical roadblocks clearly",
        ]

        # 3. Candidate Response
        candidate_answer = (
            "During our major cloud migration, I hosted daily standups to listen to developer blockers. "
            "I summarized complex architectural decisions in a shared doc so all teams were aligned on the rollout."
        )

        # 4. Deterministic NLP Scoring
        with patch("app.scoring.analyzer.embed", side_effect=_mock_embed_fn):
            dim_score = analyze_response(
                answer=candidate_answer,
                dimension_name="communication",
                indicator_names=q1_indicators,
                indicator_texts=q1_indicator_texts,
            )
        assert dim_score.status == "scored"
        assert dim_score.normalized_score > 0
        assert len(dim_score.evidence) == 2

        # 5. Deterministic Alignment Calculation
        candidate_scores = [
            {
                "dimension_name": dim_score.dimension_name,
                "normalized_score": dim_score.normalized_score,
                "confidence": dim_score.confidence,
                "status": dim_score.status,
            }
        ]
        alignment = calculate_alignment(requirements, candidate_scores, candidate_name="Bob Test", job_title="Lead Dev")
        assert alignment["overall_score"] > 0
        assert alignment["assessed_dimensions_count"] == 1
        assert alignment["total_dimensions_count"] == 2

        # 6. Report Service Verification
        report_svc = ReportService()
        inquiry_prompts = report_svc._generate_inquiry_prompts(
            alignment["dimension_alignments"],
            alignment["areas_for_review"],
        )
        # Should generate an inquiry prompt for the missing teamwork evaluation
        assert any("teamwork" in p.lower() for p in inquiry_prompts)
