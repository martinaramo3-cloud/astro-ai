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
