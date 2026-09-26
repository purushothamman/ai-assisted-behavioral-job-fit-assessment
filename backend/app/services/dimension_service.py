"""
services/dimension_service.py
Business logic for reading behavioral dimensions and indicators.

These tables are seeded, read-only (from the application's perspective),
and have a public-read RLS policy, so we use the admin client for consistency
with other services, but the anon client would also work for SELECT-only ops.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from app.db.client import get_supabase_admin
from app.schemas.dimensions import DimensionDetail, DimensionRead, IndicatorRead

logger = logging.getLogger(__name__)


class DimensionService:
    """Stateless service — one instance per request is fine."""

    def __init__(self) -> None:
        self._db = get_supabase_admin()

    # ── List all dimensions ────────────────────────────────────────────────

    def list_dimensions(self, active_only: bool = True) -> list[dict]:
        """
        Return all behavioral dimensions, ordered by name.
        If active_only=True (default), filters to is_active=True rows only.
        """
        query = (
            self._db.table("behavioral_dimensions")
            .select("id, name, description, is_active, created_at")
            .order("name")
        )
        if active_only:
            query = query.eq("is_active", True)

        result = query.execute()
        self._raise_if_error(result)
        return result.data or []

    # ── Get single dimension with indicators ───────────────────────────────

    def get_dimension(self, dimension_id: str) -> Optional[dict]:
        """
        Return a single dimension with its indicators embedded.
        Returns None if the dimension is not found.
        """
        # 1. Fetch the dimension row
        dim_result = (
            self._db.table("behavioral_dimensions")
            .select("id, name, description, is_active, created_at")
            .eq("id", dimension_id)
            .maybe_single()
            .execute()
        )
        self._raise_if_error(dim_result)
        if not dim_result.data:
            return None

        dimension = dim_result.data

        # 2. Fetch its indicators
        ind_result = (
            self._db.table("behavioral_indicators")
            .select("id, dimension_id, name, description, example_behaviors, created_at")
            .eq("dimension_id", dimension_id)
            .order("name")
            .execute()
        )
        self._raise_if_error(ind_result)
        dimension["indicators"] = ind_result.data or []

        return dimension

    # ── Get dimension by name (utility for Phase 3+) ───────────────────────

    def get_dimension_by_name(self, name: str) -> Optional[dict]:
        """
        Return a single dimension (with indicators) matched by name.
        Useful when Groq returns dimension names rather than UUIDs.
        """
        dim_result = (
            self._db.table("behavioral_dimensions")
            .select("id, name, description, is_active, created_at")
            .eq("name", name)
            .maybe_single()
            .execute()
        )
        self._raise_if_error(dim_result)
        if not dim_result.data:
            return None

        return self.get_dimension(str(dim_result.data["id"]))

    # ── Get indicators for a dimension (utility for Phase 7+) ─────────────

    def list_indicators(self, dimension_id: str) -> list[dict]:
        """
        Return all indicators for a given dimension, ordered by name.
        Used by the NLP pipeline to build indicator embeddings.
        """
        result = (
            self._db.table("behavioral_indicators")
            .select("id, dimension_id, name, description, example_behaviors, created_at")
            .eq("dimension_id", dimension_id)
            .order("name")
            .execute()
        )
        self._raise_if_error(result)
        return result.data or []

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _raise_if_error(result) -> None:
        """Raise a RuntimeError if the Supabase response indicates an error."""
        if hasattr(result, "error") and result.error:
            logger.error("Supabase error: %s", result.error)
            raise RuntimeError(str(result.error))
