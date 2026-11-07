from __future__ import annotations

from config import DEFAULT_RESOURCES, LOADS, PRIORITY_ORDER


def round_value(value, digits=2):
    return round(float(value), digits)


def build_loads(demand_multiplier=1.0, custom_loads=None):
    source = custom_loads or LOADS
    loads = []
    for load in source:
        demand = load["demand_kw"] * float(demand_multiplier)
        loads.append(
            {
                "id": load["id"],
                "name": load["name"],
                "demand_kw": round_value(demand),
                "priority": load["priority"],
                "minimum_kw": round_value(load["minimum_kw"]),
            }
        )
    return loads


def total_initial_demand(loads):
    return round_value(sum(load["demand_kw"] for load in loads))


def compute_battery_limits(resources, interval_hours=0.25):
    capacity = float(resources.get("battery_capacity_kwh", 0))
    soc = float(resources.get("battery_soc_percent", 0))
    reserve = float(resources.get("minimum_battery_reserve_percent", 0))
    max_discharge = float(resources.get("max_battery_discharge_kw", 0))
    available_energy = max(0.0, capacity * max((soc - reserve) / 100.0, 0.0))
    max_by_energy = available_energy / max(interval_hours, 0.01)
    allowed_power = min(max_discharge, max_by_energy)
    return {
        "available_energy_kwh": round_value(available_energy),
        "max_discharge_power_kw": round_value(allowed_power),
        "soc_percent": round_value(soc),
        "reserve_percent": round_value(reserve),
    }


def total_available_supply(resources):
    grid = float(resources.get("grid_availability_kw", 0))
    solar = float(resources.get("solar_generation_kw", 0))
    generator = float(resources.get("generator_capacity_kw", 0)) if resources.get("generator_available", False) else 0.0
    battery = compute_battery_limits(resources, max(float(resources.get("interval_minutes", 15)) / 60.0, 0.25))["max_discharge_power_kw"]
    return round_value(grid + solar + generator + battery)


def build_resource_snapshot(scenario):
    merged = dict(DEFAULT_RESOURCES)
    merged.update(scenario)
    interval_hours = max(float(merged.get("interval_minutes", 15)) / 60.0, 0.25)
    battery = compute_battery_limits(merged, interval_hours)
    total_supply = total_available_supply(merged)
    return {
        "grid_capacity_kw": round_value(merged.get("grid_capacity_kw", merged.get("grid_availability_kw", 0))),
        "grid_availability_kw": round_value(merged.get("grid_availability_kw", merged.get("grid_capacity_kw", 0))),
        "solar_generation_kw": round_value(merged.get("solar_generation_kw", 0)),
        "generator_capacity_kw": round_value(merged.get("generator_capacity_kw", 0)),
        "generator_available": bool(merged.get("generator_available", False)),
        "battery_capacity_kwh": round_value(merged.get("battery_capacity_kwh", 0)),
        "battery_soc_percent": round_value(merged.get("battery_soc_percent", 0)),
        "minimum_battery_reserve_percent": round_value(merged.get("minimum_battery_reserve_percent", 20)),
        "max_battery_discharge_kw": round_value(merged.get("max_battery_discharge_kw", 0)),
        "interval_minutes": round_value(merged.get("interval_minutes", 15)),
        "battery_allowed_power_kw": battery["max_discharge_power_kw"],
        "available_supply_kw": total_supply,
    }


def allocate_loads_for_strategy(
    loads,
    available_supply_kw,
    strategy_name,
    priority_order=None,
    allocation_proposal=None,
):
    remaining = float(available_supply_kw)
    allocations = []
    order = {name: index for index, name in enumerate(priority_order or [])}
    proposal = {
        item["id"]: float(item.get("allocated_kw", 0))
        for item in (allocation_proposal or [])
    }
    sorted_loads = sorted(
        loads,
        key=lambda item: (
            order.get(item["name"], len(order) + PRIORITY_ORDER.get(item["priority"], 99)),
            PRIORITY_ORDER.get(item["priority"], 99),
            item["demand_kw"],
        ),
    )
    for load in sorted_loads:
        priority = load["priority"]
        target = max(load["minimum_kw"], proposal.get(load["id"], 0.0))

        if strategy_name == "Critical Loads First":
            if priority == "Critical":
                target = load["demand_kw"]
            elif priority == "High":
                target = load["demand_kw"] * 0.9
            elif priority == "Normal":
                target = load["minimum_kw"] + max(0.0, (load["demand_kw"] - load["minimum_kw"]) * 0.6)
            else:
                target = 0.0
        elif strategy_name == "Balanced Distribution":
            if priority == "Critical":
                target = load["demand_kw"]
            elif priority == "High":
                target = load["minimum_kw"] + max(0.0, (load["demand_kw"] - load["minimum_kw"]) * 0.8)
            elif priority == "Normal":
                target = load["minimum_kw"] + max(0.0, (load["demand_kw"] - load["minimum_kw"]) * 0.7)
            else:
                target = min(load["minimum_kw"], load["demand_kw"]) * 0.5
        elif strategy_name == "Maximum Backup Conservation":
            if priority == "Critical":
                target = max(load["minimum_kw"], load["demand_kw"] * 0.6)
            elif priority == "High":
                target = max(load["minimum_kw"], load["demand_kw"] * 0.5)
            elif priority == "Normal":
                target = max(load["minimum_kw"], load["demand_kw"] * 0.4)
            else:
                target = 0.0
        else:
            target = load["minimum_kw"]

        allocation = min(max(0.0, target), max(0.0, remaining), float(load["demand_kw"]))
        if priority == "Critical" and allocation < load["minimum_kw"] and remaining >= load["minimum_kw"]:
            allocation = min(load["minimum_kw"], load["demand_kw"], remaining)
        remaining = max(0.0, remaining - allocation)
        allocations.append(
            {
                "id": load["id"],
                "name": load["name"],
                "priority": load["priority"],
                "demand_kw": round_value(load["demand_kw"]),
                "minimum_kw": round_value(load["minimum_kw"]),
                "allocated_kw": round_value(allocation),
                "remaining_after_allocation_kw": round_value(remaining),
            }
        )

    total_allocated = sum(item["allocated_kw"] for item in allocations)
    total_demand = sum(item["demand_kw"] for item in loads)
    critical_coverage = sum(item["allocated_kw"] for item in allocations if item["priority"] in {"Critical", "High"})
    unmet = max(0.0, total_demand - total_allocated)
    score = max(0.0, ((total_allocated / max(total_demand, 1)) * 100) - (unmet * 0.8) + (critical_coverage * 0.7))
    return {
        "strategy_name": strategy_name,
        "allocated_kw": round_value(total_allocated),
        "unmet_demand_kw": round_value(unmet),
        "critical_coverage_kw": round_value(critical_coverage),
        "allocations": allocations,
        "score": round_value(score),
    }


def compare_strategies(strategy_results):
    return sorted(strategy_results, key=lambda item: item["score"], reverse=True)
