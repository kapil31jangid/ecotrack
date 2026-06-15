import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import calculate_footprint_endpoint
from backend.models import FootprintInput

input_data = FootprintInput(
    session_id="test-session",
    transport_mode="car",
    transport_km_per_week=100.0,
    diet_type="vegetarian",
    energy_kwh_per_month=200.0,
    shopping_level="medium"
)

async def test():
    try:
        res = await calculate_footprint_endpoint(input_data)
        print("Success:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(test())
