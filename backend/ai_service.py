import json
import logging
import hashlib
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    GenerationConfig,
    SafetySetting,
    HarmCategory,
    HarmBlockThreshold,
)
from backend.config import (
    GOOGLE_CLOUD_PROJECT,
    VERTEX_AI_LOCATION,
    VERTEX_AI_MODEL_PRIMARY,
    VERTEX_AI_MODEL_FALLBACK,
)

logger = logging.getLogger("ecotrack")

# Simple in-memory cache for duplicate Vertex AI queries within same context and session
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

GENERATION_CONFIG = GenerationConfig(
    temperature=0.7,
    top_p=0.95,
    max_output_tokens=300,
)

SAFETY_SETTINGS = [
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    ),
]

_vertex_initialized = False

def _initialize_vertex():
    """Initialize Vertex AI with project and location from config."""
    global _vertex_initialized
    if not _vertex_initialized:
        # Avoid crash if project is empty during local testing without GCP configs
        project = GOOGLE_CLOUD_PROJECT if GOOGLE_CLOUD_PROJECT else None
        vertexai.init(
            project=project,
            location=VERTEX_AI_LOCATION
        )
        _vertex_initialized = True
        logger.info(f"Initialized Vertex AI with project: '{project}', location: '{VERTEX_AI_LOCATION}'")

async def _call_gemini(model_name: str, prompt: str) -> str:
    """Call a specific Gemini model and return text response."""
    _initialize_vertex()
    model = GenerativeModel(
        model_name,
        system_instruction=SYSTEM_PROMPT,
        generation_config=GENERATION_CONFIG,
        safety_settings=SAFETY_SETTINGS,
    )
    # Using async call for FastAPI compatibility
    response = await model.generate_content_async(prompt)
    return response.text

async def get_ai_response(message: str, footprint_context: dict | None, session_id: str) -> tuple[str, str]:
    """
    Get AI response from Vertex AI Gemini.
    1. Try gemini-1.5-flash (primary, faster + cheaper)
    2. On failure, fallback to gemini-1.0-pro
    3. On both failing, return friendly static message
    Returns: (reply_text, model_used_string)
    
    Build the prompt as:
    system_part = SYSTEM_PROMPT
    if footprint_context:
        system_part += f"\n\nUser's current carbon footprint data:\n{json.dumps(footprint_context, indent=2)}"
    full_prompt = f"{system_part}\n\nUser message: {message}"
    
    Log which model responded via Cloud Logging.
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
