"""
services/profile_service.py
Business logic for recruiter profile management.
Profiles are created by the DB trigger on auth.users insertion;
this service provides read/update only.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.db.client import get_supabase_admin

logger = logging.getLogger(__name__)


class ProfileService:

    def __init__(self) -> None:
        self._db = get_supabase_admin()

    def get_profile(self, user_id: str) -> Optional[dict]:
        """Return the recruiter's profile row, or None if not found."""
        result = (
            self._db.table("profiles")
            .select("*")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        return result.data

    def upsert_profile(self, user_id: str, email: str, role: str = "recruiter") -> dict:
        """
        Create the profile if it doesn't exist yet, or return existing.
        Called after successful Supabase Auth sign-up to ensure the row exists.
        """
        result = (
            self._db.table("profiles")
            .upsert(
                {"id": user_id, "role": role},
                on_conflict="id",
                ignore_duplicates=False,
            )
            .execute()
        )
        return result.data[0] if result.data else {}

    def update_profile(self, user_id: str, full_name: str) -> Optional[dict]:
        """Update the full_name field for the recruiter's profile."""
        result = (
            self._db.table("profiles")
            .update({"full_name": full_name})
            .eq("id", user_id)
            .execute()
        )
        return result.data[0] if result.data else None
