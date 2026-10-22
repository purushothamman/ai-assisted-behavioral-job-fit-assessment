"""
fairness/service.py
Service layer for controlled demographic evaluation dataset ingestion and audit execution.

Isolation & Security:
  - Operates strictly in the platform administration boundary.
  - Demographic evaluation data is stored in dedicated evaluation tables
    (fairness_datasets, fairness_audits) and is NEVER connected to candidate_responses,
    response_scores, or recruiter assessment reports.
  - Persists to Supabase with graceful local fallback if migrations have not yet been applied.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.db.client import get_supabase_admin
from app.fairness.metrics import (
    DEFAULT_MIN_SAMPLE_SIZE,
    DEFAULT_SCORE_THRESHOLD,
    calculate_fairness_metrics,
)
from app.fairness.schemas import (
    FairnessAuditRead,
    FairnessAuditRunRequest,
    FairnessDatasetCreate,
    FairnessDatasetRead,
    SubgroupMetricRead,
)

logger = logging.getLogger(__name__)

# In-memory fallback stores (for test environments or before SQL migration is applied)
_FALLBACK_DATASETS: Dict[str, dict] = {}
_FALLBACK_AUDITS: Dict[str, dict] = {}


class FairnessService:
    """Service for managing evaluation datasets and running demographic fairness audits."""

    def __init__(self) -> None:
        self._db = get_supabase_admin()

    @staticmethod
    def _raise_if_error(result) -> None:
        if hasattr(result, "error") and result.error:
            logger.error("Supabase fairness DB error: %s", result.error)
            raise RuntimeError(str(result.error))

    # ── Dataset Ingestion ─────────────────────────────────────────────────────

    def ingest_dataset(
        self,
        payload: FairnessDatasetCreate,
        user_id: Optional[str] = None,
    ) -> FairnessDatasetRead:
        """
        Validate and ingest a controlled evaluation dataset.
        Validates that at least two distinct demographic groups are present.
        """
        dataset_id = str(uuid4())
        now_utc = datetime.now(timezone.utc)

        # Extract distinct groups
        groups = sorted(list({r.group.strip() for r in payload.records}))
        if len(groups) < 2:
            raise ValueError(
                f"Evaluation dataset must contain at least 2 distinct demographic groups. Found: {groups}"
            )

        # Check ground truth coverage
        has_gt = all(r.ground_truth is not None for r in payload.records) and len(payload.records) > 0

        # Prepare serialized records
        records_json = [r.model_dump() for r in payload.records]

        row = {
            "id":                  dataset_id,
            "name":                payload.name,
            "description":         payload.description,
            "sensitive_attribute": payload.sensitive_attribute,
            "reference_group":     payload.reference_group or groups[0],
            "score_threshold":     float(payload.score_threshold),
            "record_count":        len(payload.records),
            "groups":              groups,
            "has_ground_truth":    has_gt,
            "records":             records_json,
            "created_at":          now_utc.isoformat(),
            "created_by":          user_id,
        }

        # Try saving to DB with fallback to memory
        saved_to_db = False
        try:
            db_row = dict(row)
            db_row["groups"] = json.dumps(groups)
            db_row["records"] = json.dumps(records_json)
            result = self._db.table("fairness_datasets").insert(db_row).execute()
            self._raise_if_error(result)
            saved_to_db = True
        except Exception as exc:
            logger.warning(
                "Could not persist fairness dataset to Supabase table (using fallback store): %s", exc
            )

        # Always store in memory store as cache / fallback
        _FALLBACK_DATASETS[dataset_id] = row

        return FairnessDatasetRead(
            id=UUID(dataset_id),
            name=payload.name,
            description=payload.description,
            sensitive_attribute=payload.sensitive_attribute,
            reference_group=payload.reference_group or groups[0],
            score_threshold=float(payload.score_threshold),
            record_count=len(payload.records),
            groups=groups,
            has_ground_truth=has_gt,
            created_at=now_utc,
            created_by=UUID(user_id) if user_id else None,
        )

    # ── Dataset Retrieval ─────────────────────────────────────────────────────

    def list_datasets(self) -> List[FairnessDatasetRead]:
        """List summary metadata for all ingested evaluation datasets."""
        try:
            result = (
                self._db.table("fairness_datasets")
                .select("id, name, description, sensitive_attribute, reference_group, score_threshold, record_count, groups, has_ground_truth, created_at, created_by")
                .order("created_at", desc=True)
                .execute()
            )
            self._raise_if_error(result)
            rows = result.data or []
            if rows:
                datasets: List[FairnessDatasetRead] = []
                for r in rows:
                    raw_groups = r.get("groups") or []
                    if isinstance(raw_groups, str):
                        try:
                            raw_groups = json.loads(raw_groups)
                        except Exception:
                            raw_groups = []
                    datasets.append(FairnessDatasetRead(
                        id=UUID(str(r["id"])),
                        name=r["name"],
                        description=r.get("description"),
                        sensitive_attribute=r["sensitive_attribute"],
                        reference_group=r.get("reference_group"),
                        score_threshold=float(r.get("score_threshold", DEFAULT_SCORE_THRESHOLD)),
                        record_count=int(r.get("record_count", 0)),
                        groups=raw_groups,
                        has_ground_truth=bool(r.get("has_ground_truth", False)),
                        created_at=datetime.fromisoformat(r["created_at"]) if isinstance(r["created_at"], str) else r["created_at"],
                        created_by=UUID(str(r["created_by"])) if r.get("created_by") else None,
                    ))
                return datasets
        except Exception as exc:
            logger.warning("Could not list fairness datasets from Supabase: %s", exc)

        # Fallback to memory
        return [
            FairnessDatasetRead(
                id=UUID(d["id"]),
                name=d["name"],
                description=d.get("description"),
                sensitive_attribute=d["sensitive_attribute"],
                reference_group=d.get("reference_group"),
                score_threshold=d["score_threshold"],
                record_count=d["record_count"],
                groups=d["groups"],
                has_ground_truth=d["has_ground_truth"],
                created_at=datetime.fromisoformat(d["created_at"]) if isinstance(d["created_at"], str) else d["created_at"],
                created_by=UUID(d["created_by"]) if d.get("created_by") else None,
            )
            for d in _FALLBACK_DATASETS.values()
        ]

    def get_dataset(self, dataset_id: str) -> Optional[dict]:
        """Fetch full dataset including records."""
        try:
            result = (
                self._db.table("fairness_datasets")
                .select("*")
                .eq("id", dataset_id)
                .maybe_single()
                .execute()
            )
            self._raise_if_error(result)
            if result.data:
                data = dict(result.data)
                if isinstance(data.get("groups"), str):
                    data["groups"] = json.loads(data["groups"])
                if isinstance(data.get("records"), str):
                    data["records"] = json.loads(data["records"])
                return data
        except Exception as exc:
            logger.warning("Could not fetch fairness dataset from Supabase: %s", exc)

        return _FALLBACK_DATASETS.get(dataset_id)

    # ── Audit Execution ───────────────────────────────────────────────────────

    def run_audit(
        self,
        dataset_id: str,
        options: Optional[FairnessAuditRunRequest] = None,
        user_id: Optional[str] = None,
    ) -> FairnessAuditRead:
        """Execute a fairness audit on an ingested evaluation dataset."""
        dataset = self.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Fairness evaluation dataset '{dataset_id}' not found.")

        threshold = (
            options.score_threshold
            if options and options.score_threshold is not None
            else float(dataset.get("score_threshold", DEFAULT_SCORE_THRESHOLD))
        )
        ref_group = (
            options.reference_group
            if options and options.reference_group
            else dataset.get("reference_group")
        )
        min_samples = (
            options.min_sample_size
            if options and options.min_sample_size is not None
            else DEFAULT_MIN_SAMPLE_SIZE
        )

        records = dataset.get("records") or []
        metrics_res = calculate_fairness_metrics(
            records=records,
            sensitive_attribute=dataset.get("sensitive_attribute", "group"),
            score_threshold=threshold,
            min_sample_size=min_samples,
            reference_group=ref_group,
        )

        audit_id = str(uuid4())
        now_utc = datetime.now(timezone.utc)

        subgroup_reads = [
            SubgroupMetricRead(
                group=sm.group,
                sample_count=sm.sample_count,
                selection_count=sm.selection_count,
                selection_rate=sm.selection_rate,
                rate_difference_from_reference=sm.rate_difference_from_reference,
                adverse_impact_ratio=sm.adverse_impact_ratio,
                ground_truth_positives=sm.ground_truth_positives,
                ground_truth_negatives=sm.ground_truth_negatives,
                true_positives=sm.true_positives,
                false_positives=sm.false_positives,
                false_negatives=sm.false_negatives,
                true_negatives=sm.true_negatives,
                recall=sm.recall,
                recall_difference_from_reference=sm.recall_difference_from_reference,
                has_sample_warning=sm.has_sample_warning,
                warnings=sm.warnings,
            )
            for sm in metrics_res.subgroup_metrics
        ]

        audit_read = FairnessAuditRead(
            id=UUID(audit_id),
            dataset_id=UUID(dataset_id),
            dataset_name=dataset.get("name", "Evaluation Dataset"),
            sensitive_attribute=metrics_res.sensitive_attribute,
            reference_group=metrics_res.reference_group,
            total_samples=metrics_res.total_samples,
            evaluated_threshold=metrics_res.evaluated_threshold,
            has_ground_truth=metrics_res.has_ground_truth,
            demographic_parity_difference=metrics_res.demographic_parity_difference,
            equal_opportunity_difference=metrics_res.equal_opportunity_difference,
            subgroup_metrics=subgroup_reads,
            warnings=metrics_res.warnings,
            limitations=metrics_res.limitations,
            created_at=now_utc,
            created_by=UUID(user_id) if user_id else None,
        )

        # Store in DB / memory
        audit_row = {
            "id":                            audit_id,
            "dataset_id":                    dataset_id,
            "dataset_name":                  dataset.get("name", "Evaluation Dataset"),
            "sensitive_attribute":           metrics_res.sensitive_attribute,
            "reference_group":               metrics_res.reference_group,
            "total_samples":                 metrics_res.total_samples,
            "evaluated_threshold":           metrics_res.evaluated_threshold,
            "has_ground_truth":              metrics_res.has_ground_truth,
            "demographic_parity_difference": metrics_res.demographic_parity_difference,
            "equal_opportunity_difference":  metrics_res.equal_opportunity_difference,
            "subgroup_metrics":              [s.model_dump() for s in subgroup_reads],
            "warnings":                      metrics_res.warnings,
            "limitations":                   metrics_res.limitations,
            "created_at":                    now_utc.isoformat(),
            "created_by":                    user_id,
        }

        try:
            db_audit = dict(audit_row)
            db_audit["subgroup_metrics"] = json.dumps(db_audit["subgroup_metrics"])
            db_audit["warnings"] = json.dumps(db_audit["warnings"])
            db_audit["limitations"] = json.dumps(db_audit["limitations"])
            res = self._db.table("fairness_audits").insert(db_audit).execute()
            self._raise_if_error(res)
        except Exception as exc:
            logger.warning("Could not persist fairness audit to Supabase table: %s", exc)

        _FALLBACK_AUDITS[audit_id] = audit_row
        return audit_read

    def evaluate_direct(
        self,
        payload: FairnessDatasetCreate,
        user_id: Optional[str] = None,
    ) -> FairnessAuditRead:
        """Ingest dataset and immediately execute an audit run in one atomic step."""
        ds_read = self.ingest_dataset(payload, user_id=user_id)
        req = FairnessAuditRunRequest(
            score_threshold=payload.score_threshold,
            reference_group=payload.reference_group,
        )
        return self.run_audit(dataset_id=str(ds_read.id), options=req, user_id=user_id)

    def list_audits(self) -> List[FairnessAuditRead]:
        """List all past fairness audit reports."""
        try:
            result = (
                self._db.table("fairness_audits")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            self._raise_if_error(result)
            rows = result.data or []
            if rows:
                audits: List[FairnessAuditRead] = []
                for r in rows:
                    audits.append(self._row_to_audit_read(r))
                return audits
        except Exception as exc:
            logger.warning("Could not list fairness audits from Supabase: %s", exc)

        return [self._row_to_audit_read(a) for a in _FALLBACK_AUDITS.values()]

    def get_audit(self, audit_id: str) -> Optional[FairnessAuditRead]:
        """Fetch a specific audit report by ID."""
        try:
            result = (
                self._db.table("fairness_audits")
                .select("*")
                .eq("id", audit_id)
                .maybe_single()
                .execute()
            )
            self._raise_if_error(result)
            if result.data:
                return self._row_to_audit_read(result.data)
        except Exception as exc:
            logger.warning("Could not fetch fairness audit from Supabase: %s", exc)

        mem = _FALLBACK_AUDITS.get(audit_id)
        return self._row_to_audit_read(mem) if mem else None

    @staticmethod
    def _row_to_audit_read(row: dict) -> FairnessAuditRead:
        sm = row.get("subgroup_metrics") or []
        if isinstance(sm, str):
            sm = json.loads(sm)
        warns = row.get("warnings") or []
        if isinstance(warns, str):
            warns = json.loads(warns)
        limits = row.get("limitations") or []
        if isinstance(limits, str):
            limits = json.loads(limits)

        subgroup_reads = [SubgroupMetricRead(**item) for item in sm]
        c_at = row["created_at"]
        if isinstance(c_at, str):
            c_at = datetime.fromisoformat(c_at)

        return FairnessAuditRead(
            id=UUID(str(row["id"])),
            dataset_id=UUID(str(row["dataset_id"])) if row.get("dataset_id") else None,
            dataset_name=row.get("dataset_name", "Evaluation Dataset"),
            sensitive_attribute=row.get("sensitive_attribute", "demographic_group"),
            reference_group=row.get("reference_group", "unknown"),
            total_samples=int(row.get("total_samples", 0)),
            evaluated_threshold=float(row.get("evaluated_threshold", DEFAULT_SCORE_THRESHOLD)),
            has_ground_truth=bool(row.get("has_ground_truth", False)),
            demographic_parity_difference=row.get("demographic_parity_difference"),
            equal_opportunity_difference=row.get("equal_opportunity_difference"),
            subgroup_metrics=subgroup_reads,
            warnings=warns,
            limitations=limits,
            created_at=c_at,
            created_by=UUID(str(row["created_by"])) if row.get("created_by") else None,
        )
