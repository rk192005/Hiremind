"""
Qdrant client wrapper — supports both Qdrant Cloud and local in-memory mode.
"""
from __future__ import annotations

import os
import logging
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    """Return a singleton QdrantClient, creating it on first call."""
    global _client
    if _client is not None:
        return _client

    from qdrant_client import QdrantClient

    url = os.getenv("QDRANT_URL", "").strip()
    api_key = os.getenv("QDRANT_API_KEY", "").strip()

    if url:
        logger.info("Connecting to Qdrant Cloud: %s", url)
        _client = QdrantClient(url=url, api_key=api_key or None)
    else:
        logger.info("Using Qdrant in-memory mode (no QDRANT_URL set)")
        _client = QdrantClient(location=":memory:")

    return _client


def ensure_collection(
    collection_name: str = "candidates",
    vector_size: int = 384,
) -> None:
    """Create the collection if it doesn't already exist."""
    from qdrant_client.models import Distance, VectorParams

    client = _get_client()
    collections = [c.name for c in client.get_collections().collections]
    if collection_name not in collections:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection '%s' (dim=%d)", collection_name, vector_size)
    else:
        logger.info("Qdrant collection '%s' already exists", collection_name)


def upsert_candidates(
    candidates: List[Dict[str, Any]],
    vectors: List[List[float]],
    collection_name: str = "candidates",
) -> None:
    """Upsert candidate documents with their embedding vectors."""
    from qdrant_client.models import PointStruct

    client = _get_client()
    points = []
    for i, (cand, vec) in enumerate(zip(candidates, vectors)):
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, cand.get("name", str(i))))
        points.append(
            PointStruct(
                id=point_id,
                vector=vec,
                payload=cand,
            )
        )

    client.upsert(collection_name=collection_name, points=points)
    logger.info("Upserted %d candidates into '%s'", len(points), collection_name)


def search_candidates(
    query_vector: List[float],
    top_k: int = 20,
    collection_name: str = "candidates",
) -> List[Dict[str, Any]]:
    """Search for candidates similar to the query vector."""
    client = _get_client()

    # qdrant-client >= 1.17 uses query_points; older versions use search
    try:
        results = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
        )
        # query_points returns a QueryResponse with .points
        points = results.points if hasattr(results, 'points') else results
    except (AttributeError, TypeError):
        # Fallback for older qdrant-client
        results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
        )
        points = results

    candidates = []
    for hit in points:
        cand = dict(hit.payload) if hit.payload else {}
        cand["_score"] = hit.score
        cand["_id"] = str(hit.id)
        candidates.append(cand)
    return candidates


def get_collection_count(collection_name: str = "candidates") -> int:
    """Return the number of points in a collection."""
    try:
        client = _get_client()
        info = client.get_collection(collection_name)
        return info.points_count or 0
    except Exception:
        return 0
