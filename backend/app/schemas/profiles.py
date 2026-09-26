"""
schemas/profiles.py
Pydantic models for user profile read operations.
Profiles are created automatically when a recruiter registers via Supabase Auth.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class ProfileRead(BaseModel):
    id: UUID
    role: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
