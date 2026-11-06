from __future__ import annotations

from config import DEFAULT_RESOURCES, SCENARIO_LIBRARY


def build_scenario(scenario_name, overrides=None):
    if scenario_name is None:
        scenario_name = "complete_grid_failure"

    if scenario_name == "custom":
        scenario = {"scenario_name": "Custom Scenario", **DEFAULT_RESOURCES}
    else:
        if scenario_name not in SCENARIO_LIBRARY:
            raise ValueError(f"Unknown scenario: {scenario_name}")
        scenario = dict(SCENARIO_LIBRARY[scenario_name])

    base = dict(DEFAULT_RESOURCES)
    base.update(scenario)
    if overrides:
        base.update(overrides)
    base["grid_capacity_kw"] = float(base.get("grid_availability_kw", base.get("grid_capacity_kw", 0)))
    base["scenario_name"] = base.get("scenario_name", scenario_name)
    return base
