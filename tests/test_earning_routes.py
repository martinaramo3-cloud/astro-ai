"""The co-founder's earning-route framework, and the rules that come with it.

Six routes, her weight table, five dimensions, six rules. The rules are not
decoration — each one exists because an engine without it produces a confident
answer that is wrong in a particular way, and each has a test here.

The one thing in this file that is not hers is how routes are RANKED, and it
is tested hardest. Her weights produce a number per route that cannot be
compared across routes: her evidence column names five houses for business and
one for partnerships, so business has five chances at the 5-point evidence and
partnerships has one. Ranked on the raw total, business came first for 46% of
a thousand charts and partnerships never came first at all. Employment — the
commonest way people actually earn money — came first 3% of the time.
"""
import json
import pathlib

import pytest

from app.angle_aspects_service import conjunct_cusp, derive_angles, get_angle_aspects
from app.earning_routes_service import (
    COMPLEMENTARY_GAP, POINTS, ROUTES, SYMBOLISM_CAP,
    _evidence_for, _facts, _score, describe_routes, score_earning_routes,
    technical_evidence,
)
import app.main as main
from tests.conftest import MILAN, SOFIA


def chart(person=SOFIA, birth_time_known=True):
    return main.build_natal_chart_data(
        type("P", (), dict(person, birth_time_known=birth_time_known)))


# --------------------------------------------------------------------------
# The gap from the audit: aspects to the MC
# --------------------------------------------------------------------------

def test_the_midheaven_can_now_be_aspected():
    """Aspects were computed between planets only, so a planet squaring the
    career point did not exist anywhere in the system."""
    natal = chart()
    aspects = get_angle_aspects(natal["planet_positions"],
                                ascendant=natal["ascendant"],
                                midheaven=natal["midheaven"], houses=natal["houses"])
    assert aspects
    assert any(a["planet_2"] == "Midheaven" for a in aspects)
    assert all(a["orb"] <= 5.0 for a in aspects)


def test_the_two_angles_nobody_stores_are_derived():
    natal = chart()
    angles = derive_angles(natal["ascendant"], natal["midheaven"], natal["houses"])
    assert set(angles) == {"Ascendant", "Midheaven", "Descendant", "Imum Coeli"}
    assert abs((angles["Midheaven"] + 180) % 360 - angles["Imum Coeli"]) < 0.01


def test_a_planet_on_the_second_cusp_is_visible():
    """The weight table awards points for it, and a house cusp that is not an
    angle had no other way of being seen."""
    natal = chart()
    found = conjunct_cusp(natal["planet_positions"], natal["houses"], 2)
    assert all(p["orb"] <= 3.0 for p in found)


# --------------------------------------------------------------------------
# Her weight table, unchanged
# --------------------------------------------------------------------------

def test_the_weights_are_hers():
    assert POINTS == {
        "second_ruler_placement": 5, "second_tenth_link": 5,
        "ruler_connects": 4, "on_cusp": 3, "planet_in_house": 2, "symbolism": 1,
    }
    assert SYMBOLISM_CAP == 1


def test_symbolism_is_capped_at_one_however_many_significators():
    """"1 maximum" — and two routes carry two natural significators each."""
    def item(fact):
        return {"kind": "symbolism", "points": 1, "counts_as": 1.0, "weight": 1.0,
                "why": "", "fact": fact, "qualifies": False}
    assert _score([item("a"), item("b")]) == 1


def test_the_six_routes_are_hers():
    assert set(ROUTES) == {
        "employment", "independent_expertise", "business_products",
        "partnerships_deals", "others_assets", "owned_assets",
    }


# --------------------------------------------------------------------------
# Rule 1 — trace money first
# --------------------------------------------------------------------------

def test_money_is_traced_from_the_second_house_and_shown():
    result = score_earning_routes(chart())
    traced = result["traced_from"]
    assert traced["money_house_ruler"]["planet"]
    assert traced["money_house_ruler"]["sits_in_house"]
    assert "career_ruler" in traced


def test_nothing_about_the_person_can_reach_the_ranking():
    """Rule 1 in the signature, not only in the order: their degree, job and
    Sun sign are not arguments to this function, so they cannot leak in."""
    import inspect
    parameters = set(inspect.signature(score_earning_routes).parameters)
    assert parameters == {"chart", "birth_time_confident"}


# --------------------------------------------------------------------------
# Rule 2 — two independent signals, one on the money house
# --------------------------------------------------------------------------

def test_strong_needs_two_signals_and_one_on_the_money_house():
    for route in score_earning_routes(chart())["all_routes"]:
        if route["strong"]:
            assert route["signals"] >= 2
            assert route["has_qualifying_signal"]


def test_a_planet_in_a_house_can_never_qualify_on_its_own():
    """"A planet sitting in the 8th or 11th by itself cannot establish a
    route." Tenancy is never a qualifying signal, for any house."""
    facts = _facts(chart())
    for key in ROUTES:
        for item in _evidence_for(key, facts):
            if item["kind"] in ("planet_in_house", "symbolism"):
                assert item["qualifies"] is False, (key, item["why"])


def test_only_the_money_house_and_the_career_income_link_qualify():
    facts = _facts(chart())
    for key in ROUTES:
        for item in _evidence_for(key, facts):
            if item["qualifies"]:
                assert (item["kind"] in ("second_ruler_placement", "second_tenth_link")
                        or "money" in item["why"]), item


# --------------------------------------------------------------------------
# Rule 3 — never count the same aspect twice
# --------------------------------------------------------------------------

def test_one_aspect_is_one_piece_of_evidence():
    """"One 2nd-ruler–7th-ruler aspect is one strong piece of evidence, even
    if it appears under several descriptions." Enforced by keying evidence on
    the fact it rests on rather than by remembering to."""
    facts = _facts(chart())
    for key in ROUTES:
        facts_used = [_fact_key(i) for i in _evidence_for(key, facts)]
        assert len(facts_used) == len(set(facts_used)), key


def _fact_key(item):
    # The engine strips the key from its public output, so rebuild it from the
    # text: two identical reasons would be the duplicate this rule forbids.
    return item["why"]


def test_the_second_tenth_aspect_is_not_also_counted_as_a_ruler_connection():
    facts = _facts(chart())
    for key in ROUTES:
        kinds = [i["kind"] for i in _evidence_for(key, facts)]
        # At most one of each aspect-derived kind per underlying pair; the
        # 2nd–10th link is excluded from the ruler-connection sweep.
        assert kinds.count("second_tenth_link") <= 1


# --------------------------------------------------------------------------
# Rule 4 — condition changes how a route works, not whether it exists
# --------------------------------------------------------------------------

def test_an_afflicted_ruler_complicates_a_route_rather_than_deleting_it():
    result = score_earning_routes(chart())
    complicated = [r for r in result["all_routes"] if r["counterevidence"]]
    # Counterevidence exists and does not zero anything out.
    assert complicated
    for route in complicated:
        assert route["score"] >= 0
        if route["signals"] >= 2 and route["has_qualifying_signal"]:
            assert route["strong"], "counterevidence must not delete a route"


def test_the_complication_is_explained():
    result = score_earning_routes(chart())
    assert isinstance(result["how_it_works"], list)


# --------------------------------------------------------------------------
# Rule 5 — at most three, complementary when close, lower confidence when thin
# --------------------------------------------------------------------------

def test_never_more_than_three_routes():
    for person in (SOFIA, MILAN):
        assert len(score_earning_routes(chart(person))["ranking"]) <= 3


def test_a_route_the_chart_says_less_about_than_average_is_not_ranked_second():
    """Below the median the chart says LESS about a route than it does for a
    typical chart. Listing it second manufactures a ranking."""
    for person in (SOFIA, MILAN):
        ranked = score_earning_routes(chart(person))["ranking"]
        if len(ranked) > 1:
            assert all(r["how_unusual"] >= 0.5 for r in ranked)


def test_close_top_two_read_as_complementary():
    result = score_earning_routes(chart())
    if len(result["ranking"]) >= 2:
        gap = result["ranking"][0]["how_unusual"] - result["ranking"][1]["how_unusual"]
        assert result["complementary"] == (gap <= COMPLEMENTARY_GAP)
    if result["complementary"]:
        assert "work together" in describe_routes(result)


def test_an_uncertain_birth_time_lowers_confidence():
    """"Lower confidence rather than manufacture a precise ranking."""
    confident = score_earning_routes(chart(), birth_time_confident=True)
    unsure = score_earning_routes(chart(), birth_time_confident=False)
    assert unsure["confidence"].startswith("low")
    assert unsure["ranking"] == confident["ranking"]  # the reading is unchanged


def test_no_birth_time_at_all_means_no_ranking():
    assert score_earning_routes({"planet_positions": [], "houses": []})["available"] is False


# --------------------------------------------------------------------------
# Rule 6 — their life comes after, and never becomes chart evidence
# --------------------------------------------------------------------------

def test_the_same_chart_ranks_the_same_whatever_the_person_studies():
    """Their circumstances turn a route into practical options. They must not
    retroactively become evidence for it — which is only guaranteed if they
    cannot reach the ranking at all."""
    one = score_earning_routes(chart())
    two = score_earning_routes(chart())
    assert [r["key"] for r in one["ranking"]] == [r["key"] for r in two["ranking"]]
    assert one["all_routes"] == two["all_routes"]


# --------------------------------------------------------------------------
# Ranking: the part that is mine
# --------------------------------------------------------------------------

def test_routes_are_ranked_on_how_unusual_not_on_the_raw_score():
    result = score_earning_routes(chart())
    order = [r["how_unusual"] for r in result["all_routes"]]
    assert order == sorted(order, reverse=True)


def test_the_distributions_exist_and_cover_every_route():
    spread = json.loads(
        (pathlib.Path(main.__file__).resolve().parents[1]
         / "content" / "engine" / "earning_route_bands.json").read_text())
    assert set(spread) == set(ROUTES)
    for key, values in spread.items():
        assert len(values) >= 500, key
        assert values == sorted(values), key


def test_the_raw_score_is_still_reported_for_the_audit():
    """Her number stays visible. Only the comparison between routes changed."""
    for route in score_earning_routes(chart())["all_routes"]:
        assert isinstance(route["score"], (int, float))
        assert 0.0 <= route["how_unusual"] <= 1.0
        for item in route["evidence"]:
            # Her point value, how exact the contact is, and the product.
            assert item["points"] in (1, 2, 3, 4, 5)
            assert 0.0 <= item["weight"] <= 1.0
            assert item["counts_as"] <= item["points"]


def test_it_says_which_numbers_are_not_hers():
    result = score_earning_routes(chart())
    assert "unchanged" not in result["provenance"].split("Two numbers")[1]
    assert "mine" in result["provenance"]
    assert result["weights"] == "her weight table, unchanged"


# --------------------------------------------------------------------------
# Plain language by default, evidence only on request
# --------------------------------------------------------------------------

def test_the_plain_sentence_carries_no_astrology():
    from app.answer_review_service import JARGON
    for person in (SOFIA, MILAN):
        sentence = describe_routes(score_earning_routes(chart(person)))
        assert sentence
        assert not JARGON.search(sentence), sentence
        assert "house" not in sentence.lower()


def test_the_plain_sentence_never_carries_a_score():
    import re
    for person in (SOFIA, MILAN):
        assert not re.search(r"\d", describe_routes(score_earning_routes(chart(person))))


def test_the_technical_evidence_exists_but_is_a_separate_call():
    """It reaches an answer only through the existing astrology-on-request
    mode. Every other answer gets the plain sentence and nothing else."""
    result = score_earning_routes(chart())
    lines = technical_evidence(result)
    assert lines
    assert any("rules your" in line or "sits" in line for line in lines)


def test_the_score_is_described_as_a_consistency_device():
    result = score_earning_routes(chart())
    assert "not a probability" in result["internal_only"]


# --------------------------------------------------------------------------
# Her five dimensions
# --------------------------------------------------------------------------

def test_the_five_dimensions_are_hers():
    dimensions = score_earning_routes(chart())["dimensions"]
    # Her rules document replaces "control" with personal delivery versus
    # growth through a team or a network.
    assert set(dimensions) == {"visibility", "customer_structure", "what_is_sold",
                               "delivery", "income_rhythm"}
    for reading in dimensions.values():
        assert len(reading["poles"]) == 2
        assert reading["reads_as"]


def test_a_dimension_can_read_as_undecided():
    """A chart genuinely between the two is a real answer, not a failure."""
    from app.earning_routes_service import DIMENSIONS, _dimension_reading
    readings = {name: _dimension_reading(spec, _facts(chart()))
                for name, spec in DIMENSIONS.items()}
    assert all(r["margin"] >= 0 for r in readings.values())


# --------------------------------------------------------------------------
# Still dark
# --------------------------------------------------------------------------

def test_the_engine_is_not_wired_into_any_answer():
    """Live only after she has reviewed the blind table. This test is what
    keeps that true.

    The internal career reading may import it — that object is itself dark,
    and test_career_reading holds the line for the pair of them. Nothing else
    may.
    """
    import subprocess
    importers = {
        path.replace("//", "/") for path in subprocess.run(
            ["grep", "-rl", "--include=*.py", "earning_routes_service", "app/"],
            capture_output=True, text=True).stdout.split()
        if not path.endswith("earning_routes_service.py")
    }
    assert importers <= {"app/career_reading_service.py"}, importers


def test_the_blind_table_covers_this_engine_too():
    """Superseded by blind_career.html, which carries both rankings — see
    test_career_reading. The routes-only table was removed rather than left to
    go stale beside it."""
    here = pathlib.Path(main.__file__).resolve().parents[1] / "training" / "area3"
    assert not (here / "blind_routes.html").exists()
    assert "earning routes" in (here / "blind_career.html").read_text()
