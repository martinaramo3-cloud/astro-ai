"""What broke, and when.

Until now the way anyone learned the app was failing was someone saying so.
Every unhandled exception is now recorded with the request that caused it, so
"is it working" is a question with an answer.

Deliberately no third-party account required: this writes to the same database
the app already has, and /admin/errors reads it back. Sentry can be layered on
later for alerts that arrive without anyone looking — this is the part that
works today.
"""
from __future__ import annotations

import traceback
from datetime import datetime, timedelta, timezone

from app.database import get_db_connection

KEEP_DAYS = 14
# Enough of a traceback to find the line, not so much that a loop fills the disk.
MAX_TRACE_CHARS = 4000


def record_error(
    path: str,
    method: str,
    exc: BaseException,
    user_id: int | None = None,
    status_code: int | None = None,
) -> None:
    """Write one failure. Never raises — an error in the error log is not an
    error worth taking the request down for."""
    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO error_events "
            "(path, method, kind, message, traceback, user_id, status_code, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                path[:300],
                method[:10],
                type(exc).__name__[:100],
                str(exc)[:600],
                traceback.format_exc()[-MAX_TRACE_CHARS:],
                user_id,
                status_code,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as inner:  # noqa: BLE001
        print("[errors] could not record:", repr(inner))


def prune_errors() -> int:
    """Drop anything older than the window, so this never grows without bound."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).isoformat()
    try:
        conn = get_db_connection()
        cursor = conn.execute("DELETE FROM error_events WHERE created_at < ?", (cutoff,))
        removed = cursor.rowcount or 0
        conn.commit()
        conn.close()
        return removed
    except Exception:  # noqa: BLE001
        return 0


def recent_errors(limit: int = 50) -> list[dict]:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT id, path, method, kind, message, traceback, user_id, status_code, created_at "
        "FROM error_events ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def error_summary() -> dict:
    """Counts that answer "is something wrong right now" at a glance."""
    conn = get_db_connection()
    now = datetime.now(timezone.utc)
    day = (now - timedelta(days=1)).isoformat()
    hour = (now - timedelta(hours=1)).isoformat()

    total = conn.execute("SELECT COUNT(*) FROM error_events").fetchone()[0]
    last_day = conn.execute(
        "SELECT COUNT(*) FROM error_events WHERE created_at >= ?", (day,)
    ).fetchone()[0]
    last_hour = conn.execute(
        "SELECT COUNT(*) FROM error_events WHERE created_at >= ?", (hour,)
    ).fetchone()[0]
    worst = conn.execute(
        "SELECT kind, path, COUNT(*) AS hits FROM error_events WHERE created_at >= ? "
        "GROUP BY kind, path ORDER BY hits DESC LIMIT 5",
        (day,),
    ).fetchall()
    conn.close()

    return {
        "total": total,
        "last_24h": last_day,
        "last_hour": last_hour,
        "most_common_today": [dict(row) for row in worst],
    }
