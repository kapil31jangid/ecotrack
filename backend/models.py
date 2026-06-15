from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict

class FootprintInput(BaseModel):
    """Input payload representing user consumption data for footprint calculation."""
    session_id: str
    transport_mode: Literal["car", "bus", "flight"]
    transport_km_per_week: float = Field(ge=0, le=5000)
    diet_type: Literal["vegan", "vegetarian", "omnivore", "meat_heavy"]
    energy_kwh_per_month: float = Field(ge=0, le=10000)
    shopping_level: Literal["low", "medium", "high"]

class CategoryBreakdown(BaseModel):
    """CO2e emissions breakdown by consumption categories."""
    transport: float
    diet: float
    energy: float
    shopping: float

class Tip(BaseModel):
    """Actionable recommendation for lowering carbon footprint."""
    action: str
    saving_kg: float
    difficulty: Literal["Easy", "Medium", "Hard"]
    category: str

class FootprintResult(BaseModel):
    """Result payload containing total emissions, breakdown, tips, comparisons, and metadata."""
    session_id: str
    co2e_monthly: float
    co2e_annual: float
    category_breakdown: CategoryBreakdown
    tips: List[Tip]
    vs_global: str
    vs_india: str
    timestamp: str

class ChatRequest(BaseModel):
    """User prompt context payload for Gemini AI chat sessions."""
    message: str = Field(min_length=1, max_length=1000)
    session_id: str
    footprint_context: Optional[Dict] = None

class ChatResponse(BaseModel):
    """AI chatbot reply payload."""
    reply: str
    session_id: str
    model_used: str

class HealthResponse(BaseModel):
    """API health indicator payload."""
    status: str
    version: str
    ai_provider: str = "Google Vertex AI Gemini"
