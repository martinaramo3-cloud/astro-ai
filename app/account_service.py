"""Data-rights operations: take everything with you, or erase it.

The privacy policy promises both of these, so they need a real route rather
than an email address someone has to trust.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.attachment_service import _remove_file
from app.database import get_db_connection

# Never leave the server, whatever else does.
_PRIVATE_USER_COLUMNS = {"hashed_password"}


def export_user_data(user_id: int) -> dict | None:
    """Everything held about one person, in a portable form."""
    conn = get_db_connection()

    user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user_row:
        conn.close()
        return None

    account = {
        key: value
        for key, value in dict(user_row).items()
        if key not in _PRIVATE_USER_COLUMNS
    }

    profiles = [
        dict(row)
        for row in conn.execute(
            "SELECT * FROM profiles WHERE owner_user_id = ? ORDER BY created_at",
            (user_id,),
        ).fetchall()
    ]

    conversations = []
    for row in conn.execute(
        "SELECT * FROM chat_sessions WHERE owner_user_id = ? ORDER BY created_at",
        (user_id,),
    ).fetchall():
        session = dict(row)
        # Stored as a JSON string; unpack it so the export is readable.
        try:
            session["messages"] = json.loads(session.pop("messages_json"))
        except (ValueError, KeyError):
            session["messages"] = []
        conversations.append(session)

    attachments = [
        dict(row)
        for row in conn.execute(
            "SELECT id, content_type, byte_size, created_at FROM attachments "
            "WHERE owner_user_id = ? ORDER BY created_at",
            (user_id,),
        ).fetchall()
    ]

    conn.close()

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "account": account,
        "saved_people": profiles,
        "conversations": conversations,
        # Listed, not embedded — the files are downloadable individually and
        # inlining them would make the export enormous.
        "uploaded_images": attachments,
    }


def delete_user_account(user_id: int) -> bool:
    """Erase the account and everything attached to it.

    Deletes children first so nothing is left orphaned if this is interrupted
    partway, and drops login tokens so any other signed-in device is cut off.
    """
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if not conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone():
            return False
        # Holding the write lock prevents a concurrent upload being orphaned.
        for row in conn.execute("SELECT stored_name FROM attachments WHERE owner_user_id=?", (user_id,)):
            _remove_file(user_id, row['stored_name'])
        for table in ("attachments", "chat_sessions", "profiles", "invites"):
            conn.execute(f"DELETE FROM {table} WHERE owner_user_id=?", (user_id,))
        conn.execute("DELETE FROM memories WHERE owner_user_id=?", (user_id,))
        conn.execute("DELETE FROM summarised_sessions WHERE owner_user_id=?", (user_id,))
        for table in ("sessions", "auth_tokens", "bug_reports", "error_events", "usage_events"):
            conn.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
