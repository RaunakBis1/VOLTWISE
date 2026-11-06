from app import app


def test_health_endpoint():
    client = app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"


def test_simulate_endpoint():
    client = app.test_client()
    response = client.post("/api/simulate", json={"scenario_name": "solar_power_collapse"})
    assert response.status_code == 200
    data = response.get_json()
    assert "diagnosis" in data


def test_invalid_scenario_is_rejected():
    client = app.test_client()
    response = client.post("/api/simulate", json={"scenario_name": "does_not_exist"})
    assert response.status_code == 400
    assert "error" in response.get_json()
