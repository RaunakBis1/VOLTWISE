from __future__ import annotations

from simulation.orchestrator import run_simulation


def simulate(scenario_name, custom_overrides=None):
    custom_overrides = custom_overrides or {}
    return run_simulation(scenario_name, custom_overrides)
