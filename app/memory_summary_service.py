"""Reading a finished conversation and keeping the few things worth keeping.

The allowed list is short on purpose, and the forbidden list is absolute. A
summariser that is merely *discouraged* from recording someone's health will
record it eventually, so nothing here asks the model to use judgement about
what is sensitive: it is given the categories it may fill and told that
anything else is discarded, and what comes back is checked again in code.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from app.database import get_db_connection
from app.memory_service import remember

# Only these. Anything a model returns outside them is dropped.
ALLOWED = {
    "fact": "where they live, how long, studies, work, languages, who matters to them",
    "plan": "something they said they intend or are weighing — a move, a course, a trip, a conversation",
    "conclusion": "what Zoli concluded, and any dates it gave",
}

# Never, under any circumstances. Checked in the instructions and again in code,
# because one is a request and the other is a guarantee.
FORBIDDEN = re.compile(
    r"\b(?:depress\w*|anxiet\w*|anxious|therapy|therapist|diagnos\w*|medication|"
    r"meds|illness|disease|cancer|pregnan\w*|abortion|miscarr\w*|self.harm|"
    r"suicid\w*|kill (?:her|him|my)self|abuse|abusive|assault|rape|trauma|ptsd|"
    r"eating disorder|addict\w*|alcohol\w*|rehab|"
    r"salary|debt|loan|rent arrears|broke|bankrupt|inheritance|savings|"
    r"visa|deportat\w*|asylum|residency|green card|undocumented|"
    r"sex|sexual|slept with|virgin|std|sti)\b", re.I)

# The crisis gate. A conversation that touched any of this is never summarised
# at all — not summarised-then-filtered.
CRISIS = re.compile(
    r"\b(?:kill myself|suicide|end my life|self.harm|hurt myself|want to die|"
    r"abusive|abused|assaulted|raped|overdose)\b", re.I)

SUMMARISER_MODEL = "gpt-4.1-mini"

INSTRUCTIONS = """You are extracting a few durable notes from one conversation
so an astrology app can be less repetitive next time. Return JSON only.

Keep ONLY these, and only when the user actually said them:
- "facts": things true about their life — where they live and how long, what
  they study or do, languages, people who matter to them.
- "plans": something they said they intend or are weighing.
- "conclusions": what the assistant concluded, and any dates it gave.

What happened BETWEEN the user and someone they know is the user's own story
and may be kept ("N called twice after a year of silence"). That other
person's private life is not: never their health, money, family problems or
anything told in confidence about them.

NEVER record, in any category, even if discussed at length: health, mental
health, therapy, diagnoses, medication, pregnancy, self-harm, crisis, abuse,
assault, addiction, sexual history, money, debt, salary, immigration or visa
status. If a fact cannot be written without one of those, leave it out.

Each item: one short sentence, under 25 words, in the third person ("Lives in
Madrid, nine years"). No quotes from the user. No names of anyone except
people the user named as mattering to them. If there is nothing worth
keeping, return empty lists.

{"facts": [], "plans": [], "conclusions": []}"""


def _transcript(messages: list[dict], limit: int = 9000) -> str:
    lines = []
    for m in messages:
        role = "User" if m.get("role") == "user" else "Zoli"
        lines.append(f"{role}: {(m.get('content') or '')[:1200]}")
    return "\n".join(lines)[-limit:]


def summarise_session(owner_user_id: int, session_id: int, messages: list[dict],
                      *, topic: str = "general", profile_id: int | None = None,
                      said_on: str | None = None, generate=None) -> list[int]:
    """Turn one finished conversation into at most a handful of memories.

    Returns the ids written. An empty list is a perfectly good outcome — most
    conversations contain nothing worth carrying, and inventing something to
    keep is how a memory feature starts being wrong about people.
    """
    text = _transcript(messages)
    if CRISIS.search(text):
        # Not summarised, and marked done so it is never reconsidered.
        _mark_done(owner_user_id, session_id)
        return []

    generate = generate or _default_generate
    try:
        raw = generate(INSTRUCTIONS + "\n\nCONVERSATION:\n" + text)
        parsed = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
    except Exception as exc:  # noqa: BLE001
        print("Memory summary failed:", type(exc).__name__)
        return []

    written = []
    for kind, key in (("fact", "facts"), ("plan", "plans"), ("conclusion", "conclusions")):
        for item in (parsed.get(key) or [])[:3]:
            item = (item or "").strip()
            # The second gate. The instructions ask; this guarantees.
            if not item or FORBIDDEN.search(item):
                continue
            written.append(remember(owner_user_id, kind, item, topic=topic,
                                    said_on=said_on, session_id=session_id,
                                    profile_id=profile_id))
    _mark_done(owner_user_id, session_id)
    return written


def _default_generate(prompt: str) -> str:
    from app.ai_service import _openai_response
    text, _ = _openai_response(prompt, SUMMARISER_MODEL, 400, None)
    return str(text)


def _mark_done(owner_user_id: int, session_id: int) -> None:
    conn = get_db_connection()
    conn.execute(
        """INSERT OR REPLACE INTO summarised_sessions (session_id, owner_user_id, summarised_at)
           VALUES (?,?,?)""",
        (session_id, owner_user_id, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()


def sessions_ready_to_summarise(owner_user_id: int, idle_minutes: int = 30,
                                limit: int = 2) -> list[dict]:
    """Conversations that have gone quiet and were never read.

    Lazily, when a new chat opens: no background jobs, and nothing is spent on
    a conversation that is still being had or never gets revisited.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=idle_minutes)).isoformat()
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT s.id, s.messages_json, s.profile_id, s.updated_at
           FROM chat_sessions s
           LEFT JOIN summarised_sessions d ON d.session_id = s.id
           WHERE s.owner_user_id = ? AND d.session_id IS NULL AND s.updated_at <= ?
           ORDER BY s.updated_at DESC LIMIT ?""",
        (owner_user_id, cutoff, limit)).fetchall()
    conn.close()
    out = []
    for r in rows:
        try:
            messages = json.loads(r["messages_json"])
        except ValueError:
            continue
        if len(messages) >= 2:
            out.append({"id": r["id"], "messages": messages,
                        "profile_id": r["profile_id"],
                        "said_on": (r["updated_at"] or "")[:10]})
    return out
