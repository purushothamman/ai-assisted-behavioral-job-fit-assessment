"""
api/sessions.py
Phase 5 — Candidate interview session endpoints.

Recruiter endpoints (require_recruiter):
  POST   /api/jobs/{job_id}/sessions        — create a candidate session + token
  GET    /api/jobs/{job_id}/sessions        — list all sessions for a job

Public endpoints (no auth — token-gated):
  GET    /api/sessions/{token}              — candidate fetches job + questions
  POST   /api/sessions/{token}/responses   — candidate submits all answers
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import require_recruiter
from app.schemas.sessions import (
    PublicQuestion,
    PublicSessionRead,
    ResponseRead,
    SessionCreate,
    SessionRead,
    SubmitResponsesPayload,
)
from app.services.job_service import JobService
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sessions"])


# ── Helper ────────────────────────────────────────────────────────────────────

def _ensure_session_accessible(session: dict) -> None:
    """
    Raise 403 if the session has expired or is already completed.
    """
    if session["status"] == "completed":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This assessment has already been submitted.",
        )
    expires_at = session.get("expires_at")
    if expires_at:
        # Parse ISO string
        if isinstance(expires_at, str):
            from datetime import datetime
            try:
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            except ValueError:
                expires_at = None
        if expires_at and datetime.now(timezone.utc) > expires_at:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This assessment link has expired.",
            )


# ── Recruiter: create session ─────────────────────────────────────────────────

@router.post(
    "/jobs/{job_id}/sessions",
    status_code=status.HTTP_201_CREATED,
    summary="Create a candidate interview session",
)
def create_session(
    job_id: str,
    payload: SessionCreate,
    user: dict = Depends(require_recruiter),
):
    """
    Create a UUID-token session for a candidate.
    Returns the session with the shareable token.
    """
    job_svc = JobService()
    job = job_svc.get_job(job_id, recruiter_id=user["id"])
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    # Verify job has approved questions
    session_svc = SessionService()
    approved = session_svc.get_approved_questions(job_id)
    if not approved:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Job has no approved questions. Please approve at least one question before sending to a candidate.",
        )

    try:
        session = session_svc.create_session(job_id, payload)
    except RuntimeError as exc:
        logger.error("Failed to create session: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create candidate session.",
        ) from exc

    return {"success": True, "data": SessionRead(**session)}


# ── Recruiter: list sessions ──────────────────────────────────────────────────

@router.get(
    "/jobs/{job_id}/sessions",
    summary="List candidate sessions for a job",
)
def list_sessions(
    job_id: str,
    user: dict = Depends(require_recruiter),
):
    """Return all candidate sessions created for this job."""
    job_svc = JobService()
    job = job_svc.get_job(job_id, recruiter_id=user["id"])
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    session_svc = SessionService()
    sessions = session_svc.list_sessions(job_id)
    return {"success": True, "data": [SessionRead(**s) for s in sessions]}


# ── Public: get session by token ──────────────────────────────────────────────

@router.get(
    "/sessions/{token}",
    summary="Candidate: fetch assessment session",
)
def get_session(token: str):
    """
    Public endpoint — no authentication required.
    Candidate opens their unique link; we return job context + approved questions.
    Also advances session status from 'pending' -> 'in_progress'.
    """
    session_svc = SessionService()
    session = session_svc.get_session_by_token(token)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found. Please check your link.",
        )

    _ensure_session_accessible(session)

    # Fetch job + questions
    job = session_svc.get_job_public(session["job_id"])
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated job not found.",
        )

    questions_raw = session_svc.get_approved_questions(session["job_id"])

    # Advance status pending -> in_progress (best-effort, non-fatal)
    if session["status"] == "pending":
        try:
            session_svc.mark_in_progress(session["id"])
        except Exception as exc:
            logger.warning("Could not advance session status: %s", exc)

    questions = [PublicQuestion(**q) for q in questions_raw]

    payload = PublicSessionRead(
        session_id=session["id"],
        job_title=job["title"],
        job_description=job.get("description") or "",
        candidate_name=session["candidate_name"],
        status=session["status"],
        expires_at=session.get("expires_at"),
        questions=questions,
    )

    return {"success": True, "data": payload}


# ── Public: submit responses ──────────────────────────────────────────────────

@router.post(
    "/sessions/{token}/responses",
    status_code=status.HTTP_201_CREATED,
    summary="Candidate: submit all assessment answers",
)
def submit_responses(token: str, payload: SubmitResponsesPayload):
    """
    Public endpoint — no authentication required.
    Candidate submits all answers at once; session is marked 'completed'.
    """
    session_svc = SessionService()
    session = session_svc.get_session_by_token(token)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found. Please check your link.",
        )

    _ensure_session_accessible(session)

    # Validate that all submitted question IDs belong to this job
    approved_qs = session_svc.get_approved_questions(session["job_id"])
    approved_ids = {str(q["id"]) for q in approved_qs}
    for resp in payload.responses:
        if str(resp.question_id) not in approved_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Question {resp.question_id} does not belong to this assessment.",
            )

    try:
        saved = session_svc.submit_responses(session["id"], payload.responses)
    except RuntimeError as exc:
        logger.error("Failed to save responses: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save your responses. Please try again.",
        ) from exc

    return {
        "success": True,
        "message": "Assessment submitted successfully. Thank you!",
        "data": [ResponseRead(**r) for r in saved],
    }
