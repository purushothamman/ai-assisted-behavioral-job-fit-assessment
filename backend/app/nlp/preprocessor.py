"""
nlp/preprocessor.py
Text-cleaning and quality-gate functions for candidate responses.

All functions are pure Python — no ML models, no DB calls.
They can be unit-tested without any mocking.

Public API:
  clean(text)          -> str          (stripped, normalised whitespace)
  quality_gate(text)   -> QualityResult
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Config thresholds
# ---------------------------------------------------------------------------

MIN_WORDS     = 5     # fewer words → flagged as too short
MIN_CHARS     = 10    # raw char minimum (mirrors ResponseCreate.min_length)
MAX_CHARS     = 10_000  # ceiling already enforced by Pydantic


@dataclass(frozen=True)
class QualityResult:
    """
    Result of a quality gate check on a single candidate answer.

    Attributes
    ----------
    is_valid : bool
        True if the response can be scored normally.
        False if the response should be scored as 0 with a status note.
    word_count : int
    char_count : int
    flag : str
        One of: '' | 'too_short' | 'empty' | 'garbled'
    """
    is_valid:   bool
    word_count: int
    char_count: int
    flag:       str = ""


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"\s+")


def clean(text: str) -> str:
    """
    Normalise a candidate response for embedding.

    Steps:
      1. Strip leading/trailing whitespace.
      2. Collapse internal runs of whitespace (including newlines) to single space.
      3. Return as a single UTF-8 string.

    Does NOT lowercase — sentence-transformers handles case internally.
    """
    if not isinstance(text, str):
        return ""
    return _WHITESPACE_RE.sub(" ", text).strip()


# ---------------------------------------------------------------------------
# Quality gate
# ---------------------------------------------------------------------------

_NON_ALPHA_RE = re.compile(r"[^a-zA-Z\s]")


def quality_gate(text: str) -> QualityResult:
    """
    Run a quality gate on a cleaned candidate answer.

    Returns a QualityResult indicating whether the answer is usable and,
    if not, why it was flagged.

    Checks (in order):
      1. Empty / whitespace-only   → flag='empty'
      2. Too short (chars < MIN_CHARS or words < MIN_WORDS) → flag='too_short'
      3. Garbled / no real words   → flag='garbled'
    """
    cleaned    = clean(text)
    char_count = len(cleaned)
    words      = cleaned.split()
    word_count = len(words)

    if char_count == 0:
        return QualityResult(is_valid=False, word_count=0, char_count=0, flag="empty")

    if char_count < MIN_CHARS or word_count < MIN_WORDS:
        return QualityResult(
            is_valid=False,
            word_count=word_count,
            char_count=char_count,
            flag="too_short",
        )

    # Garbled check: if removing all non-alpha chars and stripping spaces leaves < 3 chars it's likely junk
    alpha_only = _NON_ALPHA_RE.sub("", cleaned).replace(" ", "")
    if len(alpha_only) < 3:
        return QualityResult(
            is_valid=False,
            word_count=word_count,
            char_count=char_count,
            flag="garbled",
        )

    return QualityResult(is_valid=True, word_count=word_count, char_count=char_count)
