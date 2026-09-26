"""
scoring/rubric.py
Deterministic, explainable scoring rubric.

Converts per-indicator cosine-similarity values into discrete evidence
levels (0/1/2), then aggregates them into a normalized 0-100 dimension score.

All functions are pure Python — no DB calls, no ML model calls.
They are fully unit-testable without mocking.

Thresholds (tuned for all-MiniLM-L6-v2 on normalized embeddings):
  sim >= STRONG_THRESHOLD  → score 2 (strong evidence)
  sim >= PARTIAL_THRESHOLD → score 1 (partial evidence)
  otherwise                → score 0 (no evidence)

Normalization:
  raw  = sum(indicator_scores) / (MAX_PER_INDICATOR * n_indicators)
  pct  = round(raw * 100)  → 0-100 integer

Confidence:
  mean of max(sim, 0) across all indicators  → 0.0-1.0 float
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

# ---------------------------------------------------------------------------
# Threshold config (tunable without breaking any interface)
# ---------------------------------------------------------------------------

STRONG_THRESHOLD  = 0.45    # sim >= 0.45 → strong evidence (score = 2)
PARTIAL_THRESHOLD = 0.28    # sim >= 0.28 → partial evidence (score = 1)
MAX_PER_INDICATOR = 2       # maximum points per indicator


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IndicatorEvidence:
    """
    Evidence record for a single behavioral indicator.

    Attributes
    ----------
    indicator_name  : str   — human-readable indicator label
    similarity      : float — cosine similarity between answer and indicator text
    score           : int   — 0 (none), 1 (partial), 2 (strong)
    matched         : bool  — True if score > 0
    level           : str   — 'none' | 'partial' | 'strong'
    """
    indicator_name: str
    similarity:     float
    score:          int
    matched:        bool
    level:          str


@dataclass
class DimensionScore:
    """
    Final score for a single behavioral dimension on a single response.

    Attributes
    ----------
    dimension_name   : str
    normalized_score : int    — 0-100
    raw_score        : float  — 0.0-1.0
    confidence       : float  — 0.0-1.0 (mean max-similarity per indicator)
    evidence         : List[IndicatorEvidence]
    indicators_matched : int  — count of indicators with score > 0
    total_indicators   : int
    status           : str    — 'scored' | 'invalid' | 'no_indicators'
    """
    dimension_name:    str
    normalized_score:  int
    raw_score:         float
    confidence:        float
    evidence:          List[IndicatorEvidence] = field(default_factory=list)
    indicators_matched: int = 0
    total_indicators:  int = 0
    status:            str = "scored"


# ---------------------------------------------------------------------------
# Core rubric functions
# ---------------------------------------------------------------------------

def score_indicator(similarity: float) -> int:
    """
    Convert a cosine similarity value to a discrete evidence score.

    Returns
    -------
    int  — 0 (no evidence), 1 (partial evidence), 2 (strong evidence)
    """
    if similarity >= STRONG_THRESHOLD:
        return 2
    if similarity >= PARTIAL_THRESHOLD:
        return 1
    return 0


def level_label(score: int) -> str:
    """Convert a 0/1/2 score to a human-readable level string."""
    return {0: "none", 1: "partial", 2: "strong"}.get(score, "none")


def build_evidence(indicator_names: List[str], similarities: List[float]) -> List[IndicatorEvidence]:
    """
    Build a list of IndicatorEvidence records from indicator names and
    corresponding cosine similarities.

    Parameters
    ----------
    indicator_names : List[str]  — ordered list of indicator labels
    similarities    : List[float]  — cosine sims, same order as names

    Returns
    -------
    List[IndicatorEvidence]  — one record per indicator
    """
    if len(indicator_names) != len(similarities):
        raise ValueError(
            f"indicator_names ({len(indicator_names)}) and "
            f"similarities ({len(similarities)}) must have the same length."
        )

    evidence = []
    for name, sim in zip(indicator_names, similarities):
        s     = max(0.0, float(sim))         # clip negatives from float noise
        score = score_indicator(s)
        evidence.append(IndicatorEvidence(
            indicator_name=name,
            similarity=round(s, 4),
            score=score,
            matched=score > 0,
            level=level_label(score),
        ))
    return evidence


def normalize_score(raw_points: int, n_indicators: int) -> int:
    """
    Normalize a raw indicator score sum to a 0-100 integer.

    raw_points  — sum of per-indicator scores (0 to 2 each)
    n_indicators — total number of indicators

    Returns 0 if n_indicators == 0 (safe guard).
    """
    if n_indicators == 0:
        return 0
    max_possible = MAX_PER_INDICATOR * n_indicators
    return round((raw_points / max_possible) * 100)


def compute_confidence(similarities: List[float]) -> float:
    """
    Compute confidence as the mean of max(0, sim) across all indicators.

    Returns float in [0.0, 1.0], rounded to 4 decimal places.
    Returns 0.0 if the list is empty.
    """
    if not similarities:
        return 0.0
    clipped = [max(0.0, float(s)) for s in similarities]
    return round(sum(clipped) / len(clipped), 4)


def aggregate_dimension_score(
    dimension_name: str,
    indicator_names: List[str],
    similarities: List[float],
) -> DimensionScore:
    """
    Full dimension scoring pipeline:
      1. Build evidence records per indicator
      2. Normalize raw point sum → 0-100
      3. Compute confidence

    Parameters
    ----------
    dimension_name  : str
    indicator_names : List[str]   — behavioral indicator labels
    similarities    : List[float] — cosine sims (same order)

    Returns
    -------
    DimensionScore
    """
    if not indicator_names:
        return DimensionScore(
            dimension_name=dimension_name,
            normalized_score=0,
            raw_score=0.0,
            confidence=0.0,
            status="no_indicators",
        )

    evidence = build_evidence(indicator_names, similarities)
    raw_sum  = sum(e.score for e in evidence)
    n        = len(evidence)

    norm_score = normalize_score(raw_sum, n)
    raw_score  = round(raw_sum / (MAX_PER_INDICATOR * n), 4)
    confidence = compute_confidence(similarities)

    return DimensionScore(
        dimension_name=dimension_name,
        normalized_score=norm_score,
        raw_score=raw_score,
        confidence=confidence,
        evidence=evidence,
        indicators_matched=sum(1 for e in evidence if e.matched),
        total_indicators=n,
        status="scored",
    )
