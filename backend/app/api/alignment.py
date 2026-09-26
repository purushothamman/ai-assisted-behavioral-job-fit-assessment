"""
api/alignment.py
FastAPI endpoints for Phase 7 Job-Candidate Behavioral Alignment.

Endpoints:
  POST /api/sessions/{session_id}/alignment
    Recruiter-triggered. Calculates deterministic weighted alignment between
    recruiter-approved job behavioral requirements and candidate response scores.
    Persists to the session_alignments table.

  GET  /api/sessions/{session_id}/alignment
    Recruiter-only. Returns the alignment breakdown, strengths, and review areas
    for a specific candidate session.

  GET  /api/jobs/{job_id}/alignments
    Recruiter-only. Returns all calculated alignments for candidate sessions
    under a specific job.

Security:
  All endpoints require a valid recruiter JWT (require_recruiter dependency).
  The recruiter must own the job associated with the session.
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import require_recruiter
from app.schemas.alignment import AlignmentTriggerPayload, SessionAlignmentRead
from app.services.alignment_service import AlignmentService
from app.services.job_service import JobService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["alignment"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_session_or_404(session_id: str, recruiter_id: str) -> dict:
    """
    Fetch session, verify it exists and belongs to a job owned by the recruiter.
    Raises HTTPException if not found or unauthorized.
    """
    svc = AlignmentService()
    session = svc.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    # Ownership check
    job = JobService().get_job(str(session["job_id"]), recruiter_id)
    if not job or str(job.get("recruiter_id")) != recruiter_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session.",
        )

    return session


def _verify_job_ownership(job_id: str, recruiter_id: str) -> dict:
    """Verify job exists and belongs to the recruiter."""
    job = JobService().get_job(job_id, recruiter_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    if str(job.get("recruiter_id")) != recruiter_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this job.",
        )
    return job


# ── POST /sessions/{session_id}/alignment ───────────────────────────────────

@router.post(
    "/sessions/{session_id}/alignment",
    status_code=status.HTTP_200_OK,
    summary="Calculate job-candidate behavioral alignment",
    response_description="Detailed alignment calculation with strengths and review areas.",
)
def calculate_session_alignment(
    session_id: UUID,
    payload: AlignmentTriggerPayload = AlignmentTriggerPayload(),
    recruiter: dict = Depends(require_recruiter),
):
    """
    Calculate deterministic weighted behavioral alignment between job requirements
    and candidate response scores.

    Formula:
      sum(candidate_score_i * job_weight_i) / sum(job_weight_i)

    Conditions:
      - Session must be 'completed'.
      - Candidate responses must be scored in Phase 6.
      - Calculations are pure Python, deterministic, and explainable.
      - Results are stored in the session_alignments table.
    """
    sid_str = str(session_id)
    rec_id = str(recruiter["id"])

    session = _get_session_or_404(sid_str, rec_id)

    if session["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Session status is '{session['status']}'. "
                "Alignment can only be calculated for completed sessions."
            ),
        )

    svc = AlignmentService()
    scores = svc.get_response_scores(sid_str)
    if not scores:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Candidate responses have not been scored yet. Please run scoring first.",
        )

    try:
        result = svc.calculate_and_save_alignment(sid_str)
    except Exception as exc:
        logger.error("Alignment calculation failed for session %s: %s", sid_str, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alignment calculation failed. Please try again.",
        ) from exc

    return {"success": True, "data": SessionAlignmentRead.model_validate(result)}


# ── GET /sessions/{session_id}/alignment ────────────────────────────────────

@router.get(
    "/sessions/{session_id}/alignment",
    status_code=status.HTTP_200_OK,
    summary="Retrieve session alignment results",
    response_description="Saved alignment result for the session.",
)
def get_session_alignment(
    session_id: UUID,
    recruiter: dict = Depends(require_recruiter),
):
    """
    Fetch the calculated alignment for a candidate session.
    If not calculated yet, will calculate automatically if session is completed and scored.
    """
    sid_str = str(session_id)
    rec_id = str(recruiter["id"])

    session = _get_session_or_404(sid_str, rec_id)
    svc = AlignmentService()

    alignment = svc.get_alignment(sid_str)
    if not alignment:
        # If completed and scores exist, auto-calculate
        if session["status"] == "completed":
            scores = svc.get_response_scores(sid_str)
            if scores:
                try:
                    alignment = svc.calculate_and_save_alignment(sid_str)
                except Exception as exc:
                    logger.warning("Auto-calculation of alignment failed: %s", exc)

    if not alignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alignment has not been calculated for this session.",
        )

    return {"success": True, "data": SessionAlignmentRead.model_validate(alignment)}


# ── GET /jobs/{job_id}/alignments ───────────────────────────────────────────

@router.get(
    "/jobs/{job_id}/alignments",
    status_code=status.HTTP_200_OK,
    summary="List all session alignments for a job",
    response_description="List of candidate session alignments for the job.",
)
def list_job_alignments(
    job_id: UUID,
    recruiter: dict = Depends(require_recruiter),
):
    """
    Retrieve all candidate session alignments for a job.
    Useful for recruiters comparing multiple applicants against role benchmarks.
    """
    jid_str = str(job_id)
    rec_id = str(recruiter["id"])

    _verify_job_ownership(jid_str, rec_id)

    svc = AlignmentService()
    alignments = svc.list_alignments_for_job(jid_str)
    validated = [SessionAlignmentRead.model_validate(a) for a in alignments]

    return {"success": True, "data": validated}
