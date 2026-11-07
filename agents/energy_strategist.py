from __future__ import annotations

from simulation.calculations import build_resource_snapshot, compute_battery_limits


def analyse_resources(resources, diagnosis=None):
    snapshot = build_resource_snapshot(resources)
    battery = compute_battery_limits(resources, max(float(resources.get("interval_minutes", 15)) / 60.0, 0.25))
    generator_power = float(resources.get("generator_capacity_kw", 0)) if resources.get("generator_available", False) else 0.0
    grid_power = max(0.0, float(resources.get("grid_availability_kw", 0)))
    solar_power = max(0.0, float(resources.get("solar_generation_kw", 0)))
    available = snapshot["available_supply_kw"]
    resource_contributions = {
        "grid_kw": grid_power,
        "solar_kw": solar_power,
        "generator_kw": generator_power,
        "battery_kw": battery["max_discharge_power_kw"],
        "battery_available_energy_kwh": battery["available_energy_kwh"],
        "battery_soc_percent": battery["soc_percent"],
        "total_available_kw": available,
    }
    return {
        "resources": resource_contributions,
        "battery_limits": battery,
        "available_supply_kw": available,
        "interval_minutes": float(resources.get("interval_minutes", 15)),
        "available_energy_kwh": round(
            grid_power * max(float(resources.get("interval_minutes", 15)), 0) / 60.0
            + solar_power * max(float(resources.get("interval_minutes", 15)), 0) / 60.0
            + generator_power * max(float(resources.get("interval_minutes", 15)), 0) / 60.0
            + battery["available_energy_kwh"],
            2,
        ),
        "constraints": {
            "grid_kw": grid_power,
            "solar_kw": solar_power,
            "generator_kw": generator_power,
            "battery_max_discharge_kw": battery["max_discharge_power_kw"],
            "battery_available_energy_kwh": battery["available_energy_kwh"],
            "battery_reserve_percent": battery["reserve_percent"],
            "interval_minutes": float(resources.get("interval_minutes", 15)),
        },
        "incident_context": {
            "incident_type": (diagnosis or {}).get("incident_type", (diagnosis or {}).get("incident")),
            "severity": (diagnosis or {}).get("severity"),
        },
        "status": "Healthy" if available > 0 else "Critical",
    }
