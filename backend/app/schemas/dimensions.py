"""
schemas/dimensions.py
Pydantic models for behavioral dimensions and indicators (read-only seed data).
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

class IndicatorRead(BaseModel):
    """A single observable indicator within a behavioral dimension."""
    id: UUID
    dimension_id: UUID
    name: str
    description: Optional[str] = None
    example_behaviors: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

class DimensionRead(BaseModel):
    """A behavioral dimension, without its indicators (list view)."""
    id: UUID
    name: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DimensionDetail(DimensionRead):
    """A behavioral dimension with its full list of indicators (detail view)."""
    indicators: List[IndicatorRead] = []
