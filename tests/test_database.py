from database.db import delete_simulation, get_simulation, list_simulations, save_simulation


def test_database_persistence():
    sim_id = save_simulation("battery_emergency", {"status": "ok", "scenario_name": "Battery Emergency"})
    item = get_simulation(sim_id)
    assert item is not None
    assert item["scenario_name"] == "battery_emergency"
    assert len(list_simulations()) >= 1
    delete_simulation(sim_id)
