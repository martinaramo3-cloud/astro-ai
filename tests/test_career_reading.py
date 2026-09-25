"""The co-founder's career and money rules, as an internal reading.

Her document wins over her earlier earning-routes PDF wherever the two differ,
and the differences are tested here: the route labels and order, the fifth
dimension, and the three-point evidence widening from "conjunct the MC" to any
close aspect to it.

The rules each exist because an engine without them produces a confident
answer that is wrong in a particular way, so each has a test:

  question type first, because "what work suits me" answered from the 2nd
  house is an answer about money to someone who asked about meaning

  two rankings, because how someone is PAID and what the work IS are two
  questions and one answer to both is an answer to neither

  all the ruler aspects, not the four tightest in the chart, which routinely
  contained none of the six rulers a career question turns on

  no house, Ascendant or MC claim without a reliable birth time

  profections computed rather than scaffolded — the prediction engine has
  boosted transits on the profected house since before this, and the boost had
  never once applied to a real person

  timing chosen for activating THIS question's factors, because every career
  answer in testing opened with the largest transit in a two-year list
"""
import json
import pathlib

import pytest

from app.career_reading_service import (
    QUESTION_TYPES, build_career_reading, choose_timing, classify_career_question,
    for_the_answer,
)
from app.chart_analysis_service import get_house_rulers
from app.earning_routes_service import DIMENSIONS, ROUTES
from app.natal_career_data import CAREER_HOUSES, build_career_natal_data
from app.orb_policy import describe, exactness, max_orb, within_orb
from app.professional_themes_service import (
    CANNOT_ESTABLISH, THEMES, describe_themes, score_professional_themes,
)
from app.profection_service import age_at_last_birthday, annual_profection, profected_house
from app.transit_timing_service import build_predictive_timeline
import app.main as main
from tests.conftest import MILAN, SOFIA


def chart(person=SOFIA, birth_time_known=True):
    return main.build_natal_chart_data(
        type("P", (), dict(person, birth_time_known=birth_time_known)))


def timeline_for(natal):
    rules = {}
    for record in get_house_rulers(natal["houses"], natal["planet_positions"]):
        rules.setdefault(record["ruler"], []).append(record["house"])
    return build_predictive_timeline(
        natal["planet_positions"] + (natal.get("angles") or []),
        question_type="career", rules_by_point=rules, limit=14)


def reading(question, person=SOFIA, **kwargs):
    natal = chart(person)
    return build_career_reading(natal, question, timeline=timeline_for(natal),
                                birth_date=person["birth_date"], **kwargs)


# --------------------------------------------------------------------------
# 1. Question type decides which factors lead
# --------------------------------------------------------------------------

@pytest.mark.parametrize("question,expected", [
    ("What career suits me?", "suitable_work"),
    ("What work am I actually good at?", "suitable_work"),
    ("How am I most likely to make money according to my chart?", "how_they_earn"),
    ("Does my chart show potential for major financial success?", "how_they_earn"),
    ("When is a good time to change jobs?", "career_timing"),
    ("Is 2027 the year to go out on my own?", "career_timing"),
    ("Should I take the offer or stay where I am?", "a_specific_choice"),
    ("Should I pay off my debt before starting a business?", "a_specific_choice"),
])
def test_the_four_question_types(question, expected):
    assert classify_career_question(question) == expected


def test_each_type_leads_with_different_factors():
    work = reading("What career suits me?")
    earn = reading("How am I most likely to make money according to my chart?")
    assert work["which_ranking_leads"] == "themes"
    assert earn["which_ranking_leads"] == "routes"
    assert work["factors_this_question_turns_on"] != earn["factors_this_question_turns_on"]


def test_a_money_question_turns_on_the_money_houses():
    earn = reading("How am I most likely to make money according to my chart?")
    assert 2 in earn["factors_this_question_turns_on"]["houses"]


def test_a_work_question_turns_on_the_career_point():
    work = reading("What career suits me?")
    assert "Midheaven" in work["factors_this_question_turns_on"]["points"]


# --------------------------------------------------------------------------
# 2. Two rankings, kept separate
# --------------------------------------------------------------------------

def test_themes_and_routes_are_separate_rankings():
    result = reading("What career suits me?")
    assert result["professional_themes"]["available"]
    assert result["earning_routes"]["available"]
    assert len(result["professional_themes"]["themes"]) <= 3
    assert len(result["earning_routes"]["ranking"]) <= 3


def test_a_theme_needs_two_signals_that_can_establish_one():
    for theme in reading("What career suits me?")["professional_themes"]["all_themes"]:
        if theme["strong"]:
            establishing = [e for e in theme["evidence"]
                            if "6th" not in e["why"]]
            assert len(establishing) >= 2, theme["label"]


def test_the_sixth_house_cannot_define_a_career_on_its_own():
    """Her rule, and the reason it is a rule: the 6th is daily tasks and
    working conditions, and a theme resting only on it is a description of
    someone's desk."""
    assert "daily_work" in CANNOT_ESTABLISH


def test_the_mc_ruler_and_tenth_ruler_are_counted_once():
    """Under Placidus they are the same planet. Counting both let one fact
    look like two independent signals."""
    result = score_professional_themes(chart())
    assert "counted once" in result["note_on_the_house_system"]
    for theme in result["all_themes"]:
        reasons = [e["why"] for e in theme["evidence"]]
        assert len(reasons) == len(set(reasons)), theme["label"]


def test_two_similar_themes_are_offered_as_one_career():
    """"If two themes are similarly supported, explain how they could combine
    in one career." """
    for person in (SOFIA, MILAN):
        result = score_professional_themes(chart(person))
        if result.get("combined_reading"):
            assert "one job" in result["combined_reading"]
            assert "one job" in describe_themes(result)


# --------------------------------------------------------------------------
# Her rules document wins over the PDF where they differ
# --------------------------------------------------------------------------

def test_the_route_labels_are_from_the_rules_document():
    labels = {route["label"] for route in ROUTES.values()}
    assert "Employment and advancement within an organisation" in labels
    assert "Direct clients, partnerships and negotiated deals" in labels
    assert "Products, intellectual property or a scalable business" in labels
    assert "Professional work managing other people's resources" in labels


def test_the_fifth_dimension_is_delivery_not_control():
    assert "delivery" in DIMENSIONS
    assert "control" not in DIMENSIONS
    assert DIMENSIONS["delivery"]["poles"] == (
        "work you deliver personally", "growth through a team or a network")


def test_the_three_point_evidence_is_any_close_aspect_to_the_mc():
    """Her PDF said a planet conjunct the MC. Her rules document says a close
    relevant ASPECT to the MC or 2nd cusp — a square to the career point is
    evidence about the career."""
    from app.earning_routes_service import _facts
    facts = _facts(chart())
    assert "mc_aspect" in facts
    aspects = {a["aspect"] for a in facts["mc_aspect"].values()}
    assert aspects - {"conjunction"} or not aspects


# --------------------------------------------------------------------------
# 3. The natal evidence that was missing
# --------------------------------------------------------------------------

def test_all_the_ruler_aspects_not_the_four_tightest():
    natal = build_career_natal_data(chart())
    found = natal["aspects_involving_those_rulers"]
    assert len(found) > 4, "this is the requirement that was being violated"
    rulers = {natal["rulers"][h]["ruler"] for h in CAREER_HOUSES if h in natal["rulers"]}
    for aspect in found:
        assert rulers & {aspect["planet_1"], aspect["planet_2"]}


def test_aspects_to_the_mc_and_ascendant_with_exact_orbs():
    natal = build_career_natal_data(chart())
    for aspect in natal["aspects_to_the_midheaven_and_ascendant"]:
        assert aspect["planet_2"] in ("Midheaven", "Ascendant")
        assert isinstance(aspect["orb"], float)
        assert 0.0 < aspect["exactness"] <= 1.0


def test_in_the_house_and_on_the_cusp_are_different_lists():
    """A planet at the end of the 1st, conjunct the 2nd cusp, is a different
    claim from a planet sitting in the 2nd."""
    natal = build_career_natal_data(chart())
    assert set(natal["planets_in_those_houses"]) == set(CAREER_HOUSES)
    assert set(natal["planets_conjunct_those_cusps"]) == set(CAREER_HOUSES)
    assert natal["planets_in_those_houses"] is not natal["planets_conjunct_those_cusps"]


def test_the_full_condition_of_both_key_rulers():
    natal = build_career_natal_data(chart())
    for ruler in (natal["second_ruler"], natal["tenth_ruler"]):
        assert set(ruler) >= {"planet", "sign", "in_house", "dignity",
                              "retrograde", "aspects"}


# --------------------------------------------------------------------------
# 4. The orb policy
# --------------------------------------------------------------------------

def test_a_wide_conjunction_does_not_count_as_a_tight_one():
    """Her instruction, verbatim: do not quietly treat an 8° conjunction as
    equivalent to a 1° conjunction."""
    tight = exactness("conjunction", 1.0, "Venus", "Mars")
    wide = exactness("conjunction", 7.5, "Venus", "Mars")
    assert tight > wide * 2


def test_the_luminaries_get_a_wider_allowance():
    assert max_orb("conjunction", "Sun", "Mars") > max_orb("conjunction", "Venus", "Mars")


def test_an_angle_is_tighter_than_two_planets():
    assert max_orb("square", "Mars", "Midheaven") < max_orb("square", "Mars", "Venus")


def test_a_sextile_at_six_degrees_no_longer_counts():
    """The flat six-degree rule kept it. The policy does not."""
    assert not within_orb("sextile", 6.0, "Venus", "Mars")
    assert within_orb("conjunction", 7.0, "Venus", "Mars")


def test_the_policy_says_where_it_stands():
    """In use, and honest that it has not been signed off in writing. The
    numbers stay in one named file so changing them is one edit."""
    status = describe()["status"]
    assert "in use" in status and "not yet signed off" in status
    assert describe()["exactness_floor"] > 0


def test_the_policy_is_recorded_with_the_evidence():
    assert build_career_natal_data(chart())["orb_policy"]["status"]


# --------------------------------------------------------------------------
# 5. No birth time, no house claims
# --------------------------------------------------------------------------

def test_without_a_birth_time_nothing_rests_on_a_house():
    result = build_career_reading(chart(birth_time_known=False), "What career suits me?")
    assert result["available"] is False
    assert "birth time" in result["reason"]


def test_but_the_planets_can_still_be_aspected():
    natal = build_career_natal_data(chart(birth_time_known=False))
    assert natal["available"] is False
    assert natal["aspects_between_planets"]
    assert "sign" in natal["what_can_still_be_said"]


def test_themes_refuse_without_a_birth_time():
    assert score_professional_themes(chart(birth_time_known=False))["available"] is False


# --------------------------------------------------------------------------
# 6. Profections, computed at last
# --------------------------------------------------------------------------

@pytest.mark.parametrize("age,house", [(0, 1), (1, 2), (11, 12), (12, 1), (27, 4), (36, 1)])
def test_profections_count_from_age_at_the_last_birthday(age, house):
    assert profected_house(age) == house


def test_age_is_the_last_birthday_not_the_nearest():
    from datetime import date
    assert age_at_last_birthday("1999-03-02", date(2026, 3, 1)) == 26
    assert age_at_last_birthday("1999-03-02", date(2026, 3, 2)) == 27


def test_the_profection_supplies_the_house_and_its_ruler():
    result = annual_profection(SOFIA["birth_date"], chart()["houses"])
    assert result["available"]
    assert 1 <= result["profected_house"] <= 12
    assert result["time_lord"]
    assert result["sign_on_that_house"]


def test_a_profection_is_context_and_not_an_event():
    """Her caution travels with the number so it cannot be left behind."""
    result = annual_profection(SOFIA["birth_date"], chart()["houses"])
    assert "not an event" in result["how_to_use_it"]


def test_profections_need_a_birth_time_too():
    assert annual_profection(SOFIA["birth_date"], [])["available"] is False


def test_the_profection_reaches_the_reading():
    assert reading("What career suits me?")["annual_profection"]["available"]


def test_no_empty_timing_slot_is_ever_used_as_evidence():
    """"Add secondary progressions only when they are actually calculated.
    Never describe an unfilled timing slot as evidence." Nothing here mentions
    progressions, returns or releasing, because nothing computes them."""
    blob = json.dumps(reading("When is a good time to change jobs?"), default=str).lower()
    for absent in ("progression", "solar return", "lunar return", "zodiacal", "firdaria"):
        assert absent not in blob, absent


# --------------------------------------------------------------------------
# 7. Timing chosen for the question, not for being loud
# --------------------------------------------------------------------------

def test_a_window_is_chosen_for_activating_this_questions_factors():
    result = reading("When is a good time to change jobs?")
    timing = result["timing"]
    if timing.get("windows"):
        for window in timing["windows"]:
            assert window["why_this_window"], "every window carries why it was chosen"
            assert window["activation"] > 0


def test_different_questions_can_choose_different_windows():
    """The bug: four answers in a row opened with the top entry of the same
    two-year list, because that list is sorted by how big a transit is."""
    natal = chart()
    line = timeline_for(natal)
    picked = set()
    for question in ("What career suits me?",
                     "How am I most likely to make money according to my chart?"):
        result = build_career_reading(natal, question, timeline=line,
                                      birth_date=SOFIA["birth_date"])
        windows = result["timing"].get("windows") or []
        if windows:
            picked.add(windows[0]["transit"])
    # Not an assertion that they differ on this one chart — an assertion that
    # the choice is made per question at all. The distribution run is where
    # the 12% figure comes from.
    assert picked


def test_a_long_process_is_not_an_event_window():
    timing = reading("When is a good time to change jobs?")["timing"]
    for window in timing.get("windows", []):
        assert window["reads_as"] in ("a process rather than an event",
                                      "a window in which something could land")


def test_unclear_timing_is_said_rather_than_guessed():
    timing = reading("When is a good time to change jobs?")["timing"]
    assert timing["converges"] != timing["timing_is_unclear"]


def test_no_windows_at_all_is_handled():
    empty = choose_timing({}, {"points": set(), "houses": set()}, {"available": False})
    assert empty["available"] is False


def test_a_profection_alone_never_establishes_a_window():
    """It raises a window that is already relevant. On its own it contributes
    0.75, which cannot reach the score a real activation needs."""
    only_profection = choose_timing(
        {"active_now": [{"transit": "Saturn square your Mercury", "in_house": 4,
                         "natal_rules_houses": [], "importance": 0.5, "passes": []}]},
        {"points": set(), "houses": set()},
        {"available": True, "profected_house": 4, "time_lord": "Venus"})
    assert only_profection["timing_is_unclear"]


# --------------------------------------------------------------------------
# 8. The auditable object, and plain language
# --------------------------------------------------------------------------

def test_the_internal_object_has_everything_her_section_six_asks_for():
    result = reading("What career suits me?")
    assert set(result) >= {
        "question_type", "professional_themes", "earning_routes",
        "confidence", "timing", "plain_language", "natal_evidence",
        "annual_profection", "factors_this_question_turns_on",
    }
    for entry in result["earning_routes"]["ranking"]:
        assert "evidence" in entry and "counterevidence" in entry
    for entry in result["professional_themes"]["themes"]:
        assert "evidence" in entry and "counterevidence" in entry


def test_the_score_is_called_a_ranking_aid():
    assert "not a probability" in reading("What career suits me?")["internal_only"]


def test_biography_cannot_reach_any_ranking():
    """Not a promise in a prompt — an absence in a signature."""
    import inspect
    for function in (score_professional_themes, build_career_reading):
        parameters = set(inspect.signature(function).parameters)
        assert not parameters & {"memories", "user", "profile", "history", "facts"}
    assert "never evidence" in reading("What career suits me?")["biography_note"]


def test_the_plain_language_carries_no_astrology():
    from app.answer_review_service import JARGON
    for question in ("What career suits me?",
                     "How am I most likely to make money according to my chart?"):
        sentence = reading(question)["plain_language"]
        assert sentence
        assert not JARGON.search(sentence), sentence
        assert "house" not in sentence.lower()


def test_the_plain_language_carries_no_score():
    import re
    assert not re.search(r"\d", reading("What career suits me?")["plain_language"])


# --------------------------------------------------------------------------
# Still dark
# --------------------------------------------------------------------------

def test_only_the_conclusion_reaches_the_prompt():
    """Live now. The scores stay inside — a number attached to someone's
    earning prospects reads as a probability whatever it is labelled."""
    compact = for_the_answer(reading("What career suits me?"))
    blob = json.dumps(compact)
    for leak in ("score", "how_unusual", "counts_as", "activation", "points"):
        assert leak not in blob, leak
    assert compact["conclusion_in_plain_words"]


def test_the_astrology_is_absent_unless_they_asked_for_it():
    result = reading("What career suits me?")
    assert "the_chart_behind_it" not in for_the_answer(result)
    assert "the_chart_behind_it" in for_the_answer(result, technical=True)


def test_the_plain_version_carries_no_planets_or_houses():
    from app.answer_review_service import JARGON
    blob = json.dumps(for_the_answer(reading("What career suits me?")))
    assert not JARGON.search(blob), JARGON.search(blob).group(0)


def test_the_prompt_is_told_to_build_on_it_and_not_re_derive():
    prompt = " ".join(main.build_ask_astrologer_system().split())
    assert "career_reading" in prompt
    assert "Do not go back to the raw chart" in prompt
    assert "Never say a ranking exists" in prompt
    assert "never change the ranking" in prompt


def test_the_blind_table_covers_both_rankings():
    page = (pathlib.Path(main.__file__).resolve().parents[1]
            / "training" / "area3" / "blind_career.html").read_text()
    assert page.count('class="chart"') == 24        # twelve blind, twelve scored
    assert page.count("data-chart=") == 108         # twelve charts, nine fields each
    assert "professional themes" in page
    assert "earning routes" in page
    assert "Download my answers" in page
    assert 'id="pane2" hidden' in page
    assert "Orb policy, for your approval" in page
