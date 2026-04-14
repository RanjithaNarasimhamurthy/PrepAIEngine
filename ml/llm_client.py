"""
Unified LLM client — Groq (cloud) with Ollama (local) fallback.

Priority:
  1. Groq  — if GROQ_API_KEY is set in the environment
  2. Ollama — local fallback (requires: ollama serve)

Set in .env:
  GROQ_API_KEY=gsk_...          # enables Groq
  GROQ_MODEL=llama3-8b-8192     # optional override (default: llama3-8b-8192)
  OLLAMA_BASE_URL=http://localhost:11434
  OLLAMA_MODEL=llama3
"""
import logging
import os
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama3-8b-8192")
_GROQ_URL    = "https://api.groq.com/openai/v1/chat/completions"

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3")

TIMEOUT = 120


# ─── Groq ─────────────────────────────────────────────────────────────────────

def _call_groq(
    prompt: str,
    system_prompt: Optional[str],
    temperature: float,
) -> Optional[str]:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = requests.post(
            _GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "temperature": temperature,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.HTTPError as exc:
        logger.error("Groq HTTP error: %s — %s", exc, resp.text[:300])
        return None
    except requests.exceptions.Timeout:
        logger.error("Groq request timed out after %ds", TIMEOUT)
        return None
    except Exception as exc:
        logger.error("Groq error: %s", exc)
        return None


# ─── Ollama ───────────────────────────────────────────────────────────────────

def _call_ollama(
    prompt: str,
    system_prompt: Optional[str],
    temperature: float,
) -> Optional[str]:
    full_prompt = (system_prompt + "\n\n" + prompt) if system_prompt else prompt
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "options": {"temperature": temperature, "top_p": 0.9},
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        logger.error(
            "Ollama is not running at %s — start it with: ollama serve",
            OLLAMA_BASE_URL,
        )
        return None
    except requests.exceptions.Timeout:
        logger.error("Ollama request timed out after %ds", TIMEOUT)
        return None
    except Exception as exc:
        logger.error("Ollama error: %s", exc)
        return None


# ─── Public API ───────────────────────────────────────────────────────────────

def call_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.0,
) -> Optional[str]:
    """
    Call the best available LLM backend.

    - Uses Groq if GROQ_API_KEY is set (fast, free tier available).
    - Falls back to Ollama for local / offline use.

    Returns the model's text response, or None on failure.
    """
    if GROQ_API_KEY:
        logger.debug("LLM provider: Groq (%s)", GROQ_MODEL)
        result = _call_groq(prompt, system_prompt, temperature)
        if result is not None:
            return result
        logger.warning("Groq failed — falling back to Ollama")

    logger.debug("LLM provider: Ollama (%s)", OLLAMA_MODEL)
    return _call_ollama(prompt, system_prompt, temperature)


def llm_provider() -> str:
    """Return which provider will be used — useful for health checks."""
    return f"groq ({GROQ_MODEL})" if GROQ_API_KEY else f"ollama ({OLLAMA_MODEL})"


def check_llm_available() -> bool:
    """Quick connectivity check — Groq via a tiny API ping, Ollama via /api/tags."""
    if GROQ_API_KEY:
        try:
            resp = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False
    else:
        try:
            resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
