"""Seed the database with demo data based on the example the user provided.
Run once: python3 seed.py  (safe to re-run, it wipes and re-creates demo content)
"""
from db import get_conn, init_db

PEOPLE = [
    "ינאי",
    "אביה",
    "יגל",
    "אלישיב",
    "יהל",
    "אלאור",
]

# name -> list of (metric_name, weekly_target or None, baseline)
METRICS = {
    "ינאי": [
        ("חוג\"ב שבוצעו", 10, 4),
        ("משת' בחוג\"ב", 150, 350),
        ("חוג\"ב מתוכנים", 20, 3),
    ],
    "אביה": [
        ("פנו להתנדב", 20, 0),
        ("שובצו להתנדב", 10, 0),
    ],
    "יגל": [
        ("הצטרפו לקב' עדכונים", 50, 350),
        ("חש' אורג' פייסבוק", None, 0),
        ("חש' אורג' אינסטגרם", None, 0),
        ("חש' אורג' טיקטוק", None, 0),
    ],
    "אלישיב": [
        ("סה\"כ כסף שגויס", None, 0),
        ("מס' תורמים", None, 0),
    ],
    "יהל": [
        ("אייטמים בתקשורת", None, 0),
        ("פג' אסטרטגיות", None, 0),
    ],
    "אלאור": [
        ("הרצאות/כנסים שבוצעו", None, 350),
        ("משתתפים בהרצאות", None, 350),
        ("הרצאות/כנסים מתוכננים", None, 0),
        ("סיורים", None, 0),
    ],
}

# metric_name -> {date: value} for the demo weeks 05/07 - 18/07/2026
ENTRIES = {
    "חוג\"ב שבוצעו": {
        "2026-07-05": 1, "2026-07-06": 2, "2026-07-07": 2, "2026-07-08": 2,
        "2026-07-09": 4, "2026-07-10": 3, "2026-07-11": 3,
    },
    "משת' בחוג\"ב": {
        "2026-07-05": 15, "2026-07-06": 50, "2026-07-07": 50, "2026-07-08": 50,
        "2026-07-09": 34, "2026-07-10": 34, "2026-07-11": 65,
    },
    "חוג\"ב מתוכנים": {
        "2026-07-05": 2, "2026-07-06": 5, "2026-07-07": 5, "2026-07-08": 5,
        "2026-07-09": 4, "2026-07-10": 4, "2026-07-11": 3,
    },
    "פנו להתנדב": {
        "2026-07-05": 15,
    },
    "שובצו להתנדב": {
        "2026-07-05": 6,
    },
    "הצטרפו לקב' עדכונים": {
        "2026-07-05": 5, "2026-07-06": 4, "2026-07-07": 3, "2026-07-08": 25,
        "2026-07-09": 4, "2026-07-10": 10, "2026-07-11": 3,
        "2026-07-12": 5, "2026-07-13": 4, "2026-07-14": 3, "2026-07-15": 25,
        "2026-07-16": 4, "2026-07-17": 10, "2026-07-18": 3,
    },
}


def run():
    init_db()
    conn = get_conn()
    conn.execute("DELETE FROM entries")
    conn.execute("DELETE FROM metrics")
    conn.execute("DELETE FROM people")

    for p_order, person in enumerate(PEOPLE):
        cur = conn.execute(
            "INSERT INTO people (name, sort_order) VALUES (?, ?)", (person, p_order)
        )
        person_id = cur.lastrowid
        for m_order, (metric_name, target, baseline) in enumerate(METRICS[person]):
            cur2 = conn.execute(
                "INSERT INTO metrics (person_id, name, weekly_target, baseline, sort_order) "
                "VALUES (?, ?, ?, ?, ?)",
                (person_id, metric_name, target, baseline, m_order),
            )
            metric_id = cur2.lastrowid
            for d, v in ENTRIES.get(metric_name, {}).items():
                conn.execute(
                    "INSERT INTO entries (metric_id, entry_date, value) VALUES (?, ?, ?)",
                    (metric_id, d, v),
                )
    conn.commit()
    conn.close()
    print("Seed complete.")


if __name__ == "__main__":
    run()
