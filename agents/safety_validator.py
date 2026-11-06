from __future__ import annotations


def validate_strategy(strategy, resources, loads):
    errors = []
    warnings = []
    total_demand = sum(float(load["demand_kw"]) for load in loads)
    allocated = float(strategy.get("allocated_kw", 0))
    battery_soc = float(resources.get("battery_soc_percent", 0))
    reserve = float(resources.get("minimum_battery_reserve_percent", 20))
    available_supply = float(resources.get("available_supply_kw", 0))
    generator_capacity = float(resources.get("generator_capacity_kw", 0))
    generator_usage = float(strategy.get("generator_usage_kw", 0))

    if allocated > available_supply + 1e-6:
        errors.append("Allocated load power exceeds available supply.")
    if battery_soc < reserve:
        errors.append("Battery state of charge has fallen below the minimum reserve.")
    if generator_usage > generator_capacity + 1e-6:
        errors.append("Generator usage exceeds generator capacity.")
    if any(load["allocated_kw"] < 0 for load in strategy.get("allocations", [])):
        errors.append("Negative allocation detected.")
    if total_demand > 0 and allocated > total_demand + 1e-6:
        errors.append("Total allocation exceeds total campus demand.")
    if strategy.get("score", 0) < 0:
        warnings.append("Strategy score is below zero and should be reviewed.")
    valid = not errors
    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "status": "Valid" if valid else "Invalid",
    }
