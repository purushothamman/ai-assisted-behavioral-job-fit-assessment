"""
core/security.py
Validates Supabase-issued JWTs and extracts the current user's identity.
Supabase JWTs are signed with the project's JWT secret (SUPABASE_ANON_KEY
acts as the audience, the service-role key signs). In practice Supabase uses
HS256 with the jwt_secret from the project settings.

For Phase 1 we rely on Supabase's own verify endpoint to keep things simple
and avoid having to manage the raw JWT secret.  The decode is intentionally
done via the supabase-py admin client so we stay inside the SDK.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.client import get_supabase_admin

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> dict:
    """
    Dependency that validates a Bearer token issued by Supabase Auth.
    Returns the decoded user dict on success.
    Raises HTTP 401 on failure.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        client = get_supabase_admin()
        response = client.auth.get_user(token)
        if response is None or response.user is None:
            raise ValueError("No user returned")
        role = (response.user.user_metadata or {}).get("role")
        if not role:
            try:
                prof_res = (
                    client.table("profiles")
                    .select("role")
                    .eq("id", response.user.id)
                    .maybe_single()
                    .execute()
                )
                if prof_res and prof_res.data:
                    role = prof_res.data.get("role", "recruiter")
            except Exception:
                role = "recruiter"

        return {
            "id": response.user.id,
            "email": response.user.email,
            "role": role or "recruiter",
        }
    except Exception as exc:
        logger.warning("Token validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_recruiter(user: dict = Security(get_current_user)) -> dict:
    """
    Dependency that additionally asserts the caller is a recruiter or admin.
    """
    if user.get("role") not in ("recruiter", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recruiter access required",
        )
    return user


async def require_admin(user: dict = Security(get_current_user)) -> dict:
    """
    Dependency that asserts the caller is an authorized platform administrator.
    Recruiters and other roles are strictly forbidden.
    """
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user

