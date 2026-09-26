"""
schemas/common.py
Shared base types and response wrappers used across all schema modules.
"""
from __future__ import annotations

from datetime import datetime
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel

DataT = TypeVar("DataT")


class APIResponse(BaseModel, Generic[DataT]):
    """Standard envelope for all API responses."""
    success: bool = True
    message: str = "OK"
    data: Optional[DataT] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    detail: Optional[str] = None


class TimestampMixin(BaseModel):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UUIDMixin(BaseModel):
    id: Optional[UUID] = None
