from __future__ import annotations

from simulation.calculations import allocate_loads_for_strategy


STRATEGIES = (
    "Critical Loads First",
    "Balanced Distribution",
    "Maximum Backup Conservation",
)


def _resource_dispatch(strategy_name, allocated_kw, resources, diagnosis):
    grid_kw = max(0.0, float(resources.get("grid_kw", resources.get("grid_availability_kw", 0))))
    solar_kw = max(0.0, float(resources.get("solar_kw", resources.get("solar_generation_kw", 0))))
    generator_limit = max(
        0.0,
        float(resources.get("generator_kw", resources.get("generator_capacity_kw", 0))),
    )
    battery_limit = max(
        0.0,
        float(resources.get("battery_kw", resources.get("battery_allowed_power_kw", 0))),
    )
    renewable_kw = grid_kw + solar_kw

    if strategy_name == "Maximum Backup Conservation":
        generator_kw = 0.0
        battery_kw = 0.0
        allocation_limit = renewable_kw
    elif strategy_name == "Balanced Distribution":
        allocation_limit = renewable_kw + generator_limit + battery_limit
        incident_type = (diagnosis or {}).get("incident_type", (diagnosis or {}).get("incident"))
        if incident_type == "Solar power collapse":
            battery_kw = min(battery_limit, max(0.0, allocated_kw - renewable_kw))
            generator_kw = min(generator_limit, max(0.0, allocated_kw - renewable_kw - battery_kw))
        else:
            generator_kw = min(generator_limit, max(0.0, allocated_kw - renewable_kw))
            battery_kw = min(battery_limit, max(0.0, allocated_kw - renewable_kw - generator_kw))
    else:
        allocation_limit = renewable_kw + generator_limit + battery_limit
        generator_kw = min(generator_limit, max(0.0, allocated_kw - renewable_kw))
        battery_kw = min(battery_limit, max(0.0, allocated_kw - renewable_kw - generator_kw))

    grid_usage = min(grid_kw, max(0.0, allocated_kw))
    solar_usage = min(solar_kw, max(0.0, allocated_kw - grid_usage))
    return {
        "allocation_limit_kw": allocation_limit,
        "grid_usage_kw": round(grid_usage, 2),
        "solar_usage_kw": round(solar_usage, 2),
        "generator_usage_kw": round(generator_kw, 2),
        "battery_discharge_kw": round(battery_kw, 2),
    }


def generate_strategies(
    resources,
    loads,
    diagnosis=None,
    energy_budget=None,
    load_proposal=None,
    feedback=None,
    strategy_names=None,
    attempt=1,
):
    budget = energy_budget or {}
    contributions = budget.get("resources", {})
    planning_resources = {
        **resources,
        **contributions,
        "available_supply_kw": budget.get(
            "available_supply_kw", resources.get("available_supply_kw", 0)
        ),
        "battery_capacity_kwh": resources.get(
            "battery_capacity_kwh", budget.get("battery_available_energy_kwh", 0)
        ),
        "battery_soc_percent": resources.get(
            "battery_soc_percent", budget.get("battery_limits", {}).get("soc_percent", 0)
        ),
        "minimum_battery_reserve_percent": resources.get(
            "minimum_battery_reserve_percent",
            budget.get("battery_limits", {}).get("reserve_percent", 0),
        ),
        "battery_available_energy_kwh": budget.get(
            "battery_limits", {}
        ).get("available_energy_kwh", resources.get("battery_available_energy_kwh", 0)),
    }
    proposal = load_proposal or {}
    priority_order = proposal.get("priority_order")
    proposed_loads = proposal.get("loads", [])
    safe_cap = (feedback or {}).get("adjustments", {}).get("allocation_cap_kw")
    available_supply = max(0.0, float(planning_resources.get("available_supply_kw", 0)))

    results = []
    for strategy_name in strategy_names or STRATEGIES:
        dispatch = _resource_dispatch(
            strategy_name,
            available_supply,
            planning_resources,
            diagnosis,
        )
        allocation_limit = min(available_supply, dispatch["allocation_limit_kw"])
        if safe_cap is not None:
            allocation_limit = min(allocation_limit, max(0.0, float(safe_cap)))
        strategy = allocate_loads_for_strategy(
            loads,
            allocation_limit,
            strategy_name,
            priority_order=priority_order,
            allocation_proposal=proposed_loads,
        )
        actual_dispatch = _resource_dispatch(
            strategy_name,
            strategy["allocated_kw"],
            planning_resources,
            diagnosis,
        )
        strategy["generator_usage_kw"] = actual_dispatch["generator_usage_kw"]
        strategy["battery_discharge_kw"] = actual_dispatch["battery_discharge_kw"]
        strategy["grid_usage_kw"] = actual_dispatch["grid_usage_kw"]
        strategy["solar_usage_kw"] = actual_dispatch["solar_usage_kw"]
        battery_energy = float(planning_resources.get("battery_available_energy_kwh", 0))
        strategy["battery_runtime_minutes"] = round(
            battery_energy / strategy["battery_discharge_kw"] * 60
            if strategy["battery_discharge_kw"] > 0 else 0,
            2,
        )
        strategy["planning_attempt"] = attempt
        strategy["explanations"] = {
            "decision": (
                f"{strategy_name} allocated {strategy['allocated_kw']} kW using the "
                f"prioritiser's load order and the incident-specific resource budget."
            ),
            "constraints_considered": [
                "available supply",
                "battery discharge and reserve",
                "generator availability and capacity",
                "load demand and priority",
            ],
            "incident_type": (diagnosis or {}).get(
                "incident_type", (diagnosis or {}).get("incident")
            ),
            "load_priority_order": priority_order or [],
            "feedback_applied": feedback or {},
        }
        results.append(strategy)
    return {"strategies": results}
