"""
services/job_requirement_service.py
Business logic for job_requirements: save AI output, list, confirm/edit.

Flow:
  1. Recruiter triggers POST /api/jobs/{id}/analyze
  2. API layer calls job_analyzer.analyze_job() -> List[DimensionRequirement]
  3. This service resolves dimension_id from the dimension name, then upserts
     rows into job_requirements (one per dimension).
  4. GET /api/jobs/{id}/requirements -> recruiter reviews list
  5. PATCH /api/jobs/{id}/requirements/{req_id} -> recruiter confirms/edits
"""
from __future__ import annotations

import logging
from typing import List, Optional

from app.ai.schemas import DimensionRequirement
from app.db.client import get_supabase_admin

logger = logging.getLogger(__name__)


class JobRequirementService:
    """Stateless service — one instance per request is fine."""

    def __init__(self) -> None:
        self._db = get_supabase_admin()

    # ── Resolve dimension name -> UUID ─────────────────────────────────────

    def _get_dimension_id(self, name: str) -> Optional[str]:
        """
        Look up a behavioral dimension by name and return its UUID string.
        Returns None if not found (should not happen with seeded data).
        """
        result = (
            self._db.table("behavioral_dimensions")
            .select("id")
            .eq("name", name)
            .maybe_single()
            .execute()
        )
        self._raise_if_error(result)
        return result.data["id"] if result.data else None

    # ── Save Groq output ───────────────────────────────────────────────────

    def save_requirements(
        self,
        job_id: str,
        requirements: List[DimensionRequirement],
    ) -> List[dict]:
        """
        Upsert one job_requirements row per dimension.
        Existing rows for the same (job_id, dimension_id) are replaced.
        Returns the full list of saved rows (with dimension_name joined).
        """
        rows_to_upsert = []
        for req in requirements:
            dim_id = self._get_dimension_id(req.dimension)
            if not dim_id:
                logger.warning(
                    "Dimension '%s' not found in DB — skipping.", req.dimension
                )
                continue
            rows_to_upsert.append({
                "job_id":       job_id,
                "dimension_id": dim_id,
                "importance":   req.importance,
                "reason":       req.reason,
                "confirmed":    False,
            })

        if not rows_to_upsert:
            raise RuntimeError("No valid dimensions were returned by Groq.")

        result = (
            self._db.table("job_requirements")
            .upsert(rows_to_upsert, on_conflict="job_id,dimension_id")
            .execute()
        )
        self._raise_if_error(result)

        # Return enriched list (with dimension name)
        return self.list_requirements(job_id)

    # ── List requirements for a job ────────────────────────────────────────

    def list_requirements(self, job_id: str) -> List[dict]:
        """
        Return all requirement rows for a job, enriched with dimension name,
        ordered by importance descending.
        """
        # Fetch requirements
        result = (
            self._db.table("job_requirements")
            .select("id, job_id, dimension_id, importance, reason, confirmed, created_at")
            .eq("job_id", job_id)
            .order("importance", desc=True)
            .execute()
        )
        self._raise_if_error(result)
        rows = result.data or []

        if not rows:
            return []

        # Enrich: fetch dimension names in one query
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

        return rows

    # ── Confirm / edit a single requirement ───────────────────────────────

    def update_requirement(
        self,
        req_id: str,
        job_id: str,
        update_data: dict,
    ) -> Optional[dict]:
        """
        Partial update of a job_requirements row.
        job_id is used as a defence-in-depth ownership check.
        Returns the updated row (enriched), or None if not found.
        """
        if not update_data:
            return self._get_requirement(req_id, job_id)

        result = (
            self._db.table("job_requirements")
            .update(update_data)
            .eq("id", req_id)
            .eq("job_id", job_id)
            .execute()
        )
        self._raise_if_error(result)
        if not result.data:
            return None

        row = result.data[0]
        # Enrich with dimension name
        dim_result = (
            self._db.table("behavioral_dimensions")
            .select("name")
            .eq("id", row["dimension_id"])
            .maybe_single()
            .execute()
        )
        self._raise_if_error(dim_result)
        row["dimension_name"] = dim_result.data["name"] if dim_result.data else None

        return row

    def _get_requirement(self, req_id: str, job_id: str) -> Optional[dict]:
        """Fetch a single requirement by id + job_id ownership check."""
        result = (
            self._db.table("job_requirements")
            .select("id, job_id, dimension_id, importance, reason, confirmed, created_at")
            .eq("id", req_id)
            .eq("job_id", job_id)
            .maybe_single()
            .execute()
        )
        self._raise_if_error(result)
        return result.data

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _raise_if_error(result) -> None:
        if hasattr(result, "error") and result.error:
            logger.error("Supabase error: %s", result.error)
            raise RuntimeError(str(result.error))
