import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import settings


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                direction TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                issuer TEXT,
                jti TEXT,
                event_type TEXT,
                subject TEXT,
                raw_jwt TEXT NOT NULL,
                verified INTEGER,
                status TEXT,
                detail TEXT
            )
            """
        )


@contextmanager
def _connect():
    import os

    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def log_event(
    *,
    direction: str,
    issuer: str | None,
    jti: str | None,
    event_type: str | None,
    subject: str | None,
    raw_jwt: str,
    verified: bool | None,
    status: str,
    detail: str | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO events
                (direction, timestamp, issuer, jti, event_type, subject, raw_jwt, verified, status, detail)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                direction,
                datetime.now(timezone.utc).isoformat(),
                issuer,
                jti,
                event_type,
                subject,
                raw_jwt,
                None if verified is None else int(verified),
                status,
                detail,
            ),
        )


def list_events(limit: int = 50) -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
