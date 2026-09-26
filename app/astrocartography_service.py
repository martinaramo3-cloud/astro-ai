"""Planetary lines: where on Earth a planet stands on one of your angles.

The relocation audit found this missing entirely — no lines, no parans, no
zenith. The relocated-chart method was there and correct; the map method was
not, and it is the one most people mean by "astrocartography".

------------------------------------------------------------------------------
What a line is
------------------------------------------------------------------------------
Your planets do not move when you move. What moves is the sky's orientation to
the ground under you, so a planet that was nowhere near your horizon in one
city is sitting exactly on it in another. A planetary LINE is the set of
places where a given planet is exactly on one of the four angles at the moment
you were born:

  MC line   the planet is at the top of the sky — it shows in your standing,
            your work, what you become known for there
  IC line   the planet is at the bottom — home, family, private life, roots
  AC line   the planet is rising — it colours how you come across and how you
            meet the place
  DC line   the planet is setting — it shows in partnerships and who you draw

MC and IC lines run north–south: one longitude, every latitude. AC and DC
lines curve, because rising depends on latitude as well as longitude, so they
are computed per city rather than as a single meridian.

------------------------------------------------------------------------------
HOW CLOSE IS CLOSE — documented because it was asked for
------------------------------------------------------------------------------
Conventionally a line is felt within a few degrees of longitude, and one
degree of longitude is about 111 km at the equator and less further from it.
The numbers below are MINE and on the astrologer's list:

  within  75 km   on the line
  within 250 km   close enough to count
  within 600 km   in range, weakly
  beyond          not counted at all

Distance is measured on the ground, not in degrees, because a degree of
longitude in Oslo is half what it is in Nairobi and a rule written in degrees
quietly favours the tropics.
"""
from __future__ import annotations

import math

ANGLES = ("MC", "IC", "AC", "DC")

# MINE. Kilometres on the ground; see the module docstring.
ON_THE_LINE = 75.0
COUNTS = 250.0
IN_RANGE = 600.0

# How much a line counts for, by how close it is.
def line_strength(km: float) -> float:
    if km <= ON_THE_LINE:
        return 1.0
    if km <= COUNTS:
        return round(1.0 - 0.4 * (km - ON_THE_LINE) / (COUNTS - ON_THE_LINE), 3)
    if km <= IN_RANGE:
        return round(0.6 - 0.45 * (km - COUNTS) / (IN_RANGE - COUNTS), 3)
    return 0.0


# What each planet on each angle says about living there. Plain language, no
# jargon, because this reaches a reader. MINE, and on her list.
LINE_MEANING = {
    ("Sun", "MC"): "you are visible here, and what you do gets attributed to you",
    ("Sun", "IC"): "you can be fully yourself here, though more privately than publicly",
    ("Sun", "AC"): "people read you clearly here; you take up your own space",
    ("Sun", "DC"): "you are defined by who you are with here more than elsewhere",
    ("Moon", "MC"): "your work here is tied to what you care about, for better and worse",
    ("Moon", "IC"): "this is a place that can feel like home quickly",
    ("Moon", "AC"): "you are more open here, and more affected by the mood around you",
    ("Moon", "DC"): "closeness comes easily here, and so does needing it",
    ("Mercury", "MC"): "you get known here for what you say and how clearly you say it",
    ("Mercury", "IC"): "home here is full of talk, books, movement, plans",
    ("Mercury", "AC"): "you think fast here and people meet you as quick",
    ("Mercury", "DC"): "you connect through conversation here; talk is the way in",
    ("Venus", "MC"): "your standing here comes through taste, charm or what you make beautiful",
    ("Venus", "IC"): "home here is comfortable, and you want it to be",
    ("Venus", "AC"): "you come across warmly here and it opens doors",
    ("Venus", "DC"): "relationships find you more easily here than in most places",
    ("Mars", "MC"): "you push hard here and it shows in what you achieve",
    ("Mars", "IC"): "there is friction close to home here, and energy too",
    ("Mars", "AC"): "you are more direct here, quicker to act and to argue",
    ("Mars", "DC"): "partnerships here are charged — attraction and conflict both",
    ("Jupiter", "MC"): "opportunity finds your work here; doors open wider",
    ("Jupiter", "IC"): "you can put down roots here and they grow",
    ("Jupiter", "AC"): "you are bigger here — more confident, more expansive",
    ("Jupiter", "DC"): "the people you meet here tend to open things up for you",
    ("Saturn", "MC"): "you build real authority here, slowly and by earning it",
    ("Saturn", "IC"): "home here is serious; it asks something of you",
    ("Saturn", "AC"): "you are more guarded here, and more disciplined",
    ("Saturn", "DC"): "commitments here are heavier and last longer",
}
# Which area of life each angle speaks to, for the scoring side.
ANGLE_AREA = {"MC": "career", "IC": "home", "AC": "day to day", "DC": "love"}

EARTH_KM = 6371.0


def _greenwich_sidereal_time(julian_day: float) -> float:
    """Sidereal time at Greenwich, in degrees."""
    t = (julian_day - 2451545.0) / 36525.0
    theta = (280.46061837 + 360.98564736629 * (julian_day - 2451545.0)
             + 0.000387933 * t * t - t * t * t / 38710000.0)
    return theta % 360.0


def _distance_km(lat1, lon1, lat2, lon2) -> float:
    one, two = math.radians(lat1), math.radians(lat2)
    dlat, dlon = two - one, math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(one) * math.cos(two) * math.sin(dlon / 2) ** 2)
    return 2 * EARTH_KM * math.asin(min(1.0, math.sqrt(a)))


def mc_longitude(planet_degree: float, julian_day: float) -> float:
    """The longitude where this planet is exactly on the Midheaven.

    The MC is wherever local sidereal time equals the planet's right
    ascension. Working from ecliptic longitude directly is an approximation —
    it ignores the planet's latitude off the ecliptic — and for every body
    this app uses that is under a degree, well inside the distance bands.
    """
    obliquity = math.radians(23.4392911)
    lam = math.radians(planet_degree)
    right_ascension = math.degrees(math.atan2(
        math.sin(lam) * math.cos(obliquity), math.cos(lam))) % 360.0
    return ((right_ascension - _greenwich_sidereal_time(julian_day) + 180) % 360) - 180


def lines_for_city(planets: list[dict], julian_day: float,
                   latitude: float, longitude: float,
                   angles_at_city: dict | None = None) -> list[dict]:
    """Which planetary lines this city sits near, and how near.

    MC and IC are true meridians, so the distance is along the ground at this
    latitude. AC and DC are read from the city's own relocated angles instead
    of solved as curves — if a planet is within a few degrees of the relocated
    Ascendant, the city is on that planet's AC line by definition, and the
    relocated chart is already being computed for every candidate.
    """
    found = []
    for planet in planets or []:
        name, degree = planet.get("planet"), planet.get("degree")
        if name not in {p for p, _ in LINE_MEANING} or not isinstance(degree, (int, float)):
            continue
        mc_lon = mc_longitude(degree, julian_day)
        for angle, line_lon in (("MC", mc_lon), ("IC", ((mc_lon + 180 + 180) % 360) - 180)):
            km = _distance_km(latitude, longitude, latitude, line_lon)
            # Longitudes wrap: 179°E and 179°W are close together.
            km = min(km, _distance_km(latitude, longitude, latitude,
                                      line_lon + (360 if line_lon < 0 else -360)))
            if km <= IN_RANGE:
                found.append(_line(name, angle, km))

    for angle, key in (("AC", "Ascendant"), ("DC", "Descendant")):
        point = (angles_at_city or {}).get(key)
        if not isinstance(point, (int, float)):
            continue
        for planet in planets or []:
            name, degree = planet.get("planet"), planet.get("degree")
            if (name, angle) not in LINE_MEANING or not isinstance(degree, (int, float)):
                continue
            gap = abs((degree - point + 180) % 360 - 180)
            # A degree of the rising point is roughly four minutes of rotation;
            # at the equator that is about 111 km of ground, less further up.
            km = gap * 111.0 * max(0.35, math.cos(math.radians(latitude)))
            if km <= IN_RANGE:
                found.append(_line(name, angle, km))

    return sorted(found, key=lambda line: line["km"])


def _line(planet: str, angle: str, km: float) -> dict:
    return {
        "planet": planet, "angle": angle,
        "km": round(km),
        "how_close": ("on the line" if km <= ON_THE_LINE
                      else "close" if km <= COUNTS else "in range"),
        "strength": line_strength(km),
        "area": ANGLE_AREA[angle],
        "in_plain_words": LINE_MEANING[(planet, angle)],
    }


def describe_bands() -> dict:
    """The distance policy as data, so a reading can say which one was used."""
    return {
        "on_the_line_km": ON_THE_LINE,
        "counts_km": COUNTS,
        "in_range_km": IN_RANGE,
        "measured": "on the ground, not in degrees of longitude",
        "why": ("a degree of longitude in Oslo is half what it is in Nairobi, "
                "so a rule written in degrees quietly favours the tropics"),
        "status": "mine, not the astrologer's — on her review list",
    }
