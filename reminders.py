import json
import os
import urllib.request
from datetime import date, datetime

from db import get_conn


def send_email(to_addr, subject, body):
    api_key = os.environ["SENDGRID_API_KEY"]
    from_addr = os.environ["GMAIL_ADDRESS"]

    payload = {
        "personalizations": [{"to": [{"email": to_addr}]}],
        "from": {"email": from_addr},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}],
    }
    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()


def send_daily_reminders(dashboard_url, force=False):
    today = date.today().isoformat()
    conn = get_conn()

    already_sent = conn.execute(
        "SELECT 1 FROM reminders_sent WHERE entry_date=?", (today,)
    ).fetchone()
    if already_sent and not force:
        conn.close()
        return {"skipped": True, "reason": "already sent today"}

    people = conn.execute("SELECT * FROM people ORDER BY sort_order, id").fetchall()
    sent_to = []
    errors = []

    for p in people:
        if not p["email"]:
            continue
        metrics = conn.execute(
            "SELECT id FROM metrics WHERE person_id=?", (p["id"],)
        ).fetchall()
        if not metrics:
            continue
        metric_ids = [m["id"] for m in metrics]
        placeholders = ",".join("?" * len(metric_ids))
        filled = conn.execute(
            f"SELECT DISTINCT metric_id FROM entries WHERE entry_date=? AND metric_id IN ({placeholders})",
            [today, *metric_ids],
        ).fetchall()
        filled_ids = {r["metric_id"] for r in filled}
        missing = [m for m in metric_ids if m not in filled_ids]

        if missing:
            body = (
                f"שלום {p['name']},\n\n"
                "תזכורת ידידותית למלא את הדיווח היומי שלך בלוח הבקרה של המפלגה.\n\n"
                f"לעדכון: {dashboard_url}/update\n\n"
                "תודה!"
            )
            try:
                send_email(p["email"], "תזכורת - עדכון יומי ללוח הבקרה", body)
                sent_to.append(p["name"])
            except Exception as e:
                errors.append(f"{p['name']}: {e}")

    conn.execute(
        "INSERT INTO reminders_sent (entry_date, sent_at) VALUES (?, ?) "
        "ON CONFLICT(entry_date) DO UPDATE SET sent_at=excluded.sent_at",
        (today, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()
    return {"skipped": False, "sent_to": sent_to, "errors": errors}
