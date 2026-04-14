"""
Search service — combines PostgreSQL structured filters with FAISS semantic retrieval.
Results are cached in Redis to avoid redundant DB / index hits.
"""
import hashlib
import json
import logging
import os
from typing import Dict, List, Optional

import redis as redis_lib
from dotenv import load_dotenv

from backend.db import get_interviews_by_ids, query_interviews
from ml.embeddings import search as faiss_search

load_dotenv()

logger = logging.getLogger(__name__)

REDIS_URL       = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL       = int(os.getenv("CACHE_TTL_SECONDS", "300"))
SEMANTIC_TOP_K  = 10

_redis: Optional[redis_lib.Redis] = None


def _get_redis() -> Optional[redis_lib.Redis]:
    global _redis
    if _redis is None:
        try:
            _redis = redis_lib.from_url(REDIS_URL, decode_responses=True)
            _redis.ping()
        except Exception as exc:
            logger.warning("Redis unavailable — search caching disabled: %s", exc)
            _redis = None
    return _redis


def _cache_key(prefix: str, **kwargs) -> str:
    raw = json.dumps(kwargs, sort_keys=True)
    return f"{prefix}:{hashlib.md5(raw.encode()).hexdigest()}"


def _from_cache(key: str) -> Optional[List[Dict]]:
    r = _get_redis()
    if r is None:
        return None
    try:
        val = r.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


def _to_cache(key: str, data: List[Dict], ttl: int = CACHE_TTL) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        r.setex(key, ttl, json.dumps(data, default=str))
    except Exception as exc:
        logger.warning("Cache write failed: %s", exc)


# ─── Structured Search ────────────────────────────────────────────────────────

def structured_search(
    company: Optional[str] = None,
    role: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict]:
    """Filter-based search backed by PostgreSQL."""
    cache_key = _cache_key("struct", company=company, role=role, topic=topic, limit=limit, offset=offset)
    cached = _from_cache(cache_key)
    if cached is not None:
        return cached

    results = query_interviews(company=company, role=role, topic=topic, limit=limit, offset=offset)
    _to_cache(cache_key, results)
    return results


# ─── Semantic Search ──────────────────────────────────────────────────────────

def semantic_search(query: str, top_k: int = SEMANTIC_TOP_K) -> List[Dict]:
    """
    FAISS semantic retrieval followed by a PostgreSQL lookup.
    Returns interview records ordered by similarity score (descending).
    """
    if not query.strip():
        return []

    cache_key = _cache_key("sem", query=query, top_k=top_k)
    cached = _from_cache(cache_key)
    if cached is not None:
        return cached

    hits = faiss_search(query, top_k=top_k)
    if not hits:
        return []

    pg_ids  = [pg_id for pg_id, _ in hits]
    score_map = {pg_id: score for pg_id, score in hits}

    records = get_interviews_by_ids(pg_ids)
    # Attach similarity score and sort
    for rec in records:
        rec["similarity_score"] = round(score_map.get(rec["id"], 0.0), 4)
    records.sort(key=lambda r: r["similarity_score"], reverse=True)

    _to_cache(cache_key, records)
    return records


# ─── Hybrid Search ────────────────────────────────────────────────────────────

def hybrid_search(
    query: Optional[str] = None,
    company: Optional[str] = None,
    role: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict:
    """
    Combine semantic FAISS results with structured PostgreSQL filters.
    If a free-text query is supplied, semantic results are prepended;
    structured results fill the remainder.
    """
    seen_ids: set = set()
    combined: List[Dict] = []

    # 1. Semantic results (if query provided)
    if query:
        sem_results = semantic_search(query, top_k=limit)
        for r in sem_results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                combined.append(r)

    # 2. Structured results
    if company or role or topic:
        struct_results = structured_search(
            company=company, role=role, topic=topic,
            limit=limit, offset=offset,
        )
        for r in struct_results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                combined.append(r)

    # 3. Fallback — recent interviews if nothing provided
    if not combined:
        combined = structured_search(limit=limit, offset=offset)

    # Filter out records with no company identified (noise)
    if query or company:
        combined = [r for r in combined if r.get("company") and r["company"].strip()]

    return {
        "results":     combined[:limit],
        "total":       len(combined),
        "has_more":    len(combined) > limit,
    }
