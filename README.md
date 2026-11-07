# VOLTWISE

VOLTWISE is a deterministic, explainable campus-microgrid simulation and decision-support platform. Its five autonomous software agents use explicit decision logic; they are not LLM-powered and do not control live electrical equipment.

## Features
- Five specialised agents
- Scenario-driven simulations
- Structured incident diagnosis, interval energy budget, and prioritized load allocation
- Three explainable recovery strategies with mandatory safety validation
- Bounded feedback/replanning (at most three attempts per strategy) and an execution event log
- SQLite history
- PDF report generation
- Modern dashboard UI


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

## Collaborative simulation flow

Each run passes structured outputs through the agents in order:

1. **Grid Detective** diagnoses the incident, affected resources, severity, supply, and constraints.
2. **Energy Strategist** calculates resource contributions and battery discharge/energy limits after reserve.
3. **Load Prioritiser** ranks loads and proposes bounded required/minimum power allocations.
4. **Recovery Planner** uses those outputs to produce Critical Loads First, Balanced Distribution, and Maximum Backup Conservation candidates with decision explanations.
5. **Safety Validator** checks each candidate. Rejections are passed back to the planner for a bounded retry; every planning attempt and validation is recorded in the response's `logs`/`agent_events`.

Only a candidate that passes mandatory checks can appear as `recommended_strategy`. If none pass, the run reports `safety_status: "unsafe"` and returns no recommendation. The existing Flask API, dashboard, SQLite history, PDF reports, and five scenarios (including custom) remain available.

## Important note
This tool is an educational simulation and decision-support system. It does not control live electrical systems.
