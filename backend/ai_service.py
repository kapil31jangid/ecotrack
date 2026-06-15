import json
import logging
import hashlib
import httpx
from backend.config import (
    GOOGLE_CLOUD_PROJECT,
    VERTEX_AI_LOCATION,
    VERTEX_AI_MODEL_PRIMARY,
    VERTEX_AI_MODEL_FALLBACK,
    GEMINI_API_KEY,
)

logger = logging.getLogger("ecotrack")

# Simple in-memory cache for duplicate Vertex AI / Gemini API queries within same context and session
_ai_cache = {}

def _get_cache_key(message: str, footprint_context: dict | None, session_id: str) -> str:
    """Generate SHA256 cache key from session_id, message and sorted footprint context."""
    ctx_str = json.dumps(footprint_context, sort_keys=True) if footprint_context else ""
    raw_key = f"{session_id}:{message}:{ctx_str}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

SYSTEM_PROMPT = """You are EcoTrack AI, a friendly and encouraging sustainability coach built on Google Gemini.
You receive the user's carbon footprint data as context in every conversation.
Rules:
- Warm, encouraging tone — never preachy or guilt-tripping
- Give SPECIFIC numbers when possible ("switching to bus could save ~80 kg CO2 monthly")
- Keep responses under 150 words unless user asks for detail
- End every response with one concrete next step the user can take TODAY
- If asked something unrelated to sustainability, gently redirect
- Use simple language, avoid jargon
"""

# Lazy-initialized Vertex AI packages and clients
_GenerativeModel = None
_GenerationConfig = None
_SafetySetting = None
_HarmCategory = None
_HarmBlockThreshold = None

def _lazy_import_vertex():
    global _GenerativeModel, _GenerationConfig, _SafetySetting, _HarmCategory, _HarmBlockThreshold
    if _GenerativeModel is None:
        import vertexai
        from vertexai.generative_models import (
            GenerativeModel,
            GenerationConfig,
            SafetySetting,
            HarmCategory,
            HarmBlockThreshold,
        )
        _GenerativeModel = GenerativeModel
        _GenerationConfig = GenerationConfig
        _SafetySetting = SafetySetting
        _HarmCategory = HarmCategory
        _HarmBlockThreshold = HarmBlockThreshold

        # Initialize Vertex AI
        project = GOOGLE_CLOUD_PROJECT if GOOGLE_CLOUD_PROJECT else None
        vertexai.init(
            project=project,
            location=VERTEX_AI_LOCATION
        )
        logger.info(f"Initialized Vertex AI with project: '{project}', location: '{VERTEX_AI_LOCATION}'")

def get_generation_config(temperature=0.7, top_p=0.95, max_output_tokens=300, response_mime_type=None):
    _lazy_import_vertex()
    return _GenerationConfig(
        temperature=temperature,
        top_p=top_p,
        max_output_tokens=max_output_tokens,
        response_mime_type=response_mime_type,
    )

def get_safety_settings():
    _lazy_import_vertex()
    return [
        _SafetySetting(
            category=_HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=_HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        ),
        _SafetySetting(
            category=_HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=_HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        ),
        _SafetySetting(
            category=_HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=_HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        ),
        _SafetySetting(
            category=_HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=_HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        ),
    ]

async def _call_gemini_rest(
    model_name: str,
    prompt: str,
    system_instruction: str = None,
    response_mime_type: str = None,
    temperature: float = 0.7,
    max_output_tokens: int = 300
) -> str:
    """Call the direct Google Gemini Developer API using the provided API key."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        }
    }
    
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [
                {"text": system_instruction}
            ]
        }
        
    if response_mime_type:
        payload["generationConfig"]["responseMimeType"] = response_mime_type
        
    headers = {
        "Content-Type": "application/json"
    }
    
    logger.info(f"Querying Gemini REST API for model '{model_name}'...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            logger.error(f"Gemini REST API returned error status {response.status_code}: {response.text}")
            raise Exception(f"Gemini REST API error {response.status_code}: {response.text}")
            
        data = response.json()
        try:
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates returned from Gemini REST API")
            
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError("No text content found in candidates parts")
                
            return parts[0].get("text", "").strip()
        except Exception as e:
            logger.error(f"Failed to parse Gemini REST API response: {str(e)}")
            raise

async def _call_gemini(model_name: str, prompt: str) -> str:
    """Call a specific Gemini model using REST API (if key present) or Vertex AI."""
    if GEMINI_API_KEY:
        try:
            return await _call_gemini_rest(
                model_name=model_name,
                prompt=prompt,
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=300
            )
        except Exception as e:
            logger.warning(f"Gemini REST API failed, trying Vertex AI fallback: {str(e)}")
            # Fallthrough to Vertex AI
            
    # Vertex AI fallback
    _lazy_import_vertex()
    model = _GenerativeModel(
        model_name,
        system_instruction=SYSTEM_PROMPT,
        generation_config=get_generation_config(),
        safety_settings=get_safety_settings(),
    )
    response = await model.generate_content_async(prompt)
    return response.text

async def get_ai_response(message: str, footprint_context: dict | None, session_id: str) -> tuple[str, str]:
    """
    Get AI response from Vertex AI Gemini or Gemini REST API.
    1. Try gemini-1.5-flash (primary, faster + cheaper)
    2. On failure, fallback to gemini-1.0-pro
    3. On both failing, return friendly static message
    Returns: (reply_text, model_used_string)
    """
    # 0. Check cache first for efficiency
    cache_key = _get_cache_key(message, footprint_context, session_id)
    if cache_key in _ai_cache:
        logger.info(f"AI response cache hit for session: {session_id}")
        return _ai_cache[cache_key]

    system_part = SYSTEM_PROMPT
    if footprint_context:
        system_part += f"\n\nUser's current carbon footprint data:\n{json.dumps(footprint_context, indent=2)}"
    full_prompt = f"{system_part}\n\nUser message: {message}"

    # 1. Try Primary (Gemini 1.5 Flash)
    try:
        reply = await _call_gemini(VERTEX_AI_MODEL_PRIMARY, full_prompt)
        logger.info(f"Successfully generated response using model '{VERTEX_AI_MODEL_PRIMARY}' for session: {session_id}")
        _ai_cache[cache_key] = (reply, VERTEX_AI_MODEL_PRIMARY)
        return reply, VERTEX_AI_MODEL_PRIMARY
    except Exception as e:
        logger.warning(f"Failed to generate response with primary model '{VERTEX_AI_MODEL_PRIMARY}' for session {session_id}: {str(e)}")
        
        # 2. Try Fallback (Gemini 1.0 Pro)
        try:
            reply = await _call_gemini(VERTEX_AI_MODEL_FALLBACK, full_prompt)
            logger.info(f"Successfully generated response using fallback model '{VERTEX_AI_MODEL_FALLBACK}' for session: {session_id}")
            _ai_cache[cache_key] = (reply, VERTEX_AI_MODEL_FALLBACK)
            return reply, VERTEX_AI_MODEL_FALLBACK
        except Exception as fallback_err:
            logger.error(
                f"Failed to generate response with fallback model '{VERTEX_AI_MODEL_FALLBACK}' for session {session_id}: {str(fallback_err)}"
            )
            # 3. Static fallback message on complete failure
            static_reply = (
                "I'm here to support you on your sustainability journey! Based on your footprint data, "
                "a simple and high-impact action you can take today is switching off standby appliances. "
                "Let me know if you want detailed suggestions on transportation, diet, or home energy saving!"
            )
            return static_reply, "static-fallback"

async def get_ai_tips(input_data: dict, breakdown: dict) -> list[dict]:
    """
    Generate 5 personalized carbon reduction tips using Gemini (REST API or Vertex AI).
    Returns a list of dictionaries matching the Tip structure.
    """
    prompt = f"""You are a carbon footprint expert.
Based on the user's consumption inputs:
- Transport mode: {input_data.get('transport_mode')} ({input_data.get('transport_km_per_week')} km/week)
- Diet type: {input_data.get('diet_type')}
- Electricity: {input_data.get('energy_kwh_per_month')} kWh/month
- Shopping level: {input_data.get('shopping_level')}

And their calculated monthly emissions breakdown (in kg CO2e):
- Transport: {breakdown.get('transport', 0.0)} kg
- Diet: {breakdown.get('diet', 0.0)} kg
- Energy: {breakdown.get('energy', 0.0)} kg
- Shopping: {breakdown.get('shopping', 0.0)} kg
- Total monthly footprint: {breakdown.get('transport', 0.0) + breakdown.get('diet', 0.0) + breakdown.get('energy', 0.0) + breakdown.get('shopping', 0.0)} kg

Provide exactly 5 highly personalized, concrete, actionable tips to reduce their carbon footprint.
Your response must be a valid JSON array of objects, where each object has exactly these fields:
- "action": string, description of the action.
- "saving_kg": float, estimated monthly CO2e savings in kg, must be a positive number.
- "difficulty": string, one of "Easy", "Medium", "Hard".
- "category": string, one of "transport", "diet", "energy", "shopping".

Return ONLY a JSON array of objects. Do not include markdown formatting or wrapper (like ```json).
"""

    text = None
    if GEMINI_API_KEY:
        try:
            text = await _call_gemini_rest(
                model_name=VERTEX_AI_MODEL_PRIMARY,
                prompt=prompt,
                response_mime_type="application/json",
                temperature=0.2,
                max_output_tokens=800
            )
            logger.info("Successfully fetched tips using direct Gemini REST API.")
        except Exception as e:
            logger.warning(f"Direct Gemini REST API tips failed: {str(e)}. Falling back to Vertex AI.")

    if text is None:
        _lazy_import_vertex()
        model = _GenerativeModel(
            VERTEX_AI_MODEL_PRIMARY,
            generation_config=get_generation_config(temperature=0.2, max_output_tokens=800, response_mime_type="application/json"),
            safety_settings=get_safety_settings(),
        )
        logger.info(f"Querying Vertex AI model '{VERTEX_AI_MODEL_PRIMARY}' for personalized tips...")
        response = await model.generate_content_async(prompt)
        text = response.text.strip()
    
    # Parse and validate JSON
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("AI response is not a list")
        
    # Standardize/validate fields
    validated_tips = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        # Ensure correct keys and defaults
        action = str(item.get("action", ""))
        saving_kg = float(item.get("saving_kg", 0.0))
        difficulty = item.get("difficulty", "Medium")
        if difficulty not in ["Easy", "Medium", "Hard"]:
            difficulty = "Medium"
        category = str(item.get("category", "")).lower()
        if category not in ["transport", "diet", "energy", "shopping"]:
            category = "energy"
            
        if not action or saving_kg <= 0:
            continue
            
        validated_tips.append({
            "action": action,
            "saving_kg": saving_kg,
            "difficulty": difficulty,
            "category": category
        })
        
    if len(validated_tips) < 3:
        raise ValueError(f"AI returned only {len(validated_tips)} valid tips, which is insufficient.")
        
    return validated_tips[:5]

async def get_ai_insights(input_data: dict, breakdown: dict) -> str:
    """
    Generate a 2-3 sentence personalized carbon footprint insight using Gemini (REST API or Vertex AI).
    """
    prompt = f"""You are a friendly and encouraging carbon footprint expert.
Based on the user's consumption inputs:
- Transport mode: {input_data.get('transport_mode')} ({input_data.get('transport_km_per_week')} km/week)
- Diet type: {input_data.get('diet_type')}
- Electricity: {input_data.get('energy_kwh_per_month')} kWh/month
- Shopping level: {input_data.get('shopping_level')}

And their monthly emissions breakdown (in kg CO2e):
- Transport: {breakdown.get('transport', 0.0)} kg
- Diet: {breakdown.get('diet', 0.0)} kg
- Energy: {breakdown.get('energy', 0.0)} kg
- Shopping: {breakdown.get('shopping', 0.0)} kg
- Total monthly footprint: {breakdown.get('transport', 0.0) + breakdown.get('diet', 0.0) + breakdown.get('energy', 0.0) + breakdown.get('shopping', 0.0)} kg

Write exactly 2-3 sentences of personalized, constructive insights.
Identify their highest emission category, highlight how they are doing (using positive reinforcement if possible), and suggest one high-impact change they can make to improve.
Keep it encouraging, specific, and under 80 words. Do not use any markdown formatting or lists.
"""

    text = None
    if GEMINI_API_KEY:
        try:
            text = await _call_gemini_rest(
                model_name=VERTEX_AI_MODEL_PRIMARY,
                prompt=prompt,
                temperature=0.7,
                max_output_tokens=150
            )
            logger.info("Successfully fetched insights using direct Gemini REST API.")
        except Exception as e:
            logger.warning(f"Direct Gemini REST API insights failed: {str(e)}. Falling back to Vertex AI.")

    if text is None:
        _lazy_import_vertex()
        model = _GenerativeModel(
            VERTEX_AI_MODEL_PRIMARY,
            generation_config=get_generation_config(temperature=0.7, max_output_tokens=150),
            safety_settings=get_safety_settings(),
        )
        logger.info(f"Querying Vertex AI model '{VERTEX_AI_MODEL_PRIMARY}' for personalized dashboard insights...")
        response = await model.generate_content_async(prompt)
        text = response.text.strip()
        
    return text
