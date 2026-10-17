"""
schemas/dimensions.py
Pydantic models for behavioral dimensions, indicators, and framework versioning.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

class IndicatorRead(BaseModel):
    """A single observable indicator within a behavioral dimension."""
    id: UUID
    dimension_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    example_behaviors: Optional[str] = None
    order_index: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class IndicatorCreate(BaseModel):
    """Payload to create an observable indicator."""
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field(..., min_length=5)
    example_behaviors: Optional[str] = None
    order_index: int = 0

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        cleaned = v.strip().lower().replace(" ", "_").replace("-", "_")
        if not re.match(r"^[a-z][a-z0-9_]{0,63}$", cleaned):
            raise ValueError(
                "Indicator name must start with a letter and contain only lowercase letters, digits, and underscores"
            )
        return cleaned


class IndicatorUpdate(BaseModel):
    """Payload to update an observable indicator."""
    name: Optional[str] = None
    description: Optional[str] = None
    example_behaviors: Optional[str] = None
    is_active: Optional[bool] = None
    order_index: Optional[int] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip().lower().replace(" ", "_").replace("-", "_")
        if not re.match(r"^[a-z][a-z0-9_]{0,63}$", cleaned):
            raise ValueError(
                "Indicator name must start with a letter and contain only lowercase letters, digits, and underscores"
            )
        return cleaned


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

class DimensionRead(BaseModel):
    """A behavioral dimension, without its indicators (list view)."""
    id: UUID
    name: str
    description: Optional[str] = None
    is_active: bool = True
    status: str = "active"
    order_index: int = 0
    indicator_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DimensionDetail(DimensionRead):
    """A behavioral dimension with its full list of indicators (detail view)."""
    indicators: List[IndicatorRead] = []
    is_referenced: Optional[bool] = False
    referenced_jobs_count: Optional[int] = 0


class DimensionCreate(BaseModel):
    """Payload to create a new behavioral dimension."""
    name: str = Field(..., min_length=2, max_length=64)
    description: str = Field(..., min_length=10)
    is_active: bool = True
    status: str = "active"
    order_index: int = 0
    initial_indicators: List[IndicatorCreate] = []

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        cleaned = v.strip().lower().replace(" ", "_").replace("-", "_")
        if not re.match(r"^[a-z][a-z0-9_]{0,63}$", cleaned):
            raise ValueError(
                "Dimension name must start with a letter and contain only lowercase letters, digits, and underscores"
            )
        return cleaned


class DimensionUpdate(BaseModel):
    """Payload to update an existing behavioral dimension."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None
    order_index: Optional[int] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip().lower().replace(" ", "_").replace("-", "_")
        if not re.match(r"^[a-z][a-z0-9_]{0,63}$", cleaned):
            raise ValueError(
                "Dimension name must start with a letter and contain only lowercase letters, digits, and underscores"
            )
        return cleaned


class DimensionReorderItem(BaseModel):
    """Single item in a reorder request."""
    id: UUID
    order_index: int


class FrameworkReorderPayload(BaseModel):
    """Payload to update order indexes for multiple dimensions."""
    items: List[DimensionReorderItem]


# ---------------------------------------------------------------------------
# Framework Validation & Versioning
# ---------------------------------------------------------------------------

class FrameworkValidationResult(BaseModel):
    """Result of validating the current draft/active framework state."""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    active_dimension_count: int
    total_indicator_count: int


class FrameworkVersionPublish(BaseModel):
    """Payload to publish and activate a new framework version."""
    name: str = Field(..., min_length=3, max_length=150)
    description: Optional[str] = None


class FrameworkVersionRead(BaseModel):
    """Framework version metadata with frozen snapshot."""
    id: UUID
    version_number: int
    name: str
    description: Optional[str] = None
    status: str
    dimensions_snapshot: List[Dict[str, Any]] = []
    created_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
