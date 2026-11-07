from __future__ import annotations

from config import PRIORITY_ORDER
from simulation.calculations import allocate_loads_for_strategy, build_loads


def prioritise_loads(loads, available_supply_kw, diagnosis=None, energy_budget=None):
    sorted_loads = sorted(loads, key=lambda item: (PRIORITY_ORDER.get(item["priority"], 99), item["demand_kw"]))
    remaining = float(available_supply_kw)
    allocations = []
    for rank, load in enumerate(sorted_loads, start=1):
        demand = float(load["demand_kw"])
        minimum = float(load["minimum_kw"])
        target = demand if load["priority"] == "Critical" else minimum if load["priority"] == "High" else min(demand, minimum)
        allocated = min(target, remaining, demand)
        remaining = max(0.0, remaining - allocated)
        allocations.append({
            **load,
            "required_kw": round(demand, 2),
            "minimum_kw": round(minimum, 2),
            "rank": rank,
            "allocated_kw": round(allocated, 2),
        })
    total_demand = sum(item["demand_kw"] for item in loads)
    total_allocated = sum(item["allocated_kw"] for item in allocations)
    return {
        "priority_order": [item["name"] for item in sorted_loads],
        "allocated_kw": round(total_allocated, 2),
        "unmet_demand_kw": round(max(0.0, total_demand - total_allocated), 2),
        "loads": allocations,
        "energy_budget_kw": round(float(available_supply_kw), 2),
        "incident_type": (diagnosis or {}).get("incident_type", (diagnosis or {}).get("incident")),
        "decision_explanation": (
            "Loads are ranked by configured priority; the proposal is bounded by the energy budget."
        ),
    }
