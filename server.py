import json
import mimetypes
import os
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from db import get_conn, init_db, week_start, week_days

ROOT = Path(__file__).parent
STATIC = ROOT / "static"

WEEKS_OF_HISTORY_FOR_TREND = 4


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def check_admin(password):
    expected = os.environ.get("ADMIN_PASSWORD", "admin123")
    return password == expected


def compute_dashboard(ref_date: date):
    conn = get_conn()
    ws = week_start(ref_date)
    days = week_days(ws)
    day_strs = [d.isoformat() for d in days]

    people_rows = conn.execute(
        "SELECT * FROM people ORDER BY sort_order, id"
    ).fetchall()
    metrics_rows = conn.execute(
        "SELECT * FROM metrics ORDER BY person_id, sort_order, id"
    ).fetchall()
    entries_rows = conn.execute(
        "SELECT metric_id, entry_date, value FROM entries"
    ).fetchall()
    conn.close()

    metrics_by_person = {}
    for m in metrics_rows:
        metrics_by_person.setdefault(m["person_id"], []).append(m)

    entries_by_metric = {}
    for e in entries_rows:
        entries_by_metric.setdefault(e["metric_id"], {})[e["entry_date"]] = e["value"]

    result_people = []
    for prow in people_rows:
        metrics_out = []
        for mrow in metrics_by_person.get(prow["id"], []):
            entry_map = entries_by_metric.get(mrow["id"], {})

            daily = {d: entry_map.get(d) for d in day_strs}
            week_sum = sum(v for d, v in daily.items() if v is not None)
            all_time_sum = sum(entry_map.values())
            total = mrow["baseline"] + all_time_sum
            has_any_data = len(entry_map) > 0 or mrow["baseline"] > 0

            # trend: sum per week for last N weeks (including current), oldest -> newest
            history = []
            for i in range(WEEKS_OF_HISTORY_FOR_TREND - 1, -1, -1):
                w_start = ws - timedelta(days=7 * i)
                w_end = w_start + timedelta(days=6)
                s = sum(
                    v
                    for d, v in entry_map.items()
                    if w_start.isoformat() <= d <= w_end.isoformat()
                )
                history.append(s)

            status = "no-data"
            pct = None
            if mrow["weekly_target"]:
                pct = round((week_sum / mrow["weekly_target"]) * 100)
                if pct >= 100:
                    status = "green"
                elif pct >= 60:
                    status = "yellow"
                else:
                    status = "red"
            elif has_any_data:
                status = "neutral"

            metrics_out.append(
                {
                    "id": mrow["id"],
                    "name": mrow["name"],
                    "weekly_target": mrow["weekly_target"],
                    "daily": daily,
                    "week_sum": week_sum,
                    "total": total,
                    "status": status,
                    "pct": pct,
                    "history": history,
                }
            )

        result_people.append(
            {"id": prow["id"], "name": prow["name"], "metrics": metrics_out}
        )

    return {
        "week_start": ws.isoformat(),
        "week_end": days[-1].isoformat(),
        "days": day_strs,
        "people": result_people,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path):
        if not path.exists() or not path.is_file():
            self.send_error(404, "Not found")
            return
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text") or "javascript" in ctype else ""))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass  # keep console quiet

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self._send_file(STATIC / "index.html")
        elif path == "/update" or path == "/update.html":
            self._send_file(STATIC / "update.html")
        elif path == "/admin" or path == "/admin.html":
            self._send_file(STATIC / "admin.html")
        elif path == "/api/admin/data":
            password = qs.get("password", [""])[0]
            if not check_admin(password):
                self._send_json({"error": "unauthorized"}, status=401)
                return
            conn = get_conn()
            people = conn.execute(
                "SELECT * FROM people ORDER BY sort_order, id"
            ).fetchall()
            all_metrics = conn.execute(
                "SELECT * FROM metrics ORDER BY person_id, sort_order, id"
            ).fetchall()
            conn.close()

            metrics_by_person = {}
            for m in all_metrics:
                metrics_by_person.setdefault(m["person_id"], []).append(dict(m))

            out = []
            for p in people:
                out.append(
                    {
                        "id": p["id"],
                        "name": p["name"],
                        "email": p["email"],
                        "sort_order": p["sort_order"],
                        "metrics": metrics_by_person.get(p["id"], []),
                    }
                )
            self._send_json(out)
        elif path == "/api/send-reminders":
            key = qs.get("key", [""])[0]
            expected = os.environ.get("REMINDER_SECRET_KEY")
            if not expected or key != expected:
                self._send_json({"error": "unauthorized"}, status=401)
                return
            import reminders

            force = qs.get("force", ["0"])[0] == "1"
            base_url = f"https://{self.headers.get('Host', '')}"
            result = reminders.send_daily_reminders(base_url, force=force)
            self._send_json(result)
        elif path == "/api/dashboard":
            ref = qs.get("date", [date.today().isoformat()])[0]
            try:
                ref_date = parse_date(ref)
            except ValueError:
                ref_date = date.today()
            self._send_json(compute_dashboard(ref_date))
        elif path == "/api/people":
            conn = get_conn()
            people = conn.execute(
                "SELECT id, name FROM people ORDER BY sort_order, id"
            ).fetchall()
            out = []
            for p in people:
                metrics = conn.execute(
                    "SELECT id, name FROM metrics WHERE person_id=? ORDER BY sort_order, id",
                    (p["id"],),
                ).fetchall()
                out.append(
                    {
                        "id": p["id"],
                        "name": p["name"],
                        "metrics": [{"id": m["id"], "name": m["name"]} for m in metrics],
                    }
                )
            conn.close()
            self._send_json(out)
        elif path == "/api/values":
            metric_ids = qs.get("metric_ids", [""])[0]
            entry_date = qs.get("date", [date.today().isoformat()])[0]
            ids = [int(x) for x in metric_ids.split(",") if x.strip().isdigit()]
            conn = get_conn()
            values = {}
            if ids:
                placeholders = ",".join("?" * len(ids))
                rows = conn.execute(
                    f"SELECT metric_id, value FROM entries WHERE entry_date=? AND metric_id IN ({placeholders})",
                    [entry_date, *ids],
                ).fetchall()
                values = {r["metric_id"]: r["value"] for r in rows}
            conn.close()
            self._send_json(values)
        elif path.startswith("/static/"):
            rel = path[len("/static/"):]
            self._send_file(STATIC / rel)
        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length else b"{}"

        if parsed.path == "/api/entry":
            try:
                data = json.loads(raw_body)
                metric_id = int(data["metric_id"])
                entry_date = data["date"]
                value = float(data["value"])
                parse_date(entry_date)
            except (KeyError, ValueError, TypeError, json.JSONDecodeError):
                self._send_json({"error": "invalid payload"}, status=400)
                return

            conn = get_conn()
            conn.execute(
                "INSERT INTO entries (metric_id, entry_date, value) VALUES (?, ?, ?) "
                "ON CONFLICT(metric_id, entry_date) DO UPDATE SET value=excluded.value",
                (metric_id, entry_date, value),
            )
            conn.commit()
            conn.close()
            self._send_json({"ok": True})

        elif parsed.path == "/api/admin/person":
            try:
                data = json.loads(raw_body)
            except json.JSONDecodeError:
                self._send_json({"error": "invalid payload"}, status=400)
                return
            if not check_admin(data.get("password", "")):
                self._send_json({"error": "unauthorized"}, status=401)
                return

            conn = get_conn()
            if data.get("delete") and data.get("id"):
                conn.execute(
                    "DELETE FROM entries WHERE metric_id IN (SELECT id FROM metrics WHERE person_id=?)",
                    (data["id"],),
                )
                conn.execute("DELETE FROM metrics WHERE person_id=?", (data["id"],))
                conn.execute("DELETE FROM people WHERE id=?", (data["id"],))
            elif data.get("id"):
                conn.execute(
                    "UPDATE people SET name=?, email=?, sort_order=? WHERE id=?",
                    (data.get("name", ""), data.get("email") or None, data.get("sort_order", 0), data["id"]),
                )
            else:
                conn.execute(
                    "INSERT INTO people (name, email, sort_order) VALUES (?, ?, ?)",
                    (data.get("name", ""), data.get("email") or None, data.get("sort_order", 0)),
                )
            conn.commit()
            conn.close()
            self._send_json({"ok": True})

        elif parsed.path == "/api/admin/metric":
            try:
                data = json.loads(raw_body)
            except json.JSONDecodeError:
                self._send_json({"error": "invalid payload"}, status=400)
                return
            if not check_admin(data.get("password", "")):
                self._send_json({"error": "unauthorized"}, status=401)
                return

            conn = get_conn()
            if data.get("delete") and data.get("id"):
                conn.execute("DELETE FROM entries WHERE metric_id=?", (data["id"],))
                conn.execute("DELETE FROM metrics WHERE id=?", (data["id"],))
            elif data.get("id"):
                conn.execute(
                    "UPDATE metrics SET name=?, weekly_target=?, baseline=?, sort_order=? WHERE id=?",
                    (
                        data.get("name", ""),
                        data.get("weekly_target") or None,
                        data.get("baseline", 0),
                        data.get("sort_order", 0),
                        data["id"],
                    ),
                )
            else:
                conn.execute(
                    "INSERT INTO metrics (person_id, name, weekly_target, baseline, sort_order) VALUES (?, ?, ?, ?, ?)",
                    (
                        data["person_id"],
                        data.get("name", ""),
                        data.get("weekly_target") or None,
                        data.get("baseline", 0),
                        data.get("sort_order", 0),
                    ),
                )
            conn.commit()
            conn.close()
            self._send_json({"ok": True})

        else:
            self.send_error(404, "Not found")


def main():
    init_db()

    # First-time boot on a fresh deployment: seed demo data so the site isn't empty.
    conn = get_conn()
    has_people = conn.execute("SELECT 1 FROM people LIMIT 1").fetchone()
    conn.close()
    if not has_people:
        import seed
        seed.run()

    port = int(os.environ.get("PORT", 8420))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Party dashboard running on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
