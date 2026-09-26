"""
api/scoring.py
FastAPI endpoints for Phase 6 response analysis and scoring.

Endpoints:
  POST /api/sessions/{session_id}/score
    Recruiter-triggered. Runs the full NLP scoring pipeline on a completed
    session's candidate responses. Idempotent (re-scores overwrite previous).

  GET  /api/sessions/{session_id}/scores
    Recruiter-only. Returns all stored scores for a session with evidence.

Security:
  Both endpoints require a valid recruiter JWT (require_recruiter dependency).
  The recruiter must own the job that the session belongs to.
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import require_recruiter
from app.schemas.scoring import ResponseScoreRead, ScoreTrigger, SessionScoreSummary
from app.services.scoring_service import ScoringService
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["scoring"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_session_or_404(session_id: str, recruiter_id: str) -> dict:
    """
    Fetch session, verify it exists and belongs to the recruiter's job.
    Raises HTTPException if not found or unauthorised.
    """
    svc     = SessionService()
    svc_sc  = ScoringService()
    session = svc_sc.get_session(session_id)

    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    # Ownership: verify the job belongs to the recruiter
    from app.services.job_service import JobService
    job = JobService().get_job(str(session["job_id"]), recruiter_id)
    if not job or str(job.get("recruiter_id")) != recruiter_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session.",
        )

    return session


# ── POST /sessions/{session_id}/score ────────────────────────────────────────

@router.post(
    "/sessions/{session_id}/score",
    status_code=status.HTTP_200_OK,
    summary="Score a completed candidate session",
    response_description="List of per-response scores with behavioral evidence.",
)
def score_session(
    session_id: UUID,
    payload: ScoreTrigger = ScoreTrigger(),
    recruiter: dict = Depends(require_recruiter),
):
    """
    Trigger NLP scoring for all candidate responses in a completed session.

    - Session must have status = 'completed'.
    - Each response is analyzed against its question's behavioral indicators.
    - Results are stored in `response_scores` (upsert — re-scoring is safe).
    - Returns a list of ResponseScoreRead objects with per-indicator evidence.
    """
    sid_str  = str(session_id)
    rec_id   = str(recruiter["id"])

    session = _get_session_or_404(sid_str, rec_id)

    if session["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Session status is '{session['status']}'. "
                "Scoring is only available for completed sessions."
            ),
        )

    try:
        svc  = ScoringService()
        rows = svc.score_session(sid_str)
    except Exception as exc:
        logger.error("Scoring failed for session %s: %s", sid_str, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scoring pipeline failed. Please try again.",
        ) from exc

    scores = [ResponseScoreRead.model_validate(r) for r in rows]
    return {"success": True, "session_id": sid_str, "scores": scores}


# ── GET /sessions/{session_id}/scores ────────────────────────────────────────

@router.get(
    "/sessions/{session_id}/scores",
    status_code=status.HTTP_200_OK,
    summary="Retrieve scores for a session",
    response_description="Session score summary with per-response breakdown.",
)
def get_scores(
    session_id: UUID,
    recruiter: dict = Depends(require_recruiter),
):
    """
    Retrieve all stored scores for a session.

    - Returns an empty scores list if scoring has not been run yet.
    - Each score includes dimension name, 0-100 score, confidence,
      and per-indicator evidence.
    """
    sid_str = str(session_id)
    rec_id  = str(recruiter["id"])

    session = _get_session_or_404(sid_str, rec_id)

    svc     = ScoringService()
    rows    = svc.get_scores(sid_str)
    scores  = [ResponseScoreRead.model_validate(r) for r in rows]

    job_title = svc.get_job_title(str(session["job_id"]))

    avg_score = (
        round(sum(s.normalized_score for s in scores) / len(scores), 1)
        if scores else 0.0
    )

    summary = SessionScoreSummary(
        session_id=UUID(sid_str),
        candidate_name=session.get("candidate_name", ""),
        job_title=job_title,
        total_responses=len(rows),
        scored_responses=sum(1 for s in scores if s.status == "scored"),
        average_score=avg_score,
        scores=scores,
        scored_at=scores[0].scored_at if scores else None,
    )

    return {"success": True, "data": summary}
