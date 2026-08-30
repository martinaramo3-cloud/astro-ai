"""Structural read of a natal chart.

The raw chart says where every planet is. This says what that arrangement
*means structurally* — which planet runs the chart, which placements work
easily and which struggle, what dominates, and how the pieces group into
recognisable patterns. These are the things a working astrologer notices
before saying anything, and without them interpretation stays generic.
"""
from __future__ import annotations

import math
from collections import Counter

import swisseph as swe

from app.astrology_engine import get_zodiac_sign
from app.content_repository import get_dignities, get_sign_rulers, get_signs

ANGULAR_HOUSES = {1, 4, 7, 10}
SUCCEDENT_HOUSES = {2, 5, 8, 11}

PERSONAL_PLANETS = {"Sun", "Moon", "Mercury", "Venus", "Mars"}

# Every house has a ruler, but sending all twelve is mostly noise. These are
# the houses that actually bear on each kind of question; house 1 is always
# included because it describes the person asking.
HOUSES_BY_QUESTION_TYPE = {
    "relationship": [1, 5, 7, 8],
    "compatibility": [1, 5, 7, 8],
    "career": [1, 2, 6, 10],
    "emotional": [1, 4, 8, 12],
    "general": [1, 4, 7, 10],
}

# How close to an angle a planet must sit to count as dominating the chart.
CONJUNCT_ANGLE_ORB = 8.0


def _separation(a: float, b: float) -> float:
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def _find(planets: list, name: str) -> dict | None:
    return next((p for p in planets if p["planet"] == name), None)


def get_lunar_nodes(utc_dt) -> dict:
    """North and South Node — growth edge and comfort zone.

    Computed separately from the planets so the chart wheel and aspect list
    keep their existing shape.
    """
    jd = swe.julday(
        utc_dt.year, utc_dt.month, utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600,
    )
    north = swe.calc_ut(jd, swe.TRUE_NODE)[0][0] % 360
    south = (north + 180) % 360
    return {
        "north_node": {
            "degree": round(north, 2),
            "sign": get_zodiac_sign(north),
            "degree_in_sign": round(north % 30, 2),
        },
        "south_node": {
            "degree": round(south, 2),
            "sign": get_zodiac_sign(south),
            "degree_in_sign": round(south % 30, 2),
        },
    }


def get_dignity(planet_name: str, sign: str) -> str | None:
    """domicile / exaltation / detriment / fall, or None if neutral."""
    entry = get_dignities().get(planet_name)
    if not entry:
        return None
    for state in ("domicile", "exaltation", "detriment", "fall"):
        if sign in entry.get(state, []):
            return state
    return None


def get_sect(planets: list, houses: list) -> dict:
    """Day or night chart.

    Sect decides which planets behave as the helpful ones: by day Jupiter is
    the stronger benefic and Saturn the more manageable malefic; by night it
    flips to Venus and Mars. It changes the tone of a whole reading.
    """
    sun = _find(planets, "Sun")
    if not sun or not sun.get("house"):
        return {}

    # Houses 7-12 sit above the horizon, so the Sun there means daytime.
    is_day = sun["house"] >= 7
    return {
        "chart_sect": "day" if is_day else "night",
        "benefic_of_sect": "Jupiter" if is_day else "Venus",
        "malefic_of_sect": "Saturn" if is_day else "Mars",
        "note": (
            "In a day chart Jupiter helps most and Saturn is the harsher test; "
            "in a night chart Venus helps most and Mars is the harsher test."
            if is_day else
            "In a night chart Venus helps most and Mars is the harsher test; "
            "Saturn is comparatively easier to work with."
        ),
    }


def get_chart_ruler(ascendant: dict, planets: list) -> dict | None:
    """The planet ruling the Ascendant — how this person moves through life."""
    rulers = get_sign_rulers().get(ascendant["sign"], [])
    if not rulers:
        return None

    # Traditional ruler is listed first and is the one this technique uses.
    ruler_name = rulers[0]
    ruler = _find(planets, ruler_name)
    if not ruler:
        return None

    return {
        "planet": ruler_name,
        "ascendant_sign": ascendant["sign"],
        "sign": ruler["sign"],
        "house": ruler["house"],
        "retrograde": ruler.get("retrograde", False),
        "dignity": get_dignity(ruler_name, ruler["sign"]),
    }


def get_house_rulers(houses: list, planets: list) -> list[dict]:
    """Where each house's ruler landed.

    This is what turns vague statements into specific ones: a 7th-house ruler
    sitting in the 12th says something concrete about that person's
    relationships that "Venus in Scorpio" alone does not.
    """
    sign_rulers = get_sign_rulers()
    results = []

    for cusp in houses:
        rulers = sign_rulers.get(cusp["sign"], [])
        if not rulers:
            continue
        ruler_name = rulers[0]
        ruler = _find(planets, ruler_name)
        if not ruler:
            continue
        results.append({
            "house": cusp["house"],
            "cusp_sign": cusp["sign"],
            "ruler": ruler_name,
            "ruler_in_sign": ruler["sign"],
            "ruler_in_house": ruler["house"],
            "ruler_dignity": get_dignity(ruler_name, ruler["sign"]),
        })

    return results


def get_angularity(planets: list, ascendant: dict, houses: list) -> dict:
    """Which planets dominate the chart by position rather than by sign."""
    angular, cadent, on_angles = [], [], []

    mc = next((h for h in houses if h["house"] == 10), None)
    angle_points = {"Ascendant": ascendant["degree"]}
    if mc:
        angle_points["Midheaven"] = mc["degree"]

    for planet in planets:
        house = planet.get("house")
        if house in ANGULAR_HOUSES:
            angular.append(planet["planet"])
        elif house and house not in SUCCEDENT_HOUSES:
            cadent.append(planet["planet"])

        for angle_name, angle_degree in angle_points.items():
            orb = _separation(planet["degree"], angle_degree)
            if orb <= CONJUNCT_ANGLE_ORB:
                on_angles.append({
                    "planet": planet["planet"],
                    "angle": angle_name,
                    "orb": round(orb, 2),
                })

    return {
        "angular_planets": angular,
        "cadent_planets": cadent,
        "conjunct_angles": sorted(on_angles, key=lambda x: x["orb"]),
        "midheaven": (
            {"degree": mc["degree"], "sign": mc["sign"]} if mc else None
        ),
    }


def get_balance(planets: list) -> dict:
    """Element and modality distribution.

    A chart with no earth reads very differently from one loaded with it —
    this is where "big vision, weak follow-through" actually comes from.
    """
    signs = get_signs()
    elements: Counter = Counter()
    modalities: Counter = Counter()

    for planet in planets:
        meta = signs.get(planet["sign"])
        if not meta:
            continue
        elements[meta["element"]] += 1
        modalities[meta["modality"]] += 1

    missing = [e for e in ("Fire", "Earth", "Air", "Water") if not elements.get(e)]
    dominant = elements.most_common(1)[0][0] if elements else None

    return {
        "elements": dict(elements),
        "modalities": dict(modalities),
        "dominant_element": dominant,
        "missing_elements": missing,
    }


def get_moon_phase_at_birth(planets: list) -> dict | None:
    """Natal lunation phase — a real temperament layer."""
    sun, moon = _find(planets, "Sun"), _find(planets, "Moon")
    if not sun or not moon:
        return None

    angle = (moon["degree"] - sun["degree"]) % 360
    names = [
        (0, "New Moon"), (45, "Waxing Crescent"), (90, "First Quarter"),
        (135, "Waxing Gibbous"), (180, "Full Moon"), (225, "Waning Gibbous"),
        (270, "Last Quarter"), (315, "Waning Crescent"),
    ]
    name = min(names, key=lambda n: abs(((angle - n[0] + 180) % 360) - 180))[1]
    return {
        "phase": name,
        "angle": round(angle, 2),
        "illumination": round((1 - math.cos(math.radians(angle))) / 2, 3),
    }


def get_aspect_patterns(aspects: list, planets: list) -> list[dict]:
    """Recognisable configurations — the shapes astrologers read first."""
    patterns: list[dict] = []

    # Stellium: three or more planets crowded into one sign or one house.
    by_sign: dict[str, list[str]] = {}
    by_house: dict[int, list[str]] = {}
    for planet in planets:
        by_sign.setdefault(planet["sign"], []).append(planet["planet"])
        if planet.get("house"):
            by_house.setdefault(planet["house"], []).append(planet["planet"])

    for sign, names in by_sign.items():
        if len(names) >= 3:
            patterns.append({"pattern": "stellium", "in": f"{sign}", "planets": names})
    for house, names in by_house.items():
        if len(names) >= 3:
            patterns.append({"pattern": "stellium", "in": f"house {house}", "planets": names})

    # Index the aspect list so pairs can be looked up in either direction.
    linked: dict[tuple[str, str], str] = {}
    for aspect in aspects:
        a, b = aspect["planet_1"], aspect["planet_2"]
        linked[(a, b)] = aspect["aspect"]
        linked[(b, a)] = aspect["aspect"]

    def relation(a: str, b: str) -> str | None:
        return linked.get((a, b))

    names_list = [p["planet"] for p in planets]

    # T-square: two planets in opposition, both square a third.
    for aspect in aspects:
        if aspect["aspect"] != "opposition":
            continue
        a, b = aspect["planet_1"], aspect["planet_2"]
        for c in names_list:
            if c in (a, b):
                continue
            if relation(a, c) == "square" and relation(b, c) == "square":
                entry = {
                    "pattern": "t-square",
                    "opposition": [a, b],
                    "apex": c,
                    "note": "Tension between the opposition discharges through the apex planet.",
                }
                if entry not in patterns:
                    patterns.append(entry)

    # Grand trine: three planets mutually trine.
    for i, a in enumerate(names_list):
        for b in names_list[i + 1:]:
            if relation(a, b) != "trine":
                continue
            for c in names_list:
                if c in (a, b):
                    continue
                if relation(a, c) == "trine" and relation(b, c) == "trine":
                    trio = sorted([a, b, c])
                    entry = {
                        "pattern": "grand trine",
                        "planets": trio,
                        "note": "Natural talent that can go unused because it costs no effort.",
                    }
                    if entry not in patterns:
                        patterns.append(entry)

    return patterns


def _relevant_house_rulers(
    houses: list, planets: list, question_type: str | None
) -> list[dict]:
    rulers = get_house_rulers(houses, planets)
    if question_type is None:
        return rulers
    wanted = HOUSES_BY_QUESTION_TYPE.get(question_type)
    if not wanted:
        return rulers
    return [r for r in rulers if r["house"] in wanted]


def build_chart_analysis(
    planets: list,
    ascendant: dict,
    houses: list,
    aspects: list,
    utc_dt=None,
    question_type: str | None = None,
) -> dict:
    """Everything above, assembled for the interpreter.

    `question_type` trims the house rulers to the ones that bear on what was
    actually asked, which is most of the size of this payload.
    """
    dignities = [
        {
            "planet": p["planet"],
            "sign": p["sign"],
            "dignity": get_dignity(p["planet"], p["sign"]),
        }
        for p in planets
        if get_dignity(p["planet"], p["sign"])
    ]

    analysis = {
        "chart_ruler": get_chart_ruler(ascendant, planets),
        "sect": get_sect(planets, houses),
        "dignities": dignities,
        "angularity": get_angularity(planets, ascendant, houses),
        "balance": get_balance(planets),
        "moon_phase_at_birth": get_moon_phase_at_birth(planets),
        "aspect_patterns": get_aspect_patterns(aspects, planets),
        "house_rulers": _relevant_house_rulers(houses, planets, question_type),
        "retrograde_at_birth": [
            p["planet"] for p in planets if p.get("retrograde")
        ],
    }

    if utc_dt is not None:
        analysis["lunar_nodes"] = get_lunar_nodes(utc_dt)

    return analysis
