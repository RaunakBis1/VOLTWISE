from __future__ import annotations

from datetime import datetime, timezone

from agents.energy_strategist import analyse_resources
from agents.grid_detective import investigate_incident
from agents.load_prioritiser import prioritise_loads
from agents.recovery_planner import generate_strategies
from agents.safety_validator import validate_strategy
from config import DEFAULT_RESOURCES, LOADS, SCENARIO_LIBRARY
from database.db import save_simulation
from simulation.calculations import build_loads, build_resource_snapshot, total_initial_demand
from simulation.scenarios import build_scenario


def run_simulation(scenario_name, custom_overrides=None):
    scenario_name = scenario_name or "complete_grid_failure"
    scenario = build_scenario(scenario_name, custom_overrides or {})
    scenario["grid_availability_kw"] = float(scenario.get("grid_availability_kw", scenario.get("grid_capacity_kw", 0)))
    scenario["solar_generation_kw"] = float(scenario.get("solar_generation_kw", 0))
    scenario["battery_soc_percent"] = float(scenario.get("battery_soc_percent", 80))
    scenario["demand_multiplier"] = float(scenario.get("demand_multiplier", 1.0))
    scenario["interval_minutes"] = float(scenario.get("interval_minutes", 15))
    if scenario["grid_availability_kw"] < 0 or scenario["solar_generation_kw"] < 0 or scenario["battery_soc_percent"] < 0 or scenario["demand_multiplier"] < 0:
        raise ValueError("Scenario values cannot be negative.")
    if not 0 <= scenario["battery_soc_percent"] <= 100:
        raise ValueError("Battery state of charge must be between 0 and 100 percent.")
    initial_loads = build_loads(scenario["demand_multiplier"], LOADS)
    total_demand = total_initial_demand(initial_loads)
    resources = build_resource_snapshot(scenario)
    available_supply = resources["available_supply_kw"]

    detective = investigate_incident(scenario)
    strategist = analyse_resources(scenario)
    prioritiser = prioritise_loads(initial_loads, available_supply)
    planner = generate_strategies({**scenario, **resources}, initial_loads)

    validated = []
    invalid = []
    for strategy in planner["strategies"]:
        validation = validate_strategy(strategy, {**scenario, **resources}, initial_loads)
        strategy["validation"] = validation
        strategy["battery_discharge_kw"] = round(resources.get("battery_allowed_power_kw", 0), 2)
        strategy["generator_usage_kw"] = round(min(float(scenario.get("generator_capacity_kw", 0)), max(0.0, available_supply * 0.2)), 2)
        if validation["valid"]:
            validated.append(strategy)
        else:
            invalid.append(strategy)

    if validated:
        recommended = max(validated, key=lambda item: item["score"])
        recommendation_status = "Passed"
    else:
        recommended = max(planner["strategies"], key=lambda item: item["score"]) if planner["strategies"] else {}
        recommendation_status = "Needs review"

    result = {
        "scenario_name": scenario.get("scenario_name", scenario_name),
        "status": "ok" if validated else "warning",
        "message": "Simulation completed successfully." if validated else "No valid strategy passed safety checks.",
        "initial_demand_kw": total_demand,
        "available_supply_kw": available_supply,
        "deficit_kw": max(0.0, total_demand - available_supply),
        "diagnosis": detective,
        "resource_analysis": strategist,
        "load_priority": prioritiser,
        "strategies": planner["strategies"],
        "recommended_strategy": recommended,
        "recommendation_status": recommendation_status,
        "logs": [
            {
                "agent_name": "Grid Detective",
                "action": "Incident investigation",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "input_summary": f"grid={scenario.get('grid_availability_kw', 0)}kW solar={scenario.get('solar_generation_kw', 0)}kW battery={scenario.get('battery_soc_percent', 0)}% demand={scenario.get('demand_multiplier', 1)}x",
                "output_summary": detective["diagnosis"],
                "status": "Completed",
            },
            {
                "agent_name": "Energy Strategist",
                "action": "Resource analysis",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "input_summary": f"resources={scenario}",
                "output_summary": f"Available supply {available_supply} kW with battery max discharge {resources.get('battery_allowed_power_kw', 0)} kW.",
                "status": "Completed",
            },
            {
                "agent_name": "Load Prioritiser",
                "action": "Critical load allocation",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "input_summary": f"Loads={len(initial_loads)} total demand={total_demand} kW",
                "output_summary": f"Priority order: {[item['name'] for item in prioritiser['loads']]}",
                "status": "Completed",
            },
            {
                "agent_name": "Recovery Planner",
                "action": "Strategy generation",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "input_summary": f"Available {available_supply} kW",
                "output_summary": f"Generated {len(planner['strategies'])} strategy options.",
                "status": "Completed",
            },
            {
                "agent_name": "Safety Validator",
                "action": "Constraint validation",
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "input_summary": f"Strategies={len(planner['strategies'])}, valid={len(validated)}",
                "output_summary": "Validated all constraints and flagged any invalid options." if planner["strategies"] else "No strategies available.",
                "status": "Completed" if planner["strategies"] else "Warning",
            },
        ],
    }

    # persist to database and attach id
    sim_id = save_simulation(result["scenario_name"], result)
    result["simulation_id"] = sim_id
    return result
