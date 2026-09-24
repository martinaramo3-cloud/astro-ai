"""Summarising conversations that have gone quiet, at the moment someone starts a new one.

No background job and no scheduler: a conversation is read once, lazily, the
next time its owner asks something — and only if it has been idle long enough
to be over. Nothing is spent on a chat still being had, or on one nobody
returns to.
"""
from __future__ import annotations

from app.question_router import classify_question
from app.memory_summary_service import sessions_ready_to_summarise, summarise_session


def catch_up_on_finished_chats(owner_user_id: int, limit: int = 2) -> int:
    """Read at most a couple of finished conversations. Never raises."""
    written = 0
    try:
        for session in sessions_ready_to_summarise(owner_user_id, limit=limit):
            opening = next((m.get("content", "") for m in session["messages"]
                            if m.get("role") == "user"), "")
            written += len(summarise_session(
                owner_user_id, session["id"], session["messages"],
                topic=classify_question(opening), profile_id=session["profile_id"],
                said_on=session["said_on"]))
    except Exception as exc:  # noqa: BLE001
        # A memory that fails to save must never cost somebody their answer.
        print("Memory catch-up failed:", type(exc).__name__)
    return written
