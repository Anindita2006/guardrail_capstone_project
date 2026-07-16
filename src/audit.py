"""Append-only audit log for every query the agent processes, plus the
escalation workflow (assignment / SLA) built on top of it."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

from src.config import DB_PATH, HIGH_STAKES_SLA_HOURS, MEDIUM_STAKES_SLA_HOURS

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    user TEXT,
    question_text TEXT NOT NULL,
    retrieved_clauses TEXT NOT NULL,   -- JSON list
    topic TEXT,
    owner TEXT,
    stakes TEXT,
    confidence REAL,
    answer_text TEXT,
    citations TEXT,                    -- JSON list
    in_corpus INTEGER,
    escalated INTEGER,
    escalation_reason TEXT,
    escalated_to TEXT,
    human_review_status TEXT,          -- n/a | pending | assigned | reviewed
    reviewer TEXT,
    review_timestamp TEXT,
    injection_flagged INTEGER,
    agent_turns INTEGER,
    tool_calls TEXT                    -- JSON list of tool call names, for trace eval
);
"""

# Columns added after the initial release. Guarded migration below adds them to
# existing databases without touching already-logged rows.
_MIGRATIONS = {
    "assigned_to": "ALTER TABLE audit_log ADD COLUMN assigned_to TEXT",
    "sla_due_at": "ALTER TABLE audit_log ADD COLUMN sla_due_at TEXT",
    "decision_note": "ALTER TABLE audit_log ADD COLUMN decision_note TEXT",
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(audit_log)")}
    for col, ddl in _MIGRATIONS.items():
        if col not in existing_cols:
            conn.execute(ddl)
    conn.commit()
    return conn


def _sla_due_at(stakes: str | None, escalated: bool, started_at: datetime) -> str | None:
    if not escalated:
        return None
    hours = HIGH_STAKES_SLA_HOURS if stakes == "high" else MEDIUM_STAKES_SLA_HOURS
    return (started_at + timedelta(hours=hours)).isoformat()


def log_query(record: dict) -> str:
    """Persist one query's full trace. Returns the record id."""
    record_id = record.get("id") or str(uuid.uuid4())
    ts = record.get("timestamp") or datetime.now(timezone.utc).isoformat()
    escalated = bool(record.get("escalated"))
    conn = _connect()
    with conn:
        conn.execute(
            """
            INSERT INTO audit_log (
                id, timestamp, user, question_text, retrieved_clauses,
                topic, owner, stakes, confidence, answer_text, citations,
                in_corpus, escalated, escalation_reason, escalated_to,
                human_review_status, reviewer, review_timestamp,
                injection_flagged, agent_turns, tool_calls,
                assigned_to, sla_due_at, decision_note
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                record_id,
                ts,
                record.get("user", "anonymous"),
                record["question_text"],
                json.dumps(record.get("retrieved_clauses", [])),
                record.get("topic"),
                record.get("owner"),
                record.get("stakes"),
                record.get("confidence"),
                record.get("answer_text"),
                json.dumps(record.get("citations", [])),
                int(bool(record.get("in_corpus"))),
                int(escalated),
                record.get("escalation_reason"),
                record.get("escalated_to"),
                record.get("human_review_status", "n/a"),
                record.get("reviewer"),
                record.get("review_timestamp"),
                int(bool(record.get("injection_flagged"))),
                record.get("agent_turns", 0),
                json.dumps(record.get("tool_calls", [])),
                None,
                _sla_due_at(record.get("stakes"), escalated, datetime.fromisoformat(ts)),
                None,
            ),
        )
    conn.close()
    return record_id


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    out = []
    for r in rows:
        d = dict(r)
        d["retrieved_clauses"] = json.loads(d["retrieved_clauses"] or "[]")
        d["citations"] = json.loads(d["citations"] or "[]")
        d["tool_calls"] = json.loads(d["tool_calls"] or "[]")
        out.append(d)
    return out


def list_records(limit: int = 50) -> list[dict]:
    conn = _connect()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def list_all_records() -> list[dict]:
    """Unbounded read for dashboard aggregation / audit trail filtering."""
    conn = _connect()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM audit_log ORDER BY timestamp DESC").fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def get_record(record_id: str) -> dict | None:
    conn = _connect()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM audit_log WHERE id = ?", (record_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return _rows_to_dicts([row])[0]


def list_escalations() -> list[dict]:
    """All escalated records, for the Escalations ticket board."""
    conn = _connect()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM audit_log WHERE escalated = 1 ORDER BY timestamp DESC"
    ).fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def assign_escalation(record_id: str, assignee: str) -> None:
    conn = _connect()
    with conn:
        conn.execute(
            """UPDATE audit_log SET human_review_status = 'assigned', assigned_to = ?
               WHERE id = ?""",
            (assignee, record_id),
        )
    conn.close()


def mark_reviewed(record_id: str, reviewer: str, decision_note: str = "") -> None:
    conn = _connect()
    with conn:
        conn.execute(
            """UPDATE audit_log SET human_review_status = 'reviewed',
               reviewer = ?, review_timestamp = ?, decision_note = ? WHERE id = ?""",
            (reviewer, datetime.now(timezone.utc).isoformat(), decision_note or None, record_id),
        )
    conn.close()
