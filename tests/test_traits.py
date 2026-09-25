"""Strengths and weaknesses, and the several ways that question goes wrong.

Every answer defaulting to taste, standards and judgment was the reported
problem, and it has one cause: nothing ranked traits, so the model reached for
whatever read well. Three readings of Venus in different coats is three
readings of Venus.

The harder requirement is the second one. A strength and a weakness are often
ONE trait at two settings — decisiveness and the argument started a day early
— and the engine only knows which pairs are real because the pair shares a
chart source. That is also what lets it refuse to force a link.
"""
import json
import pathlib

import pytest

from app.answer_review_service import review_issues, _serious
from app.conversation_service import TRAITS_BUDGET, budget_for, conversation_state
from app.trait_profile_service import (
    FAMILIES, PROVENANCE, SATURN_JUPITER, asks_about_traits,
    build_trait_reading, describe_traits, for_the_answer, score_traits,
)
import app.main as main
from tests.conftest import MILAN, SOFIA

QUESTION = "What are my biggest strengths and weaknesses?"


def chart(person=SOFIA, birth_time_known=True):
    return main.build_natal_chart_data(
        type("P", (), dict(person, birth_time_known=birth_time_known)))


def state_for(question=QUESTION):
    state = conversation_state(question, [])
    state["max_words"] = TRAITS_BUDGET[1]
    return state


# --------------------------------------------------------------------------
# A. the engine ranks, rather than the model picking
# --------------------------------------------------------------------------

def test_traits_are_ranked_from_the_chart():
    scored = score_traits(chart())
    assert scored["available"]
    assert scored["traits"]
    order = [t["how_unusual"] for t in scored["traits"]]
    assert order == sorted(order, reverse=True)


def test_prominence_is_not_virtue():
    """A planet in detriment is loud, not weak: the same function arrives
    under strain, so the overuse is what shows first. Without that, this
    becomes a list of compliments."""
    scored = score_traits(chart())
    strained = [t for t in scored["traits"]
                if t["placement"]["dignity"] in ("detriment", "fall")]
    for trait in strained:
        assert trait["leads_as"] == "overuse", trait["key"]
    assert "not by how good it is" in scored["note"]


def test_nothing_about_the_person_can_reach_it():
    import inspect
    assert set(inspect.signature(score_traits).parameters) == {"chart"}
    assert set(inspect.signature(build_trait_reading).parameters) == {"chart"}


# --------------------------------------------------------------------------
# B. three distinct, enforced rather than requested
# --------------------------------------------------------------------------

def test_three_strengths_and_three_weaknesses():
    reading = build_trait_reading(chart())
    assert len(reading["strengths"]) == 3
    assert len(reading["weaknesses"]) == 3


def test_no_trait_family_appears_twice_on_a_side():
    """"Taste, standards and judgment" is one trait said three times. A prompt
    asking for variety would lose to the chart data behind it, the way every
    prompt instruction in this app has, so it is enforced here."""
    for person in (SOFIA, MILAN):
        reading = build_trait_reading(chart(person))
        for side in ("strengths", "weaknesses"):
            families = [t["family"] for t in reading[side]]
            assert len(families) == len(set(families)), (person, side, families)


def test_different_charts_are_not_interchangeable():
    one = build_trait_reading(chart(SOFIA))
    two = build_trait_reading(chart(MILAN))
    assert ([t["family"] for t in one["strengths"]]
            != [t["family"] for t in two["strengths"]])


# --------------------------------------------------------------------------
# C. paired only where it is genuinely the same trait
# --------------------------------------------------------------------------

def test_a_pair_is_always_the_same_family():
    for person in (SOFIA, MILAN):
        reading = build_trait_reading(chart(person))
        strengths = {t["family"] for t in reading["strengths"]}
        weaknesses = {t["family"] for t in reading["weaknesses"]}
        for pair in reading["paired"]:
            assert pair["family"] in strengths and pair["family"] in weaknesses


def test_unpaired_weaknesses_are_reported_as_unpaired():
    reading = build_trait_reading(chart())
    strengths = {t["family"] for t in reading["strengths"]}
    for family in reading["unpaired_weaknesses"]:
        assert family not in strengths


def test_no_link_is_forced_when_there_is_none():
    compact = for_the_answer({
        "available": True, "strengths": [], "weaknesses": [], "paired": [],
        "unpaired_weaknesses": [], "provenance": ""})
    assert "Do not force a link" in compact["nothing_is_paired_here"]


# --------------------------------------------------------------------------
# D. situations, not labels; possibilities, not diagnoses
# --------------------------------------------------------------------------

def test_the_heavy_words_never_leave_the_module():
    """The underlying table says "wounded ego", "suppressed anger",
    "dependence on validation". None of it is sent."""
    compact = for_the_answer(build_trait_reading(chart()))
    blob = json.dumps(compact).lower()
    for label in ("wounded ego", "suppressed anger", "dependence on validation",
                  "repressed", "insecurity", "trauma"):
        assert label not in blob, label


def test_every_trait_arrives_with_a_situation():
    compact = for_the_answer(build_trait_reading(chart()))
    for side in ("strengths", "weaknesses"):
        for entry in compact[side]:
            assert entry["shows_up_as"]
            assert len(entry["shows_up_as"].split()) >= 6, entry


def test_the_prompt_is_told_how_to_phrase_the_weaknesses():
    compact = for_the_answer(build_trait_reading(chart()))
    how = compact["how_to_say_the_weaknesses"]
    assert "possibility" in how and "able to read it and say no" in how


@pytest.mark.parametrize("draft", [
    "What you secretly fear is being ordinary.",
    "Deep down, you are afraid of being found out.",
    "Stress shows up in your body before you notice it.",
    "You have a wounded ego about this.",
    "Your suppressed anger is the thing to watch.",
    "You were taught that love had to be earned.",
])
def test_psychology_the_chart_cannot_see_is_blocked(draft):
    issues = review_issues(draft, state_for())
    assert any("what they feel or fear" in i for i in issues), issues
    assert _serious(issues)


@pytest.mark.parametrize("draft", [
    "This can happen when the same instinct runs too hot — a correction lands "
    "harder than it was meant to.",
    "You may find the small objection goes unsaid for weeks and arrives later "
    "as a much larger one.",
    "It is worth watching whether a short reply gets read as a verdict.",
    "The thing that makes you good at this is the same thing that overshoots it.",
])
def test_a_read_offered_as_a_possibility_gets_through(draft):
    assert review_issues(draft, state_for()) == []


# --------------------------------------------------------------------------
# E. plain by default, astrology on request, tightly gated
# --------------------------------------------------------------------------

def test_the_plain_version_carries_no_astrology():
    from app.answer_review_service import JARGON
    blob = json.dumps(for_the_answer(build_trait_reading(chart())))
    assert not JARGON.search(blob), JARGON.search(blob).group(0)
    assert "the_chart_behind_it" not in blob


def test_the_astrology_comes_only_when_asked():
    reading = build_trait_reading(chart())
    assert "the_chart_behind_it" in for_the_answer(reading, technical=True)


def test_no_score_reaches_the_prompt():
    compact = for_the_answer(build_trait_reading(chart()))
    blob = json.dumps(compact)
    for leak in ('"score"', "how_unusual", "leads_as", "prominence"):
        assert leak not in blob, leak


@pytest.mark.parametrize("question,expected", [
    ("What are my biggest strengths and weaknesses?", True),
    ("what am I like", True),
    ("what are my flaws", True),
    ("what am I good at", True),
    ("what are my blind spots", True),
    ("why do I pull away in relationships", False),
    ("should I text him", False),
    ("what's the moon doing today", False),
])
def test_the_gate_is_tight(question, expected):
    """This classifies as a general question, which is most of the traffic.
    A loose gate is paid for on every chat in the product."""
    assert asks_about_traits(question) is expected


def test_it_gets_room_for_six_findings():
    assert budget_for(QUESTION, 4, conversation_state(QUESTION, [])) == TRAITS_BUDGET
    ordinary = "why do I pull away in relationships"
    assert budget_for(ordinary, 4, conversation_state(ordinary, [])) != TRAITS_BUDGET


def test_it_reaches_a_real_request():
    request = main.AstrologyQuestionRequest(question=QUESTION, **SOFIA)
    prep = main._prepare_astrologer_call(
        request, dict(id=1, memory_enabled=0, birth_time_known=1, **SOFIA))
    assert "strengths_and_weaknesses" in prep["chat_context"]


def test_an_ordinary_question_does_not_pay_for_it():
    request = main.AstrologyQuestionRequest(question="should I text him", **SOFIA)
    prep = main._prepare_astrologer_call(
        request, dict(id=1, memory_enabled=0, birth_time_known=1, **SOFIA))
    assert "strengths_and_weaknesses" not in prep["chat_context"]


# --------------------------------------------------------------------------
# Provenance: whose astrology is this
# --------------------------------------------------------------------------

def test_saturn_and_jupiter_cover_every_sign():
    for planet in ("Saturn", "Jupiter"):
        assert len(SATURN_JUPITER[planet]) == 12, planet
        for sign, entry in SATURN_JUPITER[planet].items():
            assert entry["gifts"] and entry["challenge"], (planet, sign)


def test_it_says_the_existing_table_is_not_the_astrologers():
    assert "not written by the astrologer" in PROVENANCE
    assert "mine" in PROVENANCE


def test_the_calibration_gate_is_recorded():
    report = json.loads(
        (pathlib.Path(main.__file__).resolve().parents[1] / "training" / "area5"
         / "trait_distribution.json").read_text())
    assert report["passes"] is True
    assert max(report["first_strength"].values()) <= 0.5
    assert max(report["first_weakness"].values()) <= 0.5
    assert report["identical_trios"] < 0.05


def test_the_prompt_carries_the_rules():
    prompt = " ".join(main.build_ask_astrologer_system().split())
    assert "three DIFFERENT things on each side" in prompt
    assert "ONE trait at two settings" in prompt
    assert "do not invent a link to make the answer tidy" in prompt
    assert "where stress sits in their body" in prompt
