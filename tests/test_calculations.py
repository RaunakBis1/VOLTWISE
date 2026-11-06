from simulation.calculations import allocate_loads_for_strategy, compute_battery_limits, total_available_supply


def test_battery_limits_respect_minimum_reserve():
    resources = {
        "battery_capacity_kwh": 200,
        "battery_soc_percent": 80,
        "minimum_battery_reserve_percent": 20,
        "max_battery_discharge_kw": 40,
        "interval_minutes": 15,
    }
    limits = compute_battery_limits(resources, 0.25)
    assert limits["available_energy_kwh"] == 120.0
    assert limits["max_discharge_power_kw"] == 40.0


def test_total_supply_is_not_over_limit():
    resources = {
        "grid_availability_kw": 100,
        "solar_generation_kw": 25,
        "battery_capacity_kwh": 200,
        "battery_soc_percent": 80,
        "minimum_battery_reserve_percent": 20,
        "max_battery_discharge_kw": 40,
        "generator_capacity_kw": 30,
        "generator_available": True,
        "interval_minutes": 15,
    }
    total = total_available_supply(resources)
    assert total <= 195.0
    assert total > 0


def test_load_allocation_keeps_total_under_supply():
    loads = [
        {"id": "a", "name": "Emergency Lighting", "demand_kw": 10, "priority": "Critical", "minimum_kw": 10},
        {"id": "b", "name": "Computer Laboratory", "demand_kw": 35, "priority": "High", "minimum_kw": 20},
        {"id": "c", "name": "Academic Building", "demand_kw": 30, "priority": "Normal", "minimum_kw": 15},
    ]
    result = allocate_loads_for_strategy(loads, 45, "Balanced Distribution")
    assert result["allocated_kw"] <= 45
    assert result["unmet_demand_kw"] >= 0
