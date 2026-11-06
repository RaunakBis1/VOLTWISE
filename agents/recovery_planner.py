from __future__ import annotations

from simulation.calculations import allocate_loads_for_strategy


def generate_strategies(resources, loads):
    available_supply = resources.get("available_supply_kw", 0)
    strategies = [
        "Critical Loads First",
        "Balanced Distribution",
        "Maximum Backup Conservation",
    ]
    results = []
    for strategy_name in strategies:
        strategy = allocate_loads_for_strategy(loads, available_supply, strategy_name)
        strategy["battery_discharge_kw"] = round(resources.get("battery_allowed_power_kw", 0), 2)
        strategy["generator_usage_kw"] = round(min(resources.get("generator_capacity_kw", 0), max(0.0, available_supply * 0.2)), 2)
        strategy["battery_runtime_minutes"] = round(max(0.0, (resources.get("battery_capacity_kwh", 0) * max(0.0, resources.get("battery_soc_percent", 0) - resources.get("minimum_battery_reserve_percent", 20)) / 100.0) / max(resources.get("max_battery_discharge_kw", 1), 1) * 60.0), 2)
        results.append(strategy)
    return {"strategies": results}
