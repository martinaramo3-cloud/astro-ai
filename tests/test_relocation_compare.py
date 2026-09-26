"""Comparing places to live: every city calculated, each area judged apart.

The engine was already good and was never reached. "Where would I have the
best life for career, love and happiness?" matched none of the old trigger
phrases, so 157 cities' worth of calculation sat unused and the answer came
from the ordinary chat path with no city scored at all.

The rest of these are the failures a city comparison invites: claiming a
search that did not run, promising somebody a person, presenting a fact about
a place as a chart finding, and quietly rewriting a ranking between answers.
"""
import json
import pathlib

import pytest

from app.answer_review_service import review_issues, _serious
from app.astrocartography_service import (
    COUNTS, IN_RANGE, ON_THE_LINE, describe_bands, line_strength, lines_for_city,
    mc_longitude,
)
from app.conversation_service import conversation_state
from app.european_cities import REGIONS, as_places
from app.relocation_compare_service import (
    AREAS, EQUAL, asks_to_compare_places, build_relocation_reading,
    cities_named_in, compare_places, decide_weighting, stated_priorities,
    what_changed,
)
import app.main as main
from tests.conftest import SOFIA

KNOWN = {
    "New York": (40.7128, -74.006, "America/New_York", "New York, United States"),
    "Miami": (25.7617, -80.1918, "America/New_York", "Miami, United States"),
    "Dubai": (25.2048, 55.2708, "Asia/Dubai", "Dubai, United Arab Emirates"),
}


def offline(name):
    """The geocoder, without the network. A follow-up that needs one is a
    follow-up that fails when the geocoder is busy."""
    key = name.split(",")[0].strip()
    if key not in KNOWN:
        return None
    lat, lon, zone, label = KNOWN[key]
    return {"latitude": lat, "longitude": lon, "timezone": zone, "display_name": label}


def natal():
    return main.build_natal_chart_data(
        type("P", (), dict(SOFIA, birth_time_known=True)))


def state_for(question, **extra):
    state = conversation_state(question, [])
    state["max_words"] = 690
    state.update(extra)
    return state


# --------------------------------------------------------------------------
# A. the question reaches the engine at all
# --------------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "Where would I have the best life for career, love and happiness?",
    "where should I live",
    "which city suits me",
    "best place for my career",
    "should I move to Berlin",
])
def test_the_questions_that_never_reached_it(question):
    assert asks_to_compare_places(question)


def test_an_ordinary_question_does_not_start_a_city_search():
    for question in ("should I text him", "what career suits me",
                     "what are my strengths"):
        assert not asks_to_compare_places(question)


# --------------------------------------------------------------------------
# B. astrocartography, and how close counts
# --------------------------------------------------------------------------

def test_planetary_lines_are_calculated():
    chart = natal()
    import swisseph as swe
    from datetime import datetime
    from app.relocation_service import chart_for
    born = datetime.fromisoformat(chart["utc_birth_time"])
    julian = swe.julday(born.year, born.month, born.day,
                        born.hour + born.minute / 60 + born.second / 3600)
    relocated = chart_for(born, 40.71, -74.01, planets=chart["planet_positions"])
    lines = lines_for_city(chart["planet_positions"], julian, 40.71, -74.01,
                           relocated.get("angles"))
    assert lines
    for line in lines:
        assert line["angle"] in ("MC", "IC", "AC", "DC")
        assert line["km"] <= IN_RANGE
        assert line["in_plain_words"]


def test_different_cities_sit_near_different_lines():
    chart = natal()
    import swisseph as swe
    from datetime import datetime
    from app.relocation_service import chart_for
    born = datetime.fromisoformat(chart["utc_birth_time"])
    julian = swe.julday(born.year, born.month, born.day,
                        born.hour + born.minute / 60 + born.second / 3600)
    seen = []
    for lat, lon in ((40.71, -74.01), (25.20, 55.27), (51.51, -0.13)):
        relocated = chart_for(born, lat, lon, planets=chart["planet_positions"])
        seen.append({(l["planet"], l["angle"]) for l in
                     lines_for_city(chart["planet_positions"], julian, lat, lon,
                                    relocated.get("angles"))})
    assert seen[0] != seen[1]


def test_the_distance_bands_are_documented_and_flagged():
    bands = describe_bands()
    assert bands["on_the_line_km"] == ON_THE_LINE
    assert "not the astrologer's" in bands["status"]
    assert "on the ground" in bands["measured"]


def test_closer_counts_for_more():
    assert line_strength(10) > line_strength(200) > line_strength(500)
    assert line_strength(IN_RANGE + 1) == 0.0


# --------------------------------------------------------------------------
# C. cities named in a question
# --------------------------------------------------------------------------

def test_named_cities_are_found():
    found, unresolved = cities_named_in("What about New York and Miami?", resolve=offline)
    assert {c["label"] for c in found} == {"New York, United States", "Miami, United States"}
    assert not unresolved


def test_a_leading_word_does_not_swallow_the_city():
    """"Add Dubai" matches as one capitalised phrase, and rejecting it on the
    word "Add" threw the city away with it."""
    found, _ = cities_named_in("Add Dubai.", resolve=offline)
    assert [c["label"] for c in found] == ["Dubai, United Arab Emirates"]


def test_a_place_that_is_not_real_is_reported_not_dropped():
    found, unresolved = cities_named_in("What about Wakanda?", resolve=offline)
    assert not found and unresolved == ["Wakanda"]


# --------------------------------------------------------------------------
# The region filter, which only ever honoured Europe
# --------------------------------------------------------------------------

def test_every_named_region_actually_filters():
    everywhere = len(as_places("world"))
    for region in REGIONS:
        found = as_places(region)
        assert 0 < len(found) < everywhere, region


def test_asking_for_the_usa_no_longer_searches_the_world():
    assert len(as_places("usa")) < len(as_places("world"))
    assert all("America" in c["timezone"] or "Pacific/Honolulu" in c["timezone"]
               for c in as_places("usa"))


# --------------------------------------------------------------------------
# Weighting: her three cases
# --------------------------------------------------------------------------

def test_stated_priorities_are_obeyed_and_nothing_is_asked():
    decided = decide_weighting("career first, then love")
    assert decided["ask"] is None
    assert decided["weights"]["career"] > decided["weights"]["love"]


def test_naming_areas_without_ordering_them_weights_them_equally():
    decided = decide_weighting(
        "Where would I have the best life for career, love and happiness?")
    assert decided["ask"] is None
    assert len(set(decided["weights"].values())) == 1


def test_memory_is_used_rather_than_asking_again():
    decided = decide_weighting("where should I live",
                               memories=[{"text": "Wants to find love"}])
    assert decided["ask"] is None
    assert decided["weights"]["love"] > decided["weights"]["career"]
    assert "Tell me if that's changed" in decided["confirm"]


def test_with_nothing_to_go_on_it_asks_one_question():
    decided = decide_weighting("where should I live")
    assert decided["ask"]
    assert len(set(decided["weights"].values())) == 1


def test_the_weighting_survives_a_follow_up():
    carried = {"weights": {"career": 1.5, "love": 1.0}, "came_from": "what you told me"}
    decided = decide_weighting("what about Miami?", carried=carried)
    assert decided["weights"] == carried["weights"]


# --------------------------------------------------------------------------
# The comparison itself
# --------------------------------------------------------------------------

def test_every_city_is_calculated_before_any_is_ranked():
    places = as_places("usa")
    result = compare_places(natal(), places=places, weighting=EQUAL)
    assert result["status"] == "ok"
    assert result["how_many_calculated"] == len(result["ranked"])
    assert set(result["compared"]) <= {p["label"] for p in places}


def test_the_areas_are_judged_separately():
    """"Best for career" and "best overall" have to be able to differ — that
    they DO, on about two thirds of charts, is the calibration's claim and is
    asserted there. On any single chart they may honestly coincide, and an
    earlier version of this test demanded otherwise and failed on a chart
    where Tirana genuinely led both.
    """
    result = compare_places(natal(), places=as_places("europe"), weighting=EQUAL)
    assert set(AREAS) == {"career", "love", "day to day happiness"}
    leader = result["ranked"][0]
    assert all(area in leader["area_rank"] for area in AREAS)
    # The three areas are scored independently, not one number relabelled.
    assert len({round(v, 4) for v in leader["area_rank"].values()}) > 1
    # Not an assertion that they differ on this chart — they may honestly
    # coincide, and an earlier version failed on a chart where Tirana led
    # both. The assertion is that they are computed apart and CAN differ.
    per_area = {area: [c["area_rank"][area] for c in result["ranked"]]
                for area in AREAS}
    assert per_area["career"] != per_area["love"]


def test_a_changed_ranking_says_which_area_moved_it():
    after = [
        {"place": "B", "area_rank": {"career": 0.9, "love": 0.3, "day to day happiness": 0.4}},
        {"place": "A", "area_rank": {"career": 0.2, "love": 0.5, "day to day happiness": 0.4}},
    ]
    changed = what_changed(["A", "B"], after, EQUAL)
    assert changed["new_leader"] == "B" and changed["previous_leader"] == "A"
    assert changed["the_area_that_moved_it"] == "career"


def test_nothing_changed_reports_nothing():
    after = [{"place": "A", "area_rank": {a: 0.5 for a in AREAS}}]
    assert what_changed(["A"], after, EQUAL) is None


# --------------------------------------------------------------------------
# The three-turn thread she tests with
# --------------------------------------------------------------------------

def test_the_three_turn_thread(monkeypatch):
    import app.relocation_compare_service as service
    monkeypatch.setattr(service.cities_named_in, "__defaults__", (offline,))
    chart = natal()

    first = service.build_relocation_reading(chart, "Where would I have the best "
                                             "life for career, love and happiness?")
    assert first["how_many_were_calculated"] > 100
    assert first["weighting_came_from"].startswith("what you asked about")

    second = service.build_relocation_reading(
        chart, "What about New York and Miami?", carried=first["_state"])
    named = {c for c in second["cities_actually_compared"]
             if c in ("New York, United States", "Miami, United States")}
    assert named == {"New York, United States", "Miami, United States"}

    third = service.build_relocation_reading(
        chart, "Add Dubai.", carried=second["_state"])
    assert "Dubai, United Arab Emirates" in third["cities_actually_compared"]
    # Her rule 5: the earlier cities and the weighting are kept.
    assert {"New York, United States", "Miami, United States"} <= set(
        third["cities_actually_compared"])
    assert third["how_many_were_calculated"] > second["how_many_were_calculated"]


def test_a_named_city_survives_a_bad_ranking():
    """It used to be dropped for placing 61st, which is both the wrong answer
    and the silent rewrite her rules forbid."""
    import app.relocation_compare_service as service
    chart = natal()
    first = service.build_relocation_reading(
        chart, "Where would I have the best life for career and love?")
    carried = dict(first["_state"])
    carried["asked_for"] = ["Reykjavik, Iceland"]
    carried["places"] = carried["places"] + [
        {"label": "Reykjavik, Iceland", "latitude": 64.1, "longitude": -21.9,
         "timezone": "Atlantic/Reykjavik"}]
    again = service.build_relocation_reading(chart, "what about it then",
                                             carried=carried)
    assert "Reykjavik, Iceland" in again["_state"]["compared"]


def test_no_birth_time_means_no_ranking():
    chart = main.build_natal_chart_data(
        type("P", (), dict(SOFIA, birth_time_known=False)))
    result = build_relocation_reading(chart, "where should I live")
    assert result["status"] == "needs_birth_time"
    assert "houses and the angles" in result["say"]


# --------------------------------------------------------------------------
# E, F: only claim what ran, keep the two sources apart
# --------------------------------------------------------------------------

@pytest.mark.parametrize("draft", [
    "You will meet someone in Lisbon.",
    "Lisbon is where you'll meet your person.",
])
def test_a_person_is_never_promised(draft):
    issues = review_issues(draft, state_for("where should I live"))
    assert any("promises them a person" in i for i in issues)
    assert _serious(issues)


@pytest.mark.parametrize("draft", [
    "Lisbon strongly favours love for you — meeting someone comes easier there.",
    "This is one of the strongest places for love in the comparison.",
    "Relationship life here tends to find you rather than the other way round.",
])
def test_a_bold_calculated_read_on_love_gets_through(draft):
    """Her rule: be bold where the calculation supports it. Certainty is the
    only thing banned."""
    assert review_issues(draft, state_for("where should I live")) == []


def test_a_search_that_did_not_run_cannot_be_claimed():
    draft = "I compared cities worldwide and Lisbon came first."
    assert any("did not run" in i for i in review_issues(draft, state_for("where should I live")))
    allowed = state_for("where should I live", relocation_scope="compared 157 worldwide")
    assert review_issues(draft, allowed) == []


def test_a_city_fact_is_not_a_chart_finding():
    draft = "Your chart shows the cost of living there suits you."
    assert any("fact about the city" in i
               for i in review_issues(draft, state_for("where should I live")))


def test_the_priorities_question_is_allowed_to_be_asked():
    draft = ("Lisbon leads for you if everything counts equally. What matters "
             "most — career, love, day-to-day happiness, or all equally?")
    asking = state_for("where should I live", may_ask_priorities=True)
    assert review_issues(draft, asking) == []
    # And is not a licence to hand every question back.
    assert review_issues("Did anything come up this week?", asking)


# --------------------------------------------------------------------------
# The payload
# --------------------------------------------------------------------------

def test_no_number_reaches_the_reader():
    import re
    result = compare_places(natal(), places=as_places("usa"), weighting=EQUAL)
    from app.relocation_compare_service import for_the_answer
    compact = for_the_answer(result)
    for entry in compact["ranking"]:
        for value in (entry["career"], entry["love"], entry["day_to_day"],
                      entry["overall_fit"]):
            assert not re.search(r"\d", value), value


def test_the_payload_says_exactly_what_ran():
    result = compare_places(natal(), places=as_places("usa"), weighting=EQUAL)
    from app.relocation_compare_service import for_the_answer
    compact = for_the_answer(result)
    assert compact["how_many_were_calculated"] == len(result["ranked"])
    assert "not in that list" in compact["you_may_not_say"]


def test_relocation_does_not_move_the_planets():
    prompt = " ".join(main.build_ask_astrologer_system().split())
    assert "The planets stay in the same signs" in prompt
    assert "one input beside those" in prompt
    assert "never promise a person" in prompt.lower() or "promise a person" in prompt


def test_the_calibration_gate_is_recorded():
    report = json.loads(
        (pathlib.Path(main.__file__).resolve().parents[1] / "training" / "area6"
         / "city_distribution.json").read_text())
    assert report["passes"] is True
    assert max(report["first_city"].values()) <= 0.5
    assert max(report["first_region"].values()) <= 0.5
    assert report["career_differs_from_overall"] > 0.2
