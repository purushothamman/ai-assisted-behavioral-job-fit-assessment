"""
scoring/analyzer.py
Full response-analysis pipeline orchestrator.

Connects the NLP embedding layer to the deterministic scoring rubric.
All heavy lifting is delegated to nlp.embedder and scoring.rubric.

Public API:
  analyze_response(answer, dimension_name, indicator_names, indicator_texts)
      -> DimensionScore

  analyze_response_safe(answer, dimension_name, indicator_names, indicator_texts)
      -> DimensionScore   (never raises; returns status='invalid' on errors)

Design:
  - No DB calls — DB interactions happen in scoring_service.py.
  - Embedder is accessed via nlp.embedder.embed() so tests can patch it.
  - Preprocessing is always applied before embedding.

Phase B additions (ES-2 / ES-3):
  - _split_sentences()            : regex sentence segmenter
  - _extract_sentence_evidence()  : per-indicator best-sentence grounding
  These are purely additive — they do NOT change the rubric math or scores.
"""
from __future__ import annotations

import logging
import re as _re
from typing import List, Optional

from app.nlp.embedder import cosine_sim_matrix, embed
from app.nlp.preprocessor import clean, quality_gate
from app.scoring.rubric import DimensionScore, aggregate_dimension_score

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ES-2: Sentence segmentation helper
# ---------------------------------------------------------------------------

_SENT_SPLIT_RE = _re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> List[str]:
    """
    Split cleaned answer text into sentence-level units.

    Uses a simple punctuation-boundary regex.  Falls back to the full text
    as a single unit when no sentence boundaries are found (e.g. one long
    sentence or heavily abbreviated text).

    Returns a non-empty list of non-empty stripped strings.
    """
    if not text or not text.strip():
        return []
    parts = [s.strip() for s in _SENT_SPLIT_RE.split(text) if s.strip()]
    return parts if parts else [text.strip()]


def _extract_sentence_evidence(
    cleaned_answer: str,
    indicator_embs,     # np.ndarray  shape (N, D)
) -> List[Optional[str]]:
    """
    ES-2/ES-3: For each indicator find the sentence from the candidate's
    answer that has the highest cosine similarity to that indicator's embedding.

    Parameters
    ----------
    cleaned_answer  : str        — preprocessed candidate answer
    indicator_embs  : np.ndarray — shape (N, D), normalised indicator embeddings

    Returns
    -------
    List[Optional[str]]
        One entry per indicator.  Each entry is the best-matching sentence text,
        or None when no sentence cleared the minimum similarity floor (0.10).

    Safety
    ------
    - NEVER raises — returns all-None list on any internal failure.
    - This similarity computation is ONLY used to pick a grounding sentence for
      the recruiter.  It does NOT alter the rubric score, which is always
      computed from the whole-answer embedding in step 4 of analyze_response().
    """
    import numpy as np  # local — mirrors embedder.py lazy import pattern

    n_indicators = indicator_embs.shape[0]
    try:
        sentences = _split_sentences(cleaned_answer)
        if not sentences:
            return [None] * n_indicators

        # Embed all sentences in one batch — reuses the singleton model
        sent_embs = embed(sentences)                        # shape (S, D)

        # Pairwise similarity: sentences vs indicators — shape (S, N)
        sent_vs_ind = cosine_sim_matrix(sent_embs, indicator_embs)

        # For each indicator (column) pick the sentence (row) with max similarity
        best_sent_indices = np.argmax(sent_vs_ind, axis=0).tolist()  # List[int]

        evidence_texts: List[Optional[str]] = []
        for ind_idx, sent_idx in enumerate(best_sent_indices):
            best_sim = float(sent_vs_ind[int(sent_idx), ind_idx])
            # Only attach sentence text when similarity clears a meaningful floor
            # to avoid attributing a completely unrelated sentence as evidence.
            evidence_texts.append(
                sentences[int(sent_idx)] if best_sim >= 0.10 else None
            )

        return evidence_texts

    except Exception as exc:
        logger.warning(
            "_extract_sentence_evidence failed — evidence_text will be None: %s", exc
        )
        return [None] * n_indicators


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
    all_texts      = [cleaned] + indicator_texts
    all_embeddings = embed(all_texts)

    answer_emb     = all_embeddings[0:1]          # shape (1, D)
    indicator_embs = all_embeddings[1:]           # shape (N, D)

    # 4. Whole-answer cosine similarity — this drives the deterministic rubric.
    #    Unchanged from Phase 6: scores are authoritative and LLM-free.
    sim_matrix   = cosine_sim_matrix(answer_emb, indicator_embs)  # (1, N)
    similarities = sim_matrix[0].tolist()                          # List[float]

    # 5. ES-2/ES-3: Sentence-level evidence grounding — additive, non-scoring.
    #    Find the best-matching sentence per indicator for recruiter context.
    evidence_texts = _extract_sentence_evidence(cleaned, indicator_embs)

    # 6. Aggregate via deterministic rubric (scoring math unchanged)
    return aggregate_dimension_score(
        dimension_name, indicator_names, similarities, evidence_texts
    )


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
