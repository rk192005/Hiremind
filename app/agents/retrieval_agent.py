"""
Retrieval Agent — embeds the parsed JD and retrieves top-k candidates
from Qdrant.  Falls back to in-memory cosine similarity when Qdrant
has no data or is unavailable.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.pipeline.embed import embed_text, embed_batch, cosine_similarity
from app.pipeline.qdrant_client import (
    ensure_collection,
    upsert_candidates,
    search_candidates,
    get_collection_count,
)

logger = logging.getLogger(__name__)


def _build_jd_query(parsed_jd: Dict[str, Any]) -> str:
    """Compose a single query string from parsed JD fields for embedding."""
    parts = []
    if parsed_jd.get("summary"):
        parts.append(parsed_jd["summary"])
    if parsed_jd.get("required_skills"):
        parts.append("Required skills: " + ", ".join(parsed_jd["required_skills"]))
    if parsed_jd.get("nice_to_have_skills"):
        parts.append("Nice to have: " + ", ".join(parsed_jd["nice_to_have_skills"]))
    if parsed_jd.get("experience_level"):
        parts.append(f"Experience level: {parsed_jd['experience_level']}")
    if parsed_jd.get("role_type"):
        parts.append(f"Role type: {parsed_jd['role_type']}")
    return " | ".join(parts)


def _build_candidate_text(cand: Dict[str, Any]) -> str:
    """Compose a single string from parsed candidate fields for embedding."""
    parts = []
    if cand.get("name"):
        parts.append(cand["name"])
    if cand.get("summary"):
        parts.append(cand["summary"])
    if cand.get("skills"):
        parts.append("Skills: " + ", ".join(cand["skills"]))
    if cand.get("experience_years") is not None:
        parts.append(f"Experience: {cand['experience_years']} years")
    if cand.get("education"):
        parts.append(cand["education"])
    return " | ".join(parts)


def retrieve_candidates(
    parsed_jd: Dict[str, Any],
    parsed_resumes: List[Dict[str, Any]],
    top_k: int = 20,
) -> List[Dict[str, Any]]:
    """
    Main retrieval entry-point.

    1. Index the parsed resumes into Qdrant (in-memory or cloud).
    2. Embed the JD query.
    3. Search Qdrant for the top-k most similar candidates.
    4. If Qdrant fails, fall back to raw cosine similarity.
    """
    # Build text representations
    candidate_texts = [_build_candidate_text(c) for c in parsed_resumes]
    query_text = _build_jd_query(parsed_jd)

    logger.info("Retrieval: embedding %d candidates + 1 JD query", len(parsed_resumes))

    # Embed everything
    candidate_vectors = embed_batch(candidate_texts)
    query_vector = embed_text(query_text)

    # Determine vector dimension from actual embeddings
    vec_dim = len(query_vector)

    # --- Try Qdrant path ---
    try:
        ensure_collection("candidates", vector_size=vec_dim)
        upsert_candidates(parsed_resumes, candidate_vectors, "candidates")
        results = search_candidates(query_vector, top_k=min(top_k, len(parsed_resumes)), collection_name="candidates")
        if results:
            logger.info("Qdrant returned %d results", len(results))
            return results
    except Exception as e:
        logger.warning("Qdrant retrieval failed (%s), using in-memory fallback", e)

    # --- Fallback: in-memory cosine similarity ---
    logger.info("Using in-memory cosine similarity fallback")
    scored = []
    for cand, vec in zip(parsed_resumes, candidate_vectors):
        sim = cosine_similarity(query_vector, vec)
        enriched = dict(cand)
        enriched["_score"] = sim
        scored.append(enriched)

    scored.sort(key=lambda x: x["_score"], reverse=True)
    return scored[:top_k]
