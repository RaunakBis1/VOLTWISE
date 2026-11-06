from reports.pdf_generator import generate_pdf_report


def test_pdf_generation_creates_file():
    report_path = generate_pdf_report({"simulation_id": 123, "scenario_name": "Test scenario", "status": "ok"})
    assert report_path.endswith(".pdf")
