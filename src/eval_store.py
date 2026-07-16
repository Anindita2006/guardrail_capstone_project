"""Persistence for evaluation runs and per-scenario judge scores. Separate from
audit.py because this tracks *evaluation-suite* history, not live user queries,
but lives in the same sqlite file for simplicity."""
from __future__ import annotations

import json
import sqlite3
import statistics
import uuid
from datetime import datetime, timezone

from src.config import DB_PATH
from src.judge import DIMENSIONS, RAGAS_METRICS

SCHEMA = """
CREATE TABLE IF NOT EXISTS eval_runs (
    run_id TEXT PRIMARY KEY,
    dataset TEXT,
    timestamp TEXT,
    n_total INTEGER,
    n_passed INTEGER,
    pass_rate REAL,
    avg_trust_score REAL,
    avg_latency REAL
);

CREATE TABLE IF NOT EXISTS judge_scores (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    scenario_name TEXT,
    category TEXT,
    audit_record_id TEXT,
    question_text TEXT,
    timestamp TEXT,
    scenario_passed INTEGER,
    verdict TEXT,
    trust_score INTEGER,
    dimensions_json TEXT,
    ragas_json TEXT,
    explanation TEXT,
    judge_model TEXT
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn


def new_run_id() -> str:
    return f"run_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"


def record_eval_run(
    run_id: str,
    dataset: str,
    n_total: int,
    n_passed: int,
    avg_latency: float,
    avg_trust_score: float | None,
) -> None:
    conn = _connect()
    with conn:
        conn.execute(
            """INSERT INTO eval_runs (run_id, dataset, timestamp, n_total, n_passed,
               pass_rate, avg_trust_score, avg_latency) VALUES (?,?,?,?,?,?,?,?)""",
            (
                run_id,
                dataset,
                datetime.now(timezone.utc).isoformat(),
                n_total,
                n_passed,
                (n_passed / n_total) if n_total else 0.0,
                avg_trust_score,
                avg_latency,
            ),
        )
    conn.close()


def record_judge_score(
    run_id: str | None,
    scenario_name: str,
    category: str,
    audit_record_id: str | None,
    question_text: str,
    scenario_passed: bool,
    judgment: dict,
) -> None:
    conn = _connect()
    with conn:
        conn.execute(
            """INSERT INTO judge_scores (
                id, run_id, scenario_name, category, audit_record_id, question_text,
                timestamp, scenario_passed, verdict, trust_score, dimensions_json,
                ragas_json, explanation, judge_model
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                run_id,
                scenario_name,
                category,
                audit_record_id,
                question_text,
                datetime.now(timezone.utc).isoformat(),
                int(bool(scenario_passed)),
                judgment["verdict"],
                judgment["trust_score"],
                json.dumps(judgment["dimensions"]),
                json.dumps(judgment["ragas"]),
                judgment["explanation"],
                judgment["judge_model"],
            ),
        )
    conn.close()


def _row_to_judge_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["dimensions"] = json.loads(d.pop("dimensions_json") or "{}")
    d["ragas"] = json.loads(d.pop("ragas_json") or "{}")
    return d


def list_eval_runs(limit: int = 50) -> list[dict]:
    conn = _connect()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM eval_runs ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_judge_scores(run_id: str | None = None, limit: int = 200) -> list[dict]:
    conn = _connect()
    conn.row_factory = sqlite3.Row
    if run_id:
        rows = conn.execute(
            "SELECT * FROM judge_scores WHERE run_id = ? ORDER BY timestamp DESC LIMIT ?",
            (run_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM judge_scores ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [_row_to_judge_dict(r) for r in rows]


def latest_run_averages() -> dict | None:
    """Dimension + RAGAS averages for the most recent eval run, for the Dashboard
    and RAGAS/8-dimension summary views. None if no run has been recorded yet."""
    runs = list_eval_runs(limit=1)
    if not runs:
        return None
    scores = list_judge_scores(run_id=runs[0]["run_id"])
    if not scores:
        return None
    dims = {d: statistics.fmean(s["dimensions"].get(d, 0) for s in scores) for d in DIMENSIONS}
    ragas = {m: statistics.fmean(s["ragas"].get(m, 0) for s in scores) for m in RAGAS_METRICS}
    pass_rate = sum(1 for s in scores if s["verdict"] == "PASS") / len(scores)
    return {
        "run": runs[0],
        "dimensions": dims,
        "ragas": ragas,
        "judge_pass_rate": pass_rate,
        "n_scored": len(scores),
    }
