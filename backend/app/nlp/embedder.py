"""
nlp/embedder.py
Lazy singleton wrapper around sentence-transformers all-MiniLM-L6-v2.

Design:
  - Model is loaded exactly once per process (heavy: ~90 MB).
  - All public functions are pure Python — no FastAPI / Supabase deps.
  - Tests swap out get_model() with a mock that returns deterministic
    numpy arrays so no GPU / internet is needed during CI.

Public API:
  get_model()             -> SentenceTransformer
  embed(texts)            -> np.ndarray  shape (N, D)
  embed_one(text)         -> np.ndarray  shape (D,)
  cosine_sim(a, b)        -> float in [0, 1]
  cosine_sim_matrix(A, B) -> np.ndarray  shape (|A|, |B|)
"""
from __future__ import annotations

import logging
import threading
from typing import List

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model config
# ---------------------------------------------------------------------------

MODEL_NAME = "all-MiniLM-L6-v2"   # ~90 MB; sentence-transformers default

_model = None
_model_lock = threading.Lock()


def get_model():
    """Return the cached SentenceTransformer singleton (loaded on first call)."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:   # double-check after acquiring lock
                logger.info("Loading sentence-transformer model: %s", MODEL_NAME)
                from sentence_transformers import SentenceTransformer  # noqa: lazy import
                _model = SentenceTransformer(MODEL_NAME)
                logger.info("Model loaded successfully.")
    return _model


# ---------------------------------------------------------------------------
# Public embedding helpers
# ---------------------------------------------------------------------------

def embed(texts: List[str]) -> np.ndarray:
    """
    Embed a list of strings into a 2-D numpy array.

    Parameters
    ----------
    texts : List[str]
        Non-empty list of strings to embed.

    Returns
    -------
    np.ndarray
        Shape (len(texts), embedding_dim), dtype float32.
    """
    if not texts:
        raise ValueError("embed() received an empty list — nothing to encode.")

    model = get_model()
    return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)


def embed_one(text: str) -> np.ndarray:
    """Embed a single string. Returns shape (D,)."""
    return embed([text])[0]


# ---------------------------------------------------------------------------
# Similarity helpers
# ---------------------------------------------------------------------------

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two 1-D vectors.

    Because we use normalize_embeddings=True in encode(), the vectors are
    already unit-normalised, so cosine_sim = dot product.

    Returns float in [0, 1].  Clipped to [0, 1] to handle floating-point noise.
    """
    sim = float(np.dot(a, b))
    return max(0.0, min(1.0, sim))


def cosine_sim_matrix(a_vecs: np.ndarray, b_vecs: np.ndarray) -> np.ndarray:
    """
    Compute pairwise cosine similarities between two sets of embeddings.

    Parameters
    ----------
    a_vecs : np.ndarray  shape (M, D)
    b_vecs : np.ndarray  shape (N, D)

    Returns
    -------
    np.ndarray  shape (M, N)  — entry [i, j] = cosine_sim(a_vecs[i], b_vecs[j])
    """
    sim = a_vecs @ b_vecs.T
    return np.clip(sim, 0.0, 1.0)
