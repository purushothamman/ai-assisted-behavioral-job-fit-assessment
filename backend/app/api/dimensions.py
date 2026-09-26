"""
api/dimensions.py
Read-only endpoints for behavioral dimensions and indicators.

Routes
------
GET  /dimensions                 List all active behavioral dimensions
GET  /dimensions/{dimension_id}  Get a dimension + its indicators

Auth: all endpoints require a valid recruiter JWT.
"""
from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_recruiter
from app.schemas.common import APIResponse
from app.schemas.dimensions import DimensionDetail, DimensionRead
from app.services.dimension_service import DimensionService

router = APIRouter(prefix="/dimensions", tags=["Dimensions"])


def _get_service() -> DimensionService:
    return DimensionService()


# ── List all active dimensions ─────────────────────────────────────────────

@router.get("", response_model=APIResponse[List[DimensionRead]])
async def list_dimensions(
    _: dict = Depends(require_recruiter),
    svc: DimensionService = Depends(_get_service),
):
    """
    Return all active behavioral dimensions (no indicators in this view).
    Ordered alphabetically by name.
    """
    try:
        dims = svc.list_dimensions(active_only=True)
        return APIResponse(data=dims)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Get single dimension with indicators ──────────────────────────────────

@router.get("/{dimension_id}", response_model=APIResponse[DimensionDetail])
async def get_dimension(
    dimension_id: UUID,
    _: dict = Depends(require_recruiter),
    svc: DimensionService = Depends(_get_service),
):
    """
    Return a single behavioral dimension with its full list of indicators.
    Returns 404 if the dimension does not exist.
    """
    try:
        dim = svc.get_dimension(str(dimension_id))
        if not dim:
            raise HTTPException(status_code=404, detail="Dimension not found")
        return APIResponse(data=dim)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
