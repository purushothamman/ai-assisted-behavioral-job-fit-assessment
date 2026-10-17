"""
ai/schemas.py
Pydantic models for Groq input/output in the job-analysis pipeline.
All models are validated BEFORE data is written to Supabase.
"""
from __future__ import annotations

import logging
from typing import List, Set
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

DEFAULT_DIMENSIONS: Set[str] = {
    "communication", "teamwork", "adaptability",
    "decision_making", "leadership", "stress_management",
}

# Dynamic registry for custom dimensions loaded or created in the framework
_DYNAMIC_DIMENSIONS: Set[str] = set()


def register_valid_dimension(name: str) -> None:
    """Register a custom dimension name in the runtime validator registry."""
    cleaned = name.strip().lower().replace(" ", "_").replace("-", "_")
    if cleaned:
        _DYNAMIC_DIMENSIONS.add(cleaned)


def get_all_valid_dimensions() -> Set[str]:
    """Return union of default, dynamic, and database behavioral dimension names."""
    valid = set(DEFAULT_DIMENSIONS) | _DYNAMIC_DIMENSIONS
    try:
        from app.db.client import get_supabase_admin
        db = get_supabase_admin()
        res = db.table("behavioral_dimensions").select("name").execute()
        if res and res.data:
            for row in res.data:
                name = (row.get("name") or "").strip().lower()
                if name:
                    valid.add(name)
    except Exception:
        pass
    return valid


# ---------------------------------------------------------------------------
# Job Analyzer — output schema
# ---------------------------------------------------------------------------

class DimensionRequirement(BaseModel):
    """
    One behavioral requirement extracted by Groq from a job description.
    Maps to a row in the job_requirements table.
    """
    dimension: str = Field(
        ...,
        description="Behavioral dimension name from the active framework.",
    )
    importance: int = Field(
        ...,
        ge=0,
        le=100,
        description="Importance of this dimension for the role (0–100).",
    )
    reason: str = Field(
        ...,
        min_length=10,
        description="Short explanation of why this dimension matters for the role.",
    )

    @field_validator("dimension")
    @classmethod
    def validate_dimension(cls, v: str) -> str:
        normalised = v.strip().lower().replace(" ", "_").replace("-", "_")
        valid = get_all_valid_dimensions()
        if normalised not in valid:
            raise ValueError(
                f"Unknown dimension '{v}'. Must be one of: {sorted(valid)}"
            )
        return normalised

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("reason must not be blank")
        return v.strip()


class JobAnalysisOutput(BaseModel):
    """Top-level Groq response for the job-analysis prompt."""
    requirements: List[DimensionRequirement] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="One entry per relevant behavioral dimension.",
    )
