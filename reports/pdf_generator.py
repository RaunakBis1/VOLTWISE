from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generate_pdf_report(simulation_data):
    reports_dir = Path(__file__).resolve().parent
    reports_dir.mkdir(parents=True, exist_ok=True)
    sim_id = simulation_data.get("simulation_id", "demo")
    file_path = reports_dir / f"voltwise_report_{sim_id}.pdf"

    c = canvas.Canvas(str(file_path), pagesize=letter)
    width, height = letter
    c.setTitle("VOLTWISE Simulation Report")
    c.setFillColorRGB(0.05, 0.12, 0.2)
    c.rect(0, 0, width, height, fill=1)
    c.setFillColorRGB(0.87, 0.95, 1)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(60, 740, "VOLTWISE")
    c.setFont("Helvetica", 12)
    c.drawString(60, 720, f"Simulation ID: {sim_id}")
    c.drawString(60, 700, f"Scenario: {simulation_data.get('scenario_name', 'Unknown')}")
    c.drawString(60, 680, f"Status: {simulation_data.get('status', 'Unknown')}")
    c.drawString(60, 660, f"Initial Demand: {simulation_data.get('initial_demand_kw', 0)} kW")
    c.drawString(60, 640, f"Available Supply: {simulation_data.get('available_supply_kw', 0)} kW")

    diagnosis = simulation_data.get("diagnosis", {})
    diagnosis_text = diagnosis.get("diagnosis", "No incident diagnosis recorded.")

    y = 600
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, "Incident Diagnosis")
    y -= 20
    c.setFont("Helvetica", 10)
    lines = [diagnosis_text[i:i + 90] for i in range(0, len(diagnosis_text), 90)]
    for line in lines[:6]:
        c.drawString(60, y, line)
        y -= 16

    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, 320, "Recommended Strategy")
    c.setFont("Helvetica", 10)
    recommended = simulation_data.get("recommended_strategy", {})
    c.drawString(60, 300, f"Strategy: {recommended.get('strategy_name', 'Unknown')}")
    c.drawString(60, 285, f"Score: {recommended.get('score', 0)}")
    c.drawString(60, 270, f"Allocated: {recommended.get('allocated_kw', 0)} kW")
    c.drawString(60, 255, f"Unmet Demand: {recommended.get('unmet_demand_kw', 0)} kW")

    c.save()
    return str(file_path)
