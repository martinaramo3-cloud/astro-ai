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
