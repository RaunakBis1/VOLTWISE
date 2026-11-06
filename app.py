from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from config import APP_NAME, APP_TAGLINE, BASE_DIR, SCENARIO_LIBRARY
from database.db import delete_simulation, get_simulation, list_simulations, reset_simulations, save_simulation
from reports.pdf_generator import generate_pdf_report
from simulation.orchestrator import run_simulation

app = Flask(__name__, static_folder=str(BASE_DIR / "static"), template_folder=str(BASE_DIR / "templates"))
app.config["JSON_SORT_KEYS"] = False


@app.route("/")
def index():
    return render_template("index.html", app_name=APP_NAME, app_tagline=APP_TAGLINE)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "app": APP_NAME, "tagline": APP_TAGLINE})


@app.route("/api/scenarios")
def scenarios():
    return jsonify({"scenarios": SCENARIO_LIBRARY})


@app.route("/api/simulate", methods=["POST"])
def simulate():
    payload = request.get_json(silent=True) or {}
    scenario_name = payload.get("scenario_name") or "complete_grid_failure"
    custom_overrides = payload.get("custom_overrides") or {}

    try:
        result = run_simulation(scenario_name, custom_overrides)
    except ValueError as exc:
        return jsonify({"error": str(exc), "status": "invalid_input"}), 400
    except Exception as exc:
        return jsonify({"error": "Simulation failed", "detail": str(exc)}), 500

    if result.get("status") in {"error", "invalid"}:
        return jsonify({"error": result.get("message", "Simulation failed"), "status": "invalid_input"}), 400

    return jsonify(result)


@app.route("/api/simulations")
def simulations():
    sims = list_simulations()
    return jsonify({"simulations": sims})


@app.route("/api/simulations/<int:simulation_id>")
def simulation_detail(simulation_id):
    item = get_simulation(simulation_id)
    if item is None:
        return jsonify({"error": "Simulation not found"}), 404
    return jsonify({"simulation": item})


@app.route("/api/simulations/<int:simulation_id>", methods=["DELETE"])
def delete_simulation_route(simulation_id):
    if delete_simulation(simulation_id):
        return jsonify({"status": "deleted", "id": simulation_id})
    return jsonify({"error": "Unable to delete simulation"}), 500


@app.route("/api/reset", methods=["POST"])
def reset():
    reset_simulations()
    return jsonify({"status": "reset"})


@app.route("/api/simulation/<int:simulation_id>/report")
def simulation_report(simulation_id):
    item = get_simulation(simulation_id)
    if item is None:
        return jsonify({"error": "Simulation not found"}), 404
    payload = json.loads(item["payload"])
    report_path = generate_pdf_report(payload)
    return send_file(report_path, as_attachment=True, download_name=Path(report_path).name)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
