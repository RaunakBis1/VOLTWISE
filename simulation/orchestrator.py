from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from math import isfinite

from agents.energy_strategist import analyse_resources
from agents.grid_detective import investigate_incident
from agents.load_prioritiser import prioritise_loads
from agents.recovery_planner import STRATEGIES, generate_strategies
from agents.safety_validator import validate_strategy
from config import LOADS
from database.db import save_simulation
from simulation.calculations import build_loads, build_resource_snapshot, total_initial_demand
from simulation.scenarios import build_scenario


MAX_PLANNING_ATTEMPTS = 3


def _record_event(
    events,
    agent_name,
    action,
    inputs,
    outputs,
    explanation,
    status="Completed",
    validation_feedback=None,
    retry_count=0,
    candidate=None,
    attempt=None,
):
    event = {
        "agent_name": agent_name,
        "execution_order": len(events) + 1,
        "action": action,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input_summary": deepcopy(inputs),
        "output_summary": deepcopy(outputs),
        "decision_explanation": explanation,
        "execution_status": status.lower(),
        "status": status,
        "validation_feedback": deepcopy(validation_feedback or {}),
        "retry_count": retry_count,
    }
    if candidate is not None:
        event["candidate_strategy"] = candidate
    if attempt is not None:
        event["planning_attempt"] = attempt
    events.append(event)


def run_simulation(scenario_name, custom_overrides=None):
    scenario_name = scenario_name or "complete_grid_failure"
    scenario = build_scenario(scenario_name, custom_overrides or {})
    scenario["grid_availability_kw"] = float(scenario.get("grid_availability_kw", scenario.get("grid_capacity_kw", 0)))
    scenario["solar_generation_kw"] = float(scenario.get("solar_generation_kw", 0))
    scenario["battery_soc_percent"] = float(scenario.get("battery_soc_percent", 80))
    scenario["demand_multiplier"] = float(scenario.get("demand_multiplier", 1.0))
    scenario["interval_minutes"] = float(scenario.get("interval_minutes", 15))
    nonnegative_fields = (
        "grid_availability_kw",
        "solar_generation_kw",
        "battery_soc_percent",
        "demand_multiplier",
        "interval_minutes",
        "battery_capacity_kwh",
        "max_battery_discharge_kw",
        "minimum_battery_reserve_percent",
        "generator_capacity_kw",
    )
    if any(
        not isfinite(float(scenario.get(field, 0))) or float(scenario.get(field, 0)) < 0
        for field in nonnegative_fields
    ):
        raise ValueError("Scenario numeric values must be finite and nonnegative.")
    if not 0 <= scenario["battery_soc_percent"] <= 100:
        raise ValueError("Battery state of charge must be between 0 and 100 percent.")
    if not 0 <= scenario["minimum_battery_reserve_percent"] <= 100:
        raise ValueError("Minimum battery reserve must be between 0 and 100 percent.")

    initial_loads = build_loads(scenario["demand_multiplier"], LOADS)
    total_demand = total_initial_demand(initial_loads)
    resources = build_resource_snapshot(scenario)
    available_supply = resources["available_supply_kw"]
    events = []

    diagnosis = investigate_incident(scenario)
    _record_event(
        events,
        "Grid Detective",
        "Incident investigation",
        {"scenario": scenario},
        diagnosis,
        diagnosis["diagnosis"],
    )

    energy_budget = analyse_resources(scenario, diagnosis)
    _record_event(
        events,
        "Energy Strategist",
        "Resource and energy budget",
        {"scenario": scenario, "diagnosis": diagnosis},
        energy_budget,
        (
            f"Computed {energy_budget['available_supply_kw']} kW available supply and "
            f"{energy_budget['battery_limits']['available_energy_kwh']} kWh dischargeable "
            "battery energy after reserve."
        ),
    )

    load_proposal = prioritise_loads(
        initial_loads,
        energy_budget["available_supply_kw"],
        diagnosis,
        energy_budget,
    )
    _record_event(
        events,
        "Load Prioritiser",
        "Priority and allocation proposal",
        {
            "loads": initial_loads,
            "diagnosis": diagnosis,
            "energy_budget": energy_budget,
        },
        load_proposal,
        load_proposal["decision_explanation"],
    )

    candidates = []
    planning_attempts = []
    for strategy_name in STRATEGIES:
        feedback = None
        candidate_attempts = []
        strategy = None
        for attempt in range(1, MAX_PLANNING_ATTEMPTS + 1):
            planner_output = generate_strategies(
                {**scenario, **resources},
                initial_loads,
                diagnosis=diagnosis,
                energy_budget=energy_budget,
                load_proposal=load_proposal,
                feedback=feedback,
                strategy_names=[strategy_name],
                attempt=attempt,
            )
            strategy = planner_output["strategies"][0]
            _record_event(
                events,
                "Recovery Planner",
                "Strategy planning" if attempt == 1 else "Revised strategy planning",
                {
                    "candidate_strategy": strategy_name,
                    "attempt": attempt,
                    "diagnosis": diagnosis,
                    "energy_budget": energy_budget,
                    "load_proposal": load_proposal,
                    "validation_feedback": feedback or {},
                },
                strategy,
                strategy["explanations"]["decision"],
                validation_feedback=feedback,
                retry_count=attempt - 1,
                candidate=strategy_name,
                attempt=attempt,
            )

            validation = validate_strategy(
                strategy,
                energy_budget,
                initial_loads,
                diagnosis,
            )
            strategy["validation"] = validation
            attempt_record = {
                "candidate_strategy": strategy_name,
                "attempt": attempt,
                "strategy": strategy,
                "validation": validation,
            }
            planning_attempts.append(attempt_record)
            candidate_attempts.append({
                "attempt": attempt,
                "validation": validation,
                "allocated_kw": strategy["allocated_kw"],
            })
            _record_event(
                events,
                "Safety Validator",
                "Constraint validation",
                {
                    "strategy": strategy,
                    "energy_budget": energy_budget,
                    "loads": initial_loads,
                },
                validation,
                (
                    "Candidate passed all mandatory checks."
                    if validation["passed"] else
                    "Candidate rejected; actionable feedback returned to the Recovery Planner."
                ),
                status="Completed" if validation["passed"] else "Warning",
                validation_feedback=validation,
                retry_count=attempt - 1,
                candidate=strategy_name,
                attempt=attempt,
            )
            if validation["passed"]:
                break
            feedback = validation

        strategy["attempts"] = candidate_attempts
        candidates.append(strategy)

    approved = [strategy for strategy in candidates if strategy["validation"]["passed"]]
    recommended = max(approved, key=lambda item: item["score"]) if approved else None
    is_approved = recommended is not None
    result = {
        "scenario_name": scenario.get("scenario_name", scenario_name),
        "status": "ok" if is_approved else "warning",
        "safety_status": "approved" if is_approved else "unsafe",
        "message": (
            "Simulation completed with a safety-approved strategy."
            if is_approved else
            "No strategy passed all mandatory safety checks; no strategy is approved."
        ),
        "initial_demand_kw": total_demand,
        "available_supply_kw": available_supply,
        "deficit_kw": max(0.0, total_demand - available_supply),
        "diagnosis": diagnosis,
        "resource_analysis": energy_budget,
        "energy_budget": energy_budget,
        "load_priority": load_proposal,
        "strategies": candidates,
        "recommended_strategy": recommended,
        "recommendation_status": "Passed" if is_approved else "Unsafe",
        "planning_attempts": planning_attempts,
        "logs": events,
        "agent_events": events,
    }

    sim_id = save_simulation(result["scenario_name"], result)
    result["simulation_id"] = sim_id
    return result
