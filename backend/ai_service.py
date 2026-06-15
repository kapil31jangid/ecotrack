"""
EcoTrack AI Service
-------------------
Two call paths — whichever works first:

1. Vertex AI REST API  — uses GCP service-account token from the metadata server.
   Works automatically on Cloud Run with NO API key. Requires the service account
   to have the "Vertex AI User" role.

2. Gemini Developer REST API — used if GEMINI_API_KEY env var is set.
   Useful for local development.

Falls back to static rule-based responses if both paths fail.
"""
import json
import logging
import hashlib
import os
from functools import lru_cache
from typing import Optional

import httpx

from backend.config import (
    GOOGLE_CLOUD_PROJECT,
    GEMINI_API_KEY,
    VERTEX_AI_LOCATION,
    VERTEX_AI_MODEL_PRIMARY,
    VERTEX_AI_MODEL_FALLBACK,
)

__all__ = ["get_ai_response", "get_ai_tips", "get_ai_insights"]

logger = logging.getLogger("ecotrack")

# ── Model identifiers ─────────────────────────────────────────────────────────
VERTEX_LOCATION  = VERTEX_AI_LOCATION
GEMINI_API_BASE  = "https://generativelanguage.googleapis.com/v1beta/models"

# ── Token budget constants ─────────────────────────────────────────────────────
_CHAT_MAX_TOKENS    = 400
_TIPS_MAX_TOKENS    = 800
_INSIGHTS_MAX_TOKENS = 150

# ── Bounded in-memory response cache (max 256 entries) ───────────────────────
_AI_CACHE_MAX_SIZE = 256
_ai_cache: dict[str, tuple[str, str]] = {}

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are EcoTrack AI, a world-class sustainability coach and climate expert, powered by Google Gemini.
You have deep knowledge across ALL sustainability topics:
- Carbon footprints and emissions (personal, household, national, global)
- Climate change science, IPCC reports, global warming targets (1.5°C, 2°C)
- Renewable energy: solar, wind, hydro, geothermal, nuclear
- Sustainable transport: EVs, public transit, cycling, aviation emissions
- Diet and food sustainability: veganism, vegetarianism, regenerative agriculture, food waste
- Energy efficiency: insulation, LED lighting, smart thermostats, appliances
- Circular economy, recycling, zero waste, plastic pollution
- Biodiversity, deforestation, ocean health, water conservation
- Carbon markets, carbon offsets, net zero pledges, ESG
- Sustainable fashion, ethical consumption, fast fashion impact
- Green finance, ESG investing, sustainability certifications
- Government policies, Paris Agreement, COP summits
- Individual vs systemic change, climate psychology, eco-anxiety
- India-specific sustainability: grid mix, monsoon patterns, rural energy access

Rules:
- Answer ALL sustainability-related questions thoroughly and with specific data/numbers
- For personal footprint questions, use the user's carbon data if provided
- Give SPECIFIC numbers when possible (e.g. "a return flight London-NYC emits ~1.7 tonnes CO2e")
- Keep responses concise (under 200 words) unless the user asks for more detail
- Warm, encouraging, never preachy or guilt-tripping
- End responses with one actionable next step or interesting fact
- If asked something completely unrelated to sustainability/environment, gently redirect
- Use emojis sparingly for warmth 🌱
"""


# ── Helper: get GCP access token from metadata server ────────────────────────
async def _get_gcp_token() -> str:
    """Fetch a short-lived OAuth2 token from the GCP metadata server (Cloud Run only)."""
    url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(url, headers={"Metadata-Flavor": "Google"})
    r.raise_for_status()
    return r.json()["access_token"]


# ── Shared response parser ─────────────────────────────────────────────────────
def _parse_gemini_response(data: dict) -> str:
    """Extract text from a Gemini/Vertex AI generateContent response dict."""
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("AI API returned no candidates")
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise ValueError("AI API candidate had no parts")
    return parts[0].get("text", "").strip()


# ── Path 1: Vertex AI REST ────────────────────────────────────────────────────
async def _call_vertex_ai(
    model: str,
    prompt: str,
    temperature: float = 0.7,
    max_output_tokens: int = _CHAT_MAX_TOKENS,
    response_mime_type: Optional[str] = None,
) -> str:
    """Call Vertex AI generateContent endpoint using the Cloud Run service-account token."""
    project = GOOGLE_CLOUD_PROJECT
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT not set")

    token = await _get_gcp_token()
    url = (
        f"https://{VERTEX_LOCATION}-aiplatform.googleapis.com/v1/"
        f"projects/{project}/locations/{VERTEX_LOCATION}/"
        f"publishers/google/models/{model}:generateContent"
    )

    payload: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }
    if any(m in model for m in ["2.0", "2.5"]):
        payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}
    if response_mime_type and "1.0-pro" not in model:
        payload["generationConfig"]["responseMimeType"] = response_mime_type

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )

    if resp.status_code != 200:
        raise RuntimeError(f"Vertex AI {resp.status_code}: {resp.text[:300]}")

    return _parse_gemini_response(resp.json())


# ── Path 2: Gemini Developer API ──────────────────────────────────────────────
async def _call_gemini_api(
    model: str,
    prompt: str,
    temperature: float = 0.7,
    max_output_tokens: int = _CHAT_MAX_TOKENS,
    response_mime_type: Optional[str] = None,
) -> str:
    """Call Google AI Studio Gemini REST API using an API key."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")

    url = f"{GEMINI_API_BASE}/{model}:generateContent?key={GEMINI_API_KEY}"
    payload: dict = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }
    if any(m in model for m in ["2.0", "2.5"]):
        payload["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}
    if response_mime_type and "1.0-pro" not in model:
        payload["generationConfig"]["responseMimeType"] = response_mime_type

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})

    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API {resp.status_code}: {resp.text[:300]}")

    return _parse_gemini_response(resp.json())


# ── Unified caller: try Vertex AI first, fall back to Gemini API key ──────────
async def _call_ai(
    prompt: str,
    temperature: float = 0.7,
    max_output_tokens: int = _CHAT_MAX_TOKENS,
    response_mime_type: Optional[str] = None,
) -> tuple[str, str]:
    """Returns (text, model_used). Tries Vertex AI then Gemini API key, respecting primary/fallback hierarchy."""
    # 1. Try Vertex AI with Primary Model
    try:
        text = await _call_vertex_ai(VERTEX_AI_MODEL_PRIMARY, prompt, temperature, max_output_tokens, response_mime_type)
        logger.info(f"AI response via Vertex AI REST (primary: {VERTEX_AI_MODEL_PRIMARY})")
        return text, VERTEX_AI_MODEL_PRIMARY
    except Exception as e:
        logger.warning(f"Vertex AI (primary: {VERTEX_AI_MODEL_PRIMARY}) failed: {e}")

    # 2. Try Vertex AI with Fallback Model
    try:
        text = await _call_vertex_ai(VERTEX_AI_MODEL_FALLBACK, prompt, temperature, max_output_tokens, response_mime_type)
        logger.info(f"AI response via Vertex AI REST (fallback: {VERTEX_AI_MODEL_FALLBACK})")
        return text, VERTEX_AI_MODEL_FALLBACK
    except Exception as e:
        logger.warning(f"Vertex AI (fallback: {VERTEX_AI_MODEL_FALLBACK}) failed: {e}")

    # 3. Try Gemini Developer API with Primary Model
    try:
        text = await _call_gemini_api(VERTEX_AI_MODEL_PRIMARY, prompt, temperature, max_output_tokens, response_mime_type)
        logger.info(f"AI response via Gemini Developer API (primary: {VERTEX_AI_MODEL_PRIMARY})")
        return text, VERTEX_AI_MODEL_PRIMARY
    except Exception as e:
        logger.warning(f"Gemini API (primary: {VERTEX_AI_MODEL_PRIMARY}) failed: {e}")

    # 4. Try Gemini Developer API with Fallback Model
    try:
        text = await _call_gemini_api(VERTEX_AI_MODEL_FALLBACK, prompt, temperature, max_output_tokens, response_mime_type)
        logger.info(f"AI response via Gemini Developer API (fallback: {VERTEX_AI_MODEL_FALLBACK})")
        return text, VERTEX_AI_MODEL_FALLBACK
    except Exception as e:
        logger.warning(f"Gemini API (fallback: {VERTEX_AI_MODEL_FALLBACK}) failed: {e}")

    raise RuntimeError("All AI providers failed")


# ── Cache helpers ─────────────────────────────────────────────────────────────
def _get_cache_key(message: str, footprint_context: Optional[dict], session_id: str) -> str:
    """Return a SHA-256 cache key for the given chat inputs."""
    ctx_str = json.dumps(footprint_context, sort_keys=True) if footprint_context else ""
    return hashlib.sha256(f"{session_id}:{message}:{ctx_str}".encode()).hexdigest()


def _cache_set(key: str, value: tuple[str, str]) -> None:
    """Insert into bounded cache, evicting oldest entry when full."""
    if len(_ai_cache) >= _AI_CACHE_MAX_SIZE:
        oldest_key = next(iter(_ai_cache))
        del _ai_cache[oldest_key]
    _ai_cache[key] = value


# ── Public API ────────────────────────────────────────────────────────────────

async def get_ai_response(
    message: str, footprint_context: Optional[dict], session_id: str
) -> tuple[str, str]:
    """Chat endpoint — returns (reply, model_used)."""
    cache_key = _get_cache_key(message, footprint_context, session_id)
    if cache_key in _ai_cache:
        logger.info(f"Cache hit for session {session_id}")
        return _ai_cache[cache_key]

    system = SYSTEM_PROMPT
    if footprint_context:
        system += f"\n\nUser's current carbon footprint data:\n{json.dumps(footprint_context, indent=2)}"

    prompt = f"{system}\n\nUser: {message}\n\nEcoTrack AI:"

    try:
        reply, model_used = await _call_ai(prompt, temperature=0.7, max_output_tokens=_CHAT_MAX_TOKENS)
        _cache_set(cache_key, (reply, model_used))
        return reply, model_used
    except Exception as e:
        logger.error(f"All AI providers failed for chat: {e}")
        static = (
            "I'm here to support your sustainability journey! "
            "Try switching off standby appliances as a quick win today. "
            "Ask me about transport, diet, or energy to get personalised tips!"
        )
        return static, "static-fallback"


async def get_ai_tips(input_data: dict, breakdown: dict) -> list[dict]:
    """Generate 5 personalised reduction tips."""
    total = sum(breakdown.get(c, 0.0) for c in ["transport", "diet", "energy", "shopping"])
    prompt = f"""{SYSTEM_PROMPT}

Generate exactly 5 personalised carbon reduction tips for this user.

User inputs:
- Transport: {input_data.get('transport_mode')} at {input_data.get('transport_km_per_week')} km/week
- Diet: {input_data.get('diet_type')}
- Energy: {input_data.get('energy_kwh_per_month')} kWh/month
- Shopping: {input_data.get('shopping_level')}

Monthly emissions (kg CO2e):
- Transport: {breakdown.get('transport', 0)} kg
- Diet: {breakdown.get('diet', 0)} kg
- Energy: {breakdown.get('energy', 0)} kg
- Shopping: {breakdown.get('shopping', 0)} kg
- Total: {total:.1f} kg

Return ONLY a JSON array of exactly 5 objects. Each object must have:
"action" (string), "saving_kg" (positive float), "difficulty" ("Easy"/"Medium"/"Hard"), "category" ("transport"/"diet"/"energy"/"shopping").
No markdown, no explanation, just the JSON array."""

    text, _ = await _call_ai(
        prompt,
        temperature=0.2,
        max_output_tokens=_TIPS_MAX_TOKENS,
        response_mime_type="application/json",
    )

    # Strip markdown fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("Tips response is not a list")

    validated: list[dict] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action", "")).strip()
        try:
            saving_kg = float(item.get("saving_kg", 0))
        except (TypeError, ValueError):
            saving_kg = 0.0
        difficulty = item.get("difficulty", "Medium")
        if difficulty not in ("Easy", "Medium", "Hard"):
            difficulty = "Medium"
        category = str(item.get("category", "")).lower()
        if category not in ("transport", "diet", "energy", "shopping"):
            category = "energy"
        if action and saving_kg > 0:
            validated.append({
                "action": action,
                "saving_kg": saving_kg,
                "difficulty": difficulty,
                "category": category,
            })

    if len(validated) < 3:
        raise ValueError(f"Only {len(validated)} valid tips returned")

    logger.info(f"Generated {len(validated)} AI tips")
    return validated[:5]


async def get_ai_insights(input_data: dict, breakdown: dict) -> str:
    """Generate 2-3 sentence personalised dashboard insight."""
    total = sum(breakdown.get(c, 0.0) for c in ["transport", "diet", "energy", "shopping"])
    prompt = f"""{SYSTEM_PROMPT}

Write a 2-3 sentence personalised coaching insight for this user's carbon footprint dashboard.

User inputs:
- Transport: {input_data.get('transport_mode')} at {input_data.get('transport_km_per_week')} km/week
- Diet: {input_data.get('diet_type')}
- Energy: {input_data.get('energy_kwh_per_month')} kWh/month
- Shopping: {input_data.get('shopping_level')}

Monthly emissions:
- Transport: {breakdown.get('transport', 0)} kg | Diet: {breakdown.get('diet', 0)} kg | Energy: {breakdown.get('energy', 0)} kg | Shopping: {breakdown.get('shopping', 0)} kg
- Total: {total:.1f} kg CO2e/month

Rules: Identify the highest emission category. Give positive reinforcement. Suggest one high-impact change.
Under 80 words. Plain text only, no markdown, no bullet points."""

    text, _ = await _call_ai(prompt, temperature=0.7, max_output_tokens=_INSIGHTS_MAX_TOKENS)
    logger.info("Generated AI dashboard insight")
    return text
