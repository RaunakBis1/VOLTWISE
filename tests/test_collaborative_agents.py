from copy import deepcopy

import simulation.orchestrator as orchestrator
import agents.recovery_planner as recovery_planner
from agents.energy_strategist import analyse_resources
from agents.load_prioritiser import prioritise_loads
from config import DEFAULT_RESOURCES, SCENARIO_LIBRARY
from simulation.calculations import build_resource_snapshot
from simulation.orchestrator import run_simulation


def _loads():
    return [
        {
            "id": "critical",
            "name": "Emergency Lighting",
            "demand_kw": 10,
            "priority": "Critical",
            "minimum_kw": 10,
        },
        {
            "id": "normal",
            "name": "Academic Building",
            "demand_kw": 20,
            "priority": "Normal",
            "minimum_kw": 0,
        },
    ]


def test_all_agents_exchange_structured_outputs_in_execution_order():
    result = run_simulation("complete_grid_failure")
    events = result["agent_events"]
    names = {event["agent_name"] for event in events}

    assert names == {
        "Grid Detective",
        "Energy Strategist",
        "Load Prioritiser",
        "Recovery Planner",
        "Safety Validator",
    }
    assert [event["execution_order"] for event in events] == list(range(1, len(events) + 1))

    energy_event = next(event for event in events if event["agent_name"] == "Energy Strategist")
    assert energy_event["input_summary"]["diagnosis"] == result["diagnosis"]
    priority_event = next(event for event in events if event["agent_name"] == "Load Prioritiser")
    assert priority_event["input_summary"]["energy_budget"] == result["energy_budget"]
    planner_event = next(event for event in events if event["agent_name"] == "Recovery Planner")
    assert planner_event["input_summary"]["load_proposal"] == result["load_priority"]
    assert isinstance(planner_event["output_summary"]["explanations"], dict)


def test_diagnosis_changes_resource_dispatch_used_by_planner():
    resources = {
        **DEFAULT_RESOURCES,
        "grid_availability_kw": 10,
        "solar_generation_kw": 2.5,
        "generator_capacity_kw": 20,
        "battery_soc_percent": 80,
    }
    budget = analyse_resources(resources)
    loads = [{
        "id": "load",
        "name": "Load",
        "demand_kw": 20,
        "priority": "Normal",
        "minimum_kw": 20,
    }]
    proposal = prioritise_loads(loads, budget["available_supply_kw"])
    planner_resources = {**resources, **build_resource_snapshot(resources)}

    solar_diagnosis = {"incident_type": "Solar power collapse"}
    battery_diagnosis = {"incident_type": "Battery emergency"}
    solar_candidate = recovery_planner.generate_strategies(
        planner_resources,
        loads,
        solar_diagnosis,
        budget,
        proposal,
        strategy_names=["Balanced Distribution"],
    )["strategies"][0]
    battery_candidate = recovery_planner.generate_strategies(
        planner_resources,
        loads,
        battery_diagnosis,
        budget,
        proposal,
        strategy_names=["Balanced Distribution"],
    )["strategies"][0]

    assert solar_candidate["battery_discharge_kw"] > battery_candidate["battery_discharge_kw"]
    assert solar_candidate["explanations"]["incident_type"] == "Solar power collapse"


def test_energy_budget_and_priority_proposal_bound_planner_allocations():
    resources = {
        **DEFAULT_RESOURCES,
        "grid_availability_kw": 10,
        "solar_generation_kw": 0,
        "generator_available": False,
        "battery_soc_percent": 20,
    }
    budget = analyse_resources(resources)
    loads = _loads()
    normal_first_proposal = {
        "priority_order": ["Academic Building", "Emergency Lighting"],
        "loads": [
            {"id": "critical", "allocated_kw": 0},
            {"id": "normal", "allocated_kw": 10},
        ],
    }
    critical_first_proposal = {
        "priority_order": ["Emergency Lighting", "Academic Building"],
        "loads": [
            {"id": "critical", "allocated_kw": 10},
            {"id": "normal", "allocated_kw": 0},
        ],
    }
    planner_resources = {**resources, **build_resource_snapshot(resources)}

    def candidate(proposal, energy_budget=budget):
        return recovery_planner.generate_strategies(
            planner_resources,
            loads,
            {"incident_type": "Normal"},
            energy_budget,
            proposal,
            strategy_names=["Critical Loads First"],
        )["strategies"][0]

    priority_changed = candidate(normal_first_proposal)
    priority_preserved = candidate(critical_first_proposal)
    assert priority_changed["allocations"][0]["id"] == "normal"
    assert priority_preserved["allocations"][0]["id"] == "critical"

    smaller_budget = deepcopy(budget)
    smaller_budget["available_supply_kw"] = 5
    reduced = candidate(critical_first_proposal, smaller_budget)
    assert reduced["allocated_kw"] <= 5
    assert reduced["allocated_kw"] < priority_preserved["allocated_kw"]


def test_rejected_candidate_feedback_is_used_for_successful_replanning(monkeypatch):
    real_validator = orchestrator.validate_strategy
    calls = []

    def reject_first(strategy, resources, loads, diagnosis=None):
        calls.append(strategy["strategy_name"])
        if len(calls) == 1:
            return {
                "valid": False,
                "passed": False,
                "status": "Invalid",
                "severity": "high",
                "errors": ["Test policy requested a lower allocation."],
                "violated_constraints": [{
                    "constraint": "test_allocation_cap",
                    "message": "Test policy requested a lower allocation.",
                    "severity": "high",
                }],
                "actionable_feedback": ["Reduce the allocation and retry."],
                "adjustments": {"allocation_cap_kw": max(0, strategy["allocated_kw"] - 5)},
            }
        return real_validator(strategy, resources, loads, diagnosis)

    monkeypatch.setattr(orchestrator, "validate_strategy", reject_first)
    result = run_simulation("complete_grid_failure")

    first_candidate = result["strategies"][0]
    assert [attempt["attempt"] for attempt in first_candidate["attempts"]] == [1, 2]
    retry = next(
        event for event in result["logs"]
        if event["agent_name"] == "Recovery Planner"
        and event.get("candidate_strategy") == first_candidate["strategy_name"]
        and event.get("planning_attempt") == 2
    )
    assert retry["input_summary"]["validation_feedback"]["violated_constraints"][0]["constraint"] == "test_allocation_cap"
    assert first_candidate["validation"]["passed"]
    assert result["recommended_strategy"]["validation"]["passed"]


def test_each_candidate_stops_after_three_rejected_attempts(monkeypatch):
    def always_reject(strategy, resources, loads, diagnosis=None):
        return {
            "valid": False,
            "passed": False,
            "status": "Invalid",
            "severity": "critical",
            "errors": ["Policy rejection."],
            "violated_constraints": [{
                "constraint": "policy_rejection",
                "message": "Policy rejection.",
                "severity": "critical",
            }],
            "actionable_feedback": ["Replan within limits."],
            "adjustments": {"allocation_cap_kw": max(0, strategy["allocated_kw"] - 1)},
        }

    monkeypatch.setattr(orchestrator, "validate_strategy", always_reject)
    result = run_simulation("complete_grid_failure")

    assert all(len(strategy["attempts"]) == 3 for strategy in result["strategies"])
    assert len(result["planning_attempts"]) == 9
    assert result["recommended_strategy"] is None
    assert result["safety_status"] == "unsafe"
    assert result["recommendation_status"] == "Unsafe"
    assert result["status"] == "warning"
    assert all(not strategy["validation"]["passed"] for strategy in result["strategies"])


def test_no_safe_strategy_is_never_returned_as_recommendation():
    result = run_simulation(
        "custom",
        {
            "grid_availability_kw": 0,
            "solar_generation_kw": 0,
            "generator_capacity_kw": 0,
            "generator_available": False,
            "battery_soc_percent": 20,
        },
    )

    assert result["available_supply_kw"] == 0
    assert result["recommended_strategy"] is None
    assert result["safety_status"] == "unsafe"
    assert all(not strategy["validation"]["passed"] for strategy in result["strategies"])


def test_existing_scenarios_keep_all_three_validated_strategies():
    for scenario_name in (*SCENARIO_LIBRARY, "custom"):
        result = run_simulation(scenario_name)

        assert len(result["strategies"]) == 3
        assert all(strategy["validation"]["passed"] for strategy in result["strategies"])
        assert result["recommended_strategy"]["strategy_name"] in {
            strategy["strategy_name"] for strategy in result["strategies"]
        }


def test_validation_events_match_every_actual_attempt_and_feedback():
    result = run_simulation("complete_grid_failure")
    planner_events = [event for event in result["logs"] if event["agent_name"] == "Recovery Planner"]
    validator_events = [event for event in result["logs"] if event["agent_name"] == "Safety Validator"]

    assert len(planner_events) == len(validator_events) == len(result["planning_attempts"])
    assert all(event["output_summary"]["strategy_name"] == event["candidate_strategy"] for event in planner_events)
    assert all(
        event["output_summary"]["passed"]
        == result["planning_attempts"][index]["validation"]["passed"]
        for index, event in enumerate(validator_events)
    )
    assert all(event["execution_status"] in {"completed", "warning"} for event in result["logs"])
    assert result["logs"] == result["agent_events"]
