"""
tests/test_phase_b_evidence.py
Regression & integration tests for Phase B — Evidence-Based Scoring Explanations (ES-1 to ES-3).

Validates:
  ES-1: IndicatorEvidence data structure supports optional evidence_text.
        Serialized into JSONB blob in response_scores.evidence.
        Consumed and surfaced by report_service in questions_evidence.
        Backwards-compatible when evidence_text is None or missing from historical rows.
  ES-2: Answer sentence segmentation (_split_sentences) handles multi-sentence answers,
        single-sentence answers, punctuation boundaries (.!?), whitespace, and edge cases.
  ES-3: Per-sentence cosine similarity against indicator embeddings selects the best-matching
        sentence as evidence grounding, respecting the 0.10 similarity floor.
        Deterministic scoring remains authoritative: scoring rubric results are completely
        unchanged by sentence evidence extraction.
        LLM does not score; sentence similarity is explainability context only.
"""
from __future__ import annotations

import json
from typing import List, Optional
from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest

from app.schemas.report import AssessmentReportRead, ReportEvidenceItem
from app.schemas.scoring import IndicatorEvidenceRead
from app.scoring.analyzer import (
    _extract_sentence_evidence,
    _split_sentences,
    analyze_response,
    analyze_response_safe,
)
from app.scoring.rubric import (
    DimensionScore,
    IndicatorEvidence,
    aggregate_dimension_score,
    build_evidence,
    compute_confidence,
    normalize_score,
    score_indicator,
)
from app.services.report_service import ReportService
from app.services.scoring_service import ScoringService


# ===========================================================================
# 1. ES-2: Sentence Segmentation Tests
# ===========================================================================

class TestSentenceSegmentation:
    """Tests for _split_sentences() helper."""

    def test_split_sentences_standard_punctuation(self):
        text = "I led the migration project. It finished on time! Did anyone doubt it? We celebrated after."
        sents = _split_sentences(text)
        assert len(sents) == 4
        assert sents[0] == "I led the migration project."
        assert sents[1] == "It finished on time!"
        assert sents[2] == "Did anyone doubt it?"
        assert sents[3] == "We celebrated after."

    def test_split_sentences_single_sentence(self):
        text = "I coordinated directly with cross-functional stakeholders daily."
        sents = _split_sentences(text)
        assert len(sents) == 1
        assert sents[0] == text

    def test_split_sentences_empty_or_whitespace(self):
        assert _split_sentences("") == []
        assert _split_sentences("   \n\t  ") == []

    def test_split_sentences_multiple_spaces_and_newlines(self):
        text = "First point made.\n\n   Second point followed.    Third point concluded."
        sents = _split_sentences(text)
        assert len(sents) == 3
        assert sents[0] == "First point made."
        assert sents[1] == "Second point followed."
        assert sents[2] == "Third point concluded."

    def test_split_sentences_strips_each_sentence(self):
        text = "  Sentence one.   Sentence two.  "
        sents = _split_sentences(text)
        for s in sents:
            assert s == s.strip()


# ===========================================================================
# 2. ES-3: Sentence Evidence Grounding & Floor Threshold Tests
# ===========================================================================

class TestSentenceEvidenceExtraction:
    """Tests for _extract_sentence_evidence()."""

    def test_extract_evidence_selects_best_matching_sentence(self):
        # 2 sentences, 2 indicators (dimension D=3)
        # Sentence 0: [1.0, 0.0, 0.0] -> matches Indicator 0 [1.0, 0.0, 0.0]
        # Sentence 1: [0.0, 1.0, 0.0] -> matches Indicator 1 [0.0, 1.0, 0.0]
        sent_embs = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ], dtype=np.float32)

        indicator_embs = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ], dtype=np.float32)

        text = "I actively listened to the user needs. I communicated the technical specs clearly."

        with patch("app.scoring.analyzer.embed", return_value=sent_embs):
            evidence = _extract_sentence_evidence(text, indicator_embs)

        assert len(evidence) == 2
        assert evidence[0] == "I actively listened to the user needs."
        assert evidence[1] == "I communicated the technical specs clearly."

    def test_extract_evidence_floor_threshold_filters_unrelated_sentences(self):
        # Indicator has embedding [0.0, 0.0, 1.0]
        # Sentence has embedding [1.0, 0.0, 0.0] -> dot product = 0.0 (< 0.10 floor)
        sent_embs = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        indicator_embs = np.array([[0.0, 0.0, 1.0]], dtype=np.float32)

        text = "Completely unrelated statement."
        with patch("app.scoring.analyzer.embed", return_value=sent_embs):
            evidence = _extract_sentence_evidence(text, indicator_embs)

        assert len(evidence) == 1
        assert evidence[0] is None  # Below 0.10 similarity floor

    def test_extract_evidence_empty_answer_returns_nones(self):
        indicator_embs = np.zeros((3, 384), dtype=np.float32)
        evidence = _extract_sentence_evidence("", indicator_embs)
        assert evidence == [None, None, None]

    def test_extract_evidence_exception_safety(self):
        indicator_embs = np.zeros((2, 384), dtype=np.float32)
        with patch("app.scoring.analyzer.embed", side_effect=RuntimeError("GPU OOM")):
            evidence = _extract_sentence_evidence("A valid answer with several words.", indicator_embs)
        # Must not raise; must return list of Nones
        assert evidence == [None, None]


# ===========================================================================
# 3. ES-1: IndicatorEvidence Data Structure & Rubric Integration
# ===========================================================================

class TestIndicatorEvidenceRubric:
    """Tests for IndicatorEvidence and build_evidence()."""

    def test_indicator_evidence_has_evidence_text_field(self):
        ev = IndicatorEvidence(
            indicator_name="Active listening",
            similarity=0.65,
            score=2,
            matched=True,
            level="strong",
            evidence_text="I listened carefully to feedback.",
        )
        assert ev.evidence_text == "I listened carefully to feedback."
        assert ev.matched is True
        assert ev.level == "strong"

    def test_indicator_evidence_default_evidence_text_is_none(self):
        ev = IndicatorEvidence(
            indicator_name="Active listening",
            similarity=0.30,
            score=1,
            matched=True,
            level="partial",
        )
        assert ev.evidence_text is None

    def test_indicator_evidence_is_frozen(self):
        ev = IndicatorEvidence(
            indicator_name="Clarity",
            similarity=0.5,
            score=2,
            matched=True,
            level="strong",
            evidence_text="Spoke clearly.",
        )
        with pytest.raises(Exception):
            ev.evidence_text = "Mutated text"  # FrozenInstanceError

    def test_build_evidence_with_evidence_texts(self):
        names = ["Ind 1", "Ind 2"]
        sims = [0.55, 0.15]
        texts = ["Sentence 1 was relevant.", None]

        ev_list = build_evidence(names, sims, texts)
        assert len(ev_list) == 2
        assert ev_list[0].indicator_name == "Ind 1"
        assert ev_list[0].evidence_text == "Sentence 1 was relevant."
        assert ev_list[0].score == 2
        assert ev_list[1].indicator_name == "Ind 2"
        assert ev_list[1].evidence_text is None
        assert ev_list[1].score == 0

    def test_build_evidence_without_evidence_texts_backwards_compatible(self):
        names = ["Ind 1"]
        sims = [0.50]
        ev_list = build_evidence(names, sims)
        assert len(ev_list) == 1
        assert ev_list[0].evidence_text is None

    def test_build_evidence_mismatched_lengths_raises_value_error(self):
        with pytest.raises(ValueError, match="evidence_texts .* must match"):
            build_evidence(["Ind 1", "Ind 2"], [0.5, 0.4], ["Only one text"])

    def test_aggregate_dimension_score_passes_evidence_text(self):
        dim_score = aggregate_dimension_score(
            dimension_name="leadership",
            indicator_names=["Conflict resolution", "Delegation"],
            similarities=[0.52, 0.35],
            evidence_texts=["I resolved team disagreements calmly.", "I assigned tasks based on strengths."],
        )
        assert dim_score.dimension_name == "leadership"
        assert dim_score.normalized_score > 0
        assert len(dim_score.evidence) == 2
        assert dim_score.evidence[0].evidence_text == "I resolved team disagreements calmly."
        assert dim_score.evidence[1].evidence_text == "I assigned tasks based on strengths."


# ===========================================================================
# 4. Deterministic Scoring Invariance Tests
# ===========================================================================

class TestScoringInvariance:
    """Verifies that evidence grounding is strictly supporting and does not alter scores."""

    def test_scores_identical_with_and_without_sentence_evidence(self):
        names = ["Ind A", "Ind B", "Ind C"]
        sims = [0.50, 0.30, 0.10]

        score_without = aggregate_dimension_score("comm", names, sims, None)
        score_with = aggregate_dimension_score("comm", names, sims, ["Sent 1", "Sent 2", "Sent 3"])

        assert score_without.normalized_score == score_with.normalized_score
        assert score_without.raw_score == score_with.raw_score
        assert score_without.confidence == score_with.confidence
        assert score_without.indicators_matched == score_with.indicators_matched
        assert score_without.total_indicators == score_with.total_indicators

        for ev_wo, ev_w in zip(score_without.evidence, score_with.evidence):
            assert ev_wo.score == ev_w.score
            assert ev_wo.similarity == ev_w.similarity
            assert ev_wo.level == ev_w.level
            assert ev_wo.matched == ev_w.matched


# ===========================================================================
# 5. Full Analyzer Integration & Safe Wrapper Tests
# ===========================================================================

class TestAnalyzerIntegration:
    """Tests for analyze_response() and analyze_response_safe()."""

    def test_analyze_response_populates_evidence_text(self):
        answer = "In my previous role, I actively listened to customer concerns. Then I resolved their issues promptly."
        dim_name = "communication"
        ind_names = ["Active listening", "Prompt resolution"]
        ind_texts = [
            "Active listening: understands and clarifies customer feedback",
            "Prompt resolution: takes decisive action to solve problems quickly",
        ]

        result = analyze_response(answer, dim_name, ind_names, ind_texts)

        assert result.status == "scored"
        assert result.normalized_score > 0
        assert len(result.evidence) == 2
        for ev in result.evidence:
            assert isinstance(ev.similarity, float)
            assert ev.evidence_text is not None
            assert len(ev.evidence_text) > 0

    def test_analyze_response_quality_gate_failure(self):
        # Gibberish or too short answer
        result = analyze_response(
            "short",
            "communication",
            ["Active listening"],
            ["Listens carefully"],
        )
        assert result.status.startswith("invalid:")
        assert result.normalized_score == 0
        assert result.confidence == 0.0
        assert result.evidence == []

    def test_analyze_response_no_indicators(self):
        result = analyze_response(
            "This is a sufficiently long valid answer describing past professional experience.",
            "communication",
            [],
            [],
        )
        assert result.status == "no_indicators"
        assert result.normalized_score == 0
        assert result.evidence == []

    def test_analyze_response_safe_catches_all_exceptions(self):
        with patch("app.scoring.analyzer.clean", side_effect=Exception("Unexpected token failure")):
            result = analyze_response_safe(
                "Some answer text",
                "communication",
                ["Ind 1"],
                ["Ind 1 text"],
            )
            assert result.status == "error"
            assert result.normalized_score == 0


# ===========================================================================
# 6. ES-1 Persistence Tests in ScoringService
# ===========================================================================

class TestScoringServicePersistence:
    """Tests that scoring_service persists evidence_text into response_scores."""

    def test_scoring_service_serializes_evidence_text(self):
        service = ScoringService()

        session_id = str(uuid4())
        question_id = str(uuid4())
        response_id = str(uuid4())

        mock_session = {
            "id": session_id,
            "job_id": str(uuid4()),
            "framework_version_id": None,
        }
        mock_question = {
            "id": question_id,
            "dimension_name": "adaptability",
            "indicator_objects": [
                {
                    "name": "Flexibility",
                    "description": "Adapts smoothly to changing priorities",
                    "example_behaviors": "Re-prioritizes work without frustration",
                }
            ],
        }
        mock_responses = [{
            "id": response_id,
            "question_id": question_id,
            "answer": "When the project requirements changed abruptly, I quickly re-prioritized all sprint tasks.",
        }]

        mock_upsert_builder = MagicMock()
        mock_upsert_builder.upsert.return_value.execute.return_value = MagicMock(
            data=[{
                "id": str(uuid4()),
                "response_id": response_id,
                "dimension_name": "adaptability",
                "normalized_score": 80,
            }],
            error=None,
        )

        with patch.object(service, "get_session", return_value=mock_session), \
             patch.object(service, "get_responses", return_value=mock_responses), \
             patch.object(service, "get_question_with_indicators", return_value=mock_question), \
             patch.object(service, "_get_snapshot_for_session", return_value=None), \
             patch.object(service._db, "table", return_value=mock_upsert_builder):

            saved_rows = service.score_session(session_id)
            assert len(saved_rows) == 1

            mock_upsert_builder.upsert.assert_called_once()
            called_row = mock_upsert_builder.upsert.call_args[0][0]
            assert "evidence" in called_row
            ev_data = json.loads(called_row["evidence"])
            assert len(ev_data) == 1
            assert "evidence_text" in ev_data[0]
            assert ev_data[0]["indicator_name"] == "Flexibility"
            assert ev_data[0]["evidence_text"] is not None


# ===========================================================================
# 7. Report Service Consumption & Backwards Compatibility Tests
# ===========================================================================

class TestReportServiceEvidence:
    """Tests for report_service.py handling of evidence_text."""

    def test_report_service_extracts_evidence_text(self):
        service = ReportService()
        session_id = str(uuid4())
        job_id = str(uuid4())
        q_id = str(uuid4())

        mock_session = {
            "id": session_id,
            "job_id": job_id,
            "status": "completed",
            "candidate_name": "Alice Tester",
            "candidate_email": "alice@example.com",
            "framework_version_id": None,
        }
        mock_job = {
            "id": job_id,
            "title": "Software Engineer",
            "framework_version_id": None,
        }
        mock_questions = [{
            "id": q_id,
            "question": "Tell me about a time you handled conflict.",
            "dimension_name": "collaboration",
            "type": "behavioral",
            "difficulty": "medium",
        }]
        mock_responses = [{
            "question_id": q_id,
            "answer": "I met with the teammate one-on-one. We resolved the disagreement amicably.",
        }]
        mock_scores = [{
            "question_id": q_id,
            "dimension_name": "collaboration",
            "normalized_score": 85,
            "confidence": 0.88,
            "status": "scored",
            "indicators_matched": 1,
            "total_indicators": 1,
            "evidence": json.dumps([{
                "indicator_name": "Constructive dialogue",
                "matched": True,
                "level": "strong",
                "similarity": 0.72,
                "evidence_text": "We resolved the disagreement amicably.",
            }]),
        }]

        with patch("app.services.report_service.SessionService") as MockSessSvc, \
             patch("app.services.report_service.JobService") as MockJobSvc, \
             patch("app.services.report_service.AlignmentService") as MockAlignSvc, \
             patch.object(service, "_get_questions_by_job", return_value=mock_questions), \
             patch.object(service, "_get_responses_by_session", return_value=mock_responses), \
             patch.object(service, "_get_scores_by_session", return_value=mock_scores), \
             patch.object(service, "_get_framework_version_label", return_value=("v1.0 - Default", None)):

            MockSessSvc.return_value.get_session.return_value = mock_session
            MockJobSvc.return_value.get_job.return_value = mock_job
            MockAlignSvc.return_value.get_alignment.return_value = {
                "overall_score": 85.0,
                "dimension_alignments": [],
            }

            report = service.get_assessment_report(session_id)
            assert report is not None
            q_ev = report["questions_evidence"]
            assert len(q_ev) == 1
            ev_list = q_ev[0]["evidence"]
            assert len(ev_list) == 1
            assert ev_list[0]["indicator_name"] == "Constructive dialogue"
            assert ev_list[0]["evidence_text"] == "We resolved the disagreement amicably."
            assert ev_list[0]["similarity"] == 0.72

    def test_report_service_legacy_row_without_evidence_text(self):
        """Historical assessments before Phase B have no evidence_text key in JSONB."""
        service = ReportService()
        session_id = str(uuid4())
        job_id = str(uuid4())
        q_id = str(uuid4())

        mock_session = {
            "id": session_id,
            "job_id": job_id,
            "status": "completed",
            "candidate_name": "Bob Legacy",
            "candidate_email": "bob@example.com",
            "framework_version_id": None,
        }
        mock_job = {
            "id": job_id,
            "title": "Data Analyst",
            "framework_version_id": None,
        }
        mock_questions = [{
            "id": q_id,
            "question": "Describe your analysis process.",
            "dimension_name": "analytical_thinking",
            "type": "behavioral",
            "difficulty": "medium",
        }]
        mock_responses = [{
            "question_id": q_id,
            "answer": "I clean the data, explore anomalies, and build dashboards.",
        }]
        # Legacy score evidence does NOT contain evidence_text
        mock_scores = [{
            "question_id": q_id,
            "dimension_name": "analytical_thinking",
            "normalized_score": 75,
            "confidence": 0.80,
            "status": "scored",
            "evidence": json.dumps([{
                "indicator_name": "Data exploration",
                "matched": True,
                "level": "strong",
                "similarity": 0.65,
            }]),
        }]

        with patch("app.services.report_service.SessionService") as MockSessSvc, \
             patch("app.services.report_service.JobService") as MockJobSvc, \
             patch("app.services.report_service.AlignmentService") as MockAlignSvc, \
             patch.object(service, "_get_questions_by_job", return_value=mock_questions), \
             patch.object(service, "_get_responses_by_session", return_value=mock_responses), \
             patch.object(service, "_get_scores_by_session", return_value=mock_scores), \
             patch.object(service, "_get_framework_version_label", return_value=("v1.0 - Default", None)):

            MockSessSvc.return_value.get_session.return_value = mock_session
            MockJobSvc.return_value.get_job.return_value = mock_job
            MockAlignSvc.return_value.get_alignment.return_value = {
                "overall_score": 75.0,
                "dimension_alignments": [],
            }

            report = service.get_assessment_report(session_id)
            assert report is not None
            ev_list = report["questions_evidence"][0]["evidence"]
            assert len(ev_list) == 1
            assert ev_list[0]["indicator_name"] == "Data exploration"
            assert ev_list[0]["evidence_text"] is None  # Defaults safely to None


# ===========================================================================
# 8. Schema Validation Tests
# ===========================================================================

class TestSchemaValidation:
    """Tests Pydantic models with and without evidence_text."""

    def test_indicator_evidence_read_schema(self):
        # With evidence_text
        item1 = IndicatorEvidenceRead(
            indicator_name="Ind A",
            similarity=0.75,
            score=2,
            matched=True,
            level="strong",
            evidence_text="Matched sentence here.",
        )
        assert item1.evidence_text == "Matched sentence here."

        # Without evidence_text (None by default)
        item2 = IndicatorEvidenceRead(
            indicator_name="Ind B",
            similarity=0.20,
            score=0,
            matched=False,
            level="none",
        )
        assert item2.evidence_text is None

    def test_report_evidence_item_schema(self):
        item1 = ReportEvidenceItem(
            indicator_name="Ind A",
            matched=True,
            level="strong",
            similarity=0.82,
            evidence_text="Grounding quote from response.",
        )
        assert item1.evidence_text == "Grounding quote from response."

        item2 = ReportEvidenceItem(
            indicator_name="Ind B",
            matched=False,
            level="none",
            similarity=0.12,
        )
        assert item2.evidence_text is None
