"""Asking someone for their birth details, by link.

Reading two people together needs the other person's birth date, time and
place — which most people don't know off the top of their head for someone
else. So instead of guessing, you send them a link and they fill it in.

That is also the only growth loop the product gets for free: the link is a
real reason to message someone, and the person who opens it meets Zodi while
doing something useful rather than being advertised at.

Tokens are random and stored only as a hash, like every other link the app
sends, so a copy of the database is not a list of working invitations.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.database import get_db_connection

TTL_DAYS = 14


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_invite(owner_user_id: int, label: str, person_name: str = "") -> str:
    """Issue a link for one person and return the raw token (shown once)."""
    token = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO invites (token_hash, owner_user_id, label, person_name, created_at, expires_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            _hash(token),
            owner_user_id,
            label.strip()[:80],
            person_name.strip()[:80],
            now.isoformat(),
            (now + timedelta(days=TTL_DAYS)).isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return token


def peek_invite(token: str | None) -> dict | None:
    """What the person opening the link should see, without spending it.

    Only ever the inviter's first name — an invitation is not a reason to hand
    a stranger someone's full name or email.
    """
    if not token:
        return None
    conn = get_db_connection()
    row = conn.execute(
        "SELECT i.id, i.label, i.person_name, i.used_at, i.expires_at, u.name AS owner_name "
        "FROM invites i JOIN users u ON u.id = i.owner_user_id WHERE i.token_hash = ?",
        (_hash(token),),
    ).fetchone()
    conn.close()

    if not row or row["used_at"]:
        return None
    try:
        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
            return None
    except ValueError:
        return None

    return {
        "from_name": (row["owner_name"] or "").split(" ")[0],
        "label": row["label"],
        "person_name": row["person_name"],
    }


def consume_invite(token: str | None) -> dict | None:
    """Spend the link and return the owner it belonged to, or None."""
    if not token:
        return None
    conn = get_db_connection()
    row = conn.execute(
        "SELECT id, owner_user_id, label, person_name, used_at, expires_at "
        "FROM invites WHERE token_hash = ?",
        (_hash(token),),
    ).fetchone()

    if not row or row["used_at"]:
        conn.close()
        return None
    try:
        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
            conn.close()
            return None
    except ValueError:
        conn.close()
        return None

    consumed = conn.execute(
        "UPDATE invites SET used_at = ? WHERE id = ? AND used_at IS NULL",
        (datetime.now(timezone.utc).isoformat(), row["id"]),
    )
    conn.commit()
    conn.close()
    if consumed.rowcount != 1:
        return None
    return {
        "owner_user_id": row["owner_user_id"],
        "label": row["label"],
        "person_name": row["person_name"],
    }


def pending_invites(owner_user_id: int) -> list[dict]:
    """Links this person has sent that nobody has filled in yet."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT label, person_name, created_at, expires_at FROM invites "
        "WHERE owner_user_id = ? AND used_at IS NULL AND expires_at > ? "
        "ORDER BY id DESC",
        (owner_user_id, datetime.now(timezone.utc).isoformat()),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def accept_invite(token: str, data: dict) -> None:
    """Reserve a slot, save the person and spend the link in one transaction."""
    from fastapi import HTTPException
    from app.subscription_service import check_people_limit
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        now = datetime.now(timezone.utc).isoformat()
        row = conn.execute("""SELECT i.*, u.subscription_tier FROM invites i
            JOIN users u ON u.id = i.owner_user_id
            WHERE i.token_hash = ? AND i.used_at IS NULL AND i.expires_at > ?""",
            (_hash(token), now)).fetchone()
        if not row:
            raise HTTPException(404, "This link has expired or has already been used.")
        count = conn.execute("SELECT COUNT(*) FROM profiles WHERE owner_user_id = ?",
                             (row["owner_user_id"],)).fetchone()[0]
        check_people_limit(row["subscription_tier"], count)
        conn.execute("""INSERT INTO profiles (owner_user_id, label, person_name,
            relationship_type, birth_date, birth_time, birth_place, birth_time_known)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (
            row["owner_user_id"], row["label"] or data["person_name"], data["person_name"],
            data.get("relationship_type"), data["birth_date"],
            data["birth_time"] if data["birth_time_known"] else "12:00",
            data["birth_place"], int(data["birth_time_known"])))
        conn.execute("UPDATE invites SET used_at = ? WHERE id = ?", (now, row["id"]))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
