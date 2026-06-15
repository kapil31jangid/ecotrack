"""
EcoTrack AI Service — uses Google Gemini Developer REST API directly via httpx.
No google-cloud-aiplatform SDK needed: fast startup, lightweight container.
Falls back to rule-based tips/insights if GEMINI_API_KEY is not set.
"""
import json
import logging
import hashlib
import httpx
from backend.config import (
    VERTEX_AI_MODEL_PRIMARY,
    VERTEX_AI_MODEL_FALLBACK,
    GEMINI_API_KEY,
)

logger = logging.getLogger("ecotrack")

# Model name for Gemini REST API (maps to gemini-1.5-flash)
GEMINI_REST_MODEL = "gemini-1.5-flash"
GEMINI_REST_MODEL_FALLBACK = "gemini-1.0-pro"
GEMINI_REST_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# In-memory cache to avoid redundant Gemini calls
_ai_cache: dict = {}

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


def _get_cache_key(message: str, footprint_context: dict | None, session_id: str) -> str:
    ctx_str = json.dumps(footprint_context, sort_keys=True) if footprint_context else ""
    return hashlib.sha256(f"{session_id}:{message}:{ctx_str}".encode()).hexdigest()


async def _call_gemini_rest(
    prompt: str,
    system_instruction: str | None = None,
    response_mime_type: str | None = None,
    temperature: float = 0.7,
    max_output_tokens: int = 300,
    model: str = GEMINI_REST_MODEL,
) -> str:
    """Call Gemini Developer REST API. Raises on failure."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not configured")

    url = f"{GEMINI_REST_BASE}/{model}:generateContent?key={GEMINI_API_KEY}"

    payload: dict = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    if response_mime_type:
        payload["generationConfig"]["responseMimeType"] = response_mime_type

    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})

    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        finish = data.get("promptFeedback", {}).get("blockReason", "unknown")
        raise ValueError(f"Gemini returned no candidates (blockReason={finish})")

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise ValueError("Gemini candidate had no parts")

    return parts[0].get("text", "").strip()


async def get_ai_response(
    message: str, footprint_context: dict | None, session_id: str
) -> tuple[str, str]:
    """Chat endpoint — returns (reply, model_used)."""
    cache_key = _get_cache_key(message, footprint_context, session_id)
    if cache_key in _ai_cache:
        logger.info(f"Cache hit for session {session_id}")
        return _ai_cache[cache_key]

    system = SYSTEM_PROMPT
    if footprint_context:
        system += f"\n\nUser's footprint data:\n{json.dumps(footprint_context, indent=2)}"
    prompt = f"{system}\n\nUser message: {message}"

    for model in [GEMINI_REST_MODEL, GEMINI_REST_MODEL_FALLBACK]:
        try:
            reply = await _call_gemini_rest(prompt, temperature=0.7, max_output_tokens=300, model=model)
            logger.info(f"Chat via Gemini REST ({model}) for session {session_id}")
            _ai_cache[cache_key] = (reply, model)
            return reply, model
        except Exception as e:
            logger.warning(f"Gemini REST ({model}) failed: {e}")

    static = (
        "I'm here to support your sustainability journey! "
        "Try switching off standby appliances as a quick win today. "
        "Ask me about transport, diet, or energy to get personalised tips!"
    )
    return static, "static-fallback"


async def get_ai_tips(input_data: dict, breakdown: dict) -> list[dict]:
    """Generate 5 personalised reduction tips. Raises on failure (caller catches → fallback)."""
    total = sum(breakdown.get(c, 0.0) for c in ["transport", "diet", "energy", "shopping"])
    prompt = f"""You are a carbon footprint expert.
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

Return exactly 5 personalised, concrete tips as a JSON array. Each object must have:
"action" (string), "saving_kg" (positive float), "difficulty" ("Easy"/"Medium"/"Hard"), "category" ("transport"/"diet"/"energy"/"shopping").
Return ONLY the JSON array, no markdown fences."""

    text = await _call_gemini_rest(
        prompt,
        response_mime_type="application/json",
        temperature=0.2,
        max_output_tokens=800,
    )
    logger.info("Gemini REST returned tips")

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
            validated.append({"action": action, "saving_kg": saving_kg,
                              "difficulty": difficulty, "category": category})

    if len(validated) < 3:
        raise ValueError(f"Only {len(validated)} valid tips returned")

    return validated[:5]


async def get_ai_insights(input_data: dict, breakdown: dict) -> str:
    """Generate 2-3 sentence personalised dashboard insight. Raises on failure."""
    total = sum(breakdown.get(c, 0.0) for c in ["transport", "diet", "energy", "shopping"])
    prompt = f"""You are a friendly carbon footprint coach.
User inputs:
- Transport: {input_data.get('transport_mode')} at {input_data.get('transport_km_per_week')} km/week
- Diet: {input_data.get('diet_type')}
- Energy: {input_data.get('energy_kwh_per_month')} kWh/month
- Shopping: {input_data.get('shopping_level')}

Monthly emissions (kg CO2e):
- Transport: {breakdown.get('transport', 0)} | Diet: {breakdown.get('diet', 0)} | Energy: {breakdown.get('energy', 0)} | Shopping: {breakdown.get('shopping', 0)}
- Total: {total:.1f} kg

Write exactly 2-3 encouraging sentences. Identify the highest emission category, give positive reinforcement, suggest one high-impact change.
Under 80 words. No markdown, no lists."""

    text = await _call_gemini_rest(prompt, temperature=0.7, max_output_tokens=150)
    logger.info("Gemini REST returned insights")
    return text
