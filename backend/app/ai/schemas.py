"""
ai/schemas.py
Pydantic models for Groq input/output in the job-analysis pipeline.
All models are validated BEFORE data is written to Supabase.
"""
from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field, field_validator


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
        description=(
            "One of: communication, teamwork, adaptability, "
            "decision_making, leadership, stress_management"
        ),
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
        valid = {
            "communication", "teamwork", "adaptability",
            "decision_making", "leadership", "stress_management",
        }
        normalised = v.strip().lower().replace(" ", "_").replace("-", "_")
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
        max_length=6,
        description="One entry per relevant behavioral dimension (1–6).",
    )
