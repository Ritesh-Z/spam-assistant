"""SQLite store for user corrections.

Only stored when the user clicks "Not spam" or "Is spam". Nothing else about
an email is ever written to disk.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "feedback.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS feedback (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               text TEXT NOT NULL,
               label INTEGER NOT NULL,          -- 1 spam, 0 safe (the corrected label)
               created_at TEXT DEFAULT CURRENT_TIMESTAMP,
               used_in_training INTEGER DEFAULT 0
           )"""
    )
    return conn


def save_feedback(text: str, is_spam: bool) -> None:
    with _conn() as c:
        c.execute("INSERT INTO feedback (text, label) VALUES (?, ?)",
                  (text, int(is_spam)))


def all_feedback() -> list[tuple[str, int]]:
    with _conn() as c:
        return [(t, l) for t, l in c.execute("SELECT text, label FROM feedback")]


def count_feedback() -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
