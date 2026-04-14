"""
LLM-based structured extraction.

Given the raw text of a Reddit interview post, returns a structured dict with:
  company, role, offer_status, rounds, oa, topics, questions, prep_insights

Uses Groq if GROQ_API_KEY is set, otherwise falls back to local Ollama.
"""
import json
import logging
import os
import re
from typing import Dict, Optional

from dotenv import load_dotenv

from ml.llm_client import call_llm, check_llm_available, llm_provider
from utils.helpers import clean_text, extract_company_from_text, is_useful_record, normalize_company, normalize_role, safe_json_loads, truncate_text

load_dotenv()

logger = logging.getLogger(__name__)  # seconds

# ─── Prompt ───────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a precise JSON extraction engine for software engineering interview reports.
Extract structured data from the given Reddit post and return ONLY a valid JSON object — no prose, no markdown fences, no extra keys.

RULES:
1. Return ONLY a valid JSON object starting with { and ending with }.
2. Do NOT hallucinate or invent information not present in the text.
3. Do NOT return vague phrases like "graph problem" or "coding challenge".
4. Map questions to canonical LeetCode problem names where possible (e.g. "Two Sum", "LRU Cache").
5. If a field cannot be determined, use null for strings/objects or [] for arrays.
6. offer_status must be one of: "offered", "rejected", "no_offer", "pending", "unknown".
7. round_type must be one of: "Behavioral", "DSA", "OOD", "System Design", "Technical Screen", "HR", "Bar Raiser", "Unknown".
8. topics must use canonical names: "Arrays", "Hash Map", "Two Pointers", "Sliding Window",
   "Binary Search", "Stack", "Queue", "Linked List", "Tree", "Graph", "BFS", "DFS",
   "Dynamic Programming", "Greedy", "Backtracking", "Recursion", "Heap", "Trie",
   "Sorting", "String Manipulation", "Bit Manipulation", "Math", "Database", "SQL",
   "System Design", "Object Oriented Design", "Behavioral", "Concurrency", "OS".
"""

_USER_TEMPLATE = """Post text:
\"\"\"
{text}
\"\"\"

Return a JSON object with this exact schema:
{{
  "company": "<string | null>",
  "role": "<string | null>",
  "offer_status": "<offered|rejected|no_offer|pending|unknown>",
  "rounds": [
    {{
      "round_number": <int>,
      "round_type": "<Behavioral|DSA|OOD|System Design|Technical Screen|HR|Bar Raiser|Unknown>",
      "questions": ["<canonical problem name>"]
    }}
  ],
  "oa": {{
    "question_type": "<string | null>",
    "difficulty": "<Easy|Medium|Hard|Mixed|null>"
  }},
  "topics": ["<canonical topic>"],
  "questions": ["<canonical problem name>"],
  "prep_insights": {{
    "questions_solved": <int | null>,
    "weak_areas": ["<topic>"]
  }}
}}"""


# ─── LLM availability check ───────────────────────────────────────────────────

def check_ollama_available() -> bool:
    """Kept for backwards compatibility — delegates to check_llm_available."""
    return check_llm_available()


# ─── Post-processing helpers ──────────────────────────────────────────────────

_VALID_OFFER_STATUSES = {"offered", "rejected", "no_offer", "pending", "unknown"}
_VALID_ROUND_TYPES = {
    "Behavioral", "DSA", "OOD", "System Design",
    "Technical Screen", "HR", "Bar Raiser", "Unknown",
}
_VALID_DIFFICULTIES = {"Easy", "Medium", "Hard", "Mixed"}


def _sanitize(data: Dict) -> Dict:
    # If LLM missed the company, try regex fallback on the raw fields
    raw_company = data.get("company") or ""
    if not raw_company or raw_company.lower() in ("unknown", "n/a", "none", ""):
        raw_company = ""
    data["company"] = normalize_company(raw_company)
    data["role"]         = normalize_role(data.get("role") or "")
    status               = (data.get("offer_status") or "unknown").lower().replace(" ", "_")
    data["offer_status"] = status if status in _VALID_OFFER_STATUSES else "unknown"

    # Sanitize rounds
    clean_rounds = []
    for r in data.get("rounds") or []:
        if not isinstance(r, dict):
            continue
        r["round_type"] = r.get("round_type", "Unknown")
        if r["round_type"] not in _VALID_ROUND_TYPES:
            r["round_type"] = "Unknown"
        r["questions"] = [q for q in (r.get("questions") or []) if isinstance(q, str) and len(q) > 2]
        clean_rounds.append(r)
    data["rounds"] = clean_rounds

    # Sanitize OA
    oa = data.get("oa") or {}
    if isinstance(oa, dict):
        diff = oa.get("difficulty")
        oa["difficulty"] = diff if diff in _VALID_DIFFICULTIES else None
        data["oa"] = oa
    else:
        data["oa"] = {}

    # Sanitize lists
    data["topics"]    = [t for t in (data.get("topics") or []) if isinstance(t, str) and len(t) > 1]
    data["questions"] = [q for q in (data.get("questions") or []) if isinstance(q, str) and len(q) > 2]

    # Sanitize prep_insights
    pi = data.get("prep_insights") or {}
    if not isinstance(pi, dict):
        pi = {}
    pi["weak_areas"] = [w for w in (pi.get("weak_areas") or []) if isinstance(w, str)]
    data["prep_insights"] = pi

    return data


# ─── Public API ───────────────────────────────────────────────────────────────

_EMPTY_EXTRACTION: Dict = {
    "company":       "",
    "role":          "",
    "offer_status":  "unknown",
    "rounds":        [],
    "oa":            {},
    "topics":        [],
    "questions":     [],
    "prep_insights": {"questions_solved": None, "weak_areas": []},
}


def extract_with_llm(text: str) -> Dict:
    """
    Extract structured interview data from raw post text.
    Uses Groq if available, otherwise Ollama.
    Returns a sanitized dict even on failure (never raises).
    """
    text = clean_text(text)
    if not text or len(text) < 50:
        logger.warning("Text too short to extract — skipping")
        return dict(_EMPTY_EXTRACTION)

    raw = call_llm(
        prompt=_USER_TEMPLATE.format(text=truncate_text(text, 3000)),
        system_prompt=_SYSTEM_PROMPT,
        temperature=0.0,
    )

    if raw is None:
        return dict(_EMPTY_EXTRACTION)

    parsed = safe_json_loads(raw)
    if parsed is None:
        logger.warning("LLM returned non-JSON; raw snippet: %s", raw[:200])
        return dict(_EMPTY_EXTRACTION)

    try:
        return _sanitize(parsed)
    except Exception as exc:
        logger.error("Sanitization error: %s", exc)
        return dict(_EMPTY_EXTRACTION)


def batch_extract(records: list, verbose: bool = True) -> list:
    """
    Process a list of {reddit_id, full_text, score} dicts and return
    a list of enriched extraction dicts ready for DB insertion.
    """
    results = []
    skipped = 0
    for i, rec in enumerate(records):
        if verbose:
            logger.info("Extracting %d/%d — reddit_id=%s", i + 1, len(records), rec.get("reddit_id"))
        raw_text  = rec.get("full_text", "")
        extracted = extract_with_llm(raw_text)

        # Regex fallback: if LLM returned no company, scan the raw text
        if not extracted.get("company"):
            fallback = extract_company_from_text(raw_text)
            if fallback:
                extracted["company"] = fallback
                logger.info("Regex fallback found company: %s", fallback)

        extracted["reddit_id"] = rec.get("reddit_id")
        extracted["raw_text"]  = raw_text
        extracted["score"]     = rec.get("score", 0)

        # Skip noise posts with no useful signal
        if not is_useful_record(extracted):
            skipped += 1
            logger.info("Skipping noise post reddit_id=%s (no signal)", rec.get("reddit_id"))
            continue

        results.append(extracted)

    if skipped:
        logger.info("Skipped %d noise posts (no company/role/topics/questions)", skipped)
    return results
