import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join("data", "arb.db")


def init_db() -> sqlite3.Connection:
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flags (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_title TEXT,
            flagged_at  TEXT,
            yes_source  TEXT,
            no_source   TEXT,
            yes_price   REAL,
            no_price    REAL,
            yes_cost    REAL,
            no_cost     REAL,
            arb_raw     REAL,
            edge        REAL,
            roi         REAL,
            resolved    INTEGER DEFAULT 0,
            outcome     TEXT,
            resolved_at TEXT
        )
    """)
    conn.commit()
    return conn


def log_opportunity(conn: sqlite3.Connection, opp: dict) -> int:
    cursor = conn.execute("""
        INSERT INTO flags
        (event_title, flagged_at, yes_source, no_source,
         yes_price, no_price, yes_cost, no_cost, arb_raw, edge, roi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        opp["title"],
        datetime.now(timezone.utc).isoformat(),
        opp["yes_source"],
        opp["no_source"],
        opp["yes_price"],
        opp["no_price"],
        opp["yes_cost"],
        opp["no_cost"],
        opp["arb_raw"],
        opp["edge"],
        opp["roi"],
    ))
    conn.commit()
    return cursor.lastrowid


def log_all(conn: sqlite3.Connection, opportunities: list[dict]) -> int:
    for opp in opportunities:
        log_opportunity(conn, opp)
    return len(opportunities)


def get_open_flags(conn: sqlite3.Connection) -> list[dict]:
    cursor = conn.execute("""
        SELECT id, event_title, flagged_at, yes_source, no_source,
               yes_price, no_price, edge, roi
        FROM flags
        WHERE resolved = 0
        ORDER BY edge DESC
    """)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def resolve_flag(conn: sqlite3.Connection, flag_id: int, outcome: str):
    conn.execute("""
        UPDATE flags
        SET resolved = 1, outcome = ?, resolved_at = ?
        WHERE id = ?
    """, (outcome, datetime.now(timezone.utc).isoformat(), flag_id))
    conn.commit()