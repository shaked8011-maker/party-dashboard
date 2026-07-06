import sqlite3
from pathlib import Path
from datetime import date, timedelta

DB_PATH = Path(__file__).parent / "data.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY,
            person_id INTEGER NOT NULL REFERENCES people(id),
            name TEXT NOT NULL,
            weekly_target REAL,
            baseline REAL NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS entries (
            metric_id INTEGER NOT NULL REFERENCES metrics(id),
            entry_date TEXT NOT NULL,
            value REAL NOT NULL,
            PRIMARY KEY (metric_id, entry_date)
        );
        """
    )
    conn.commit()
    conn.close()


def week_start(d: date) -> date:
    # Sunday-based week (Israeli convention)
    offset = (d.weekday() + 1) % 7  # Sunday -> 0, Monday -> 1, ... Saturday -> 6
    return d - timedelta(days=offset)


def week_days(ws: date):
    return [ws + timedelta(days=i) for i in range(7)]
