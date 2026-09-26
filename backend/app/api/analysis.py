"""
api/analysis.py
Endpoints for AI-powered job analysis and behavioral requirement management.

Routes
------
POST  /jobs/{job_id}/analyze                    Groq: extract behavioral requirements
GET   /jobs/{job_id}/requirements               List all requirements for a job
PATCH /jobs/{job_id}/requirements/{req_id}      Confirm/edit a single requirement

Auth: all endpoints require recruiter JWT.
Ownership: job_id is cross-checked against recruiter_id on every request.
"""
from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.groq_client import GroqError
from app.ai.job_analyzer import analyze_job
from app.core.security import require_recruiter
from app.schemas.common import APIResponse
from app.schemas.requirements import RequirementConfirm, RequirementRead
from app.services.job_requirement_service import JobRequirementService
from app.services.job_service import JobService

router = APIRouter(tags=["Analysis"])


# ── Helpers ────────────────────────────────────────────────────────────────

def _get_job_svc() -> JobService:
    return JobService()


def _get_req_svc() -> JobRequirementService:
    return JobRequirementService()


def _assert_job_ownership(job_id: str, recruiter_id: str, job_svc: JobService) -> dict:
    """Fetch the job and raise 404 if it doesn't exist or isn't owned by recruiter."""
    job = job_svc.get_job(job_id, recruiter_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── POST /jobs/{job_id}/analyze ────────────────────────────────────────────

@router.post(
    "/jobs/{job_id}/analyze",
    response_model=APIResponse[List[RequirementRead]],
    status_code=status.HTTP_201_CREATED,
)
async def analyze_job_endpoint(
    job_id: UUID,
    current_user: dict = Depends(require_recruiter),
    job_svc: JobService = Depends(_get_job_svc),
    req_svc: JobRequirementService = Depends(_get_req_svc),
):
    """
    Trigger Groq analysis of a job description.

    1. Validates job ownership.
    2. Calls Groq to extract behavioral dimension requirements.
    3. Upserts results into job_requirements (existing rows replaced).
    4. Updates job status to 'analyzed'.
    5. Returns the list of saved requirements.
    """
    job = _assert_job_ownership(str(job_id), current_user["id"], job_svc)

    # Check the job has enough text to analyze
    if not job.get("description"):
        raise HTTPException(
            status_code=422,
            detail="Job must have a description before it can be analyzed.",
        )

    # Call Groq
    try:
        requirements = analyze_job(
            title=job["title"],
            description=job.get("description", ""),
            responsibilities=job.get("responsibilities", "") or "",
            requirements=job.get("requirements", "") or "",
        )
    except GroqError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Save to DB
    try:
        saved = req_svc.save_requirements(str(job_id), requirements)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Advance job status to 'analyzed'
    try:
        job_svc.update_job(str(job_id), current_user["id"], _AnalyzedStatus())
    except Exception:
        pass  # Non-fatal: status update failure should not block the response

    return APIResponse(
        message=f"Analysis complete. {len(saved)} behavioral requirements extracted.",
        data=saved,
    )


class _AnalyzedStatus:
    """Minimal duck-typed payload for JobService.update_job status change."""
    def model_dump(self, exclude_none=True):  # noqa: D102
        return {"status": "analyzed"}


# ── GET /jobs/{job_id}/requirements ───────────────────────────────────────

@router.get(
    "/jobs/{job_id}/requirements",
    response_model=APIResponse[List[RequirementRead]],
)
async def list_requirements(
    job_id: UUID,
    current_user: dict = Depends(require_recruiter),
    job_svc: JobService = Depends(_get_job_svc),
    req_svc: JobRequirementService = Depends(_get_req_svc),
):
    """List all behavioral requirements for a job (with dimension name)."""
    _assert_job_ownership(str(job_id), current_user["id"], job_svc)

    try:
        reqs = req_svc.list_requirements(str(job_id))
        return APIResponse(data=reqs)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── PATCH /jobs/{job_id}/requirements/{req_id} ────────────────────────────

@router.patch(
    "/jobs/{job_id}/requirements/{req_id}",
    response_model=APIResponse[RequirementRead],
)
async def update_requirement(
    job_id: UUID,
    req_id: UUID,
    payload: RequirementConfirm,
    current_user: dict = Depends(require_recruiter),
    job_svc: JobService = Depends(_get_job_svc),
    req_svc: JobRequirementService = Depends(_get_req_svc),
):
    """
    Recruiter confirms or edits a behavioral requirement.
    Only fields present in the body are updated.
    """
    _assert_job_ownership(str(job_id), current_user["id"], job_svc)

    update_data = payload.model_dump(exclude_none=True)
    try:
        updated = req_svc.update_requirement(str(req_id), str(job_id), update_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if not updated:
        raise HTTPException(status_code=404, detail="Requirement not found")

    return APIResponse(message="Requirement updated", data=updated)
