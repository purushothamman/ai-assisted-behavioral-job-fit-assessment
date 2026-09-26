"""
api/reports.py
FastAPI endpoints for Phase 8 Assessment Reports & Recruiter Dashboard.

Endpoints:
  GET /api/sessions/{session_id}/report
    Recruiter-only. Generates and returns a comprehensive, explainable candidate
    assessment report including overall alignment, dimension breakdown, question
    evidence, and targeted inquiry prompts.

  GET /api/jobs/{job_id}/reports/summary
    Recruiter-only. Returns summary records for all candidate sessions under a job
    to populate the recruiter dashboard candidate pipeline.

Security:
  All endpoints require a valid recruiter JWT (require_recruiter).
  Recruiters can only access reports for jobs they own.
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import require_recruiter
from app.schemas.report import AssessmentReportRead, SessionReportSummaryItem
from app.services.job_service import JobService
from app.services.report_service import ReportService
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reports"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _verify_session_access(session_id: str, recruiter_id: str) -> dict:
    """Verify session exists and recruiter owns the associated job."""
    sess_svc = SessionService()
    session = sess_svc.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate session not found.",
        )

    job_id = str(session["job_id"])
    job = JobService().get_job(job_id)
    if not job or str(job.get("recruiter_id")) != recruiter_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this candidate's report.",
        )

    return session


def _verify_job_ownership(job_id: str, recruiter_id: str) -> dict:
    """Verify job exists and recruiter owns it."""
    job = JobService().get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    if str(job.get("recruiter_id")) != recruiter_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to reports for this job.",
        )
    return job


# ── GET /sessions/{session_id}/report ───────────────────────────────────────

@router.get(
    "/sessions/{session_id}/report",
    status_code=status.HTTP_200_OK,
    summary="Get full candidate behavioral assessment report",
    response_description="Comprehensive assessment report with alignment, evidence, and inquiry prompts.",
)
def get_assessment_report(
    session_id: UUID,
    recruiter: dict = Depends(require_recruiter),
):
    """
    Retrieve the comprehensive assessment report for a candidate session.

    Includes:
      - Overall weighted job-candidate alignment score
      - Dimension benchmark comparison & point contributions
      - Per-question candidate responses, scores, and behavioral evidence
      - Targeted recruiter inquiry prompts for follow-up interviews
      - Ethical compliance safeguards
    """
    sid_str = str(session_id)
    rec_id = str(recruiter["id"])

    _verify_session_access(sid_str, rec_id)

    svc = ReportService()
    report = svc.get_assessment_report(sid_str)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report could not be generated for this session.",
        )

    return {"success": True, "data": AssessmentReportRead.model_validate(report)}


# ── GET /jobs/{job_id}/reports/summary ──────────────────────────────────────

@router.get(
    "/jobs/{job_id}/reports/summary",
    status_code=status.HTTP_200_OK,
    summary="Get candidate assessment summaries for a job",
    response_description="List of candidate assessment summaries for dashboard.",
)
def get_job_reports_summary(
    job_id: UUID,
    recruiter: dict = Depends(require_recruiter),
):
    """
    Retrieve candidate summaries across all assessment sessions for a job.
    Used on the recruiter dashboard for applicant comparison and rankings.
    """
    jid_str = str(job_id)
    rec_id = str(recruiter["id"])

    _verify_job_ownership(jid_str, rec_id)

    svc = ReportService()
    summaries = svc.get_job_reports_summary(jid_str)
    validated = [SessionReportSummaryItem.model_validate(s) for s in summaries]

    return {"success": True, "data": validated}
