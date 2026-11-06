from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "voltwise.db"
REPORTS_DIR = BASE_DIR / "reports"

APP_NAME = "VOLTWISE"
APP_TAGLINE = "Think Smart. Distribute Power. Restore Stability."

LOADS = [
    {"id": "emergency_lighting", "name": "Emergency Lighting", "demand_kw": 10, "priority": "Critical", "minimum_kw": 10},
    {"id": "computer_lab", "name": "Computer Laboratory", "demand_kw": 35, "priority": "High", "minimum_kw": 20},
    {"id": "research_lab", "name": "Research Laboratory", "demand_kw": 25, "priority": "High", "minimum_kw": 15},
    {"id": "academic_building", "name": "Academic Building", "demand_kw": 30, "priority": "Normal", "minimum_kw": 15},
    {"id": "library", "name": "Library", "demand_kw": 20, "priority": "Normal", "minimum_kw": 10},
    {"id": "non_essential", "name": "Non-essential Facilities", "demand_kw": 20, "priority": "Deferrable", "minimum_kw": 0},
]

DEFAULT_RESOURCES = {
    "grid_capacity_kw": 100,
    "solar_generation_kw": 25,
    "battery_capacity_kwh": 200,
    "battery_soc_percent": 80,
    "max_battery_discharge_kw": 40,
    "minimum_battery_reserve_percent": 20,
    "generator_capacity_kw": 30,
    "generator_available": True,
    "interval_minutes": 15,
}

PRIORITY_ORDER = {"Critical": 0, "High": 1, "Normal": 2, "Deferrable": 3}

SCENARIO_LIBRARY = {
    "complete_grid_failure": {
        "scenario_name": "Complete Grid Failure",
        "grid_availability_kw": 0,
        "solar_generation_kw": 25,
        "battery_soc_percent": 80,
        "generator_available": True,
        "demand_multiplier": 1.0,
        "interval_minutes": 15,
    },
    "solar_power_collapse": {
        "scenario_name": "Solar Power Collapse",
        "grid_availability_kw": 100,
        "solar_generation_kw": 2.5,
        "battery_soc_percent": 80,
        "generator_available": True,
        "demand_multiplier": 1.0,
        "interval_minutes": 15,
    },
    "battery_emergency": {
        "scenario_name": "Battery Emergency",
        "grid_availability_kw": 100,
        "solar_generation_kw": 25,
        "battery_soc_percent": 25,
        "generator_available": True,
        "demand_multiplier": 1.0,
        "interval_minutes": 15,
    },
    "demand_surge": {
        "scenario_name": "Demand Surge",
        "grid_availability_kw": 100,
        "solar_generation_kw": 25,
        "battery_soc_percent": 80,
        "generator_available": True,
        "demand_multiplier": 1.4,
        "interval_minutes": 15,
    },
}
