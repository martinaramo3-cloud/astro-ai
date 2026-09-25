"""A thread that goes somewhere, and a memory that stays in its lane.

Three career questions in one thread came back with the same three points each
time: the same conclusion about the work, the same pressure window, and the
same memory — a memory about a country the person had never once mentioned in
any of the three questions.

Two separate failures, each of which had a rule that was supposed to stop it.
The repetition rule compared WORDING and only ever caught copy-paste, so a
conclusion restated in fresh words scored 0.46 against its own earlier version
and went straight through. The memory rule lived in the prompt, which asked for
one memory while the code sent three.
"""
import pytest

from app.answer_review_service import (
    ENOUGH_TO_MEASURE, REPEATED_GROUND, _ground, review_issues,
)
from app.conversation_service import conversation_state
from app.memory_service import relevant_memories, remember
import app.main as main
from tests.conftest import SOFIA

FIRST = ("You earn most when your name is visibly attached to the work rather "
         "than buried in a team's output. The pressure window runs from late "
         "October to late January. The Albania decision is doing double duty here.")
SECOND = ("There is real potential, and it concentrates where your name is on "
          "the work. Late October to late January is when the pressure lands. "
          "The Albania decision is carrying two jobs at once.")

THREAD = [
    {"role": "user", "content": "How am I most likely to make money according to my chart?"},
    {"role": "assistant", "content": FIRST},
    {"role": "user", "content": "Does my chart show potential for major financial success?"},
    {"role": "assistant", "content": SECOND},
]


def third_turn(question="What career suits me?"):
    state = conversation_state(question, THREAD)
    state["max_words"] = 620
    return state


# --------------------------------------------------------------------------
# Repetition measured as ground covered, not as words reused
# --------------------------------------------------------------------------

def test_the_third_answer_may_not_re_argue_the_first_two():
    draft = ("The career that suits you is one where your name is visibly "
             "attached to the work, not hidden inside a team. Again, late "
             "October through late January is the pressure window to plan "
             "around. And the Albania decision is still doing double duty.")
    assert any("ground already given" in i for i in review_issues(draft, third_turn()))


def test_rephrasing_a_point_is_still_repeating_it():
    """The old check compared wording. This is the hole it left: every one of
    these scores below the copy-paste threshold against its own original."""
    from difflib import SequenceMatcher
    from app.answer_review_service import _normal
    rephrased = ("The money follows when the work carries your name on it "
                 "rather than a team's. From late October through to the end "
                 "of January the pressure is on. That Albania decision is "
                 "carrying two jobs at once, which is the other half of this.")
    assert SequenceMatcher(None, _normal(rephrased), _normal(FIRST)).ratio() < 0.77
    assert any("ground already given" in i for i in review_issues(rephrased, third_turn()))


@pytest.mark.parametrize("draft", [
    # New routes, new buyer, new risk.
    "Advising beats teaching for you, for one reason: you are paid for a "
    "decision, not for hours in a room. Charge per engagement. The buyers are "
    "founders and heads of department, who pay when the cost of being wrong is "
    "high. Your risk is agreeing to build what you should have been retained "
    "to specify.",
    # A clause referring back, then somewhere new — exactly what was asked for.
    "Same window as before, so plan around it. What is new is the shape of the "
    "offer: you are paid for a decision rather than hours, which means a "
    "retainer with a named scope beats a day rate. The buyer is whoever "
    "carries the cost of getting it wrong.",
    # Going deeper on one thing already named is new ground, not repetition.
    "Retained specification work: they pay you to decide what gets built "
    "before anyone builds it. Scope it by the decision, charge per report, and "
    "price the build separately.",
])
def test_adding_new_ground_is_not_repetition(draft):
    assert not any("ground already given" in i for i in review_issues(draft, third_turn()))


def test_a_short_leaning_follow_up_is_allowed_to_reuse_the_words():
    """"Advising, not teaching" is supposed to be three words and is supposed
    to reuse them. There is nothing to measure in an answer this size."""
    for draft in ("Advising, not teaching.", "Yes — the retainer, not the rate."):
        assert len(_ground(draft)) < ENOUGH_TO_MEASURE
        assert review_issues(draft, third_turn()) == []


def test_the_threshold_sits_in_a_real_gap():
    """Measured, not picked: re-arguing recycles 70%+, referencing recycles
    under 25%, and nothing observed lands between."""
    covered = _ground(FIRST) | _ground(SECOND)
    def recycled(text):
        words = _ground(text)
        return len(words & covered) / len(words)
    re_argues = ("The career that suits you is one where your name is visibly "
                 "attached to the work, not hidden inside a team. Again, late "
                 "October through late January is the pressure window. And the "
                 "Albania decision is still doing double duty for you here.")
    references = ("Same window as before, so plan around it. What is new is "
                  "the shape of the offer: you are paid for a decision rather "
                  "than hours, which means a retainer with a named scope beats "
                  "a day rate.")
    assert recycled(re_argues) > REPEATED_GROUND
    assert recycled(references) < REPEATED_GROUND
    assert recycled(re_argues) - recycled(references) > 0.4


def test_a_first_question_has_nothing_to_repeat():
    state = conversation_state("What career suits me?", [])
    state["max_words"] = 620
    assert review_issues(FIRST, state) == []


def test_a_recap_is_allowed_to_repeat():
    state = third_turn("can you recap that?")
    assert not any("ground already given" in i for i in review_issues(SECOND, state))


def test_the_prompt_asks_for_a_clause_not_an_argument():
    prompt = main.build_ask_astrologer_system()
    assert "referenced in a CLAUSE and never argued again" in prompt
    assert "saying it in fresh words is still" in prompt


# --------------------------------------------------------------------------
# One memory, and only when they are still on it
# --------------------------------------------------------------------------

@pytest.fixture
def user_with_memories(account, client):
    user, headers = account()
    client.patch("/me/memory", json={"enabled": True}, headers=headers)
    uid = user["user"]["id"] if "user" in user else user["id"]
    remember(uid, "fact", "Moving to Albania in March", topic="general")
    remember(uid, "fact", "Studies law", topic="general")
    remember(uid, "plan", "Deciding whether to practise or go in-house", topic="general")
    return uid, headers


def test_only_one_memory_reaches_an_answer(user_with_memories):
    """Three were being sent while the prompt asked for one, and the model
    used all three."""
    uid, _ = user_with_memories
    req = main.AstrologyQuestionRequest(
        question="How am I most likely to make money according to my chart?", **SOFIA)
    prep = main._prepare_astrologer_call(
        req, dict(id=uid, memory_enabled=1, birth_time_known=1, **SOFIA))
    assert len(prep["chat_context"].get("what_they_told_you", [])) <= 1


def test_the_same_memory_does_not_come_back_the_next_answer(user_with_memories):
    """It used to, indefinitely: nothing recorded that an ordinary memory had
    surfaced, so the rule against two answers running had nothing to act on."""
    uid, _ = user_with_memories
    first = relevant_memories(uid, "career", limit=1, continued_in="how do I make money?")
    assert first
    from app.memory_service import note_mentioned
    note_mentioned(uid, first[0]["id"])
    again = relevant_memories(uid, "career", limit=3, continued_in="what career suits me?")
    assert first[0]["id"] not in [m["id"] for m in again]


def test_it_does_come_back_when_they_raise_it_themselves(user_with_memories):
    """"Unless they are still on that subject" means the person brought it up,
    not that a classifier put two questions in the same bucket."""
    uid, _ = user_with_memories
    from app.memory_service import note_mentioned
    albania = next(m for m in relevant_memories(uid, "career", limit=3)
                   if "Albania" in m["text"])
    note_mentioned(uid, albania["id"])
    back = relevant_memories(uid, "career", limit=3,
                             continued_in="does the Albania move change any of that?")
    assert albania["id"] in [m["id"] for m in back]


def test_a_career_question_does_not_drag_in_an_unrelated_memory_twice(user_with_memories):
    """The end-to-end version of the bug she reported: the same fact appearing
    in consecutive answers to questions that never mentioned it."""
    uid, _ = user_with_memories
    user = dict(id=uid, memory_enabled=1, birth_time_known=1, **SOFIA)
    surfaced = []
    for question in ("How am I most likely to make money according to my chart?",
                     "What career suits me?"):
        prep = main._prepare_astrologer_call(
            main.AstrologyQuestionRequest(question=question, **SOFIA), user)
        surfaced += [m["note"] for m in prep["chat_context"].get("what_they_told_you", [])]
    assert len(surfaced) == len(set(surfaced)), surfaced


def test_memory_appears_once_in_a_thread_not_once_per_answer(user_with_memories):
    """The fix that wasn't enough. "At most one per answer" was kept, and four
    questions in one thread still surfaced four DIFFERENT memories —
    "choosing between Albania and New York" then "graduating without a job
    lined up" is one situation told twice, whatever it is stored as. Matching
    subjects does not catch it either: those two share no words."""
    uid, _ = user_with_memories
    user = dict(id=uid, memory_enabled=1, birth_time_known=1, **SOFIA)
    history, surfaced = [], []
    for question in ("How am I most likely to make money according to my chart?",
                     "Does my chart show potential for major financial success?",
                     "What career suits me?"):
        prep = main._prepare_astrologer_call(
            main.AstrologyQuestionRequest(question=question, history=history, **SOFIA), user)
        told = prep["chat_context"].get("what_they_told_you") or []
        surfaced.append([m["note"] for m in told])
        history = history + [{"role": "user", "content": question},
                             {"role": "assistant", "content": "An answer."}]
    assert surfaced[0], "the opening question should be allowed a memory"
    assert surfaced[1] == [] and surfaced[2] == [], surfaced


def test_but_it_comes_back_when_they_raise_it_mid_thread(user_with_memories):
    uid, _ = user_with_memories
    user = dict(id=uid, memory_enabled=1, birth_time_known=1, **SOFIA)
    history = [{"role": "user", "content": "How do I make money?"},
               {"role": "assistant", "content": "An answer."}]
    prep = main._prepare_astrologer_call(
        main.AstrologyQuestionRequest(
            question="does the Albania move change any of that?",
            history=history, **SOFIA), user)
    told = prep["chat_context"].get("what_they_told_you") or []
    assert any("Albania" in m["note"] for m in told), told


def test_the_memory_is_marked_as_the_only_one(user_with_memories):
    uid, _ = user_with_memories
    prep = main._prepare_astrologer_call(
        main.AstrologyQuestionRequest(question="What career suits me?", **SOFIA),
        dict(id=uid, memory_enabled=1, birth_time_known=1, **SOFIA))
    told = prep["chat_context"].get("what_they_told_you") or []
    assert told and "only thing" in told[0]["note_to_self"]
