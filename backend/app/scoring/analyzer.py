"""
scoring/analyzer.py
Full response-analysis pipeline orchestrator.

Connects the NLP embedding layer to the deterministic scoring rubric.
All heavy lifting is delegated to nlp.embedder and scoring.rubric.

Public API:
  analyze_response(answer, question_indicators, indicator_texts)
      -> DimensionScore

  analyze_response_safe(answer, question_indicators, indicator_texts)
      -> DimensionScore   (never raises; returns status='invalid' on errors)

Design:
  - No DB calls — DB interactions happen in scoring_service.py.
  - Embedder is accessed via nlp.embedder.embed() so tests can patch it.
  - Preprocessing is always applied before embedding.
"""
from __future__ import annotations

import logging
from typing import List

from app.nlp.embedder import cosine_sim_matrix, embed
from app.nlp.preprocessor import clean, quality_gate
from app.scoring.rubric import DimensionScore, aggregate_dimension_score

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core analysis function
# ---------------------------------------------------------------------------

def analyze_response(
    answer: str,
    dimension_name: str,
    indicator_names: List[str],
    indicator_texts: List[str],
) -> DimensionScore:
    """
    Score a single candidate answer against a set of behavioral indicators.

    Parameters
    ----------
    answer          : str   — raw candidate answer text
    dimension_name  : str   — e.g. 'communication'
    indicator_names : List[str]  — human-readable indicator labels (for evidence)
    indicator_texts : List[str]  — indicator text to embed (description + examples)
                                   same length and order as indicator_names

    Returns
    -------
    DimensionScore  — contains normalized_score, confidence, evidence list

    Raises
    ------
    ValueError      — if indicator_names and indicator_texts mismatch
    """
    if len(indicator_names) != len(indicator_texts):
        raise ValueError(
            "indicator_names and indicator_texts must have the same length. "
            f"Got {len(indicator_names)} names vs {len(indicator_texts)} texts."
        )

    # 1. Preprocess the answer
    cleaned = clean(answer)
    quality = quality_gate(cleaned)

    if not quality.is_valid:
        logger.info(
            "Response quality gate failed: flag=%s, chars=%d, words=%d",
            quality.flag, quality.char_count, quality.word_count,
        )
        return DimensionScore(
            dimension_name=dimension_name,
            normalized_score=0,
            raw_score=0.0,
            confidence=0.0,
            status=f"invalid:{quality.flag}",
        )

    # 2. Handle no indicators edge case
    if not indicator_names:
        return DimensionScore(
            dimension_name=dimension_name,
            normalized_score=0,
            raw_score=0.0,
            confidence=0.0,
            status="no_indicators",
        )

    # 3. Embed answer + all indicator texts together for efficiency
    all_texts     = [cleaned] + indicator_texts
    all_embeddings = embed(all_texts)

    answer_emb     = all_embeddings[0:1]          # shape (1, D)
    indicator_embs = all_embeddings[1:]           # shape (N, D)

    # 4. Compute cosine similarity: answer vs each indicator
    sim_matrix   = cosine_sim_matrix(answer_emb, indicator_embs)  # (1, N)
    similarities = sim_matrix[0].tolist()                          # List[float]

    # 5. Aggregate via deterministic rubric
    return aggregate_dimension_score(dimension_name, indicator_names, similarities)


# ---------------------------------------------------------------------------
# Safe wrapper
# ---------------------------------------------------------------------------

def analyze_response_safe(
    answer: str,
    dimension_name: str,
    indicator_names: List[str],
    indicator_texts: List[str],
) -> DimensionScore:
    """
    Wrapper around analyze_response that catches all exceptions.

    Returns a DimensionScore with status='error' instead of raising,
    so a single bad response doesn't block scoring the entire session.
    """
    try:
        return analyze_response(answer, dimension_name, indicator_names, indicator_texts)
    except Exception as exc:
        logger.error(
            "analyze_response failed for dimension '%s': %s",
            dimension_name, exc, exc_info=True,
        )
        return DimensionScore(
            dimension_name=dimension_name,
            normalized_score=0,
            raw_score=0.0,
            confidence=0.0,
            status="error",
        )
