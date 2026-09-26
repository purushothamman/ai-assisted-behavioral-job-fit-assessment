"""
api/jobs.py
CRUD endpoints for Job management.
All endpoints require a valid Supabase recruiter JWT.

Routes
------
POST   /jobs                      Create a new job
GET    /jobs                      List all jobs owned by the recruiter
GET    /jobs/{job_id}             Get a single job
PATCH  /jobs/{job_id}             Partial update
DELETE /jobs/{job_id}             Delete a job
"""
from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import require_recruiter
from app.schemas.common import APIResponse
from app.schemas.jobs import JobCreate, JobListItem, JobRead, JobUpdate
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _get_service() -> JobService:
    return JobService()


# ── Create ─────────────────────────────────────────────────────────────────

@router.post("", response_model=APIResponse[JobRead], status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    current_user: dict = Depends(require_recruiter),
    svc: JobService = Depends(_get_service),
):
    """Create a new job listing owned by the authenticated recruiter."""
    try:
        job = svc.create_job(recruiter_id=current_user["id"], payload=payload)
        return APIResponse(message="Job created", data=job)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── List ───────────────────────────────────────────────────────────────────

@router.get("", response_model=APIResponse[List[JobListItem]])
async def list_jobs(
    current_user: dict = Depends(require_recruiter),
    svc: JobService = Depends(_get_service),
):
    """Return all jobs belonging to the authenticated recruiter."""
    jobs = svc.list_jobs(recruiter_id=current_user["id"])
    return APIResponse(data=jobs)


# ── Get single ─────────────────────────────────────────────────────────────

@router.get("/{job_id}", response_model=APIResponse[JobRead])
async def get_job(
    job_id: UUID,
    current_user: dict = Depends(require_recruiter),
    svc: JobService = Depends(_get_service),
):
    """Return a single job if it belongs to the recruiter."""
    job = svc.get_job(str(job_id), current_user["id"])
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return APIResponse(data=job)


# ── Update ─────────────────────────────────────────────────────────────────

@router.patch("/{job_id}", response_model=APIResponse[JobRead])
async def update_job(
    job_id: UUID,
    payload: JobUpdate,
    current_user: dict = Depends(require_recruiter),
    svc: JobService = Depends(_get_service),
):
    """Partially update a job (only fields present in the body are changed)."""
    updated = svc.update_job(str(job_id), current_user["id"], payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Job not found")
    return APIResponse(message="Job updated", data=updated)


# ── Delete ─────────────────────────────────────────────────────────────────

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    current_user: dict = Depends(require_recruiter),
    svc: JobService = Depends(_get_service),
):
    """Hard-delete a job. Returns 204 on success, 404 if not found."""
    deleted = svc.delete_job(str(job_id), current_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
