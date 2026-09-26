"""
services/question_service.py
Business logic for interview_questions: save AI output, list, update, delete.

Flow:
  1. Recruiter triggers POST /api/jobs/{id}/questions/generate
  2. API layer calls question_generator.generate_questions() -> List[GeneratedQuestion]
  3. This service resolves dimension_id from dimension name, inserts rows into
     interview_questions (fresh insert — generate replaces previous batch).
  4. GET /api/jobs/{id}/questions  -> recruiter reviews and approves
  5. PATCH /api/questions/{id}     -> recruiter edits / approves a question
  6. DELETE /api/questions/{id}    -> recruiter removes a question
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

from app.ai.question_schemas import GeneratedQuestion
from app.db.client import get_supabase_admin

logger = logging.getLogger(__name__)


class QuestionService:
    """Stateless service — one instance per request is fine."""

    def __init__(self) -> None:
        self._db = get_supabase_admin()

    # ── Resolve dimension name -> UUID ──────────────────────────────────────

    def _get_dimension_id(self, name: str) -> Optional[str]:
        """Return the UUID of a behavioral dimension by name, or None."""
        result = (
            self._db.table("behavioral_dimensions")
            .select("id")
            .eq("name", name)
            .maybe_single()
            .execute()
        )
        self._raise_if_error(result)
        return result.data["id"] if result.data else None

    # ── Save generated questions ────────────────────────────────────────────

    def save_questions(
        self,
        job_id: str,
        questions: List[GeneratedQuestion],
    ) -> List[dict]:
        """
        Delete previous questions for the job, then insert the new batch.
        Returns the full list of saved rows enriched with dimension_name.
        """
        # Delete previous batch (re-generate replaces)
        del_result = (
            self._db.table("interview_questions")
            .delete()
            .eq("job_id", job_id)
            .execute()
        )
        self._raise_if_error(del_result)

        rows_to_insert = []
        for q in questions:
            dim_id = self._get_dimension_id(q.dimension)
            if not dim_id:
                logger.warning(
                    "Dimension '%s' not found in DB — skipping question.", q.dimension
                )
                continue
            rows_to_insert.append({
                "job_id":       job_id,
                "dimension_id": dim_id,
                "question":     q.question,
                "type":         q.type,
                "difficulty":   q.difficulty,
                "indicators":   json.dumps(q.indicators),   # stored as JSONB / text
                "approved":     False,
            })

        if not rows_to_insert:
            raise RuntimeError("No valid questions could be saved (dimension IDs missing).")

        result = (
            self._db.table("interview_questions")
            .insert(rows_to_insert)
            .execute()
        )
        self._raise_if_error(result)

        return self.list_questions(job_id)

    # ── List questions for a job ────────────────────────────────────────────

    def list_questions(self, job_id: str) -> List[dict]:
        """
        Return all question rows for a job, enriched with dimension_name,
        ordered by dimension_id then created_at.
        """
        result = (
            self._db.table("interview_questions")
            .select("id, job_id, dimension_id, question, type, difficulty, indicators, approved, created_at")
            .eq("job_id", job_id)
            .order("created_at", desc=False)
            .execute()
        )
        self._raise_if_error(result)
        rows = result.data or []

        if not rows:
            return []

        # Enrich with dimension names in one query
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
            # Deserialize indicators if stored as JSON string
            if isinstance(row.get("indicators"), str):
                try:
                    row["indicators"] = json.loads(row["indicators"])
                except json.JSONDecodeError:
                    row["indicators"] = []

        return rows

    # ── Update (edit / approve) a single question ───────────────────────────

    def update_question(
        self,
        question_id: str,
        job_id: str,
        update_data: dict,
    ) -> Optional[dict]:
        """
        Partial update of an interview_questions row.
        job_id is used as an ownership check.
        Returns the updated row enriched with dimension_name, or None if not found.
        """
        if not update_data:
            return self._get_question(question_id, job_id)

        # Serialize indicators list -> JSON if present
        if "indicators" in update_data and isinstance(update_data["indicators"], list):
            update_data = {**update_data, "indicators": json.dumps(update_data["indicators"])}

        result = (
            self._db.table("interview_questions")
            .update(update_data)
            .eq("id", question_id)
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

        # Deserialize indicators
        if isinstance(row.get("indicators"), str):
            try:
                row["indicators"] = json.loads(row["indicators"])
            except json.JSONDecodeError:
                row["indicators"] = []

        return row

    # ── Delete a single question ────────────────────────────────────────────

    def delete_question(self, question_id: str, job_id: str) -> bool:
        """
        Delete a single question. job_id is the ownership check.
        Returns True if deleted, False if not found.
        """
        result = (
            self._db.table("interview_questions")
            .delete()
            .eq("id", question_id)
            .eq("job_id", job_id)
            .execute()
        )
        self._raise_if_error(result)
        return bool(result.data)

    # ── Single-row fetch helper ─────────────────────────────────────────────

    def _get_question(self, question_id: str, job_id: str) -> Optional[dict]:
        """Fetch a single question by id + job_id ownership check."""
        result = (
            self._db.table("interview_questions")
            .select("id, job_id, dimension_id, question, type, difficulty, indicators, approved, created_at")
            .eq("id", question_id)
            .eq("job_id", job_id)
            .maybe_single()
            .execute()
        )
        self._raise_if_error(result)
        row = result.data
        if row and isinstance(row.get("indicators"), str):
            try:
                row["indicators"] = json.loads(row["indicators"])
            except json.JSONDecodeError:
                row["indicators"] = []
        return row

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _raise_if_error(result) -> None:
        if hasattr(result, "error") and result.error:
            logger.error("Supabase error: %s", result.error)
            raise RuntimeError(str(result.error))
