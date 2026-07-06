import json
import os
import urllib.request
from datetime import date, timedelta

_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS people (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT,
        sort_order INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY,
        person_id INTEGER NOT NULL REFERENCES people(id),
        name TEXT NOT NULL,
        weekly_target REAL,
        baseline REAL NOT NULL DEFAULT 0,
        sort_order INTEGER NOT NULL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS entries (
        metric_id INTEGER NOT NULL REFERENCES metrics(id),
        entry_date TEXT NOT NULL,
        value REAL NOT NULL,
        PRIMARY KEY (metric_id, entry_date)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reminders_sent (
        entry_date TEXT PRIMARY KEY,
        sent_at TEXT NOT NULL
    )
    """,
]


def _encode_value(v):
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "integer", "value": str(int(v))}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    return {"type": "text", "value": str(v)}


def _decode_value(cell):
    t = cell.get("type")
    v = cell.get("value")
    if t == "null":
        return None
    if t == "integer":
        return int(v)
    if t == "float":
        return float(v)
    return v


class Row:
    def __init__(self, columns, values):
        self._map = dict(zip(columns, values))

    def __getitem__(self, key):
        return self._map[key]

    def keys(self):
        return self._map.keys()

    def __repr__(self):
        return f"Row({self._map!r})"


class _Cursor:
    def __init__(self, result):
        cols = [c["name"] for c in result.get("cols", [])]
        self._rows = [
            Row(cols, [_decode_value(cell) for cell in r])
            for r in result.get("rows", [])
        ]
        self._idx = 0
        lir = result.get("last_insert_rowid")
        self.lastrowid = int(lir) if lir is not None else None
        self.rowcount = result.get("affected_row_count", 0)

    def fetchall(self):
        return self._rows

    def fetchone(self):
        if self._idx < len(self._rows):
            row = self._rows[self._idx]
            self._idx += 1
            return row
        return None


class TursoConn:
    def __init__(self, base_url, auth_token):
        self._url = base_url.rstrip("/") + "/v2/pipeline"
        self._token = auth_token

    def _post(self, requests_list):
        body = json.dumps({"requests": requests_list}).encode("utf-8")
        req = urllib.request.Request(
            self._url,
            data=body,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())

    def execute(self, sql, params=()):
        stmt = {"sql": sql}
        if params:
            stmt["args"] = [_encode_value(p) for p in params]
        data = self._post([{"type": "execute", "stmt": stmt}, {"type": "close"}])
        result_entry = data["results"][0]
        if result_entry["type"] == "error":
            raise RuntimeError(result_entry["error"].get("message", "Turso query error"))
        return _Cursor(result_entry["response"]["result"])

    def executescript(self, script):
        for statement in script.split(";"):
            statement = statement.strip()
            if statement:
                self.execute(statement)

    def commit(self):
        pass  # each execute() commits immediately over the Turso HTTP API

    def close(self):
        pass


def get_conn():
    url = os.environ["TURSO_DATABASE_URL"]
    if url.startswith("libsql://"):
        url = "https://" + url[len("libsql://"):]
    auth_token = os.environ["TURSO_AUTH_TOKEN"]
    return TursoConn(url, auth_token)


def init_db():
    conn = get_conn()
    for statement in _SCHEMA_STATEMENTS:
        conn.execute(statement)

    # migration: add email column for databases created before this field existed
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(people)").fetchall()]
    if "email" not in cols:
        conn.execute("ALTER TABLE people ADD COLUMN email TEXT")
    conn.close()


def week_start(d: date) -> date:
    # Sunday-based week (Israeli convention)
    offset = (d.weekday() + 1) % 7  # Sunday -> 0, Monday -> 1, ... Saturday -> 6
    return d - timedelta(days=offset)


def week_days(ws: date):
    return [ws + timedelta(days=i) for i in range(7)]
