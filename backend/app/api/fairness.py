"""
api/fairness.py
Platform Admin endpoints for Demographic Fairness Audits.

Endpoints:
  - POST /fairness/datasets             : Ingest a controlled demographic evaluation dataset
  - GET  /fairness/datasets             : List all evaluation datasets
  - GET  /fairness/datasets/{id}        : Retrieve dataset detail
  - POST /fairness/datasets/{id}/audit  : Execute fairness audit on dataset
  - POST /fairness/evaluate             : Direct on-the-fly dataset evaluation
  - GET  /fairness/audits               : List past fairness audit reports
  - GET  /fairness/audits/{id}          : Retrieve a specific fairness audit report

Security & Isolation:
  - Strictly requires platform administrator privileges (require_admin).
  - Recruiters and candidate sessions receive HTTP 403 Forbidden.
  - Demographic evaluation records are completely decoupled from applicant assessment flows.
"""
from __future__ import annotations

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import require_admin
from app.fairness.schemas import (
    FairnessAuditRead,
    FairnessAuditRunRequest,
    FairnessDatasetCreate,
    FairnessDatasetRead,
)
from app.fairness.service import FairnessService
from app.schemas.common import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fairness", tags=["Fairness & Bias Audits"])


def _get_service() -> FairnessService:
    return FairnessService()


# ── Dataset Ingestion & Management ──────────────────────────────────────────

@router.post(
    "/datasets",
    response_model=APIResponse[FairnessDatasetRead],
    status_code=status.HTTP_201_CREATED,
)
async def ingest_dataset(
    payload: FairnessDatasetCreate,
    user: dict = Depends(require_admin),
    svc: FairnessService = Depends(_get_service),
):
    """
    Ingest a controlled demographic evaluation dataset for bias audit.
    Validates group structure, minimum 2 groups, and score/prediction formats.
    """
    try:
        dataset = svc.ingest_dataset(payload, user_id=str(user.get("id")))
        return APIResponse(data=dataset)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to ingest fairness evaluation dataset: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/datasets",
    response_model=APIResponse[List[FairnessDatasetRead]],
)
async def list_datasets(
    _: dict = Depends(require_admin),
    svc: FairnessService = Depends(_get_service),
):
    """List summary metadata for all ingested evaluation datasets."""
    try:
        datasets = svc.list_datasets()
        return APIResponse(data=datasets)
    except Exception as exc:
        logger.error("Failed to list fairness datasets: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/datasets/{dataset_id}",
    response_model=APIResponse[FairnessDatasetRead],
)
async def get_dataset(
    dataset_id: UUID,
    _: dict = Depends(require_admin),
    svc: FairnessService = Depends(_get_service),
):
    """Retrieve metadata for a specific evaluation dataset."""
    dataset = svc.get_dataset(str(dataset_id))
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    
    return APIResponse(data=FairnessDatasetRead(
        id=UUID(str(dataset["id"])),
        name=dataset["name"],
        description=dataset.get("description"),
        sensitive_attribute=dataset["sensitive_attribute"],
        reference_group=dataset.get("reference_group"),
        score_threshold=float(dataset.get("score_threshold", 70.0)),
        record_count=int(dataset.get("record_count", 0)),
        groups=dataset.get("groups", []),
        has_ground_truth=bool(dataset.get("has_ground_truth", False)),
        created_at=dataset["created_at"],
        created_by=UUID(str(dataset["created_by"])) if dataset.get("created_by") else None,
    ))


# ── Audit Execution ──────────────────────────────────────────────────────────

@router.post(
    "/datasets/{dataset_id}/audit",
    response_model=APIResponse[FairnessAuditRead],
)
async def run_audit_on_dataset(
    dataset_id: UUID,
    payload: Optional[FairnessAuditRunRequest] = None,
    user: dict = Depends(require_admin),
    svc: FairnessService = Depends(_get_service),
):
    """
    Execute a demographic fairness audit on an ingested evaluation dataset.
    Calculates Demographic Parity Difference (DPD), Equal Opportunity Difference (EOD),
    and Subgroup Recall with explicit sample-size warnings and ethical guardrails.
    """
    try:
        report = svc.run_audit(
            dataset_id=str(dataset_id),
            options=payload,
            user_id=str(user.get("id")),
        )
        return APIResponse(data=report)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to run fairness audit: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/evaluate",
    response_model=APIResponse[FairnessAuditRead],
    status_code=status.HTTP_201_CREATED,
)
async def evaluate_direct(
    payload: FairnessDatasetCreate,
    user: dict = Depends(require_admin),
    svc: FairnessService = Depends(_get_service),
):
    """
    Direct evaluation: ingest dataset and immediately execute fairness audit.
    Useful for automated CI/CD pipeline fairness evaluations or one-off audit uploads.
    """
    try:
        report = svc.evaluate_direct(payload, user_id=str(user.get("id")))
        return APIResponse(data=report)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to run direct fairness evaluation: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/audits",
    response_model=APIResponse[List[FairnessAuditRead]],
)
async def list_audits(
    _: dict = Depends(require_admin),
    svc: FairnessService = Depends(_get_service),
):
    """List all completed demographic fairness audit reports."""
    try:
        audits = svc.list_audits()
        return APIResponse(data=audits)
    except Exception as exc:
        logger.error("Failed to list fairness audits: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get(
    "/audits/{audit_id}",
    response_model=APIResponse[FairnessAuditRead],
)
async def get_audit(
    audit_id: UUID,
    _: dict = Depends(require_admin),
    svc: FairnessService = Depends(_get_service),
):
    """Retrieve a specific completed demographic fairness audit report."""
    audit = svc.get_audit(str(audit_id))
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fairness audit report not found")
    return APIResponse(data=audit)
