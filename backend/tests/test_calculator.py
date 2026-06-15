import pytest
import sys
import os

# Add parent path to support modular imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.calculator import (
    calculate_transport_emissions,
    calculate_diet_emissions,
    calculate_energy_emissions,
    calculate_shopping_emissions,
    calculate_total_footprint,
    generate_tips,
)

def test_transport_car_100km():
    """Assert car transport CO2e calculations are correct."""
    result = calculate_transport_emissions("car", 100.0)
    assert abs(result - 90.93) < 0.5

def test_transport_bus_100km():
    """Assert bus transport CO2e calculations are correct."""
    result = calculate_transport_emissions("bus", 100.0)
    assert abs(result - 38.54) < 0.5

def test_transport_zero_km():
    """Assert 0 km weekly travel yields 0 emissions."""
    result = calculate_transport_emissions("car", 0.0)
    assert result == 0.0

def test_diet_vegan():
    """Assert vegan diet emissions factors map correctly."""
    result = calculate_diet_emissions("vegan")
    assert result == 55.0

def test_diet_meat_heavy():
    """Assert meat heavy diet emissions factors map correctly."""
    result = calculate_diet_emissions("meat_heavy")
    assert result == 230.0

def test_energy_300kwh():
    """Assert home grid energy usage scales with emissions factor."""
    result = calculate_energy_emissions(300.0)
    assert abs(result - 246.0) < 0.1

def test_energy_zero():
    """Assert 0 energy usage yields 0 emissions."""
    result = calculate_energy_emissions(0.0)
    assert result == 0.0

def test_total_footprint_fields():
    """Verify combined calculations return all required fields with mathematical relationships."""
    mock_input = {
        "session_id": "test-session",
        "transport_mode": "car",
        "transport_km_per_week": 120.0,
        "diet_type": "vegetarian",
        "energy_kwh_per_month": 250.0,
        "shopping_level": "medium",
    }
    result = calculate_total_footprint(mock_input)
    assert "co2e_monthly" in result
    assert "co2e_annual" in result
    assert "category_breakdown" in result
    assert "tips" in result
    assert "vs_global" in result
    assert "vs_india" in result
    assert abs(result["co2e_annual"] - result["co2e_monthly"] * 12.0) < 0.1

def test_generate_tips_returns_five():
    """Confirm recommendations engine produces exactly 5 tips sorted by user's highest category."""
    mock_breakdown = {
        "transport": 10.0,
        "diet": 85.0,
        "energy": 246.0,
        "shopping": 30.0,
    }
    tips = generate_tips(mock_breakdown)
    assert len(tips) == 5
    for tip in tips:
        assert "action" in tip
        assert "saving_kg" in tip
        assert "difficulty" in tip
        assert "category" in tip
        assert tip["difficulty"] in ["Easy", "Medium", "Hard"]
    # Primary tip should be energy related because energy is the highest category
    assert tips[0]["category"] == "energy"

def test_invalid_diet_raises():
    """Verify calculations with unsupported parameters raise error."""
    with pytest.raises(KeyError):
        calculate_diet_emissions("junkfood_only")
