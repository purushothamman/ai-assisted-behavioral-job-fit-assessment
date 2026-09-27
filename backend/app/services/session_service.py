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
        Returns the created session row.
        """
        token = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)

        result = (
            self._db.table("interview_sessions")
            .insert({
                "job_id":          job_id,
                "token":           token,
                "candidate_name":  payload.candidate_name,
                "candidate_email": payload.candidate_email,
                "status":          "pending",
                "expires_at":      expires_at.isoformat(),
            })
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

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _raise_if_error(result) -> None:
        if hasattr(result, "error") and result.error:
            logger.error("Supabase error: %s", result.error)
            raise RuntimeError(str(result.error))
