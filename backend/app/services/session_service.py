"""
services/session_service.py
Business logic for interview_sessions and candidate_responses (Phase 5).

Flow:
  1. Recruiter: POST /api/jobs/{id}/sessions
     -> creates interview_sessions row with a UUID token + expiry
  2. Candidate: GET /api/sessions/{token}
     -> fetch session (check token valid, not expired, not completed)
     -> return job context + approved questions
  3. Candidate: POST /api/sessions/{token}/responses
     -> save all answers to candidate_responses
     -> mark session status = 'completed', record submitted_at
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.schemas.sessions import ResponseCreate, SessionCreate
from app.schemas.alignment import SessionReviewPayload
from app.db.client import get_supabase_admin

logger = logging.getLogger(__name__)


class SessionService:
    """Stateless service — one instance per request is fine."""

    def __init__(self) -> None:
        self._db = get_supabase_admin()

    # ── Create a session ─────────────────────────────────────────────────────

    def create_session(self, job_id: str, payload: SessionCreate) -> dict:
        """
        Create a new candidate interview session with a UUID access token.
        Binds the job's current framework_version_id to the session so that
        all scoring and reporting remain anchored to the frozen snapshot that
        was active when the session was created (FS-2).
        Returns the created session row.
        """
        token = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)

        # FS-2: Resolve the job's pinned framework version to freeze at session level.
        framework_version_id: Optional[str] = None
        try:
            job_res = (
                self._db.table("jobs")
                .select("framework_version_id")
                .eq("id", job_id)
                .limit(1)
                .execute()
            )
            if job_res and job_res.data:
                framework_version_id = (job_res.data[0] or {}).get("framework_version_id")
        except Exception as exc:
            logger.debug("Could not read job.framework_version_id for session creation: %s", exc)

        session_data: dict = {
            "job_id":          job_id,
            "token":           token,
            "candidate_name":  payload.candidate_name,
            "candidate_email": payload.candidate_email,
            "status":          "pending",
            "expires_at":      expires_at.isoformat(),
        }
        if framework_version_id:
            session_data["framework_version_id"] = framework_version_id

        result = (
            self._db.table("interview_sessions")
            .insert(session_data)
            .execute()
        )
        self._raise_if_error(result)
        if not result.data:
            raise RuntimeError("Failed to create interview session.")
        data = dict(result.data[0])
        data.setdefault("email_status", "pending")
        return data

    # ── Update email status ──────────────────────────────────────────────────

    def update_email_status(self, session_id: str, email_status: str) -> bool:
        """
        Update the email_status field of a session (pending/sent/failed).
        Gracefully handles environments where the database column is not yet migrated.
        """
        try:
            self._db.table("interview_sessions").update({
                "email_status": email_status
            }).eq("id", session_id).execute()
            return True
        except Exception as exc:
            logger.warning("Could not persist email_status to database: %s", exc)
            return False

    # ── Get session by ID ───────────────────────────────────────────────────

    def get_session(self, session_id: str) -> Optional[dict]:
        """Fetch a session row by its ID."""
        result = (
            self._db.table("interview_sessions")
            .select("*")
            .eq("id", session_id)
            .maybe_single()
            .execute()
        )
        self._raise_if_error(result)
        if not result.data:
            return None
        data = dict(result.data)
        data.setdefault("email_status", "pending")
        return data

    # ── List sessions for a job ──────────────────────────────────────────────

    def list_sessions(self, job_id: str) -> List[dict]:
        """Return all sessions for a job, newest first."""
        result = (
            self._db.table("interview_sessions")
            .select("*")
            .eq("job_id", job_id)
            .order("created_at", desc=True)
            .execute()
        )
        self._raise_if_error(result)
        sessions = []
        for row in (result.data or []):
            item = dict(row)
            item.setdefault("email_status", "pending")
            sessions.append(item)
        return sessions

    # ── Get public session by token ─────────────────────────────────────────

    def get_session_by_token(self, token: str) -> Optional[dict]:
        """
        Fetch a session row by its UUID token.
        Returns None if not found.
        Does NOT enforce expiry here — API layer handles that.
        """
        result = (
            self._db.table("interview_sessions")
            .select("*")
            .eq("token", token)
            .maybe_single()
            .execute()
        )
        self._raise_if_error(result)
        if not result.data:
            return None
        data = dict(result.data)
        data.setdefault("email_status", "pending")
        return data

    # ── Get approved questions for a session's job ──────────────────────────

    def get_approved_questions(self, job_id: str) -> List[dict]:
        """
        Return only approved questions for the job, enriched with dimension_name.
        """
        import json

        result = (
            self._db.table("interview_questions")
            .select("id, job_id, dimension_id, question, type, difficulty, indicators")
            .eq("job_id", job_id)
            .eq("approved", True)
            .order("created_at", desc=False)
            .execute()
        )
        self._raise_if_error(result)
        rows = result.data or []

        if not rows:
            return []

        # Enrich with dimension names
        dim_ids = list({r["dimension_id"] for r in rows})
        dim_result = (
            self._db.table("behavioral_dimensions")
            .select("id, name")
            .in_("id", dim_ids)
            .execute()
        )
        self._raise_if_error(dim_result)
        dim_map = {d["id"]: d["name"] for d in (dim_result.data or [])}

        for row in rows:
            row["dimension_name"] = dim_map.get(row["dimension_id"])
            if isinstance(row.get("indicators"), str):
                try:
                    row["indicators"] = json.loads(row["indicators"])
                except json.JSONDecodeError:
                    row["indicators"] = []

        return rows

    # ── Get job info ────────────────────────────────────────────────────────

    def get_job_public(self, job_id: str) -> Optional[dict]:
        """Fetch minimal public job info (title + description)."""
        result = (
            self._db.table("jobs")
            .select("id, title, description")
            .eq("id", job_id)
            .maybe_single()
            .execute()
        )
        self._raise_if_error(result)
        return result.data

    # ── Submit candidate responses ──────────────────────────────────────────

    def submit_responses(
        self,
        session_id: str,
        responses: List[ResponseCreate],
    ) -> List[dict]:
        """
        Insert all candidate responses and mark the session as completed.
        Returns the list of saved response rows.
        """
        rows = [
            {
                "session_id":  session_id,
                "question_id": str(r.question_id),
                "answer":      r.answer,
            }
            for r in responses
        ]

        result = (
            self._db.table("candidate_responses")
            .insert(rows)
            .execute()
        )
        self._raise_if_error(result)

        # Mark session completed
        submitted_at = datetime.now(timezone.utc).isoformat()
        upd_result = (
            self._db.table("interview_sessions")
            .update({"status": "completed", "submitted_at": submitted_at})
            .eq("id", session_id)
            .execute()
        )
        self._raise_if_error(upd_result)

        return result.data or []

    # ── Mark session in_progress ────────────────────────────────────────────

    def mark_in_progress(self, session_id: str) -> None:
        """Set session status to in_progress when candidate opens the link."""
        result = (
            self._db.table("interview_sessions")
            .update({"status": "in_progress"})
            .eq("id", session_id)
            .eq("status", "pending")    # only advance from pending
            .execute()
        )
        self._raise_if_error(result)

    # ── Recruiter Review & Oversight (Phase D: OV-2, OV-3, OV-4, OV-5) ────────

    def review_session(
        self,
        session_id: str,
        reviewer_id: str,
        reviewer_role: str,
        payload: SessionReviewPayload,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> dict:
        """
        Record a recruiter oversight review for an interview session.
        Enforces tenant isolation, validates allowed review actions, preserves
        authoritative scores, records override scores and recruiter notes,
        detects repeated reviews, and writes an auditable event to audit_logs.
        """
        from app.services.alignment_service import AlignmentService
        from app.services.audit_service import AuditService
        from app.services.job_service import JobService
        from fastapi import HTTPException, status

        ALLOWED_ACTIONS = {"reviewed", "flagged_for_interview", "request_reassessment", "overridden", "completed"}
        action = payload.resolved_action
        if action not in ALLOWED_ACTIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid review action '{action}'. Must be one of: {sorted(list(ALLOWED_ACTIONS))}",
            )

        session = self.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")

        job_id = str(session["job_id"])
        job = JobService().get_job(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated job not found.")

        # Tenant isolation: recruiters can only review sessions for jobs they own
        if reviewer_role != "admin" and str(job.get("recruiter_id")) != str(reviewer_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to review this candidate session.",
            )

        align_svc = AlignmentService()
        alignment = align_svc.get_alignment(session_id)
        if not alignment and session.get("status") == "completed":
            try:
                alignment = align_svc.calculate_and_save_alignment(session_id)
            except Exception as exc:
                logger.warning("Could not auto-calculate alignment for session %s: %s", session_id, exc)

        if not alignment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot review an assessment session before candidate scores and alignments are calculated.",
            )

        is_repeated = bool(alignment.get("reviewed_at"))
        prev_action = alignment.get("review_action")
        prev_reviewer = alignment.get("reviewed_by")

        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        notes = payload.resolved_notes
        override_score = payload.override_score

        # Update session_alignments with reviewer decision and notes
        update_data = {
            "reviewed_at": now_iso,
            "reviewed_by": str(reviewer_id),
            "review_action": action,
            "recruiter_notes": notes,
            "override_score": float(override_score) if override_score is not None else None,
        }

        try:
            upd_res = (
                self._db.table("session_alignments")
                .update(update_data)
                .eq("session_id", session_id)
                .execute()
            )
            self._raise_if_error(upd_res)
        except Exception as exc:
            logger.warning("DB update on session_alignments failed (using fallback): %s", exc)

        # Log audit event (redacting any credentials/passwords/tokens)
        audit_entry = AuditService().log_event(
            action="assessment.reviewed",
            entity_type="assessment_session",
            entity_id=session_id,
            user_id=reviewer_id,
            user_role=reviewer_role,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "session_id": session_id,
                "job_id": job_id,
                "review_action": action,
                "original_overall_score": float(alignment.get("overall_score", 0.0)),
                "override_score": float(override_score) if override_score is not None else None,
                "recruiter_notes_length": len(notes) if notes else 0,
                "is_repeated_review": is_repeated,
                "previous_action": prev_action,
                "previous_reviewer": str(prev_reviewer) if prev_reviewer else None,
            },
        )
        audit_log_id = audit_entry.get("id") if audit_entry else None

        return {
            "session_id": uuid.UUID(session_id),
            "reviewed_at": now_dt,
            "reviewed_by": uuid.UUID(reviewer_id) if isinstance(reviewer_id, str) and "-" in reviewer_id and len(reviewer_id) == 36 else reviewer_id,
            "review_action": action,
            "recruiter_notes": notes,
            "original_score": float(alignment.get("overall_score", 0.0)),
            "override_score": float(override_score) if override_score is not None else None,
            "audit_log_id": uuid.UUID(audit_log_id) if isinstance(audit_log_id, str) and "-" in audit_log_id and len(audit_log_id) == 36 else audit_log_id,
            "is_repeated_review": is_repeated,
        }

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _raise_if_error(result) -> None:
        if hasattr(result, "error") and result.error:
            logger.error("Supabase error: %s", result.error)
            raise RuntimeError(str(result.error))
