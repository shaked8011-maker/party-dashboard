# לוח בקרה - מפלגה

אתר דשבורד לניהול ומעקב יומי אחר ביצועי כל אחראי תחום במפלגה, עם סיכום שבועי אוטומטי וצבעים לפי עמידה ביעד.

הקוד עצמו הוא Python 3 טהור (בלי npm, בלי build). הנתונים נשמרים במסד נתונים חיצוני **Turso** (תואם-SQLite, שכבה חינמית קבועה) כדי שהמידע לא יימחק בכל עדכון/דיפלוי.

**כתובת האתר החי**: https://party-dashboard-15fl.onrender.com
**מסך ניהול**: https://party-dashboard-15fl.onrender.com/admin

## הרצה מקומית

צריך משתני סביבה של Turso (`TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`) כדי להריץ מקומית. יש קובץ `run_local.sh` (לא ב-git, מכיל את הפרטים) שמריץ את השרת עם המשתנים הנכונים:

```bash
cd party-dashboard
bash run_local.sh
```

לאחר מכן פתחו בדפדפן:
- לוח הבקרה הציבורי: http://localhost:8420/
- טופס העדכון היומי (לאחראים): http://localhost:8420/update
- מסך הניהול: http://localhost:8420/admin

## מבנה הקבצים

- `server.py` - השרת (API + הגשת הדפים)
- `db.py` - לקוח מינימלי (stdlib בלבד, ללא ספריות חיצוניות) לשיחה מול Turso HTTP API
- `reminders.py` - שליחת מיילי תזכורת יומיים דרך SendGrid
- `seed.py` - נתוני דוגמה התחלתיים (רץ אוטומטית פעם ראשונה בלבד כשמסד הנתונים ריק)
- `static/index.html` + `app.js` - לוח הבקרה
- `static/update.html` + `update.js` - טופס העדכון היומי
- `static/admin.html` + `admin.js` - מסך ניהול אנשים/מדדים (מוגן בסיסמה)
- `.github/workflows/daily-reminder.yml` - מתזמן קריאה יומית לשליחת התזכורות

## איך מוסיפים/משנים אחראים ומדדים

הכי קל: דרך מסך הניהול **/admin** (סיסמה נדרשת) - אפשר להוסיף/לערוך/למחוק אנשים ומדדים ולהגדיר אימייל ויעד שבועי, בלי לגעת בקוד.

## משתני סביבה (מוגדרים ב-Render, תחת Environment)

- `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` - חיבור למסד הנתונים
- `ADMIN_PASSWORD` - סיסמת הכניסה למסך הניהול
- `SENDGRID_API_KEY`, `GMAIL_ADDRESS` - שליחת מיילי תזכורת (הכתובת חייבת להיות "Verified Single Sender" ב-SendGrid)
- `REMINDER_SECRET_KEY` - מפתח סודי שמגן על ה-endpoint שמפעיל את התזכורות (`/api/send-reminders`), חייב להיות זהה ל-secret ששמור ב-GitHub Actions

## תזכורת יומית

`.github/workflows/daily-reminder.yml` רץ אוטומטית ב-16:00 וב-17:00 UTC (מכסה גם שעון קיץ וגם חורף בישראל - 19:00 מקומי) וקורא ל-endpoint שבודק מי לא מילא דיווח היום ושולח לו מייל. יש הגנה מובנית מפני שליחה כפולה באותו יום.

הרצה ידנית לבדיקה: `curl "https://party-dashboard-15fl.onrender.com/api/send-reminders?key=REMINDER_SECRET_KEY&force=1"` (הפרמטר `force=1` מתעלם מבדיקת "כבר נשלח היום", לצורך בדיקות בלבד).

## הרשאות

כרגע כל אחד יכול לבחור את שמו בטופס העדכון ולמלא נתונים (ללא סיסמה) - נוח לשימוש יומיומי. לוח הבקרה עצמו פתוח לצפייה לכולם. מסך הניהול (/admin) מוגן בסיסמה נפרדת.
