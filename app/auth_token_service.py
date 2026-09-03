"""Single-use, expiring tokens for the email links: password reset and email
verification.

Only the SHA-256 hash of each token is stored, so a stolen database can't be
turned into a password reset. A token is spent the moment it's used, and only
the newest one for a purpose stays valid — asking for a second reset quietly
invalidates the first.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.database import get_db_connection

PURPOSE_RESET = "password_reset"
PURPOSE_VERIFY = "email_verify"

# A reset link is a key to the account, so it expires fast. Verification is
# lower-stakes and can sit in an inbox for a day.
TTL_MINUTES = {PURPOSE_RESET: 60, PURPOSE_VERIFY: 60 * 24}


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token(user_id: int, purpose: str) -> str:
    """Create a token for one purpose and return the raw value (shown once).

    Any earlier unused token for the same purpose is dropped, so only the link
    in the most recent email works.
    """
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=TTL_MINUTES.get(purpose, 60))
    token = secrets.token_urlsafe(32)

    conn = get_db_connection()
    conn.execute(
        "DELETE FROM auth_tokens WHERE user_id = ? AND purpose = ? AND used_at IS NULL",
        (user_id, purpose),
    )
    conn.execute(
        "INSERT INTO auth_tokens (user_id, purpose, token_hash, expires_at, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, purpose, _hash(token), expires.isoformat(), now.isoformat()),
    )
    conn.commit()
    conn.close()
    return token


def consume_token(token: str | None, purpose: str) -> int | None:
    """Spend a token and return its user id, or None if it's invalid.

    Invalid means: unknown, wrong purpose, already used, or expired. Marking it
    used before returning means the same link can't be replayed.
    """
    if not token:
        return None

    conn = get_db_connection()
    row = conn.execute(
        "SELECT id, user_id, expires_at, used_at FROM auth_tokens "
        "WHERE token_hash = ? AND purpose = ?",
        (_hash(token), purpose),
    ).fetchone()

    if not row or row["used_at"] is not None:
        conn.close()
        return None

    try:
        expires = datetime.fromisoformat(row["expires_at"])
    except ValueError:
        conn.close()
        return None
    if expires < datetime.now(timezone.utc):
        conn.close()
        return None

    conn.execute(
        "UPDATE auth_tokens SET used_at = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), row["id"]),
    )
    conn.commit()
    conn.close()
    return row["user_id"]
