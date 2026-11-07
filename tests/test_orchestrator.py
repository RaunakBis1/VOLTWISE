import pytest

from simulation.orchestrator import run_simulation


def test_complete_grid_failure_case():
    result = run_simulation("complete_grid_failure")
    assert result["status"] in {"ok", "warning"}
    assert result["diagnosis"]["incident"] == "Complete grid failure"
    assert result["simulation_id"]
    assert result["diagnosis"]["severity"] == "Critical"
    assert result["available_supply_kw"] == 95.0
    assert sum(
        result["resource_analysis"]["resources"][key]
        for key in ("grid_kw", "solar_kw", "generator_kw", "battery_kw")
    ) == result["available_supply_kw"]
    assert result["recommended_strategy"]["battery_discharge_kw"] == 40.0


def test_battery_dispatch_respects_soc_reserve_in_grid_failure():
    result = run_simulation("complete_grid_failure", {"battery_soc_percent": 20})

    assert result["diagnosis"]["incident"] == "Complete grid failure"
    assert result["resource_analysis"]["resources"]["battery_soc_percent"] == 20.0
    assert result["resource_analysis"]["resources"]["battery_kw"] == 0.0
    assert result["available_supply_kw"] == 55.0
    assert result["recommended_strategy"]["battery_discharge_kw"] == 0.0


def test_custom_scenario_runs():
    result = run_simulation("custom", {"grid_availability_kw": 35, "solar_generation_kw": 10, "battery_soc_percent": 60, "generator_available": True, "demand_multiplier": 1.2})
    assert result["status"] in {"ok", "warning"}
    assert result["scenario_name"] == "Custom Scenario"


def test_invalid_scenario_rejected():
    with pytest.raises(ValueError):
        run_simulation("not_a_real_scenario")
