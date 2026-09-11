"""The arithmetic, against answers that never change.

A birth chart is not a matter of opinion: for one moment at one place there is
exactly one right answer, and it will be the same in ten years. That makes the
maths the easiest thing in the app to protect and the worst thing to get
quietly wrong — nobody reading a warm paragraph can tell that Saturn is two
degrees off.

Positions below were taken from Swiss Ephemeris directly and checked by hand
against the sign boundaries.
"""
from datetime import datetime

import pytest
import pytz

from app.astrology_engine import (
    get_houses_and_ascendant,
    get_planet_positions_from_utc,
    get_zodiac_sign,
)

# 2 March 1999, 07:15 in Sofia — 05:15 UTC.
BIRTH_UTC = datetime(1999, 3, 2, 5, 15, tzinfo=pytz.utc)
SOFIA_LAT, SOFIA_LON = 42.6977, 23.3219


def positions():
    return {p["planet"]: p for p in get_planet_positions_from_utc(BIRTH_UTC)}


@pytest.mark.parametrize("body, sign, degree", [
    ("Sun", "Pisces", 11.17),
    ("Moon", "Virgo", 10.32),
    ("Saturn", "Taurus", 0.11),
    ("North Node", "Leo", 22.14),
    ("Chiron", "Sagittarius", 3.70),
])
def test_known_positions(body, sign, degree):
    """Drift here means something in the ephemeris path has changed."""
    p = positions()[body]
    assert p["sign"] == sign
    assert p["degree_in_sign"] == pytest.approx(degree, abs=0.05)


def test_chiron_needs_its_data_file_and_has_it():
    """Chiron is the only body read from a shipped file; its absence is silent."""
    assert "Chiron" in positions(), (
        "Chiron is missing, which means the ephemeris files are not being found. "
        "The chart still builds without it, so nothing else will tell you."
    )


def test_the_angles_are_calculated_and_kept():
    """The Midheaven used to be computed on the same line and thrown away."""
    houses = get_houses_and_ascendant(BIRTH_UTC, SOFIA_LAT, SOFIA_LON)
    assert houses["ascendant"]["sign"] == "Pisces"
    assert houses["midheaven"]["sign"] == "Sagittarius"
    assert houses["midheaven"]["degree"] == pytest.approx(262.31, abs=0.05)


def test_angles_are_shaped_like_aspect_targets():
    """They have to slot into the transit search without a parallel code path."""
    angles = get_houses_and_ascendant(BIRTH_UTC, SOFIA_LAT, SOFIA_LON)["angles"]
    assert [a["planet"] for a in angles] == ["Ascendant", "Midheaven"]
    for angle in angles:
        assert {"planet", "degree", "sign"} <= set(angle)


def test_twelve_houses_in_order():
    houses = get_houses_and_ascendant(BIRTH_UTC, SOFIA_LAT, SOFIA_LON)["houses"]
    assert [h["house"] for h in houses] == list(range(1, 13))
    assert all(0 <= h["degree"] < 360 for h in houses)


@pytest.mark.parametrize("degree, sign", [
    (0, "Aries"), (29.99, "Aries"), (30, "Taurus"),
    (180, "Libra"), (359.99, "Pisces"),
])
def test_sign_boundaries(degree, sign):
    """Off-by-one at a cusp would misplace a planet by a whole sign."""
    assert get_zodiac_sign(degree) == sign


def test_the_node_is_not_called_retrograde():
    """It travels backwards almost always; saying so every time is noise."""
    assert positions()["North Node"]["retrograde"] is False


def test_mercury_retrograde_is_still_reported():
    """Only the node is suppressed. This is the one everybody cares about."""
    retro = {
        p["planet"]
        for p in get_planet_positions_from_utc(datetime(2026, 3, 10, 12, tzinfo=pytz.utc))
        if p["retrograde"]
    }
    assert "Mercury" in retro
