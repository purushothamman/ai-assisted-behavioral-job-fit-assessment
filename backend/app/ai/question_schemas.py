"""
ai/question_schemas.py
Pydantic models for Groq question-generation input/output (Phase 4).
All models are validated BEFORE data is written to Supabase.
"""
from __future__ import annotations

from typing import List, Literal
from pydantic import BaseModel, Field, field_validator

VALID_DIMENSIONS = {
    "communication", "teamwork", "adaptability",
    "decision_making", "leadership", "stress_management",
}

VALID_TYPES = {"behavioral", "situational", "competency"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


class GeneratedQuestion(BaseModel):
    """
    One interview question produced by Groq.
    Maps to a row in the interview_questions table.
    """
    dimension: str = Field(
        ...,
        description="One of the six behavioral dimension names.",
    )
    question: str = Field(
        ...,
        min_length=20,
        description="The full, open-ended interview question text.",
    )
    type: Literal["behavioral", "situational", "competency"] = Field(
        ...,
        description="Question category.",
    )
    difficulty: Literal["easy", "medium", "hard"] = Field(
        ...,
        description="Estimated question difficulty.",
    )
    indicators: List[str] = Field(
        ...,
        min_length=2,
        max_length=4,
        description="Observable signals of a strong response.",
    )

    @field_validator("dimension")
    @classmethod
    def validate_dimension(cls, v: str) -> str:
        normalised = v.strip().lower().replace(" ", "_").replace("-", "_")
        if normalised not in VALID_DIMENSIONS:
            raise ValueError(
                f"Unknown dimension '{v}'. Must be one of: {sorted(VALID_DIMENSIONS)}"
            )
        return normalised

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be blank")
        return v.strip()

    @field_validator("indicators", mode="before")
    @classmethod
    def indicators_not_empty_strings(cls, v: list) -> list:
        cleaned = [s.strip() for s in v if isinstance(s, str) and s.strip()]
        if len(cleaned) < 2:
            raise ValueError("indicators must contain at least 2 non-blank strings")
        return cleaned


class QuestionGeneratorOutput(BaseModel):
    """Top-level Groq response for the question-generation prompt."""
    questions: List[GeneratedQuestion] = Field(
        ...,
        min_length=1,
        description="One or more interview questions.",
    )
