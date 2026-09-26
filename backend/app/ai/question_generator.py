"""
ai/question_generator.py
Groq integration: generate behavioral interview questions from confirmed
job requirements.

The prompt receives the job title/description and the list of confirmed
behavioral dimensions (with importance & reason), and returns a structured
set of STAR-format interview questions — one or more per dimension —
each tagged with type, difficulty, and observable success indicators.

Groq NEVER determines hire/reject decisions — it generates questions only.
"""
from __future__ import annotations

import logging
from typing import List

from pydantic import ValidationError

from app.ai.groq_client import GroqError, call_groq_json
from app.ai.question_schemas import GeneratedQuestion, QuestionGeneratorOutput

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a behavioral interview designer specialised in structured STAR-format \
interviews.

Given a job description and a list of confirmed behavioral dimensions, generate \
targeted behavioral interview questions. Each question must:
- Follow the STAR format (Situation, Task, Action, Result).
- Be directly relevant to the specific role and dimension.
- Include observable indicators of a strong response.

You MUST respond with a JSON object in EXACTLY this format:
{
  "questions": [
    {
      "dimension": "<one of the six dimension names>",
      "question": "<the full interview question>",
      "type": "<behavioral|situational|competency>",
      "difficulty": "<easy|medium|hard>",
      "indicators": ["<observable indicator 1>", "<observable indicator 2>", ...]
    }
  ]
}

The six valid dimension names (use underscores):
  communication, teamwork, adaptability, decision_making, leadership, stress_management

Rules:
- Generate 2–3 questions per dimension provided. No more, no less.
- type must be exactly one of: behavioral, situational, competency.
- difficulty must be exactly one of: easy, medium, hard.
- indicators: list 2–4 specific, observable signals that distinguish a strong answer.
- question must be a complete, open-ended sentence (not a heading).
- Do NOT include markdown, commentary, or any keys outside the schema.
"""


def _build_user_prompt(
    title: str,
    description: str,
    requirements: List[dict],
) -> str:
    """
    Build the user-role message sent to Groq.

    requirements is a list of dicts with keys: dimension_name, importance, reason.
    """
    req_lines = "\n".join(
        f"  - {r['dimension_name']} (importance {r['importance']}): {r['reason']}"
        for r in requirements
        if r.get("dimension_name") and r.get("confirmed", True)
    )
    return (
        f"Job Title: {title}\n"
        f"Job Description: {description}\n\n"
        f"Confirmed Behavioral Dimensions:\n{req_lines}"
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def generate_questions(
    title: str,
    description: str,
    requirements: List[dict],
) -> List[GeneratedQuestion]:
    """
    Call Groq to generate behavioral interview questions for a job.

    Parameters
    ----------
    title : str
        Job title.
    description : str
        Job description text.
    requirements : list of dict
        Each dict must have: dimension_name, importance, reason, confirmed.
        Only confirmed requirements are sent to Groq.

    Returns
    -------
    List[GeneratedQuestion]
        Validated list of generated questions.

    Raises
    ------
    GroqError
        If Groq is unavailable after retries.
    ValueError
        If Groq's output fails Pydantic validation.
    """
    confirmed = [r for r in requirements if r.get("confirmed")]
    if not confirmed:
        raise ValueError(
            "No confirmed behavioral requirements found. "
            "Please confirm at least one requirement before generating questions."
        )

    user_prompt = _build_user_prompt(title, description, confirmed)

    logger.info(
        "Calling Groq to generate questions for '%s' (%d confirmed dimensions).",
        title,
        len(confirmed),
    )
    raw = call_groq_json(SYSTEM_PROMPT, user_prompt, max_tokens=2048)

    try:
        output = QuestionGeneratorOutput.model_validate(raw)
    except ValidationError as exc:
        logger.error("Groq question output failed validation: %s | raw: %s", exc, raw)
        raise ValueError(
            f"Groq returned an invalid response structure: {exc}"
        ) from exc

    logger.info(
        "Question generation complete — %d questions generated.", len(output.questions)
    )
    return output.questions
