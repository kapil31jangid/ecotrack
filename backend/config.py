import os
from dotenv import load_dotenv

# Load environment variables from parent .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

TRANSPORT_FACTORS = {"car": 0.21, "bus": 0.089, "flight": 0.255}   # kg CO2e per km
DIET_FACTORS = {"vegan": 55, "vegetarian": 85, "omnivore": 150, "meat_heavy": 230}
ENERGY_FACTOR = 0.82          # India grid kg CO2e per kWh
SHOPPING_FACTORS = {"low": 30, "medium": 70, "high": 130}
WEEKS_PER_MONTH = 4.33
GLOBAL_AVERAGE_MONTHLY = 333.0
INDIA_AVERAGE_MONTHLY = 150.0
APP_VERSION = "1.0.0"

# Vertex AI config — 100% Google, zero Anthropic
VERTEX_AI_LOCATION = "asia-south1"
VERTEX_AI_MODEL_PRIMARY = "gemini-1.5-flash"
VERTEX_AI_MODEL_FALLBACK = "gemini-1.0-pro"

# Load from environment
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
FIRESTORE_COLLECTION = os.getenv("FIRESTORE_COLLECTION", "footprints")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
IS_GCP = bool(GOOGLE_CLOUD_PROJECT) and bool(os.getenv("K_SERVICE"))
