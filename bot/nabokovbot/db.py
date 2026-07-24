"""SQLite storage: users, quotas, pending texts, payments, job log."""

import sqlite3
import threading
from contextlib import contextmanager

from . import config

_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    tg_id INTEGER PRIMARY KEY,
    username TEXT,
    free_used INTEGER NOT NULL DEFAULT 0,
    balance INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS pending (
    tg_id INTEGER PRIMARY KEY,
    text TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'editor',
    creative INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER NOT NULL,
    stars INTEGER NOT NULL,
    texts INTEGER NOT NULL,
    charge_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER NOT NULL,
    words INTEGER NOT NULL,
    mode TEXT NOT NULL,
    creative INTEGER NOT NULL,
    score_before INTEGER,
    score_after INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@contextmanager
def _conn():
    with _lock:
        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init() -> None:
    with _conn() as c:
        c.executescript(_SCHEMA)


def get_user(tg_id: int, username: str | None) -> sqlite3.Row:
    with _conn() as c:
        c.execute(
            "INSERT INTO users (tg_id, username) VALUES (?, ?) "
            "ON CONFLICT(tg_id) DO UPDATE SET username = excluded.username",
            (tg_id, username),
        )
        return c.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)).fetchone()


def is_admin(username: str | None) -> bool:
    return bool(username) and username.lower() in config.ADMIN_USERNAMES


def texts_left(user: sqlite3.Row, username: str | None) -> int | None:
    """None = unlimited (admin)."""
    if is_admin(username):
        return None
    free_left = max(0, config.FREE_TEXTS - user["free_used"])
    return free_left + user["balance"]


def consume_text(tg_id: int, username: str | None) -> None:
    if is_admin(username):
        return
    with _conn() as c:
        row = c.execute("SELECT free_used, balance FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        if row["free_used"] < config.FREE_TEXTS:
            c.execute("UPDATE users SET free_used = free_used + 1 WHERE tg_id = ?", (tg_id,))
        elif row["balance"] > 0:
            c.execute("UPDATE users SET balance = balance - 1 WHERE tg_id = ?", (tg_id,))


def add_pack(tg_id: int, charge_id: str | None) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE users SET balance = balance + ? WHERE tg_id = ?",
            (config.PACK_TEXTS, tg_id),
        )
        c.execute(
            "INSERT INTO payments (tg_id, stars, texts, charge_id) VALUES (?, ?, ?, ?)",
            (tg_id, config.PACK_STARS, config.PACK_TEXTS, charge_id),
        )


def set_pending(tg_id: int, text: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO pending (tg_id, text) VALUES (?, ?) "
            "ON CONFLICT(tg_id) DO UPDATE SET text = excluded.text, "
            "mode = 'editor', creative = 0",
            (tg_id, text),
        )


def get_pending(tg_id: int) -> sqlite3.Row | None:
    with _conn() as c:
        return c.execute("SELECT * FROM pending WHERE tg_id = ?", (tg_id,)).fetchone()


def update_pending(tg_id: int, mode: str | None = None, creative: int | None = None) -> None:
    with _conn() as c:
        if mode is not None:
            c.execute("UPDATE pending SET mode = ? WHERE tg_id = ?", (mode, tg_id))
        if creative is not None:
            c.execute("UPDATE pending SET creative = ? WHERE tg_id = ?", (creative, tg_id))


def clear_pending(tg_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM pending WHERE tg_id = ?", (tg_id,))


def log_job(tg_id, words, mode, creative, score_before, score_after) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO jobs (tg_id, words, mode, creative, score_before, score_after) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (tg_id, words, mode, creative, score_before, score_after),
        )
