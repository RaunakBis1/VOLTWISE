# VOLTWISE

VOLTWISE is an autonomous AI grid intelligence and recovery simulation platform for a campus microgrid.

## Features
- Five specialised agents
- Scenario-driven simulations
- Power allocation and battery safety logic
- SQLite history
- PDF report generation
- Modern dashboard UI

## Quick start on Windows

```powershell
cd D:\VOLTWISE
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

If PowerShell blocks script execution, run:

```powershell
cd D:\VOLTWISE
python -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe app.py
```

## Project structure
- `agents/` - agent logic
- `simulation/` - orchestration and calculations
- `database/` - database layer
- `reports/` - PDF reports
- `templates/` - HTML frontend
- `static/` - CSS and JS assets
- `tests/` - automated pytest checks

## Demo scenarios
- Complete grid failure
- Solar collapse
- Battery emergency
- Demand surge
- Custom scenario

## Important note
This tool is an educational simulation and decision-support system. It does not control live electrical systems.
