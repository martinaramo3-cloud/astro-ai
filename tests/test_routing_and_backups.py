"""How big an answer gets, and whether the database can come back.

The tier decides how much of the chart is even sent, so a routing mistake is
not a matter of length — a real question routed small is answered from almost
no data, which is what "bland" turned out to mean.

The backup tests are the ones that matter most and look most boring: a copy
that cannot be reopened is not a backup, and nothing would ever tell you.
"""
import sqlite3

import pytest

from app.backup_service import create_backup, list_backups, backup_dir
from app.question_router import classify_tier
from tests.conftest import MILAN, SOFIA

ANSWERED = [{"role": "user", "content": "is this jacket a mistake"},
            {"role": "assistant", "content": "Buy it."}]


@pytest.mark.parametrize("question, history, expected", [
    # Certain from the words alone.
    ("hi", [], 1),
    ("hey zodi", [], 1),
    ("thanks", [], 1),
    # Mid-thread, however heavy the subject.
    ("so yes??", ANSWERED, 3),
    ("and the boots", ANSWERED, 3),
    ("wait really", ANSWERED, 3),
    # Small decisions.
    ("ok is this jacket a mistake", [], 2),
    ("should we go out tonight?", [], 2),
    # Unmistakably real.
    ("should i text my ex back?", [], 4),
    ("why do i pull away in relationships", [], 4),
    ("am i crazy for feeling like he doesn't care", [], 4),
])
def test_tiers_that_can_be_known_from_the_text(question, history, expected):
    assert classify_tier(question, history) == expected


@pytest.mark.parametrize("question", [
    "is he thinking about me",
    "what's going on with me",
    "do you think he likes me",
])
def test_the_ambiguous_ones_are_handed_upward(question):
    """These have no alarming word in them and matter enormously. Guessing from
    length is what made real questions come back as one line."""
    assert classify_tier(question, []) is None


def test_a_greeting_is_sent_far_less_of_the_chart(client, account):
    """The honest way to get a short answer is to stop sending the chart with it."""
    user, headers = account()
    body = {**SOFIA, "user_id": user["id"], "history": []}

    small = client.post("/ask-astrologer", json={**body, "question": "hi"}, headers=headers).json()
    big = client.post("/ask-astrologer", json={
        **body, "question": "why do i pull away in relationships"}, headers=headers).json()

    assert small["answer_tier"] == 1
    assert big["answer_tier"] == 4
    assert "chart_structure" not in small["context"]
    assert "chart_structure" in big["context"]


# ── Backups ────────────────────────────────────────────────────────────────

def test_a_backup_reopens_as_a_real_database(client, account):
    """The only question that matters: can it be restored from?"""
    account(email="backed-up@example.com")

    result = create_backup()
    copy = backup_dir() / result["name"]
    assert copy.exists() and result["bytes"] > 0

    restored = sqlite3.connect(copy)
    emails = [r[0] for r in restored.execute("SELECT email FROM users")]
    restored.close()
    assert "backed-up@example.com" in emails


def test_taking_a_backup_twice_in_a_day_keeps_one(client, account):
    account(email="daily@example.com")
    create_backup()
    create_backup()
    assert len([b for b in list_backups() if b["name"].startswith("zodi-")]) == 1


def test_a_backup_can_be_downloaded(client, admin, account):
    account(email="download@example.com")
    name = create_backup()["name"]

    response = client.get(f"/admin/backups/{name}", headers=admin)
    assert response.status_code == 200
    assert response.content[:15] == b"SQLite format 3", "the download is not a database"


# ── "US" is a country, not "us" ────────────────────────────────────────────

@pytest.mark.parametrize("question", [
    "i have always felt this pull to the US ever since I was younger",
    "moving to the US",
    "should i get a US visa",
    "the US and New York",
])
def test_the_united_states_is_not_a_relationship(question):
    """"us" used to be a compatibility keyword, so one mention of the US made a
    whole thread a two-person reading — and "I live in New York, but idk if
    it's the right choice" was answered with "what have they actually said or
    done?"."""
    from app.question_router import classify_question
    assert classify_question(question) != "compatibility"


@pytest.mark.parametrize("question", [
    "tell me about us", "the two of us", "what's the chemistry between us",
    "me and him", "are we long term",
])
def test_actual_two_person_questions_still_read_that_way(question):
    from app.question_router import classify_question
    assert classify_question(question) == "compatibility"


@pytest.mark.parametrize("question, topic", [
    ("why do i pull away in relationships", "relationship"),
    ("my exes all do the same thing", "relationship"),
    ("my feelings are all over the place", "emotional"),
])
def test_plurals_are_matched(question, topic):
    """The match is whole-word, so "relationships" was not a relationship
    question — which is most of how anyone phrases one."""
    from app.question_router import classify_question
    assert classify_question(question) == topic


def test_a_place_question_never_gets_the_two_person_fallback():
    from app.conversation_service import conversation_state
    from app.answer_review_service import safe_reply
    history = [
        {"role": "user", "content": "i have always felt this pull to the US ever since I was younger"},
        {"role": "assistant", "content": "That pull is real, not nostalgia dressed up as destiny."},
    ]
    state = conversation_state("remember I told you i live in new york, but idk if its the right choice", history)
    assert "what they intend" not in safe_reply(state)
