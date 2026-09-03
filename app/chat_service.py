from __future__ import annotations

import json

from app.database import get_db_connection


def _row_to_session(row):
    session = dict(row)
    session["messages"] = json.loads(session.pop("messages_json"))
    return session


def list_chat_sessions(owner_user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, owner_user_id, profile_id, title, messages_json, created_at, updated_at
        FROM chat_sessions
        WHERE owner_user_id = ?
        ORDER BY updated_at DESC, id DESC
        """,
        (owner_user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_session(row) for row in rows]


def get_chat_session_by_id(session_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, owner_user_id, profile_id, title, messages_json, created_at, updated_at
        FROM chat_sessions
        WHERE id = ?
        """,
        (session_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return _row_to_session(row) if row else None


def create_chat_session(owner_user_id: int, profile_id: int | None, title: str, messages: list[dict]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO chat_sessions (owner_user_id, profile_id, title, messages_json)
        VALUES (?, ?, ?, ?)
        """,
        (owner_user_id, profile_id, title, json.dumps(messages)),
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_chat_session_by_id(session_id)


def update_chat_session(session_id: int, title: str, profile_id: int | None, messages: list[dict]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE chat_sessions
        SET title = ?, profile_id = ?, messages_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (title, profile_id, json.dumps(messages), session_id),
    )
    conn.commit()
    conn.close()
    return get_chat_session_by_id(session_id)


def delete_chat_session_by_id(session_id: int) -> bool:
    """Remove one conversation. Returns False if it wasn't there."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def summarize_recent_sessions(
    owner_user_id: int,
    exclude_session_id: int | None = None,
    limit: int = 5,
    profile_id: int | None = None,
) -> list[dict]:
    """A light index of someone's other conversations.

    Titles and opening questions only — enough for the astrologer to say
    "you asked about your Saturn return last week", without shipping every
    past transcript into the prompt or letting it invent details it never saw.

    `profile_id` narrows it to conversations about one saved person. A chat
    about someone should see the earlier chats about that same someone, and
    nothing else — which is both more useful and the opposite of the bleed
    that happens when every conversation can see every other one.
    """
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT s.id, s.title, s.messages_json, s.updated_at, p.label AS person
        FROM chat_sessions s
        LEFT JOIN profiles p ON p.id = s.profile_id
        WHERE s.owner_user_id = ?
          AND (? IS NULL OR s.profile_id = ?)
        ORDER BY s.updated_at DESC
        LIMIT ?
        """,
        (owner_user_id, profile_id, profile_id, limit + 1),
    ).fetchall()
    conn.close()

    summaries = []
    for row in rows:
        if exclude_session_id is not None and row["id"] == exclude_session_id:
            continue

        opening = ""
        try:
            for message in json.loads(row["messages_json"]):
                if message.get("role") == "user":
                    opening = message.get("content", "")[:120]
                    break
        except ValueError:
            pass

        summaries.append({
            "title": row["title"],
            "opening_question": opening,
            "last_active": (row["updated_at"] or "")[:10],
            # Whose chart that conversation was about. Without this a chat
            # about a partner is indistinguishable from one about themselves,
            # and the two bleed into each other.
            "about": row["person"] or "themselves",
        })
        if len(summaries) >= limit:
            break

    return summaries
