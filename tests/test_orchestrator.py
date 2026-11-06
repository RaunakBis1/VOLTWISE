import pytest

from simulation.orchestrator import run_simulation


def test_complete_grid_failure_case():
    result = run_simulation("complete_grid_failure")
    assert result["status"] in {"ok", "warning"}
    assert result["diagnosis"]["incident"] == "Complete grid failure"
    assert result["simulation_id"]


def test_custom_scenario_runs():
    result = run_simulation("custom", {"grid_availability_kw": 35, "solar_generation_kw": 10, "battery_soc_percent": 60, "generator_available": True, "demand_multiplier": 1.2})
    assert result["status"] in {"ok", "warning"}
    assert result["scenario_name"] == "Custom Scenario"


def test_invalid_scenario_rejected():
    with pytest.raises(ValueError):
        run_simulation("not_a_real_scenario")
