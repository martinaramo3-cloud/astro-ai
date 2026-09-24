"""Predictive timing, against Martina's specification.

The rules here are astrological judgements, not implementation details — she
set them and these pin them down, so a later change to the engine cannot
quietly drift away from what an astrologer actually asked for.
"""
from datetime import datetime

import pytest
import pytz

from app.astrology_engine import get_houses_and_ascendant, get_planet_positions_from_utc
from app.transit_timing_service import (
    allowed_orb,
    find_transit_cycles,
    strength_band,
    _group_into_cycles,
)

BIRTH = datetime(1999, 3, 2, 5, 15, tzinfo=pytz.utc)


@pytest.fixture(scope="module")
def points():
    from app.astrology_engine import add_house_to_planets
    houses = get_houses_and_ascendant(BIRTH, 42.6977, 23.3219)
    # Placed in houses: without this a transit has no area of life to land in,
    # and a month reads as if only the angles existed.
    placed = add_house_to_planets(get_planet_positions_from_utc(BIRTH), houses["houses"])
    return placed + houses["angles"]


@pytest.fixture(scope="module")
def cycles(points):
    # A fixed "now", so these never change meaning as time passes.
    return find_transit_cycles(points, months_ahead=30, now=datetime(2026, 9, 14, tzinfo=pytz.utc))


# ── Orbs ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("planet, aspect, orb", [
    ("Moon", "conjunction", 1.5),
    ("Mercury", "square", 1.75),
    ("Venus", "trine", 2.25),
    ("Mars", "sextile", 2.0),
    ("Saturn", "conjunction", 3.5),
    ("Pluto", "square", 2.75),
    ("Chiron", "trine", 2.0),
])
def test_the_orb_depends_on_planet_and_aspect(planet, aspect, orb):
    """The universal 3 degrees is gone: it buried fast transits and smeared slow ones."""
    assert allowed_orb(planet, aspect, "Venus") == orb


def test_the_important_points_get_a_wider_orb():
    """Saturn conjunct the Sun is 3.5 plus a half for the Sun being the Sun."""
    assert allowed_orb("Saturn", "conjunction", "Sun") == 4.0
    assert allowed_orb("Saturn", "conjunction", "Midheaven") == 4.0
    assert allowed_orb("Saturn", "conjunction", "Ascendant") == 4.0


def test_the_generational_planets_get_a_tighter_one():
    """Otherwise every reading drowns in contacts to Neptune and Pluto."""
    assert allowed_orb("Mercury", "trine", "Pluto") == 1.25
    assert allowed_orb("Mercury", "trine", "Mercury") == 1.75


@pytest.mark.parametrize("orb, band", [
    (0.0, "exact"), (0.2, "exact"),
    (0.5, "very strong"), (1.0, "very strong"),
    (1.5, "strong"), (2.0, "strong"),
    (2.5, "background"), (3.4, "background"),
])
def test_exactness_bands(orb, band):
    """"Saturn is technically active" and "Saturn is exact this week" are
    different sentences and must be distinguishable."""
    assert strength_band(orb) == band


# ── Passes ─────────────────────────────────────────────────────────────────

def test_a_retrograde_loop_is_one_cycle_of_several_passes(cycles):
    multi = [c for c in cycles if len(c["passes"]) >= 3]
    assert multi, "no three-pass cycles found in thirty months"

    for cycle in multi:
        # Numbered in order, each knowing how many there are in total.
        assert [w["pass"] for w in cycle["passes"]] == list(range(1, len(cycle["passes"]) + 1))
        assert all(w["of"] == len(cycle["passes"]) for w in cycle["passes"])
        # Passes are only grouped because the planet turned back.
        assert cycle["retrograde_involved"] is True
        # And the model is told they belong together.
        assert "retrograde loop" in (cycle["note"] or "")


def test_every_pass_is_exact_inside_its_own_window_and_in_order(cycles):
    """Passes can share a window: a slow planet may be exact, station, and be
    exact again without the orb ever widening enough to close it."""
    for cycle in cycles:
        previous_exact = None
        for window in cycle["passes"]:
            assert window["starts"] <= window["exact"] <= window["ends"], (
                f"{cycle['transit_planet']} {cycle['aspect']} {cycle['natal_point']}: "
                "a window cannot end before it is exact"
            )
            if previous_exact:
                assert window["exact"] > previous_exact, "passes must run forwards"
            previous_exact = window["exact"]


def test_an_annual_return_is_not_called_a_retrograde_pass(cycles):
    """The Sun crossing a point in two consecutive Decembers is the Sun coming
    round again, not pass one and pass two of one cycle.

    The test is on retrograde *motion*, not on a retrograde pass: a planet
    usually turns back between two exact hits rather than at one of them, which
    is precisely why the transit repeats.
    """
    for cycle in cycles:
        if len(cycle["passes"]) > 1:
            assert cycle["retrograde_involved"], (
                f"{cycle['transit_planet']} {cycle['aspect']} {cycle['natal_point']} "
                "grouped crossings with no retrograde motion to explain them"
            )

    # The Sun never turns back, so it can never produce a multi-pass cycle.
    for cycle in cycles:
        if cycle["transit_planet"] == "Sun":
            assert len(cycle["passes"]) == 1


def test_crossings_a_year_apart_are_separate_cycles():
    def window(year, month, retro=False):
        middle = datetime(year, month, 10, tzinfo=pytz.utc)
        return {"from": datetime(year, month, 1, tzinfo=pytz.utc),
                "to": datetime(year, month, 20, tzinfo=pytz.utc),
                "series": [(middle, 0.1, retro)]}

    far_apart = [window(2026, 1), window(2027, 1)]
    assert len(_group_into_cycles(far_apart)) == 2

    one_loop = [window(2026, 1), window(2026, 5, retro=True), window(2026, 9)]
    assert len(_group_into_cycles(one_loop)) == 1


# ── Importance is not exactness ────────────────────────────────────────────

def test_a_wide_saturn_outranks_an_exact_mercury(cycles):
    """Sorting by orb would put these the wrong way round."""
    saturn = next(c for c in cycles
                  if c["transit_planet"] == "Saturn" and c["natal_point"] in ("Sun", "Midheaven", "Ascendant"))
    mercury = next(c for c in cycles
                   if c["transit_planet"] == "Mercury" and c["aspect"] == "sextile")
    assert saturn["importance"] > mercury["importance"]
    assert cycles.index(saturn) < cycles.index(mercury)


def test_the_list_leads_with_importance(cycles):
    weights = [c["importance"] for c in cycles]
    assert weights == sorted(weights, reverse=True)


# ── The Moon ───────────────────────────────────────────────────────────────

def test_the_moon_opens_no_windows_of_its_own(points):
    """It is a trigger inside an existing window, never a forecast."""
    cycles = find_transit_cycles(points, months_ahead=6,
                                 now=datetime(2026, 9, 14, tzinfo=pytz.utc))
    assert not any(c["transit_planet"] == "Moon" for c in cycles)


def test_the_angles_are_transited(cycles):
    """A Saturn conjunction to the Midheaven is exactly the dated event people want."""
    hit = {c["natal_point"] for c in cycles}
    assert "Midheaven" in hit and "Ascendant" in hit


def test_two_years_is_searched_quickly_enough_to_sit_in_a_request(points):
    import time
    started = time.time()
    found = find_transit_cycles(points, months_ahead=24,
                                now=datetime(2026, 9, 14, tzinfo=pytz.utc))
    assert found
    assert time.time() - started < 5.0


# ── The month, whole ───────────────────────────────────────────────────────

def _month(points):
    from app.month_outlook_service import build_month_outlook
    return build_month_outlook(points, 2026, 10, now=datetime(2026, 9, 14, tzinfo=pytz.utc))


def test_a_month_is_read_across_a_whole_life(points):
    """Asked what a month holds, it used to answer about one area and leave
    work, money, health and everyone's friends unmentioned."""
    outlook = _month(points)
    named = {a["area"] for a in outlook["areas"]}
    assert len(named) >= 4, f"only {named} covered"
    assert any(a["verdict"] == "supported" for a in outlook["areas"]), (
        "a month with nothing good in it is a reading that only names risks"
    )


def test_the_verdict_is_supported_by_what_is_shown(points):
    """An area marked "under pressure" listing only helpful transits reads as
    a contradiction; the transits shown are the ones that drove it."""
    for area in _month(points)["areas"]:
        if area["verdict"] == "under pressure":
            assert any(not t["helps"] for t in area["transits"])
        if area["verdict"] == "supported":
            assert any(t["helps"] for t in area["transits"])


def test_the_periods_actually_differ(points):
    """Listing everything still in orb made every stretch identical, which is
    the opposite of splitting a month up."""
    periods = _month(points)["periods"]
    assert len(periods) >= 2
    signatures = [tuple(t["transit"] for t in p["peaking_now"]) for p in periods]
    assert len(set(signatures)) == len(signatures), "two periods reported the same thing"


def test_no_transit_is_counted_in_two_periods(points):
    seen = set()
    for period in _month(points)["periods"]:
        for hit in period["peaking_now"]:
            key = (hit["transit"], hit["exact"])
            assert key not in seen, f"{key} appears in more than one period"
            seen.add(key)


def test_periods_run_in_order_and_stay_inside_the_month(points):
    periods = _month(points)["periods"]
    for period in periods:
        assert period["from"].startswith("2026-10")
        assert period["to"].startswith("2026-10")
        for hit in period["peaking_now"]:
            assert period["from"] <= hit["exact"] <= period["to"]
    assert [p["from"] for p in periods] == sorted(p["from"] for p in periods)


def test_a_transit_exact_outside_the_month_is_flagged_as_ongoing(points):
    flags = [t["ongoing"] for a in _month(points)["areas"] for t in a["transits"]]
    assert any(flags), "a long transit exact either side of the month should be marked"
    for area in _month(points)["areas"]:
        for hit in area["transits"]:
            if not hit["ongoing"]:
                assert hit["exact"].startswith("2026-10")


# ── When the thing between two people actually moves ───────────────────────

def _two_charts():
    from tests.conftest import SOFIA, MILAN
    from types import SimpleNamespace
    import app.main as main
    one = main.build_natal_chart_data(SimpleNamespace(**SOFIA, birth_time_known=True))
    two = main.build_natal_chart_data(SimpleNamespace(**MILAN, birth_time_known=True))
    return one, two, main.get_synastry_aspects(one["planet_positions"], two["planet_positions"])


def test_a_relationship_window_carries_a_date():
    """A saved-person chat used to get each person's transits as two separate
    eight-week lists, and the one thing the code calls the strongest evidence
    for timing — a transit landing where the charts touch — had no date at all.
    So "will something happen between us" had nothing datable behind it."""
    from app.transit_timing_service import build_relationship_timeline
    one, two, syn = _two_charts()
    timeline = build_relationship_timeline(
        one["planet_positions"] + one.get("angles", []),
        two["planet_positions"] + two.get("angles", []), syn)

    windows = timeline["active_now"] + timeline["starting_soon"] + timeline["major_ahead"]
    assert windows
    for window in windows:
        assert window["passes"][0]["exact"], "a window with no exact day is not an answer to when"
    assert timeline["searched_months_ahead"] == 24


def test_it_says_whose_point_is_being_hit():
    from app.transit_timing_service import build_relationship_timeline
    one, two, syn = _two_charts()
    timeline = build_relationship_timeline(
        one["planet_positions"], two["planet_positions"], syn)
    described = [w["transit"] for w in timeline["active_now"] + timeline["starting_soon"]]
    assert any(t.startswith(("your", "their")) or " your " in t or " their " in t
               for t in described), described


def test_contacts_between_the_charts_are_marked_and_ranked_first():
    """A transit to one person's Venus is their week. A transit to the degree
    where their Venus meets the other's Mars is the two of them."""
    from app.transit_timing_service import build_relationship_timeline
    one, two, syn = _two_charts()
    timeline = build_relationship_timeline(
        one["planet_positions"], two["planet_positions"], syn)
    active = timeline["active_now"]
    if any(w.get("lights_contact") for w in active):
        assert active[0].get("lights_contact"), "a shared-degree window should sort first"


def test_something_is_always_reserved_for_what_is_coming():
    """Live windows filling the whole budget left nothing under "what's
    coming" — the half that answers "will something happen"."""
    from app.transit_timing_service import build_relationship_timeline
    one, two, syn = _two_charts()
    t = build_relationship_timeline(one["planet_positions"], two["planet_positions"], syn)
    assert len(t["active_now"]) <= 3
    assert t["starting_soon"] or t["major_ahead"]


def test_the_payload_stays_small():
    """It travels beside two full charts and a synastry engine."""
    import json
    from app.transit_timing_service import build_relationship_timeline
    one, two, syn = _two_charts()
    t = build_relationship_timeline(one["planet_positions"], two["planet_positions"], syn)
    total = len(t["active_now"]) + len(t["starting_soon"]) + len(t["major_ahead"])
    assert total <= 7, total
    assert len(json.dumps(t)) < 6000, len(json.dumps(t))


# ── Asking when, without saying "when" ─────────────────────────────────────

@pytest.mark.parametrize("question", [
    "will something happen between us", "is anything going to come of this",
    "do we have a chance", "when is this coming to a head", "will he come back",
])
def test_these_are_timing_questions(question):
    from app.question_router import asks_for_timing
    assert asks_for_timing(question)


@pytest.mark.parametrize("question", [
    "why do i pull away in relationships", "should i text him",
    "what does the full moon mean for me", "is he serious",
])
def test_these_are_not(question):
    from app.question_router import asks_for_timing
    assert not asks_for_timing(question)


def test_a_timing_answer_with_no_date_is_rejected():
    """The windows were in the request, dated, and the answer described the
    chemistry and named none of them. The prompt asks for a date; asking was
    not enough, the same way it was not enough for the tiers."""
    from app.answer_review_service import review_issues
    from app.conversation_service import conversation_state
    state = conversation_state("will something happen between us")
    state["expects_a_date"] = True
    state["max_words"] = 420
    vague = "There is real heat here but it is unstable. Let it be what it is."
    assert 'a timing question answered without a date' in review_issues(vague, state)


@pytest.mark.parametrize("answer", [
    "The window opens around 17 October — that is when this stops being theoretical.",
    "Mid-December is where it turns.",
    "Nothing until next spring, and then it moves quickly.",
    "Thursday is the one to watch.",
])
def test_any_form_of_a_date_satisfies_it(answer):
    from app.answer_review_service import review_issues
    from app.conversation_service import conversation_state
    state = conversation_state("will something happen between us")
    state["expects_a_date"] = True
    state["max_words"] = 420
    assert review_issues(answer, state) == []


def test_no_windows_means_no_requirement():
    """When the sky genuinely holds nothing, demanding a date would invent one."""
    import app.main as main
    assert main._has_windows(None) is False
    assert main._has_windows({}) is False
    assert main._has_windows({"active_now": [], "starting_soon": [], "major_ahead": []}) is False
    # A window with no exact day is not datable, so it does not count.
    assert main._has_windows({"active_now": [{"transit": "x", "passes": []}]}) is False
    dated = {"active_now": [{"transit": "Saturn conjunction your Venus",
                             "passes": [{"exact": "2026-10-17"}]}]}
    assert main._has_windows(dated) is True
    assert main._datable_windows(dated) == ["2026-10-17 — Saturn conjunction your Venus"]


def test_the_rewrite_is_handed_the_actual_days():
    """"You left the date out" produced no date twice running. The days
    themselves are what makes the second attempt land."""
    from app.answer_review_service import reviewed_answer
    from app.conversation_service import conversation_state
    prompts = []

    def generate(prompt, **kwargs):
        prompts.append(prompt)
        return ("It opens around 17 October.", 10) if len(prompts) > 1 else \
               ("There is real heat here, but it is unstable.", 10)

    state = conversation_state("will something happen between us")
    state["expects_a_date"] = True
    state["max_words"] = 420
    state["dates_available"] = ["2026-10-17 — Saturn conjunction your Venus"]
    answer, _ = reviewed_answer(generate, "prompt", {"conversation": state})
    assert answer == "It opens around 17 October."
    assert "cite_one_of_these_dates" in prompts[1]
    assert "2026-10-17" in prompts[1]
