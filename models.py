import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "sprint.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS study_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            subject TEXT NOT NULL,
            duration_hours REAL NOT NULL,
            content TEXT NOT NULL,
            mood TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_log(date, subject, duration_hours, content, mood):
    conn = get_db()
    conn.execute(
        "INSERT INTO study_logs (date, subject, duration_hours, content, mood, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (date, subject, duration_hours, content, mood, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_logs(limit=50):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM study_logs ORDER BY date DESC, id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_logs(days=14):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM study_logs WHERE date >= date('now', ?) ORDER BY date DESC",
        (f"-{days} days",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = get_db()
    # 最近30天的每日学习时长
    rows = conn.execute("""
        SELECT date, SUM(duration_hours) as total_hours
        FROM study_logs
        WHERE date >= date('now', '-30 days')
        GROUP BY date
        ORDER BY date
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
