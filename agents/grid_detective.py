from __future__ import annotations

from datetime import datetime, timezone

from config import DEFAULT_RESOURCES, LOADS
from simulation.calculations import build_loads, build_resource_snapshot, total_initial_demand


def investigate_incident(scenario):
    default_scenario = dict(DEFAULT_RESOURCES)
    default_scenario.update({
        "grid_availability_kw": default_scenario["grid_capacity_kw"],
        "solar_generation_kw": default_scenario["solar_generation_kw"],
        "battery_soc_percent": default_scenario["battery_soc_percent"],
        "generator_available": default_scenario["generator_available"],
        "demand_multiplier": 1.0,
    })
    default_scenario.update(scenario)
    demand = total_initial_demand(build_loads(default_scenario.get("demand_multiplier", 1.0), LOADS))
    supply = build_resource_snapshot(default_scenario)["available_supply_kw"]
    deficit = demand - supply

    if float(default_scenario.get("grid_availability_kw", 0)) <= 0:
        incident = "Complete grid failure"
    elif float(default_scenario.get("solar_generation_kw", 0)) <= 5:
        incident = "Solar power collapse"
    elif float(default_scenario.get("battery_soc_percent", 0)) <= 30:
        incident = "Battery emergency"
    elif float(default_scenario.get("demand_multiplier", 1)) > 1.2:
        incident = "Demand surge"
    else:
        incident = "Normal condition with elevated stress"

    if deficit > 40:
        severity = "Critical"
    elif deficit > 0 or incident != "Normal condition with elevated stress":
        severity = "Warning"
    else:
        severity = "Stable"

    affected_resources = {
        "Complete grid failure": ["grid"],
        "Solar power collapse": ["solar"],
        "Battery emergency": ["battery"],
        "Demand surge": ["loads"],
    }.get(incident, [])
    constraints = {
        "grid_available_kw": float(default_scenario.get("grid_availability_kw", 0)),
        "solar_available_kw": float(default_scenario.get("solar_generation_kw", 0)),
        "battery_soc_percent": float(default_scenario.get("battery_soc_percent", 0)),
        "battery_reserve_percent": float(default_scenario.get("minimum_battery_reserve_percent", 20)),
        "battery_capacity_kwh": float(default_scenario.get("battery_capacity_kwh", 0)),
        "battery_max_discharge_kw": float(default_scenario.get("max_battery_discharge_kw", 0)),
        "generator_available": bool(default_scenario.get("generator_available", False)),
        "generator_capacity_kw": float(default_scenario.get("generator_capacity_kw", 0)),
        "interval_minutes": float(default_scenario.get("interval_minutes", 15)),
        "demand_multiplier": float(default_scenario.get("demand_multiplier", 1)),
    }
    diagnosis = (
        f"Main grid supply is {default_scenario.get('grid_availability_kw', 0)} kW. "
        f"Available recovery resources provide {supply} kW against a campus demand of {demand} kW. "
        f"The current incident profile indicates {incident.lower()}. "
        f"Critical loads must be protected while the margin sits at {abs(deficit):.1f} kW {'shortfall' if deficit > 0 else 'surplus'}."
    )

    return {
        "incident": incident,
        "incident_type": incident,
        "affected_resources": affected_resources,
        "severity": severity,
        "total_demand_kw": demand,
        "available_supply_kw": supply,
        "deficit_kw": max(0.0, deficit),
        "constraints": constraints,
        "diagnosis": diagnosis,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
