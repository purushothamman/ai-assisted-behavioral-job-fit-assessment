"""
services/job_service.py
Business logic for job CRUD.
All database interaction goes through the Supabase admin client.
RLS is enforced at the DB level; this service also filters by recruiter_id
as a defence-in-depth measure.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.db.client import get_supabase_admin
from app.schemas.jobs import JobCreate, JobStatus, JobUpdate

logger = logging.getLogger(__name__)


def _now() -> str:
    """ISO timestamp for updated_at fields."""
    return datetime.now(timezone.utc).isoformat()


class JobService:
    """Stateless service — one instance per request is fine."""

    def __init__(self) -> None:
        self._db = get_supabase_admin()

    # ── Create ────────────────────────────────────────────────────────────────

    def create_job(self, recruiter_id: str, payload: JobCreate) -> dict:
        """Insert a new job and return the full record."""
        data = {
            "recruiter_id": recruiter_id,
            "title": payload.title,
            "description": payload.description,
            "responsibilities": payload.responsibilities,
            "requirements": payload.requirements,
            "status": JobStatus.DRAFT.value,
        }
        result = (
            self._db.table("jobs")
            .insert(data)
            .execute()
        )
        self._raise_if_error(result)
        return result.data[0]

    # ── Read (single) ─────────────────────────────────────────────────────────

    def get_job(self, job_id: str, recruiter_id: Optional[str] = None) -> Optional[dict]:
        """Return a single job or None if not found / not owned by recruiter."""
        query = self._db.table("jobs").select("*").eq("id", job_id)
        if recruiter_id:
            query = query.eq("recruiter_id", recruiter_id)
        result = query.maybe_single().execute()
        if result is None:
            return None
        self._raise_if_error(result)
        return result.data

    # ── Read (list) ───────────────────────────────────────────────────────────

    def list_jobs(self, recruiter_id: str) -> list[dict]:
        """Return all jobs belonging to this recruiter, newest first."""
        result = (
            self._db.table("jobs")
            .select("id, title, status, created_at")
            .eq("recruiter_id", recruiter_id)
            .order("created_at", desc=True)
            .execute()
        )
        self._raise_if_error(result)
        return result.data or []

    # ── Update ────────────────────────────────────────────────────────────────

    def update_job(self, job_id: str, recruiter_id: str, payload: JobUpdate) -> Optional[dict]:
        """
        Partial update. Returns the updated record or None if not found.
        Only non-None fields are included in the PATCH.
        """
        update_data = payload.model_dump(exclude_none=True)
        if not update_data:
            # Nothing to update — return current record
            return self.get_job(job_id, recruiter_id)

        update_data["updated_at"] = _now()

        result = (
            self._db.table("jobs")
            .update(update_data)
            .eq("id", job_id)
            .eq("recruiter_id", recruiter_id)
            .execute()
        )
        self._raise_if_error(result)
        return result.data[0] if result.data else None

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete_job(self, job_id: str, recruiter_id: str) -> bool:
        """Hard-delete a job. Returns True if a row was deleted."""
        result = (
            self._db.table("jobs")
            .delete()
            .eq("id", job_id)
            .eq("recruiter_id", recruiter_id)
            .execute()
        )
        self._raise_if_error(result)
        return bool(result.data)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _raise_if_error(result) -> None:
        """Raise a RuntimeError if the Supabase response indicates an error."""
        # supabase-py v2 raises exceptions internally on HTTP errors,
        # but we add a belt-and-suspenders check.
        if hasattr(result, "error") and result.error:
            logger.error("Supabase error: %s", result.error)
            raise RuntimeError(str(result.error))
