"""What Zoli may carry between conversations, and what it must never carry."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.database import get_db_connection
from app.memory_service import (
    LIFETIME_DAYS, age_memories, apply_check_in_answer, forget, forget_all,
    list_memories, pick_check_in, relevant_memories, remember, update_text,
)
from app.memory_summary_service import summarise_session


def _age(memory_id, days):
    """Pretend a memory was made `days` ago, expiry recalculated from then —
    the way it would actually have been written at the time."""
    said = datetime.now(timezone.utc) - timedelta(days=days)
    conn = get_db_connection()
    kind = conn.execute("SELECT kind FROM memories WHERE id=?", (memory_id,)).fetchone()["kind"]
    conn.execute("UPDATE memories SET said_on=?, created_at=?, expires_at=? WHERE id=?",
                 (said.date().isoformat(), said.isoformat(),
                  (said + timedelta(days=LIFETIME_DAYS[kind])).date().isoformat(),
                  memory_id))
    conn.commit()
    conn.close()


# ── What is never kept ─────────────────────────────────────────────────────

def test_a_crisis_conversation_is_never_summarised(account):
    user, _ = account()
    messages = [{"role": "user", "content": "i keep thinking about how i want to die"},
                {"role": "assistant", "content": "Are you safe right now?"}]
    written = summarise_session(user["id"], 1, messages,
                                generate=lambda p: pytest.fail("no model call for a crisis chat"))
    assert written == []
    assert list_memories(user["id"]) == []


@pytest.mark.parametrize("sensitive", [
    "Has been in therapy for depression since March",
    "Is on medication for anxiety",
    "Earns 32000 and has debt",
    "Is waiting on a visa decision",
    "Had an abortion last year",
    "Her brother is an alcoholic",
])
def test_sensitive_notes_are_dropped_even_if_the_model_returns_them(account, sensitive):
    """The instructions ask. This guarantees — one is a request, the other is
    not, and a summariser merely discouraged from recording someone's health
    will record it eventually."""
    user, _ = account()
    written = summarise_session(
        user["id"], 2, [{"role": "user", "content": "hello"},
                        {"role": "assistant", "content": "hi"}],
        generate=lambda p: json.dumps({"facts": [sensitive], "plans": [], "conclusions": []}))
    assert written == []
    assert list_memories(user["id"]) == []


def test_what_happened_between_them_and_someone_is_kept(account):
    """Her story about him is hers. His private life is not."""
    user, _ = account()
    written = summarise_session(
        user["id"], 3, [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hi"}],
        generate=lambda p: json.dumps({
            "facts": ["N called twice after a year of silence"],
            "plans": [], "conclusions": []}))
    assert len(written) == 1
    assert "called twice" in list_memories(user["id"])[0]["text"]


# ── How long things last ───────────────────────────────────────────────────

def test_the_three_lifetimes(account):
    assert LIFETIME_DAYS == {"fact": 365, "plan": 60, "conclusion": 90}


def test_a_plan_asks_before_it_disappears(account):
    """A plan that goes quiet is asked about, not dropped — and a stale plan
    asserted as current is worse than no memory at all."""
    user, _ = account()
    plan = remember(user["id"], "plan", "Weighing New York, Miami, London and Paris")
    _age(plan, 61)
    age_memories(user["id"])
    held = list_memories(user["id"])
    assert held and held[0]["status"] == "needs_check_in"

    # Asked once; a plan somebody stepped over is not asked about twice.
    first = pick_check_in(relevant_memories(user["id"], "general"), topic="general", allowed=True)
    assert first and first["id"] == plan

    _age(plan, 61 + 31)
    age_memories(user["id"])
    assert list_memories(user["id"]) == [], "it should lapse quietly after the grace period"


def test_a_fact_outlives_a_plan(account):
    user, _ = account()
    fact = remember(user["id"], "fact", "Lives in Madrid, nine years")
    _age(fact, 120)
    age_memories(user["id"])
    assert list_memories(user["id"]), "a hometown does not go stale in four months"


# ── Obeying the answer ─────────────────────────────────────────────────────

def test_never_mind_deletes_the_plan_and_what_was_built_on_it(account):
    """Otherwise Zoli keeps acting on a reading drawn from a cancelled plan,
    which is worse than never having known."""
    user, _ = account()
    plan = remember(user["id"], "plan", "Moving to Berlin in spring")
    reading = remember(user["id"], "conclusion", "This year is about leaving", derived_from=plan)
    assert apply_check_in_answer(user["id"], plan, "cancelled") == "deleted"
    kept = {m["id"] for m in list_memories(user["id"])}
    assert plan not in kept and reading not in kept


def test_changed_replaces_it(account):
    user, _ = account()
    plan = remember(user["id"], "plan", "Moving to Berlin in spring")
    _age(plan, 61)
    assert apply_check_in_answer(user["id"], plan, "changed", "Moving to London instead") == "replaced"
    held = list_memories(user["id"])[0]
    assert "London" in held["text"] and held["status"] == "active"


def test_still_on_resets_the_clock(account):
    user, _ = account()
    plan = remember(user["id"], "plan", "Moving to Berlin in spring")
    _age(plan, 61)
    age_memories(user["id"])
    assert apply_check_in_answer(user["id"], plan, "still_on") == "refreshed"
    held = list_memories(user["id"])[0]
    assert held["status"] == "active"


# ── When a memory may be used ──────────────────────────────────────────────

def test_a_crush_question_does_not_reach_a_plan_to_move(account):
    """A memory that merely could be mentioned will be. That is not
    attentiveness, it is odd."""
    user, _ = account()
    remember(user["id"], "plan", "Weighing New York and London", topic="general")
    assert relevant_memories(user["id"], "relationship") == []


def test_a_question_about_where_to_live_does(account):
    user, _ = account()
    remember(user["id"], "plan", "Weighing New York and London", topic="general")
    assert relevant_memories(user["id"], "general", is_relocation=True)


def test_a_check_in_is_never_offered_when_there_is_no_room_for_a_question(account):
    user, _ = account()
    plan = remember(user["id"], "plan", "Weighing cities")
    _age(plan, 61)
    age_memories(user["id"])
    found = relevant_memories(user["id"], "general")
    assert pick_check_in(found, topic="general", allowed=False) is None


# ── The person's control over it ───────────────────────────────────────────

def test_memory_is_off_until_someone_says_yes(client, account):
    user, headers = account()
    body = client.get("/me/memory", headers=headers).json()
    assert body["enabled"] is False and body["asked"] is False


def test_turning_it_off_forgets_everything(client, account):
    """Off means forgotten, not kept quietly in case they change their mind."""
    user, headers = account()
    remember(user["id"], "fact", "Lives in Madrid, nine years")
    client.patch("/me/memory", headers=headers, json={"enabled": True})
    off = client.patch("/me/memory", headers=headers, json={"enabled": False}).json()
    assert off["forgotten"] == 1
    assert list_memories(user["id"]) == []


def test_they_can_edit_and_delete_one(client, account):
    user, headers = account()
    kept = remember(user["id"], "fact", "Lives in Madrit")
    assert client.patch(f"/me/memory/{kept}", headers=headers,
                        json={"text": "Lives in Madrid, nine years"}).status_code == 200
    assert "Madrid" in list_memories(user["id"])[0]["text"]
    assert client.delete(f"/me/memory/{kept}", headers=headers).status_code == 200
    assert list_memories(user["id"]) == []


def test_one_account_cannot_touch_another_persons_memories(client, account):
    mine, _ = account()
    theirs, their_headers = account(email="other@example.com")
    kept = remember(mine["id"], "fact", "Lives in Madrid")
    assert client.delete(f"/me/memory/{kept}", headers=their_headers).status_code == 404
    assert list_memories(mine["id"])


def test_deleting_the_account_takes_the_memories(client, account):
    user, headers = account()
    remember(user["id"], "fact", "Lives in Madrid, nine years")
    assert client.delete("/me", headers=headers).status_code == 200
    conn = get_db_connection()
    left = conn.execute("SELECT COUNT(*) FROM memories WHERE owner_user_id=?",
                        (user["id"],)).fetchone()[0]
    conn.close()
    assert left == 0


# ── What the prompt is told ────────────────────────────────────────────────

def test_the_prompt_explains_the_new_fields_and_the_timeline_check():
    """The bug this feature exists for: a window opening in January reported
    as a move, to someone who had said she graduates in May."""
    from app.ai_context_service import build_ask_astrologer_system
    flat = " ".join(build_ask_astrologer_system().split())
    for phrase in ("what_they_told_you", "ask_about_this_once", "Never invent a memory",
                   "graduate in May", "at most one per answer"):
        assert phrase.lower() in flat.lower(), phrase
