"""
ai/groq_client.py
Shared Groq API client with retry logic, structured-JSON output helpers,
and graceful error handling.

Design principles:
- Single client instance per process (module-level singleton).
- All prompts request JSON mode to guarantee parseable output.
- Retry up to MAX_RETRIES times on rate-limit or malformed JSON.
- Never let a Groq failure crash the caller — callers receive a typed
  exception they can catch and handle gracefully.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from groq import APIConnectionError, APIStatusError, Groq, RateLimitError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_BACKOFF = 1.5   # seconds; doubles each retry


class GroqError(RuntimeError):
    """Raised when Groq fails after all retries or returns unusable output."""


def get_groq_client() -> Groq:
    """Return a module-level Groq singleton (thread-safe construction)."""
    settings = get_settings()
    if not settings.groq_api_key:
        raise GroqError(
            "GROQ_API_KEY is not set. "
            "Add it to your .env file before using AI features."
        )
    return Groq(api_key=settings.groq_api_key)


def call_groq_json(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    """
    Call Groq and return parsed JSON.

    Parameters
    ----------
    system_prompt : str
        The system role message (defines output schema).
    user_prompt : str
        The user role message (the actual input, e.g. the job description).
    model / max_tokens / temperature : optional overrides.

    Returns
    -------
    dict
        The parsed JSON object from Groq's response.

    Raises
    ------
    GroqError
        If all retries are exhausted or the response is not valid JSON.
    """
    settings = get_settings()
    client   = get_groq_client()

    req_model       = model       or settings.groq_model
    req_max_tokens  = max_tokens  or settings.groq_max_tokens
    req_temperature = temperature if temperature is not None else settings.groq_temperature

    last_exc: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=req_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=req_max_tokens,
                temperature=req_temperature,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content or ""
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "Groq returned non-JSON (attempt %d/%d). Raw: %.200s",
                    attempt, MAX_RETRIES, raw,
                )
                last_exc = exc
                # Retry on malformed JSON

        except RateLimitError as exc:
            wait = BASE_BACKOFF ** attempt
            logger.warning(
                "Groq rate limit hit (attempt %d/%d). Waiting %.1fs.",
                attempt, MAX_RETRIES, wait,
            )
            time.sleep(wait)
            last_exc = exc

        except APIConnectionError as exc:
            wait = BASE_BACKOFF ** attempt
            logger.warning("Groq connection error (attempt %d/%d).", attempt, MAX_RETRIES)
            time.sleep(wait)
            last_exc = exc

        except APIStatusError as exc:
            # 4xx errors (bad key, model not found, etc.) are not retryable
            logger.error("Groq API status error %s: %s", exc.status_code, exc.message)
            raise GroqError(f"Groq API error {exc.status_code}: {exc.message}") from exc

    raise GroqError(
        f"Groq call failed after {MAX_RETRIES} attempts. Last error: {last_exc}"
    )
