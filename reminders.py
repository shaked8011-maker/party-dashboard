import os
import smtplib
from datetime import date, datetime
from email.mime.text import MIMEText

from db import get_conn


def send_email(to_addr, subject, body):
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", 587))
    user = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"]

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_addr

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


def send_daily_reminders(dashboard_url):
    today = date.today().isoformat()
    conn = get_conn()

    already_sent = conn.execute(
        "SELECT 1 FROM reminders_sent WHERE entry_date=?", (today,)
    ).fetchone()
    if already_sent:
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
        "INSERT INTO reminders_sent (entry_date, sent_at) VALUES (?, ?)",
        (today, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()
    return {"skipped": False, "sent_to": sent_to, "errors": errors}
