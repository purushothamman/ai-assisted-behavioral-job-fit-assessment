"""
api/admin_framework.py
Platform Admin endpoints for behavioral dimensions, indicators, and framework versioning.

Auth: All endpoints strictly require platform administrator authorization (require_admin).
Recruiters and candidates receive HTTP 403 Forbidden.
"""
from __future__ import annotations

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import require_admin
from app.schemas.common import APIResponse
from app.schemas.dimensions import (
    DimensionCreate,
    DimensionDetail,
    DimensionRead,
    DimensionUpdate,
    FrameworkReorderPayload,
    FrameworkValidationResult,
    FrameworkVersionPublish,
    FrameworkVersionRead,
    IndicatorCreate,
    IndicatorRead,
    IndicatorUpdate,
)
from app.services.framework_service import FrameworkService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Framework"])


def _get_service() -> FrameworkService:
    return FrameworkService()


# ── Framework Versions & Lifecycle ──────────────────────────────────────────

@router.get("/framework/versions", response_model=APIResponse[List[FrameworkVersionRead]])
async def list_framework_versions(
    _: dict = Depends(require_admin),
    svc: FrameworkService = Depends(_get_service),
):
    """List all framework versions (draft, active, archived)."""
    try:
        versions = svc.list_versions()
        return APIResponse(data=versions)
    except Exception as exc:
        logger.error("Failed to list framework versions: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/framework/current", response_model=APIResponse[FrameworkVersionRead])
async def get_current_framework_version(
    _: dict = Depends(require_admin),
    svc: FrameworkService = Depends(_get_service),
):
    """Get the currently active published framework version."""
    try:
        active_ver = svc.get_active_version()
        if not active_ver:
            # Fall back to synthesizing a v1 representation from active dimensions
            val = svc.validate_framework()
            dims = svc.list_dimensions_admin(include_archived=False)
            synthetic = {
                "id": "00000000-0000-0000-0000-000000000001",
                "version_number": 1,
                "name": "v1.0 - Default Behavioral Framework",
                "description": "Baseline framework",
                "status": "active",
                "dimensions_snapshot": [d for d in dims if d.get("is_active")],
                "created_at": None,
                "activated_at": None,
            }
            return APIResponse(data=synthetic)
        return APIResponse(data=active_ver)
    except Exception as exc:
        logger.error("Failed to get current framework: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/framework/validate", response_model=APIResponse[FrameworkValidationResult])
async def validate_framework(
    _: dict = Depends(require_admin),
    svc: FrameworkService = Depends(_get_service),
):
    """Validate current draft/active framework dimensions and indicators before activation."""
    try:
        result = svc.validate_framework()
        return APIResponse(data=result)
    except Exception as exc:
        logger.error("Framework validation error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/framework/publish", response_model=APIResponse[FrameworkVersionRead], status_code=status.HTTP_201_CREATED)
async def publish_framework_version(
    payload: FrameworkVersionPublish,
    current_admin: dict = Depends(require_admin),
    svc: FrameworkService = Depends(_get_service),
):
    """Publish and activate a new framework version with frozen snapshot."""
    try:
        new_version = svc.publish_version(payload, created_by=current_admin.get("id"))
        return APIResponse(
            message=f"Framework Version {new_version.get('version_number')} successfully activated.",
            data=new_version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to publish framework version: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Dimensions Management ───────────────────────────────────────────────────

@router.get("/dimensions", response_model=APIResponse[List[DimensionDetail]])
async def list_admin_dimensions(
    include_archived: bool = True,
    _: dict = Depends(require_admin),
    svc: FrameworkService = Depends(_get_service),
):
    """List all dimensions (active, draft, archived) with indicator counts."""
    try:
        dims = svc.list_dimensions_admin(include_archived=include_archived)
        return APIResponse(data=dims)
    except Exception as exc:
        logger.error("Failed to list admin dimensions: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/dimensions", response_model=APIResponse[DimensionDetail], status_code=status.HTTP_201_CREATED)
async def create_dimension(
    payload: DimensionCreate,
    _: dict = Depends(require_admin),
    svc: FrameworkService = Depends(_get_service),
):
    """Create a new behavioral dimension with optional initial indicators."""
    try:
        created = svc.create_dimension(payload)
        return APIResponse(
            message=f"Dimension '{payload.name}' created successfully.",
            data=created,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to create dimension: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/dimensions/{dimension_id}", response_model=APIResponse[DimensionDetail])
async def get_admin_dimension(
    dimension_id: UUID,
    _: dict = Depends(require_admin),
    svc: FrameworkService = Depends(_get_service),
):
    """Get single dimension detail with indicators and usage stats."""
    try:
        dim = svc.get_dimension_admin(str(dimension_id))
        if not dim:
            raise HTTPException(status_code=404, detail="Dimension not found")
        return APIResponse(data=dim)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get dimension: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/dimensions/{dimension_id}", response_model=APIResponse[DimensionDetail])
async def update_dimension(
    dimension_id: UUID,
    payload: DimensionUpdate,
    _: dict = Depends(require_admin),
    svc: FrameworkService = Depends(_get_service),
):
    """Update dimension properties (name, description, status, order_index)."""
    try:
        updated = svc.update_dimension(str(dimension_id), payload)
        return APIResponse(
            message="Dimension updated successfully.",
            data=updated,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to update dimension: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/dimensions/{dimension_id}", response_model=APIResponse[dict])
async def archive_or_delete_dimension(
    dimension_id: UUID,
    _: dict = Depends(require_admin),
    svc: FrameworkService = Depends(_get_service),
):
    """
    Safely archive or delete a dimension.
    If historical assessments/jobs reference it, it is safely archived.
    """
    try:
        res = svc.archive_or_delete_dimension(str(dimension_id))
        return APIResponse(
            message=res.get("message", "Dimension processed successfully."),
            data=res,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to archive/delete dimension: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/dimensions/reorder", response_model=APIResponse[List[DimensionDetail]])
async def reorder_dimensions(
    payload: FrameworkReorderPayload,
    _: dict = Depends(require_admin),
    svc: FrameworkService = Depends(_get_service),
):
    """Update display order for multiple dimensions."""
    try:
        reordered = svc.reorder_dimensions(payload.items)
        return APIResponse(
            message="Dimensions reordered successfully.",
            data=reordered,
        )
    except Exception as exc:
        logger.error("Failed to reorder dimensions: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Indicators Management ───────────────────────────────────────────────────

@router.post("/dimensions/{dimension_id}/indicators", response_model=APIResponse[IndicatorRead], status_code=status.HTTP_201_CREATED)
async def add_indicator(
    dimension_id: UUID,
    payload: IndicatorCreate,
    _: dict = Depends(require_admin),
    svc: FrameworkService = Depends(_get_service),
):
    """Add an observable behavioral indicator to a dimension."""
    try:
        ind = svc.add_indicator(str(dimension_id), payload)
        return APIResponse(
            message=f"Indicator '{payload.name}' added successfully.",
            data=ind,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to add indicator: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/indicators/{indicator_id}", response_model=APIResponse[dict])
async def update_indicator(
    indicator_id: UUID,
    payload: IndicatorUpdate,
    _: dict = Depends(require_admin),
    svc: FrameworkService = Depends(_get_service),
):
    """Update an observable behavioral indicator."""
    try:
        updated = svc.update_indicator(str(indicator_id), payload)
        return APIResponse(
            message="Indicator updated successfully.",
            data=updated,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to update indicator: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/indicators/{indicator_id}", response_model=APIResponse[dict])
async def delete_indicator(
    indicator_id: UUID,
    _: dict = Depends(require_admin),
    svc: FrameworkService = Depends(_get_service),
):
    """Delete an observable behavioral indicator."""
    try:
        res = svc.delete_indicator(str(indicator_id))
        return APIResponse(
            message="Indicator deleted successfully.",
            data=res,
        )
    except Exception as exc:
        logger.error("Failed to delete indicator: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
