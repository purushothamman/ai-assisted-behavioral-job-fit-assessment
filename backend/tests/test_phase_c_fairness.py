"""
tests/test_phase_c_fairness.py
Comprehensive regression & unit tests for Phase C — Demographic Fairness Evaluation (FA-1 to FA-5).

Coverage:
  1. FA-2: Demographic Parity Difference (DPD) & Selection Rates
  2. FA-2: Equal Opportunity Difference (EOD) & Subgroup Recall
  3. FA-2: Missing Ground-Truth handling (EOD is strictly omitted)
  4. FA-2: Zero-denominator safeguards & edge cases (empty dataset, single group, zero positives)
  5. FA-3: Subgroup sample-size warnings (N < 30 threshold and configurable limits)
  6. FA-4: Adverse Impact Ratio (80% / Four-Fifths Rule)
  7. FA-1 / FA-5: Dataset Ingestion & Validation Workflow (FairnessService & Schemas)
  8. FA-1: Admin-only Authorization & API Access Control
  9. FA-4: Strict Isolation between Fairness Data and Candidate Assessment Scoring
"""
from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.fairness.metrics import (
    DEFAULT_MIN_SAMPLE_SIZE,
    DEFAULT_SCORE_THRESHOLD,
    calculate_fairness_metrics,
)
from app.fairness.schemas import (
    EvaluationRecordInput,
    FairnessAuditRunRequest,
    FairnessDatasetCreate,
)
from app.fairness.service import FairnessService
from app.main import app


# ===========================================================================
# 1. FA-2: Metric Calculations — Demographic Parity Difference (DPD)
# ===========================================================================

class TestDemographicParityMetrics:
    """Tests for DPD calculation, selection rates, and reference comparisons."""

    def test_dpd_two_groups_known_rates(self):
        # Group A: 80 selected out of 100 (rate = 0.80)
        # Group B: 60 selected out of 100 (rate = 0.60)
        # Expected DPD = 0.80 - 0.60 = 0.20
        records = (
            [{"group": "Group_A", "prediction": 1} for _ in range(80)] +
            [{"group": "Group_A", "prediction": 0} for _ in range(20)] +
            [{"group": "Group_B", "prediction": 1} for _ in range(60)] +
            [{"group": "Group_B", "prediction": 0} for _ in range(40)]
        )
        res = calculate_fairness_metrics(
            records=records,
            sensitive_attribute="group",
            reference_group="Group_A",
        )

        assert res.total_samples == 200
        assert res.demographic_parity_difference == pytest.approx(0.20, abs=1e-4)
        assert res.reference_group == "Group_A"

        metrics_map = {sm.group: sm for sm in res.subgroup_metrics}
        assert metrics_map["Group_A"].selection_rate == 0.80
        assert metrics_map["Group_A"].rate_difference_from_reference == 0.0
        assert metrics_map["Group_B"].selection_rate == 0.60
        assert metrics_map["Group_B"].rate_difference_from_reference == pytest.approx(-0.20, abs=1e-4)

    def test_dpd_with_continuous_scores(self):
        # Threshold = 70.0
        # Group A: 2 scores >= 70 (80.0, 75.0), 1 score < 70 (60.0) -> rate = 2/3 = 0.6667
        # Group B: 1 score >= 70 (70.0), 2 scores < 70 (65.0, 50.0) -> rate = 1/3 = 0.3333
        records = [
            {"group": "A", "score": 80.0},
            {"group": "A", "score": 75.0},
            {"group": "A", "score": 60.0},
            {"group": "B", "score": 70.0},
            {"group": "B", "score": 65.0},
            {"group": "B", "score": 50.0},
        ]
        res = calculate_fairness_metrics(records, score_threshold=70.0)
        assert res.demographic_parity_difference == pytest.approx(0.3334, abs=1e-3)

    def test_adverse_impact_ratio_four_fifths_rule(self):
        # Group Reference: rate = 0.80
        # Group Protected: rate = 0.50 -> AIR = 0.50 / 0.80 = 0.625 (< 0.80 -> flag warning)
        records = (
            [{"group": "Ref", "prediction": 1} for _ in range(80)] +
            [{"group": "Ref", "prediction": 0} for _ in range(20)] +
            [{"group": "Prot", "prediction": 1} for _ in range(50)] +
            [{"group": "Prot", "prediction": 0} for _ in range(50)]
        )
        res = calculate_fairness_metrics(records, reference_group="Ref")
        prot_metric = next(sm for sm in res.subgroup_metrics if sm.group == "Prot")

        assert prot_metric.adverse_impact_ratio == pytest.approx(0.625, abs=1e-3)
        assert any("Four-Fifths Rule" in w for w in prot_metric.warnings)


# ===========================================================================
# 2. FA-2: Equal Opportunity Difference (EOD) & Subgroup Recall
# ===========================================================================

class TestEqualOpportunityMetrics:
    """Tests for EOD, subgroup recall (TPR), and ground-truth validation."""

    def test_eod_with_complete_ground_truth(self):
        # Group A:
        #   GT=1: 40 candidates. Model selected 36 -> Recall = 36/40 = 0.90
        #   GT=0: 20 candidates. Model selected 4  (FP)
        # Group B:
        #   GT=1: 30 candidates. Model selected 21 -> Recall = 21/30 = 0.70
        #   GT=0: 20 candidates. Model selected 5  (FP)
        # Expected EOD = 0.90 - 0.70 = 0.20
        records = (
            [{"group": "A", "prediction": 1, "ground_truth": 1} for _ in range(36)] +
            [{"group": "A", "prediction": 0, "ground_truth": 1} for _ in range(4)] +
            [{"group": "A", "prediction": 1, "ground_truth": 0} for _ in range(4)] +
            [{"group": "A", "prediction": 0, "ground_truth": 0} for _ in range(16)] +
            [{"group": "B", "prediction": 1, "ground_truth": 1} for _ in range(21)] +
            [{"group": "B", "prediction": 0, "ground_truth": 1} for _ in range(9)] +
            [{"group": "B", "prediction": 1, "ground_truth": 0} for _ in range(5)] +
            [{"group": "B", "prediction": 0, "ground_truth": 0} for _ in range(15)]
        )
        res = calculate_fairness_metrics(records, reference_group="A")

        assert res.has_ground_truth is True
        assert res.equal_opportunity_difference == pytest.approx(0.20, abs=1e-4)

        metrics_map = {sm.group: sm for sm in res.subgroup_metrics}
        assert metrics_map["A"].recall == 0.90
        assert metrics_map["B"].recall == 0.70
        assert metrics_map["B"].recall_difference_from_reference == pytest.approx(-0.20, abs=1e-4)

    def test_eod_none_when_ground_truth_is_missing(self):
        """CRITICAL: If ground truth is not provided, EOD MUST NOT be calculated."""
        records = [
            {"group": "A", "prediction": 1},
            {"group": "A", "prediction": 0},
            {"group": "B", "prediction": 1},
            {"group": "B", "prediction": 0},
        ]
        res = calculate_fairness_metrics(records)

        assert res.has_ground_truth is False
        assert res.equal_opportunity_difference is None
        for sm in res.subgroup_metrics:
            assert sm.recall is None
        assert any("Ground-truth outcome labels are unavailable" in w for w in res.warnings)

    def test_eod_none_when_ground_truth_is_partially_missing(self):
        """If only some candidates have ground truth, omit EOD to avoid attrition bias."""
        records = [
            {"group": "A", "prediction": 1, "ground_truth": 1},
            {"group": "A", "prediction": 0, "ground_truth": None},  # Missing
            {"group": "B", "prediction": 1, "ground_truth": 1},
            {"group": "B", "prediction": 0, "ground_truth": 0},
        ]
        res = calculate_fairness_metrics(records)

        assert res.has_ground_truth is False
        assert res.equal_opportunity_difference is None
        assert any("partially missing" in w for w in res.warnings)

    def test_eod_none_when_subgroup_has_zero_positive_ground_truth(self):
        """If group has 0 positive ground truth, recall is undefined -> EOD is None."""
        records = (
            [{"group": "A", "prediction": 1, "ground_truth": 1} for _ in range(30)] +
            [{"group": "B", "prediction": 1, "ground_truth": 0} for _ in range(30)]  # No positive GT
        )
        res = calculate_fairness_metrics(records)

        assert res.equal_opportunity_difference is None
        b_metric = next(sm for sm in res.subgroup_metrics if sm.group == "B")
        assert b_metric.recall is None
        assert any("0 positive ground-truth outcomes" in w for w in b_metric.warnings)


# ===========================================================================
# 3. FA-3: Subgroup Sample Counts & Sample-Size Warnings
# ===========================================================================

class TestSampleCountWarnings:
    """Tests sample size thresholds, small group warnings, and configurability."""

    def test_subgroup_under_30_triggers_warning(self):
        # Group A has 40 observations (no warning)
        # Group B has 15 observations (< 30 -> warning)
        records = (
            [{"group": "Group_A", "prediction": 1} for _ in range(40)] +
            [{"group": "Group_B", "prediction": 1} for _ in range(15)]
        )
        res = calculate_fairness_metrics(records, min_sample_size=30)

        metrics_map = {sm.group: sm for sm in res.subgroup_metrics}
        assert metrics_map["Group_A"].has_sample_warning is False
        assert metrics_map["Group_B"].has_sample_warning is True
        assert any("15 observations (< 30)" in w for w in metrics_map["Group_B"].warnings)

    def test_configurable_sample_size_threshold(self):
        records = (
            [{"group": "Group_A", "prediction": 1} for _ in range(50)] +
            [{"group": "Group_B", "prediction": 1} for _ in range(45)]
        )
        # With threshold=60, both should trigger warnings
        res = calculate_fairness_metrics(records, min_sample_size=60)
        for sm in res.subgroup_metrics:
            assert sm.has_sample_warning is True

    def test_overall_dataset_under_threshold_warning(self):
        records = [
            {"group": "A", "prediction": 1},
            {"group": "B", "prediction": 0},
        ]
        res = calculate_fairness_metrics(records, min_sample_size=30)
        assert any("Total sample count (2) is below" in w for w in res.warnings)


# ===========================================================================
# 4. Zero-Denominator Safeguards & Edge Cases
# ===========================================================================

class TestEdgeCasesAndZeroDenominators:
    """Ensures mathematics never raise ZeroDivisionError or produce NaN."""

    def test_empty_dataset(self):
        res = calculate_fairness_metrics([])
        assert res.total_samples == 0
        assert res.demographic_parity_difference is None
        assert res.equal_opportunity_difference is None
        assert len(res.warnings) > 0

    def test_single_group_in_dataset(self):
        records = [{"group": "OnlyOne", "prediction": 1} for _ in range(50)]
        res = calculate_fairness_metrics(records)
        assert res.total_samples == 50
        assert res.demographic_parity_difference is None  # Needs >= 2 groups
        assert any("contains only 1 group" in w for w in res.warnings)

    def test_subgroup_with_zero_selections(self):
        records = (
            [{"group": "A", "prediction": 1} for _ in range(35)] +
            [{"group": "B", "prediction": 0} for _ in range(35)]
        )
        res = calculate_fairness_metrics(records, reference_group="A")
        assert res.demographic_parity_difference == 1.0
        metrics_map = {sm.group: sm for sm in res.subgroup_metrics}
        assert metrics_map["B"].selection_rate == 0.0
        assert metrics_map["B"].adverse_impact_ratio == 0.0

    def test_limitations_always_present(self):
        records = [
            {"group": "A", "prediction": 1},
            {"group": "B", "prediction": 1},
        ]
        res = calculate_fairness_metrics(records)
        assert len(res.limitations) >= 3
        assert any("distinct notions of algorithmic fairness" in lim for lim in res.limitations)


# ===========================================================================
# 5. FA-1 & FA-5: Dataset Ingestion & Validation Workflow
# ===========================================================================

class TestDatasetIngestionWorkflow:
    """Tests Pydantic validation and FairnessService ingestion."""

    def test_pydantic_validates_minimum_two_groups(self):
        service = FairnessService()
        payload = FairnessDatasetCreate(
            name="Single Group Dataset",
            sensitive_attribute="gender",
            records=[
                EvaluationRecordInput(record_id="rec-1", group="Male", score=75.0),
                EvaluationRecordInput(record_id="rec-2", group="Male", score=80.0),
            ],
        )
        with pytest.raises(ValueError, match="at least 2 distinct"):
            service.ingest_dataset(payload)

    def test_pydantic_rejects_records_without_score_or_prediction(self):
        with pytest.raises(Exception):
            FairnessDatasetCreate(
                name="Invalid Records",
                sensitive_attribute="gender",
                records=[
                    EvaluationRecordInput(record_id="rec-1", group="Male"),  # Neither score nor pred
                ],
            )

    def test_pydantic_rejects_blank_group_name(self):
        with pytest.raises(Exception):
            EvaluationRecordInput(record_id="rec-1", group="   ", score=75.0)

    def test_service_ingest_and_audit_flow(self):
        service = FairnessService()
        payload = FairnessDatasetCreate(
            name="Q4 Engineering Audit",
            description="Controlled benchmark audit for senior developer applicants",
            sensitive_attribute="gender",
            reference_group="Group_X",
            score_threshold=70.0,
            records=(
                [EvaluationRecordInput(record_id=f"x-{i}", group="Group_X", score=75.0, ground_truth=1) for i in range(35)] +
                [EvaluationRecordInput(record_id=f"y-{i}", group="Group_Y", score=65.0, ground_truth=1) for i in range(35)]
            ),
        )

        # Ingestion
        dataset_read = service.ingest_dataset(payload, user_id=str(uuid4()))
        assert dataset_read.record_count == 70
        assert len(dataset_read.groups) == 2
        assert dataset_read.has_ground_truth is True

        # Audit
        audit_read = service.run_audit(dataset_id=str(dataset_read.id))
        assert audit_read.total_samples == 70
        assert audit_read.demographic_parity_difference is not None
        assert len(audit_read.subgroup_metrics) == 2

        # Retrieval
        fetched_audit = service.get_audit(str(audit_read.id))
        assert fetched_audit is not None
        assert fetched_audit.id == audit_read.id


# ===========================================================================
# 6. FA-1: API Endpoints & Admin-Only Authorization
# ===========================================================================

class TestFairnessApiAuthorization:
    """Verifies that fairness endpoints are strictly admin-only."""

    def test_endpoints_reject_unauthenticated_request(self):
        """Unauthenticated requests must receive HTTP 401 Unauthorized."""
        saved_overrides = dict(app.dependency_overrides)
        try:
            app.dependency_overrides.clear()
            with TestClient(app) as raw_client:
                resp = raw_client.get("/api/fairness/datasets")
                assert resp.status_code == 401
        finally:
            app.dependency_overrides.update(saved_overrides)

    def test_endpoints_reject_ordinary_recruiter(self, client: TestClient):
        """Recruiters must receive HTTP 403 Forbidden."""
        resp = client.get("/api/fairness/datasets")
        assert resp.status_code == 403
        assert "Admin access required" in resp.json()["detail"]

    def test_endpoints_allow_platform_admin(self, admin_client: TestClient):
        """Platform administrators receive 200 OK."""
        resp = admin_client.get("/api/fairness/datasets")
        assert resp.status_code == 200
        assert "data" in resp.json()

    def test_direct_evaluate_endpoint_success(self, admin_client: TestClient):
        payload = {
            "name": "Direct Evaluation Test",
            "sensitive_attribute": "ethnicity",
            "score_threshold": 70.0,
            "records": (
                [{"record_id": f"a-{i}", "group": "Group_A", "score": 85.0} for i in range(30)] +
                [{"record_id": f"b-{i}", "group": "Group_B", "score": 60.0} for i in range(30)]
            ),
        }
        resp = admin_client.post("/api/fairness/evaluate", json=payload)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["total_samples"] == 60
        assert data["demographic_parity_difference"] == 1.0


# ===========================================================================
# 7. FA-4: Isolation Guarantee
# ===========================================================================

class TestFairnessDataIsolation:
    """Verifies that demographic evaluation data never pollutes candidate scoring."""

    def test_candidate_scoring_has_no_demographic_attributes(self):
        """Rubric DimensionScore and IndicatorEvidence do not store demographic attributes."""
        from app.scoring.rubric import DimensionScore, IndicatorEvidence

        ev = IndicatorEvidence("Active listening", 0.7, 2, True, "strong")
        assert not hasattr(ev, "gender")
        assert not hasattr(ev, "demographic_group")

        ds = DimensionScore("communication", 85, 0.85, 0.9)
        assert not hasattr(ds, "group")
        assert not hasattr(ds, "sensitive_attribute")

    def test_report_service_schema_unaffected(self):
        """Assessment report schema does not contain demographic or protected attributes."""
        from app.schemas.report import AssessmentReportRead

        fields = AssessmentReportRead.model_fields.keys()
        for forbidden in ["demographic", "ethnicity", "gender", "race", "age", "protected_group"]:
            assert forbidden not in fields
