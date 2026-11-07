from __future__ import annotations


def validate_strategy(strategy, resources, loads, diagnosis=None):
    budget = resources if "available_supply_kw" in resources else {}
    contributions = budget.get("resources", {})
    battery_limits = budget.get("battery_limits", {})
    available_supply = float(
        budget.get("available_supply_kw", resources.get("available_supply_kw", 0))
    )
    battery_limit = float(
        contributions.get(
            "battery_kw",
            resources.get(
                "battery_allowed_power_kw",
                resources.get("max_battery_discharge_kw", 0),
            ),
        )
    )
    battery_energy = float(
        battery_limits.get(
            "available_energy_kwh",
            resources.get(
                "battery_available_energy_kwh",
                max(
                    0.0,
                    float(resources.get("battery_capacity_kwh", 0))
                    * (
                        float(resources.get("battery_soc_percent", 0))
                        - float(resources.get("minimum_battery_reserve_percent", 0))
                    ) / 100.0,
                ),
            ),
        )
    )
    interval_hours = max(float(resources.get("interval_minutes", 15)) / 60.0, 0.0)
    generator_limit = float(
        contributions.get(
            "generator_kw",
            resources.get("generator_capacity_kw", 0)
            if resources.get("generator_available", False) else 0,
        )
    )
    grid_limit = float(
        contributions.get("grid_kw", resources.get("grid_availability_kw", 0))
    )
    solar_limit = float(
        contributions.get("solar_kw", resources.get("solar_generation_kw", 0))
    )
    total_demand = sum(float(load["demand_kw"]) for load in loads)
    allocated = float(strategy.get("allocated_kw", 0))
    battery_usage = float(strategy.get("battery_discharge_kw", 0))
    generator_usage = float(strategy.get("generator_usage_kw", 0))
    implicit_renewable_usage = max(0.0, allocated - generator_usage - battery_usage)
    grid_usage = float(
        strategy.get("grid_usage_kw", min(grid_limit, implicit_renewable_usage))
    )
    solar_usage = float(
        strategy.get("solar_usage_kw", max(0.0, implicit_renewable_usage - grid_usage))
    )
    allocation_rows = strategy.get("allocations", [])
    row_total = sum(float(load.get("allocated_kw", 0)) for load in allocation_rows)
    violations = []

    def violate(constraint_id, message, severity):
        violations.append({
            "constraint": constraint_id,
            "message": message,
            "severity": severity,
        })

    if allocated > available_supply + 1e-6:
        violate("supply_limit", "Allocated load power exceeds available supply.", "critical")
    if battery_usage > battery_limit + 1e-6:
        violate("battery_power_limit", "Battery discharge exceeds its interval power limit.", "critical")
    if battery_usage * interval_hours > battery_energy + 1e-6:
        violate("battery_energy_reserve", "Battery discharge would breach the minimum reserve.", "critical")
    if generator_usage > generator_limit + 1e-6:
        violate("generator_limit", "Generator usage exceeds available generator capacity.", "high")
    if grid_usage > grid_limit + 1e-6:
        violate("grid_limit", "Grid dispatch exceeds available grid power.", "high")
    if solar_usage > solar_limit + 1e-6:
        violate("solar_limit", "Solar dispatch exceeds available solar power.", "high")
    if abs(grid_usage + solar_usage + generator_usage + battery_usage - allocated) > 0.02:
        violate("resource_dispatch_balance", "Resource dispatch does not account for all allocated power.", "critical")
    if abs(row_total - allocated) > 1e-4:
        violate("allocation_total", "Load allocations do not match the strategy total.", "high")
    if any(float(load.get("allocated_kw", 0)) < 0 for load in allocation_rows):
        violate("nonnegative_loads", "Negative load allocation detected.", "critical")
    if any(
        float(load.get("allocated_kw", 0)) > float(load.get("demand_kw", 0)) + 1e-6
        for load in allocation_rows
    ):
        violate("load_demand_limit", "A load allocation exceeds its demand.", "high")
    if allocated > total_demand + 1e-6:
        violate("campus_demand_limit", "Total allocation exceeds campus demand.", "high")

    load_by_id = {load["id"]: load for load in loads}
    for allocation in allocation_rows:
        load = load_by_id.get(allocation.get("id"))
        if load and load.get("priority") == "Critical":
            minimum = float(load.get("minimum_kw", 0))
            if float(allocation.get("allocated_kw", 0)) + 1e-6 < minimum:
                violate(
                    "critical_load_minimum",
                    f"Critical load {load['name']} is below its minimum required power.",
                    "critical",
                )

    valid = not violations
    severity_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    severity = max(
        (item["severity"] for item in violations),
        key=lambda item: severity_rank[item],
        default="none",
    )
    adjustments = {}
    if any(item["constraint"] == "supply_limit" for item in violations):
        adjustments["allocation_cap_kw"] = max(0.0, available_supply)
    if not valid and not adjustments and allocated > 0:
        adjustments["allocation_cap_kw"] = max(0.0, allocated - 1.0)
    actionable_feedback = (
        ["Reduce planned load allocation to the reported safe power budget and revalidate."]
        if not valid else []
    )
    return {
        "valid": valid,
        "passed": valid,
        "errors": [item["message"] for item in violations],
        "warnings": [],
        "violated_constraints": violations,
        "severity": severity,
        "actionable_feedback": actionable_feedback,
        "adjustments": adjustments,
        "status": "Valid" if valid else "Invalid",
        "incident_type": (diagnosis or {}).get(
            "incident_type", (diagnosis or {}).get("incident")
        ),
    }
