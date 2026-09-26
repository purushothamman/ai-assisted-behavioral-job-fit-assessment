"""
api/auth.py
Authentication endpoints.
Supabase handles the actual auth flow; these endpoints provide:
  - /auth/me  : return the current authenticated recruiter's profile
  - /auth/profile : update recruiter's display name
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import require_recruiter
from app.schemas.common import APIResponse
from app.schemas.profiles import ProfileRead, ProfileUpdate
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/me", response_model=APIResponse[ProfileRead])
async def get_me(current_user: dict = Depends(require_recruiter)):
    """
    Return the authenticated recruiter's profile.
    The Supabase JWT is validated in the security dependency.
    """
    svc = ProfileService()

    # Upsert ensures the profile row exists (covers first-login edge case)
    svc.upsert_profile(
        user_id=current_user["id"],
        email=current_user.get("email", ""),
        role=current_user.get("role", "recruiter"),
    )

    profile = svc.get_profile(current_user["id"])
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    # Merge email from JWT (not stored in profiles table)
    profile["email"] = current_user.get("email")

    return APIResponse(data=profile)


@router.patch("/profile", response_model=APIResponse[ProfileRead])
async def update_profile(
    payload: ProfileUpdate,
    current_user: dict = Depends(require_recruiter),
):
    """Update the recruiter's display name."""
    svc = ProfileService()
    if payload.full_name is not None:
        updated = svc.update_profile(current_user["id"], payload.full_name)
        if not updated:
            raise HTTPException(status_code=404, detail="Profile not found")
        updated["email"] = current_user.get("email")
        return APIResponse(data=updated)

    profile = svc.get_profile(current_user["id"])
    profile["email"] = current_user.get("email")
    return APIResponse(data=profile)
