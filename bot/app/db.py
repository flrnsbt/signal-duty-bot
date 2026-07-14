import sqlite3
import threading
from contextlib import contextmanager

from . import config

_lock = threading.Lock()


def init_db():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS members (
                phone_number TEXT PRIMARY KEY,
                display_name TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        # seed admins as members automatically so they can use the bot out of the box
        for number in config.ADMIN_NUMBERS:
            conn.execute(
                "INSERT OR IGNORE INTO members (phone_number, display_name) VALUES (?, ?)",
                (number, number),
            )
        conn.commit()


@contextmanager
def _connect():
    conn = sqlite3.connect(config.DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def add_member(phone_number: str, display_name: str):
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO members (phone_number, display_name) VALUES (?, ?)",
            (phone_number, display_name),
        )
        conn.commit()


def remove_member(phone_number: str):
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM members WHERE phone_number = ?", (phone_number,))
        conn.commit()


def is_member(phone_number: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM members WHERE phone_number = ?", (phone_number,)
        ).fetchone()
        return row is not None


def get_member_name(phone_number: str) -> str:
    with _connect() as conn:
        row = conn.execute(
            "SELECT display_name FROM members WHERE phone_number = ?", (phone_number,)
        ).fetchone()
        return row[0] if row else phone_number


def list_members() -> list[tuple[str, str]]:
    with _connect() as conn:
        return conn.execute(
            "SELECT phone_number, display_name FROM members ORDER BY display_name"
        ).fetchall()


def set_on_duty(phone_number: str | None):
    with _lock, _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO state (key, value) VALUES ('on_duty', ?)",
            (phone_number,),
        )
        conn.commit()


def get_on_duty() -> str | None:
    with _connect() as conn:
        row = conn.execute("SELECT value FROM state WHERE key = 'on_duty'").fetchone()
        return row[0] if row and row[0] else None
