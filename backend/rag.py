"""
RAG (Retrieval-Augmented Generation) service.

Pipeline:
  1. Embed the user question (FAISS)
  2. Retrieve top-K relevant interview records from PostgreSQL
  3. Construct a grounded prompt
  4. Call LLM (Groq if available, otherwise Ollama)
  5. Cache the response in Redis
  6. Return answer + source interviews
"""
import hashlib
import json
import logging
import os
from typing import Dict, List, Optional

import redis as redis_lib
from dotenv import load_dotenv

from backend.db import get_interviews_by_ids
from ml.embeddings import search as faiss_search
from ml.llm_client import call_llm

load_dotenv()

logger = logging.getLogger(__name__)

REDIS_URL     = os.getenv("REDIS_URL", "redis://localhost:6379/0")
LLM_CACHE_TTL = int(os.getenv("LLM_CACHE_TTL_SECONDS", "3600"))
RAG_TOP_K     = 5

_redis: Optional[redis_lib.Redis] = None


def _get_redis() -> Optional[redis_lib.Redis]:
    global _redis
    if _redis is None:
        try:
            _redis = redis_lib.from_url(REDIS_URL, decode_responses=True)
            _redis.ping()
        except Exception as exc:
            logger.warning("Redis unavailable — LLM caching disabled: %s", exc)
            _redis = None
    return _redis


def _cache_key(question: str) -> str:
    return "rag:" + hashlib.md5(question.lower().strip().encode()).hexdigest()


def _from_cache(key: str) -> Optional[Dict]:
    r = _get_redis()
    if r:
        try:
            val = r.get(key)
            return json.loads(val) if val else None
        except Exception:
            pass
    return None


def _to_cache(key: str, data: Dict) -> None:
    r = _get_redis()
    if r:
        try:
            r.setex(key, LLM_CACHE_TTL, json.dumps(data, default=str))
        except Exception:
            pass


# ─── Context builder ──────────────────────────────────────────────────────────

def _build_context(interviews: List[Dict]) -> str:
    parts = []
    for i, iview in enumerate(interviews, 1):
        company  = iview.get("company") or "Unknown"
        role     = iview.get("role") or "Unknown"
        status   = iview.get("offer_status") or "unknown"
        topics   = ", ".join(iview.get("topics") or []) or "N/A"
        questions = "; ".join((iview.get("questions") or [])[:5]) or "N/A"

        rounds_txt = ""
        for rnd in (iview.get("rounds") or [])[:4]:
            rnd_type = rnd.get("round_type", "Unknown")
            rnd_qs   = ", ".join((rnd.get("questions") or [])[:3]) or "—"
            rounds_txt += f"      Round {rnd.get('round_number', '?')} ({rnd_type}): {rnd_qs}\n"

        parts.append(
            f"[Interview {i}] {company} — {role} (result: {status})\n"
            f"  Topics:    {topics}\n"
            f"  Questions: {questions}\n"
            f"  Rounds:\n{rounds_txt}"
        )
    return "\n".join(parts)


# ─── Prompt ───────────────────────────────────────────────────────────────────

_SYSTEM = (
    "You are PrepAI, an expert career coach specialised in software engineering interviews. "
    "Answer the user's question using ONLY the interview data provided below. "
    "Be specific, practical, and cite interview details when relevant. "
    "Do NOT invent information not present in the context."
)


def _build_user_prompt(question: str, context: str) -> str:
    return (
        f"--- INTERVIEW DATA ---\n{context}\n"
        f"--- END OF DATA ---\n\n"
        f"User question: {question}\n\n"
        f"Answer:"
    )




# ─── Public API ───────────────────────────────────────────────────────────────

def answer(question: str, session_id: Optional[str] = None) -> Dict:
    """
    RAG pipeline entry point.
    Returns:
      {
        "answer": str,
        "sources": [{ "company", "role", "offer_status", "topics" }],
        "cached": bool
      }
    """
    if not question.strip():
        return {"answer": "Please provide a question.", "sources": [], "cached": False}

    key    = _cache_key(question)
    cached = _from_cache(key)
    if cached:
        cached["cached"] = True
        return cached

    # 1. Retrieve
    hits = faiss_search(question, top_k=RAG_TOP_K)
    if not hits:
        return {
            "answer": (
                "I don't have enough interview data indexed yet. "
                "Please run the pipeline to load interview data first."
            ),
            "sources": [],
            "cached": False,
        }

    pg_ids     = [pg_id for pg_id, _ in hits]
    interviews = get_interviews_by_ids(pg_ids)

    if not interviews:
        return {
            "answer": "No matching interview data found for your question.",
            "sources": [],
            "cached": False,
        }

    # 2. Build prompt
    context = _build_context(interviews)
    user_prompt = _build_user_prompt(question, context)

    # 3. Generate (Groq if available, else Ollama)
    answer_text = call_llm(user_prompt, system_prompt=_SYSTEM, temperature=0.3)
    if answer_text is None:
        answer_text = (
            "The AI model is not available right now. "
            "If running locally, ensure Ollama is running: `ollama serve`. "
            "For cloud hosting, set GROQ_API_KEY in your environment."
        )

    # 4. Build response
    sources = [
        {
            "company":      i.get("company", ""),
            "role":         i.get("role", ""),
            "offer_status": i.get("offer_status", ""),
            "topics":       i.get("topics", []),
        }
        for i in interviews
    ]

    result = {"answer": answer_text, "sources": sources, "cached": False}
    _to_cache(key, result)
    return result
