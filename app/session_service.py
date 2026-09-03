"""Opaque login tokens.

Only the SHA-256 hash of each token is persisted, so a leaked copy of the
database cannot be replayed to impersonate a user.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.database import get_db_connection

TOKEN_TTL_DAYS = 30


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id: int) -> str:
    """Issue a new token for a user and return the raw value (shown once)."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=TOKEN_TTL_DAYS)

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at)"
        " VALUES (?, ?, ?, ?)",
        (_hash_token(token), user_id, now.isoformat(), expires.isoformat()),
    )
    conn.commit()
    conn.close()
    return token


def get_user_id_for_token(token: str | None) -> int | None:
    """Resolve a token to a user id, or None if missing/unknown/expired."""
    if not token:
        return None

    conn = get_db_connection()
    row = conn.execute(
        "SELECT user_id, expires_at FROM sessions WHERE token_hash = ?",
        (_hash_token(token),),
    ).fetchone()
    conn.close()

    if not row:
        return None

    try:
        expires_at = datetime.fromisoformat(row["expires_at"])
    except ValueError:
        return None
    if expires_at <= datetime.now(timezone.utc):
        return None

    return row["user_id"]


def delete_session(token: str | None) -> None:
    """Log out a single session."""
    if not token:
        return
    conn = get_db_connection()
    conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))
    conn.commit()
    conn.close()


def purge_expired_sessions() -> None:
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM sessions WHERE expires_at <= ?",
        (datetime.now(timezone.utc).isoformat(),),
    )
    conn.commit()
    conn.close()


def delete_all_sessions_for_user(user_id: int) -> None:
    """Sign a user out everywhere. Used after a password reset, so a stolen
    session can't outlive the password it was created under."""
    conn = get_db_connection()
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
