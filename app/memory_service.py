"""What Zoli is allowed to remember between conversations.

Someone told Zoli across earlier chats that she had lived in Madrid nine
years, was graduating, and was choosing between four cities. Weeks later it
said her "home and family ground" would be rearranged in early 2027 — a
correct reading of a real transit — and then, asked what that meant, invented
events to fill the space where those three facts should have been. It also
named the transit's own dates as the move, which did not fit a graduation in
May it had been told about.

The reading was right. It simply had nothing of hers to attach it to, because
a new conversation received the titles of the old ones and nothing else.

Three rules shape everything here:

  Facts and readings stay apart. "You are planning to leave Madrid" is
  something she said. "This period is about deciding it" is Zoli's
  interpretation, and it expires faster because it is worth less when stale.

  Nothing sensitive is kept, ever. Not health, not crisis, not money, not
  someone else's private life. What happened *between* her and a saved person
  is her story and may be kept; his health is not hers to store.

  A plan that goes quiet is asked about, not silently dropped, and the answer
  is obeyed immediately.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app.database import get_db_connection

# What each kind is worth once it is old.
#
# A hometown does not go stale; a plan does, and a stale plan is worse than no
# memory at all — "you're considering Berlin" six months on is wrong and reads
# as carelessness. Readings sit between: still useful, but Zoli should be
# forming new ones rather than leaning on old.
LIFETIME_DAYS = {"fact": 365, "plan": 60, "conclusion": 90}

# After a plan goes quiet, how long it waits for a natural moment to ask.
CHECK_IN_GRACE_DAYS = 30

KINDS = tuple(LIFETIME_DAYS)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def remember(owner_user_id: int, kind: str, text: str, *, topic: str = "general",
             said_on: str | None = None, session_id: int | None = None,
             profile_id: int | None = None, derived_from: int | None = None) -> int:
    """Write one memory. `said_on` is the day the user said it, not today.

    Dating them is what lets Zoli say "last time you were weighing Berlin"
    instead of asserting it as current — the difference between attentive and
    presumptuous.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown memory kind: {kind}")
    now = _now()
    said = said_on or now.date().isoformat()
    conn = get_db_connection()
    cursor = conn.execute(
        """INSERT INTO memories
           (owner_user_id, kind, text, topic, said_on, created_at, expires_at,
            status, session_id, profile_id, derived_from)
           VALUES (?,?,?,?,?,?,?, 'active', ?,?,?)""",
        (owner_user_id, kind, text.strip()[:400], topic, said,
         now.isoformat(),
         (now + timedelta(days=LIFETIME_DAYS[kind])).date().isoformat(),
         session_id, profile_id, derived_from),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def age_memories(owner_user_id: int) -> None:
    """Move things along in time. Cheap, and run before every read.

    A plan past its date does not vanish — it becomes something to ask about,
    and only lapses if no natural moment to ask ever arrives.
    """
    today = _now().date().isoformat()
    lapse = (_now() - timedelta(days=CHECK_IN_GRACE_DAYS)).date().isoformat()
    conn = get_db_connection()
    conn.execute(
        """UPDATE memories SET status='needs_check_in'
           WHERE owner_user_id=? AND kind='plan' AND status='active' AND expires_at<=?""",
        (owner_user_id, today))
    # A plan nobody found a moment to ask about goes quietly.
    conn.execute(
        """DELETE FROM memories
           WHERE owner_user_id=? AND kind='plan' AND status='needs_check_in'
             AND expires_at<=?""",
        (owner_user_id, lapse))
    conn.execute(
        """DELETE FROM memories
           WHERE owner_user_id=? AND kind IN ('fact','conclusion') AND expires_at<=?""",
        (owner_user_id, today))
    conn.commit()
    conn.close()


def forget(owner_user_id: int, memory_id: int) -> bool:
    """Delete one memory and everything Zoli built on top of it.

    "Never mind, I'm not doing that" has to take the reading with it.
    Otherwise Zoli keeps acting on a conclusion drawn from a cancelled plan,
    which is worse than having forgotten the plan in the first place.
    """
    conn = get_db_connection()
    row = conn.execute("SELECT id FROM memories WHERE id=? AND owner_user_id=?",
                       (memory_id, owner_user_id)).fetchone()
    if not row:
        conn.close()
        return False
    conn.execute("DELETE FROM memories WHERE owner_user_id=? AND derived_from=?",
                 (owner_user_id, memory_id))
    conn.execute("DELETE FROM memories WHERE id=? AND owner_user_id=?",
                 (memory_id, owner_user_id))
    conn.commit()
    conn.close()
    return True


def forget_all(owner_user_id: int) -> int:
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM memories WHERE owner_user_id=?",
                         (owner_user_id,)).fetchone()[0]
    conn.execute("DELETE FROM memories WHERE owner_user_id=?", (owner_user_id,))
    conn.commit()
    conn.close()
    return count


def list_memories(owner_user_id: int) -> list[dict]:
    """Everything held about someone, for the screen where they can delete it."""
    age_memories(owner_user_id)
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT id, kind, text, topic, said_on, expires_at, status
           FROM memories WHERE owner_user_id=?
           ORDER BY kind, said_on DESC""", (owner_user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_text(owner_user_id: int, memory_id: int, text: str) -> bool:
    """Let someone correct what was recorded rather than only delete it."""
    conn = get_db_connection()
    changed = conn.execute(
        "UPDATE memories SET text=? WHERE id=? AND owner_user_id=?",
        (text.strip()[:400], memory_id, owner_user_id)).rowcount
    conn.commit()
    conn.close()
    return bool(changed)


# ── Choosing what, if anything, belongs in this answer ─────────────────────

# Which memories a question can reach. A crush question does not bring up
# Berlin; a question about where to live does. Matched on the topic the
# memory was recorded under, plus the topics that plainly overlap.
TOPIC_REACH = {
    "relationship": {"relationship", "compatibility"},
    "compatibility": {"relationship", "compatibility"},
    "career": {"career", "general"},
    "emotional": {"emotional"},
    "general": {"general", "career"},
}


def relevant_memories(owner_user_id: int, topic: str, *, is_relocation: bool = False,
                      profile_id: int | None = None, limit: int = 3) -> list[dict]:
    """The few memories that could change what Zoli says to this question.

    Deliberately narrow. A memory that merely *could* be mentioned will be
    mentioned, and an app that works your hometown into a question about a
    crush is not attentive, it is odd.
    """
    age_memories(owner_user_id)
    reach = TOPIC_REACH.get(topic, {"general"})
    if is_relocation:
        # Where to live reaches everything about where they live and are going.
        reach = reach | {"general", "career", "relocation"}
    today = _now().date().isoformat()
    yesterday = (_now() - timedelta(days=1)).date().isoformat()

    conn = get_db_connection()
    rows = conn.execute(
        f"""SELECT id, kind, text, topic, said_on, status, check_in_asked_on,
                   last_mentioned_on, profile_id
            FROM memories
            -- A plan waiting to be asked about is past its date by
            -- definition. Filtering on the date alone hid exactly the rows
            -- the check-in exists for, so it could never be asked.
            WHERE owner_user_id=? AND (expires_at >= ? OR status='needs_check_in')
              AND (topic IN ({','.join('?' * len(reach))}) OR profile_id IS NOT NULL)
            ORDER BY CASE kind WHEN 'plan' THEN 0 WHEN 'fact' THEN 1 ELSE 2 END,
                     said_on DESC""",
        (owner_user_id, today, *reach)).fetchall()
    conn.close()

    chosen = []
    for row in rows:
        memory = dict(row)
        # A memory about a saved person belongs only in that person's chat.
        if memory["profile_id"] and memory["profile_id"] != profile_id:
            continue
        # Not two answers running, unless they are still on that subject.
        if memory["last_mentioned_on"] in (today, yesterday) and memory["topic"] != topic:
            continue
        chosen.append(memory)
        if len(chosen) >= limit:
            break
    return chosen


def pick_check_in(memories: list[dict], *, topic: str, allowed: bool) -> dict | None:
    """The one plan, if any, worth asking about in this answer.

    Asked once and only once: a plan somebody stepped over does not get asked
    about again, because them not answering is itself an answer, and asking
    twice is nagging.
    """
    if not allowed:
        return None
    for memory in memories:
        if memory["kind"] == "plan" and memory["status"] == "needs_check_in" \
                and not memory["check_in_asked_on"]:
            return memory
    return None


def note_mentioned(owner_user_id: int, memory_id: int, *, asked: bool = False) -> None:
    conn = get_db_connection()
    today = _now().date().isoformat()
    if asked:
        conn.execute("""UPDATE memories SET last_mentioned_on=?, check_in_asked_on=?
                        WHERE id=? AND owner_user_id=?""",
                     (today, today, memory_id, owner_user_id))
    else:
        conn.execute("UPDATE memories SET last_mentioned_on=? WHERE id=? AND owner_user_id=?",
                     (today, memory_id, owner_user_id))
    conn.commit()
    conn.close()


def apply_check_in_answer(owner_user_id: int, memory_id: int, verdict: str,
                          replacement: str | None = None) -> str:
    """Obey what they said about a plan, immediately.

    "Never mind" means gone, along with anything Zoli built on it, and never
    raised again — not softened, not kept quietly in case.
    """
    if verdict == "cancelled":
        forget(owner_user_id, memory_id)
        return "deleted"
    now = _now()
    conn = get_db_connection()
    if verdict == "changed" and replacement:
        conn.execute(
            """UPDATE memories SET text=?, said_on=?, expires_at=?, status='active',
                                   check_in_asked_on=NULL
               WHERE id=? AND owner_user_id=?""",
            (replacement.strip()[:400], now.date().isoformat(),
             (now + timedelta(days=LIFETIME_DAYS["plan"])).date().isoformat(),
             memory_id, owner_user_id))
        outcome = "replaced"
    else:
        conn.execute(
            """UPDATE memories SET said_on=?, expires_at=?, status='active',
                                   check_in_asked_on=NULL
               WHERE id=? AND owner_user_id=?""",
            (now.date().isoformat(),
             (now + timedelta(days=LIFETIME_DAYS["plan"])).date().isoformat(),
             memory_id, owner_user_id))
        outcome = "refreshed"
    conn.commit()
    conn.close()
    return outcome
