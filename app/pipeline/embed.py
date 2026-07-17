"""
Embedding utility — lazy-loads a sentence-transformers model
and provides sync embed functions.
"""
from __future__ import annotations

import os
import logging
from functools import lru_cache
from typing import List

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model singleton
# ---------------------------------------------------------------------------

_model = None


def _get_model():
    """Lazy-load the embedding model (heavy; ~130 MB – 1.3 GB)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        logger.info("Loading embedding model: %s", model_name)
        _model = SentenceTransformer(model_name)
        logger.info("Embedding model loaded  (dim=%d)", _model.get_embedding_dimension())
    return _model


def get_embedding_dim() -> int:
    """Return the dimensionality of the active model."""
    return _get_model().get_embedding_dimension()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def embed_text(text: str) -> List[float]:
    """Embed a single string and return a list of floats."""
    model = _get_model()
    # BGE models recommend prefixing queries with "Represent this sentence: "
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_batch(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """Embed a list of strings and return a list of float-lists."""
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, batch_size=batch_size)
    return vectors.tolist()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors."""
    a_np = np.asarray(a, dtype=np.float32)
    b_np = np.asarray(b, dtype=np.float32)
    denom = np.linalg.norm(a_np) * np.linalg.norm(b_np)
    if denom == 0:
        return 0.0
    return float(np.dot(a_np, b_np) / denom)
