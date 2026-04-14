"""
Analytics service — aggregates interview data for dashboard visualisation.
Results are cached in Redis with a long TTL because they change infrequently.
"""
import json
import logging
import os
from collections import Counter
from typing import Dict, List, Optional

import redis as redis_lib
from dotenv import load_dotenv

from backend.db import get_analytics_data, query_interviews

load_dotenv()

logger = logging.getLogger(__name__)

REDIS_URL     = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ANALYTICS_TTL = 600   # 10 minutes

_redis: Optional[redis_lib.Redis] = None
_CACHE_KEY = "analytics:dashboard"


def _get_redis() -> Optional[redis_lib.Redis]:
    global _redis
    if _redis is None:
        try:
            _redis = redis_lib.from_url(REDIS_URL, decode_responses=True)
            _redis.ping()
        except Exception as exc:
            logger.warning("Redis unavailable — analytics caching disabled: %s", exc)
            _redis = None
    return _redis


def _cached() -> Optional[Dict]:
    r = _get_redis()
    if r:
        try:
            val = r.get(_CACHE_KEY)
            return json.loads(val) if val else None
        except Exception:
            pass
    return None


def _cache(data: Dict) -> None:
    r = _get_redis()
    if r:
        try:
            r.setex(_CACHE_KEY, ANALYTICS_TTL, json.dumps(data, default=str))
        except Exception:
            pass


# ─── Round-type analysis ──────────────────────────────────────────────────────

def _round_type_distribution(interviews: List[Dict]) -> List[Dict]:
    counter: Counter = Counter()
    for iview in interviews:
        for rnd in iview.get("rounds") or []:
            rt = rnd.get("round_type", "Unknown")
            counter[rt] += 1
    return [{"name": k, "count": v} for k, v in counter.most_common()]


# ─── Public API ───────────────────────────────────────────────────────────────

def get_dashboard_analytics(company_filter: Optional[str] = None) -> Dict:
    """
    Return aggregated analytics for the dashboard.
    When company_filter is supplied, per-company drill-down stats are included.
    """
    # Serve from cache when no filter is applied
    if not company_filter:
        cached = _cached()
        if cached:
            return cached

    base = get_analytics_data()

    # If filtering by company, compute round-type breakdown for that company
    if company_filter:
        company_interviews = query_interviews(company=company_filter, limit=500)
        base["round_type_distribution"] = _round_type_distribution(company_interviews)
        base["filtered_company"] = company_filter
    else:
        # Global round-type distribution (sampled — fetch top-500)
        all_interviews = query_interviews(limit=500)
        base["round_type_distribution"] = _round_type_distribution(all_interviews)

    if not company_filter:
        _cache(base)

    return base


def get_topic_heatmap() -> List[Dict]:
    """
    Returns topic frequency sorted descending — useful for heatmap / word-cloud.
    """
    data = get_analytics_data()
    return data.get("topics", [])


def get_company_stats(company: str) -> Dict:
    """
    Per-company summary: total, offer rate, top topics, top questions.
    """
    interviews = query_interviews(company=company, limit=500)
    if not interviews:
        return {"company": company, "total": 0}

    total = len(interviews)
    offered = sum(1 for i in interviews if i.get("offer_status") == "offered")
    rejected = sum(1 for i in interviews if i.get("offer_status") == "rejected")

    topic_counter: Counter = Counter()
    question_counter: Counter = Counter()
    for iview in interviews:
        for t in iview.get("topics") or []:
            topic_counter[t] += 1
        for q in iview.get("questions") or []:
            question_counter[q] += 1

    return {
        "company":      company,
        "total":        total,
        "offered":      offered,
        "rejected":     rejected,
        "offer_rate":   round(offered / total * 100, 1) if total else 0,
        "top_topics":   [{"name": k, "count": v} for k, v in topic_counter.most_common(10)],
        "top_questions": [{"name": k, "count": v} for k, v in question_counter.most_common(10)],
        "round_types":  _round_type_distribution(interviews),
    }
