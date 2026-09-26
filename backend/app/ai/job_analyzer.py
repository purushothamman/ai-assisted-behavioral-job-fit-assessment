"""
ai/job_analyzer.py
Groq integration: extract behavioral requirements from a job description.

The prompt asks Groq to map the JD onto the six fixed behavioral dimensions
and assign an importance score (0-100) plus a plain-English reason.
Output is validated with Pydantic before it leaves this module.

Groq NEVER determines hire/reject decisions — it only extracts signals.
"""
from __future__ import annotations

import logging
from typing import List

from pydantic import ValidationError

from app.ai.groq_client import GroqError, call_groq_json
from app.ai.schemas import DimensionRequirement, JobAnalysisOutput

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a behavioral competency analyst.
Your job is to read a job description and identify which of the six behavioral
dimensions are important for success in that role.

The six dimensions are:
- communication      : clarity, active listening, information sharing
- teamwork           : collaboration, conflict resolution, supportiveness
- adaptability       : flexibility, handling change, learning new processes
- decision_making    : information evaluation, risk consideration, prioritization
- leadership         : delegation, accountability, coordination, motivation
- stress_management  : managing competing demands, prioritization under pressure, task focus

You MUST respond with a JSON object in EXACTLY this format:
{
  "requirements": [
    {
      "dimension": "<one of the six dimension names above>",
      "importance": <integer 0-100>,
      "reason": "<one or two sentences explaining why this dimension matters for this specific role>"
    }
  ]
}

Rules:
- Include only dimensions that are genuinely relevant (score > 20).
- importance 80-100 = critical; 50-79 = important; 20-49 = useful but secondary.
- Minimum 1, maximum 6 dimensions.
- dimension name must match exactly one of the six names above (use underscores).
- reason must be specific to the role, not generic filler.
- Do NOT include any commentary, markdown, or keys outside the schema.
"""


def _build_user_prompt(title: str, description: str, responsibilities: str = "", requirements: str = "") -> str:
    parts = [f"Job Title: {title}", f"\nJob Description:\n{description}"]
    if responsibilities:
        parts.append(f"\nResponsibilities:\n{responsibilities}")
    if requirements:
        parts.append(f"\nRequirements:\n{requirements}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def analyze_job(
    title: str,
    description: str,
    responsibilities: str = "",
    requirements: str = "",
) -> List[DimensionRequirement]:
    """
    Call Groq to extract behavioral dimension requirements from a job description.

    Parameters
    ----------
    title, description, responsibilities, requirements : str
        The job posting text.

    Returns
    -------
    List[DimensionRequirement]
        Validated list of behavioral requirements (1–6 items).

    Raises
    ------
    GroqError
        If Groq is unavailable or returns unusable output after retries.
    ValueError
        If Groq's output fails Pydantic validation after retries.
    """
    user_prompt = _build_user_prompt(title, description, responsibilities, requirements)

    logger.info("Calling Groq to analyze job: %s", title)
    raw = call_groq_json(SYSTEM_PROMPT, user_prompt)

    try:
        output = JobAnalysisOutput.model_validate(raw)
    except ValidationError as exc:
        logger.error("Groq output failed validation: %s | raw: %s", exc, raw)
        raise ValueError(
            f"Groq returned an invalid response structure: {exc}"
        ) from exc

    logger.info(
        "Job analysis complete — %d dimensions identified.", len(output.requirements)
    )
    return output.requirements
