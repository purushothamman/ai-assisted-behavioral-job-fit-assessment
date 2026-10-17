"""
ai/job_analyzer.py
Groq integration: extract behavioral requirements from a job description.

The prompt asks Groq to map the JD onto active behavioral framework dimensions
and assign an importance score (0-100) plus a plain-English reason.
Output is validated with Pydantic before it leaves this module.

Groq NEVER determines hire/reject decisions — it only extracts signals.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from pydantic import ValidationError

from app.ai.groq_client import GroqError, call_groq_json
from app.ai.schemas import DimensionRequirement, JobAnalysisOutput

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default Prompt templates
# ---------------------------------------------------------------------------

DEFAULT_SYSTEM_PROMPT = """You are a behavioral competency analyst.
Your job is to read a job description and identify which of the active behavioral
framework dimensions are important for success in that role.

The available behavioral framework dimensions are:
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
      "dimension": "<one of the valid framework dimension names above>",
      "importance": <integer 0-100>,
      "reason": "<one or two sentences explaining why this dimension matters for this specific role>"
    }
  ]
}

Rules:
- Include only dimensions that are genuinely relevant (score > 20).
- importance 80-100 = critical; 50-79 = important; 20-49 = useful but secondary.
- Minimum 1, maximum 6 dimensions.
- dimension name must match exactly one of the valid framework dimension names above (use underscores).
- reason must be specific to the role, not generic filler.
- Do NOT include any commentary, markdown, or keys outside the schema.
"""

SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT


def build_dynamic_system_prompt(dimensions: List[dict]) -> str:
    """Build a dynamic system prompt listing available framework dimensions."""
    if not dimensions:
        return DEFAULT_SYSTEM_PROMPT

    dim_lines = []
    for d in dimensions:
        name = d.get("name", "")
        desc = d.get("description", "")
        indicators = d.get("indicators", [])
        if indicators and isinstance(indicators, list):
            ind_names = ", ".join(
                i.get("name") if isinstance(i, dict) else str(i) for i in indicators[:4]
            )
            dim_lines.append(f"- {name:<20}: {desc} (Signals: {ind_names})")
        elif desc:
            dim_lines.append(f"- {name:<20}: {desc}")
        else:
            dim_lines.append(f"- {name}")

    dims_formatted = "\n".join(dim_lines)
    max_dims = max(len(dimensions), 1)

    return f"""You are a behavioral competency analyst.
Your job is to read a job description and identify which of the active behavioral
framework dimensions are important for success in that role.

The available behavioral framework dimensions are:
{dims_formatted}

You MUST respond with a JSON object in EXACTLY this format:
{{
  "requirements": [
    {{
      "dimension": "<one of the valid framework dimension names above>",
      "importance": <integer 0-100>,
      "reason": "<one or two sentences explaining why this dimension matters for this specific role>"
    }}
  ]
}}

Rules:
- Include only dimensions that are genuinely relevant (score > 20).
- importance 80-100 = critical; 50-79 = important; 20-49 = useful but secondary.
- Minimum 1, maximum {max_dims} dimensions.
- dimension name must match exactly one of the valid framework dimension names above (use underscores).
- reason must be specific to the role, not generic filler.
- Do NOT include any commentary, markdown, or keys outside the schema.
"""


def _build_user_prompt(
    title: str,
    description: str,
    responsibilities: str = "",
    requirements: str = "",
) -> str:
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
    dimensions: Optional[List[dict]] = None,
) -> List[DimensionRequirement]:
    """
    Call Groq to extract behavioral dimension requirements from a job description.

    Parameters
    ----------
    title, description, responsibilities, requirements : str
        The job posting text.
    dimensions : list of dict, optional
        Active dimensions in the behavioral framework. If None, loaded from DimensionService
        or falls back to default 6 dimensions.

    Returns
    -------
    List[DimensionRequirement]
        Validated list of behavioral requirements.
    """
    system_prompt = SYSTEM_PROMPT
    if dimensions:
        system_prompt = build_dynamic_system_prompt(dimensions)
    else:
        try:
            from app.services.dimension_service import DimensionService
            active_dims = DimensionService().list_dimensions(active_only=True)
            if active_dims:
                system_prompt = build_dynamic_system_prompt(active_dims)
        except Exception as exc:
            logger.debug("Falling back to default system prompt: %s", exc)

    user_prompt = _build_user_prompt(title, description, responsibilities, requirements)

    logger.info("Calling Groq to analyze job: %s", title)
    raw = call_groq_json(system_prompt, user_prompt)

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
