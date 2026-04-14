"""
Personalised study roadmap generator.

Input:  company, role, time_available (weeks), experience_level
Output: week-by-week topic plan backed by real interview data.

Strategy:
  1. Query DB for relevant interviews (company + role)
  2. Rank topics by frequency in the dataset
  3. Apply experience-level weight adjustments
  4. Assign topics to weeks (LLM enhances the description when available)
"""
import logging
from collections import Counter
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

from backend.db import query_interviews
from ml.llm_client import call_llm

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Topic meta ───────────────────────────────────────────────────────────────
# importance_score: how often it appears in senior-level interviews (heuristic)
# experience_weight: multiplier applied to beginner (1.5), intermediate (1.0), advanced (0.7)

_TOPIC_META: Dict[str, Dict] = {
    "Arrays":              {"base_importance": 1.0, "beginner_bonus": 1.5},
    "Hash Map":            {"base_importance": 1.0, "beginner_bonus": 1.4},
    "Two Pointers":        {"base_importance": 0.9, "beginner_bonus": 1.3},
    "Sliding Window":      {"base_importance": 0.9, "beginner_bonus": 1.2},
    "Binary Search":       {"base_importance": 0.9, "beginner_bonus": 1.2},
    "Stack":               {"base_importance": 0.8, "beginner_bonus": 1.3},
    "Queue":               {"base_importance": 0.7, "beginner_bonus": 1.2},
    "Linked List":         {"base_importance": 0.8, "beginner_bonus": 1.3},
    "Tree":                {"base_importance": 1.0, "beginner_bonus": 1.0},
    "Graph":               {"base_importance": 1.0, "beginner_bonus": 0.9},
    "BFS":                 {"base_importance": 0.9, "beginner_bonus": 1.0},
    "DFS":                 {"base_importance": 0.9, "beginner_bonus": 1.0},
    "Dynamic Programming": {"base_importance": 1.2, "beginner_bonus": 0.7},
    "Greedy":              {"base_importance": 0.8, "beginner_bonus": 0.9},
    "Backtracking":        {"base_importance": 0.8, "beginner_bonus": 0.8},
    "Heap":                {"base_importance": 0.9, "beginner_bonus": 0.9},
    "Trie":                {"base_importance": 0.7, "beginner_bonus": 0.8},
    "System Design":       {"base_importance": 1.3, "beginner_bonus": 0.5},
    "Object Oriented Design": {"base_importance": 1.0, "beginner_bonus": 0.7},
    "Behavioral":          {"base_importance": 0.8, "beginner_bonus": 1.0},
    "SQL":                 {"base_importance": 0.6, "beginner_bonus": 1.0},
    "Concurrency":         {"base_importance": 0.7, "beginner_bonus": 0.6},
    "String Manipulation": {"base_importance": 0.8, "beginner_bonus": 1.2},
    "Bit Manipulation":    {"base_importance": 0.6, "beginner_bonus": 0.7},
}

_EXPERIENCE_MULTIPLIER = {"beginner": 1.5, "intermediate": 1.0, "advanced": 0.7}

TOPICS_PER_WEEK = 3


# ─── Scoring ──────────────────────────────────────────────────────────────────

def _score_topics(
    topic_counts: Counter,
    experience_level: str,
) -> List[Tuple[str, float]]:
    """
    Compute a weighted importance score for each topic.
    Returns [(topic, score)] sorted descending.
    """
    exp_mult = _EXPERIENCE_MULTIPLIER.get(experience_level.lower(), 1.0)
    scored: List[Tuple[str, float]] = []

    for topic, freq in topic_counts.items():
        meta  = _TOPIC_META.get(topic, {"base_importance": 0.5, "beginner_bonus": 1.0})
        bonus = meta["beginner_bonus"] if experience_level == "beginner" else 1.0
        score = freq * meta["base_importance"] * bonus * exp_mult
        scored.append((topic, round(score, 3)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def _assign_weeks(
    scored_topics: List[Tuple[str, float]],
    weeks: int,
) -> List[Dict]:
    """
    Assign topics to weeks.
    First few weeks get foundational topics; later weeks get advanced ones.
    Always ends with a revision + mock week.
    """
    plan_weeks = max(1, weeks - 1)    # last week = mock interviews / revision
    slots      = plan_weeks * TOPICS_PER_WEEK
    topics_to_assign = [t for t, _ in scored_topics[:slots]]

    week_plan: List[Dict] = []
    for w in range(1, plan_weeks + 1):
        start = (w - 1) * TOPICS_PER_WEEK
        batch = topics_to_assign[start : start + TOPICS_PER_WEEK]
        if not batch:
            break
        week_plan.append({"week": w, "topics": batch, "focus": "Study + Practice"})

    # Final week
    week_plan.append({
        "week":   weeks,
        "topics": ["Mock Interviews", "Weak Area Review", "Behavioral Prep"],
        "focus":  "Mock Interviews & Revision",
    })
    return week_plan


# ─── LLM enhancement ──────────────────────────────────────────────────────────

def _enrich_with_llm(
    company: str,
    role: str,
    experience_level: str,
    week_plan: List[Dict],
    top_questions: List[str],
) -> Optional[str]:
    """
    Ask the LLM to write a one-paragraph narrative and daily tips for the plan.
    Returns a string with additional context, or None if Ollama is unavailable.
    """
    plan_str = "\n".join(
        f"Week {w['week']}: {', '.join(w['topics'])} — {w['focus']}"
        for w in week_plan
    )
    questions_str = "\n".join(f"- {q}" for q in top_questions[:8])

    prompt = (
        f"You are a senior engineer helping a {experience_level}-level candidate prepare "
        f"for a {role} interview at {company}.\n\n"
        f"Based on real interview data, the top questions asked were:\n{questions_str}\n\n"
        f"Here is their {len(week_plan)}-week study plan:\n{plan_str}\n\n"
        f"Write 2-3 concise sentences of personalised advice for this candidate: "
        f"what to focus on first, a common pitfall to avoid, and an encouragement tip."
    )

    result = call_llm(prompt, temperature=0.5)
    if result is None:
        logger.warning("LLM enrichment unavailable")
    return result


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_roadmap(
    company: str,
    role: str,
    time_available: int,
    experience_level: str,
) -> Dict:
    """
    Generate a personalised week-wise study roadmap.

    Returns:
    {
      "company": str,
      "role": str,
      "experience_level": str,
      "weeks": int,
      "week_plan": [{"week": int, "topics": [...], "focus": str}],
      "top_questions": [...],
      "top_topics": [...],
      "llm_advice": str | null,
      "data_source_count": int
    }
    """
    weeks = max(1, min(time_available, 24))

    # 1. Retrieve relevant interviews
    interviews = query_interviews(company=company, role=role, limit=300)

    # If no exact match, fall back to role-only
    if not interviews:
        interviews = query_interviews(role=role, limit=200)

    # Ultimate fallback — generic popular topics
    if not interviews:
        logger.warning("No interviews found for %s/%s — using defaults", company, role)
        default_topics: Counter = Counter({
            "Arrays": 50, "Dynamic Programming": 40, "Graph": 35,
            "Tree": 35, "System Design": 30, "Behavioral": 25,
            "Binary Search": 25, "Hash Map": 45, "Two Pointers": 30,
        })
        scored = _score_topics(default_topics, experience_level)
        week_plan = _assign_weeks(scored, weeks)
        return {
            "company": company,
            "role": role,
            "experience_level": experience_level,
            "weeks": weeks,
            "week_plan": week_plan,
            "top_questions": [],
            "top_topics": [t for t, _ in scored[:10]],
            "llm_advice": None,
            "data_source_count": 0,
        }

    # 2. Aggregate topics and questions
    topic_counter:    Counter = Counter()
    question_counter: Counter = Counter()
    for iview in interviews:
        for t in iview.get("topics") or []:
            topic_counter[t] += 1
        for q in iview.get("questions") or []:
            question_counter[q] += 1

    # 3. Score and plan
    scored    = _score_topics(topic_counter, experience_level)
    week_plan = _assign_weeks(scored, weeks)

    top_questions = [q for q, _ in question_counter.most_common(15)]
    top_topics    = [t for t, _ in scored[:10]]

    # 4. Enrich with LLM narrative
    llm_advice = _enrich_with_llm(company, role, experience_level, week_plan, top_questions)

    return {
        "company":           company,
        "role":              role,
        "experience_level":  experience_level,
        "weeks":             weeks,
        "week_plan":         week_plan,
        "top_questions":     top_questions,
        "top_topics":        top_topics,
        "llm_advice":        llm_advice,
        "data_source_count": len(interviews),
    }
