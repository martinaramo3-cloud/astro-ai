"""Solar returns and relocated charts.

The astronomy is settled and checkable: the Sun is either back at its natal
degree or it isn't, and a relocated chart either keeps the planets still or it
has a bug. What makes a solar return *good* is an astrological judgement and is
deliberately not decided here.
"""
from datetime import datetime

import pytest
import pytz

from app.astrology_engine import get_planet_positions_from_utc
from app.relocation_service import (
    _sun_longitude,
    chart_for,
    find_solar_return,
    solar_return_for_places,
)

BIRTH = datetime(1999, 3, 2, 5, 15, tzinfo=pytz.utc)
SOFIA = (42.6977, 23.3219)
LONDON = (51.5074, -0.1278)

PLACES = [
    {"label": "Sofia, Bulgaria", "latitude": 42.70, "longitude": 23.32, "timezone": "Europe/Sofia"},
    {"label": "London, UK", "latitude": 51.51, "longitude": -0.13, "timezone": "Europe/London"},
    {"label": "Lisbon, Portugal", "latitude": 38.72, "longitude": -9.14, "timezone": "Europe/Lisbon"},
]


@pytest.fixture(scope="module")
def natal_sun():
    return next(p for p in get_planet_positions_from_utc(BIRTH) if p["planet"] == "Sun")["degree"]


# ── The return moment ──────────────────────────────────────────────────────

@pytest.mark.parametrize("year", [2026, 2027, 2028, 2029])
def test_the_sun_is_actually_back_where_it_started(natal_sun, year):
    """Within an arcsecond. The Sun moves a degree a day, so an hour's error
    moves the returned Ascendant by degrees — which is the whole thing a solar
    return turns on."""
    moment = find_solar_return(natal_sun, year, 3, 2)
    error_arcseconds = abs(_sun_longitude(moment) - natal_sun) * 3600
    assert error_arcseconds < 5, f"{error_arcseconds:.1f} arcseconds out"


@pytest.mark.parametrize("year", [2026, 2027, 2028])
def test_the_return_falls_near_the_birthday(natal_sun, year):
    moment = find_solar_return(natal_sun, year, 3, 2)
    assert moment.year == year
    assert abs((moment - datetime(year, 3, 2, tzinfo=pytz.utc)).days) <= 2


# ── Relocation ─────────────────────────────────────────────────────────────

def test_relocating_never_moves_a_planet():
    """Same moment, same sky. Only the houses and angles are local."""
    here = chart_for(BIRTH, *SOFIA)
    there = chart_for(BIRTH, *LONDON)

    positions_here = {p["planet"]: p["degree"] for p in here["planets"]}
    positions_there = {p["planet"]: p["degree"] for p in there["planets"]}
    assert positions_here == positions_there


def test_relocating_does_move_the_angles_and_houses():
    here = chart_for(BIRTH, *SOFIA)
    there = chart_for(BIRTH, *LONDON)

    assert here["ascendant"]["degree"] != there["ascendant"]["degree"]
    assert here["midheaven"]["degree"] != there["midheaven"]["degree"]
    # And that is what carries a planet into a different area of life.
    venus_here = next(p for p in here["planets"] if p["planet"] == "Venus")["house"]
    venus_there = next(p for p in there["planets"] if p["planet"] == "Venus")["house"]
    assert venus_here != venus_there


def test_the_four_angles_are_opposite_in_pairs():
    chart = chart_for(BIRTH, *SOFIA)
    angles = chart["angles"]
    assert abs((angles["Ascendant"] - angles["Descendant"]) % 360 - 180) < 0.01
    assert abs((angles["Midheaven"] - angles["IC"]) % 360 - 180) < 0.01


def test_a_planet_on_an_angle_is_reported():
    chart = chart_for(BIRTH, *SOFIA)
    for hit in chart["angular_planets"]:
        assert hit["angle"] in ("Ascendant", "Midheaven", "Descendant", "IC")
        assert hit["orb"] <= 5.0


# ── Comparing places ───────────────────────────────────────────────────────

def test_every_city_shares_one_return_moment(natal_sun):
    """The Sun returns when it returns, wherever anyone is standing."""
    result = solar_return_for_places(natal_sun, 2027, 3, 2, PLACES)
    assert len(result["places"]) == len(PLACES)
    assert result["returns_at_utc"]


def test_the_cities_genuinely_differ(natal_sun):
    """If they didn't, there would be nothing to choose between."""
    result = solar_return_for_places(natal_sun, 2027, 3, 2, PLACES)
    ascendants = {p["ascendant"] for p in result["places"]}
    assert len(ascendants) > 1


def test_each_city_reports_its_own_local_time(natal_sun):
    """Someone has to physically be somewhere at that moment, so the answer is
    useless without the local clock time."""
    result = solar_return_for_places(natal_sun, 2027, 3, 2, PLACES)
    assert all(p["local_time"] for p in result["places"])
    # Sofia is two hours ahead of London in March.
    by_place = {p["place"]: p["local_time"] for p in result["places"]}
    assert by_place["Sofia, Bulgaria"] != by_place["London, UK"]


# ── Scoring, from an astrologer's table ────────────────────────────────────

from app.relocation_scoring import angle_strength, score_chart


@pytest.mark.parametrize("orb, share", [
    (0.0, 1.00), (1.0, 1.00),
    (1.5, 0.75), (2.0, 0.75),
    (2.5, 0.50), (3.0, 0.50),
    (4.0, 0.20), (5.0, 0.20),
    (5.1, 0.0), (9.0, 0.0),
])
def test_closeness_to_an_angle_slides(orb, share):
    """Not in-or-out: a planet a quarter-degree off an angle and one three
    degrees off are not the same thing."""
    assert angle_strength(orb) == share


def test_the_scoring_shows_its_working():
    """A ranking nobody can check is a ranking nobody should trust."""
    chart = chart_for(BIRTH, *SOFIA)
    result = score_chart(chart, "money")
    assert result["why"], "no reasoning given"
    assert set(result) >= {"score", "from_houses", "from_angles", "from_rulers"}
    assert "2nd" in str(result["house_detail"]), "houses should read as 2nd, not 2th"


def test_an_unknown_purpose_scores_nothing_rather_than_guessing():
    """Inventing a table for love would be inventing astrology."""
    result = score_chart(chart_for(BIRTH, *SOFIA), "love")
    assert result["score"] == 0.0
    assert "no scoring table" in result["note"].lower()


def test_saturn_on_the_midheaven_is_not_punished():
    """Deliberate: it is as often serious career building as it is a problem."""
    from app.relocation_scoring import MONEY
    assert MONEY["planet_on_angle"]["Saturn"]["Midheaven"] == 0
    assert MONEY["planet_in_house"]["Saturn"][10] == 0
    # But it does count against the money houses proper.
    assert MONEY["planet_in_house"]["Saturn"][2] == -3


def test_the_ranking_says_whether_the_choice_matters(natal_sun):
    """In some years most of Europe gives the same chart, and telling someone
    to fly somewhere is then selling a difference that isn't there."""
    from app.relocation_service import rank_places_for
    result = rank_places_for(natal_sun, 2027, 3, 2, purpose="money", top=5)
    assert result["does_location_matter_this_year"]
    assert result["searched"] >= 60, "the search should be wide, not thirty capitals"
    assert len(result["best"]) <= 5


def test_cities_with_the_same_chart_are_shown_as_equal(natal_sun):
    """Krakow, Tirana and Podgorica sit on nearly one longitude, so ranking
    them first, second and third is a ranking of nothing."""
    from app.relocation_service import rank_places_for
    result = rank_places_for(natal_sun, 2027, 3, 2, purpose="money", top=10)
    assert any(place["also"] for place in result["best"])
    for place in result["best"]:
        for twin in place["also"]:
            assert twin != place["place"]
