"""
EcoTrack carbon footprint calculator.

Provides pure, deterministic emission calculation functions for transport,
diet, energy and shopping categories, plus comparison utilities and tip generation.
"""
from functools import lru_cache

__all__ = [
    "calculate_transport_emissions",
    "calculate_diet_emissions",
    "calculate_energy_emissions",
    "calculate_shopping_emissions",
    "compare_to_averages",
    "generate_tips",
    "calculate_total_footprint",
]
from backend.config import (
    TRANSPORT_FACTORS,
    DIET_FACTORS,
    ENERGY_FACTOR,
    SHOPPING_FACTORS,
    WEEKS_PER_MONTH,
    GLOBAL_AVERAGE_MONTHLY,
    INDIA_AVERAGE_MONTHLY,
)

@lru_cache(maxsize=64)
def calculate_transport_emissions(mode: str, km_per_week: float) -> float:
    """Calculate monthly transport CO2e. Formula: km_per_week * WEEKS_PER_MONTH * TRANSPORT_FACTORS[mode]"""
    if mode not in TRANSPORT_FACTORS:
        raise KeyError(f"Invalid transport mode: {mode}")
    return float(km_per_week * WEEKS_PER_MONTH * TRANSPORT_FACTORS[mode])

@lru_cache(maxsize=64)
def calculate_diet_emissions(diet_type: str) -> float:
    """Return monthly diet CO2e from DIET_FACTORS."""
    if diet_type not in DIET_FACTORS:
        raise KeyError(f"Invalid diet type: {diet_type}")
    return float(DIET_FACTORS[diet_type])

@lru_cache(maxsize=64)
def calculate_energy_emissions(kwh_per_month: float) -> float:
    """Calculate monthly energy CO2e: kwh * ENERGY_FACTOR."""
    return float(kwh_per_month * ENERGY_FACTOR)

@lru_cache(maxsize=64)
def calculate_shopping_emissions(level: str) -> float:
    """Return monthly shopping CO2e from SHOPPING_FACTORS."""
    if level not in SHOPPING_FACTORS:
        raise KeyError(f"Invalid shopping level: {level}")
    return float(SHOPPING_FACTORS[level])

def compare_to_averages(co2e_monthly: float) -> tuple[str, str]:
    """Return (vs_global, vs_india) human-readable comparison strings."""
    # Global comparison
    if abs(co2e_monthly - GLOBAL_AVERAGE_MONTHLY) < 1e-5:
        vs_global = "equal to the global average"
    else:
        diff_global = ((co2e_monthly - GLOBAL_AVERAGE_MONTHLY) / GLOBAL_AVERAGE_MONTHLY) * 100
        direction = "higher" if diff_global > 0 else "lower"
        vs_global = f"{abs(diff_global):.1f}% {direction} than the global average"

    # India comparison
    if abs(co2e_monthly - INDIA_AVERAGE_MONTHLY) < 1e-5:
        vs_india = "equal to the India average"
    else:
        diff_india = ((co2e_monthly - INDIA_AVERAGE_MONTHLY) / INDIA_AVERAGE_MONTHLY) * 100
        direction = "higher" if diff_india > 0 else "lower"
        vs_india = f"{abs(diff_india):.1f}% {direction} than the India average"

    return vs_global, vs_india

def generate_tips(breakdown: dict) -> list[dict]:
    """
    Generate exactly 5 personalized tips sorted by impact.
    Full tips pool:
    Sort: match user's highest emission category first, then by saving_kg descending.
    """
    tips_pool = [
        {"action": "Switch to public transport", "saving_kg": 80.0, "difficulty": "Medium", "category": "transport"},
        {"action": "Work from home 2 days/week", "saving_kg": 18.0, "difficulty": "Easy", "category": "transport"},
        {"action": "Carpool with colleagues", "saving_kg": 45.0, "difficulty": "Easy", "category": "transport"},
        {"action": "Switch to vegetarian diet", "saving_kg": 65.0, "difficulty": "Medium", "category": "diet"},
        {"action": "Reduce beef to once/week", "saving_kg": 40.0, "difficulty": "Easy", "category": "diet"},
        {"action": "Eat local seasonal produce", "saving_kg": 20.0, "difficulty": "Easy", "category": "diet"},
        {"action": "Switch to LED bulbs", "saving_kg": 10.0, "difficulty": "Easy", "category": "energy"},
        {"action": "Unplug idle electronics", "saving_kg": 8.0, "difficulty": "Easy", "category": "energy"},
        {"action": "Install solar panels", "saving_kg": 120.0, "difficulty": "Hard", "category": "energy"},
        {"action": "Set AC to 24°C instead of 20°C", "saving_kg": 15.0, "difficulty": "Easy", "category": "energy"},
        {"action": "Buy second-hand clothing", "saving_kg": 40.0, "difficulty": "Easy", "category": "shopping"},
        {"action": "Repair instead of replace electronics", "saving_kg": 30.0, "difficulty": "Medium", "category": "shopping"},
    ]

    # Find the category with the highest emission in the breakdown
    highest_category = max(breakdown, key=breakdown.get)

    # Sort key: primary is whether it's highest category (0 for Yes, 1 for No), secondary is saving_kg descending
    sorted_tips = sorted(
        tips_pool,
        key=lambda x: (0 if x["category"] == highest_category else 1, -x["saving_kg"])
    )

    return sorted_tips[:5]

def calculate_total_footprint(input_data: dict) -> dict:
    """
    Orchestrate all calculations.
    Returns: {
      co2e_monthly, co2e_annual,
      category_breakdown: {transport, diet, energy, shopping},
      tips: list[dict],
      vs_global: str,
      vs_india: str
    }
    """
    transport = calculate_transport_emissions(
        input_data["transport_mode"], input_data["transport_km_per_week"]
    )
    diet = calculate_diet_emissions(input_data["diet_type"])
    energy = calculate_energy_emissions(input_data["energy_kwh_per_month"])
    shopping = calculate_shopping_emissions(input_data["shopping_level"])

    co2e_monthly = transport + diet + energy + shopping
    co2e_annual = co2e_monthly * 12.0

    breakdown = {
        "transport": round(transport, 2),
        "diet": round(diet, 2),
        "energy": round(energy, 2),
        "shopping": round(shopping, 2),
    }

    vs_global, vs_india = compare_to_averages(co2e_monthly)
    tips = generate_tips(breakdown)

    return {
        "co2e_monthly": round(co2e_monthly, 2),
        "co2e_annual": round(co2e_annual, 2),
        "category_breakdown": breakdown,
        "tips": tips,
        "vs_global": vs_global,
        "vs_india": vs_india,
    }
