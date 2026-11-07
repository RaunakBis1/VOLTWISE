from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from config import DB_PATH


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_name TEXT,
            created_at TEXT,
            payload TEXT,
            summary TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def save_simulation(scenario_name, payload):
    conn = get_connection()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO simulations (scenario_name, created_at, payload, summary) VALUES (?, ?, ?, ?)",
        (
            scenario_name,
            created_at,
            json.dumps(payload, default=str),
            json.dumps({
                "recommendation": (payload.get("recommended_strategy") or {}).get("strategy_name"),
                "status": payload.get("status"),
                "created_at": created_at,
            }, default=str),
        ),
    )
    conn.commit()
    sim_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.close()
    return sim_id


def list_simulations():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, scenario_name, created_at, payload, summary FROM simulations ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_simulation(simulation_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, scenario_name, created_at, payload, summary FROM simulations WHERE id = ?",
        (simulation_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_simulation(simulation_id):
    conn = get_connection()
    conn.execute("DELETE FROM simulations WHERE id = ?", (simulation_id,))
    conn.commit()
    conn.close()
    return True


def reset_simulations():
    conn = get_connection()
    conn.execute("DELETE FROM simulations")
    conn.commit()
    conn.close()
    return True


init_db()
