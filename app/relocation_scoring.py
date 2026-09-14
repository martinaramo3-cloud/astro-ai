"""Scoring a relocated chart for a purpose.

Martina's tables, not mine. The astronomy — where the angles fall for a given
place at a given moment — has a right answer and lives in relocation_service.
What makes one chart *better than another for money* is astrology, and every
number below came from an astrologer.

Built as a framework because the same machinery answers "where should I be for
my career" or "for love" with nothing changed but a table. Money is complete;
the other purposes carry their house buckets and are marked as awaiting their
scoring, because inventing them would be inventing astrology.

How the pieces combine:
  * Each money house scores the planets sitting in it.
  * Those house scores are weighted against each other — income counts for
    more than shared money.
  * Planets on the angles score separately, because an angle is not a house.
  * The rulers of those houses score separately again, since where a house's
    ruler lands says more than which planets happen to sit in it.
"""
from __future__ import annotations

from app.content_repository import get_sign_rulers


def _ordinal(house: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(house, f"{house}th")

# ── How close counts, and how much ─────────────────────────────────────────
# A sliding scale rather than in-or-out: a planet a quarter-degree off an angle
# and one three degrees off are not the same thing.
ORB_BANDS = ((1.0, 1.00), (2.0, 0.75), (3.0, 0.50), (5.0, 0.20))


def angle_strength(orb: float) -> float:
    for limit, share in ORB_BANDS:
        if orb <= limit:
            return share
    return 0.0


# ── Money ──────────────────────────────────────────────────────────────────
MONEY = {
    "label": "money",
    # What each money house is, and what it is worth relative to the others.
    "houses": {
        2: {"means": "personal income and cashflow", "weight": 0.35},
        10: {"means": "career and status", "weight": 0.30},
        11: {"means": "gains, network and business growth", "weight": 0.25},
        8: {"means": "investments, shared money and funding", "weight": 0.10},
    },
    "planet_in_house": {
        "Jupiter": {2: 5, 11: 5, 10: 4, 8: 3},
        "Venus":   {2: 4, 11: 4, 10: 3, 8: 3},
        "Sun":     {10: 3, 11: 2, 2: 2},
        "Mercury": {2: 2, 10: 2, 11: 2, 8: 1},
        "Mars":    {10: 1, 11: 1, 2: 1, 8: -1},
        # Saturn in the 10th is deliberately not negative: it is as often
        # serious career building, authority and responsibility. Left at zero
        # and meant to be modified by rulership and aspect.
        "Saturn":  {2: -3, 8: -3, 11: -2, 10: 0},
    },
    "planet_on_angle": {
        "Jupiter": {"Midheaven": 6, "Ascendant": 4},
        "Venus":   {"Midheaven": 5, "Ascendant": 4},
        "Sun":     {"Midheaven": 4, "Ascendant": 3},
        "Mercury": {"Midheaven": 3, "Ascendant": 2},
        # Saturn on the Midheaven is not automatically a bad thing either.
        "Saturn":  {"Midheaven": 0, "Ascendant": 0},
    },
    # Where a money house's ruler lands. This is what stops a ranking being
    # merely "who has Jupiter in the 2nd".
    "ruler_lands_in": {
        2: {10: 3, 11: 3},
        10: {2: 3, 11: 3},
        11: {2: 3},
        8: {2: 2, 10: 2},
    },
    "ruler_angular": 2,
    "ruler_with_benefic": 2,
}

# The other purposes: houses agreed, scoring still to come. Listed rather than
# guessed, so nobody mistakes an invention for an astrologer's judgement.
AWAITING_SCORING = {
    "career": (10, 6, 2, 1),
    "love": (7, 5, 8, 1),
    "visibility": (10, 1, 11, 3),
    "social life": (11, 3, 7, 5),
    "study": (9, 3, 6, 10),
    "home and family": (4, 2, 12, 3),
}

PURPOSES = {"money": MONEY}


def _rulers_of(houses: list[dict], planets: list[dict], wanted: set[int]) -> dict[int, dict]:
    """The planet ruling each house, and where that planet ended up."""
    sign_rulers = get_sign_rulers()
    found = {}
    for cusp in houses:
        if cusp["house"] not in wanted:
            continue
        owners = sign_rulers.get(cusp["sign"], [])
        if not owners:
            continue
        ruler = next((p for p in planets if p["planet"] == owners[0]), None)
        if ruler:
            found[cusp["house"]] = ruler
    return found


def score_chart(chart: dict, purpose: str = "money") -> dict:
    """Score one relocated chart, showing the working.

    The breakdown matters as much as the number: a ranking nobody can check is
    a ranking nobody should trust, and the reading has to be able to say why
    one city came first.
    """
    table = PURPOSES.get(purpose)
    if not table:
        return {"purpose": purpose, "score": 0.0,
                "note": f"No scoring table for {purpose!r} yet."}

    planets = chart["planets"]
    reasons: list[str] = []

    # 1. Planets sitting in the houses that matter, weighted against each other.
    house_total = 0.0
    per_house = {}
    for house, meta in table["houses"].items():
        raw = 0.0
        for planet in planets:
            points = table["planet_in_house"].get(planet["planet"], {}).get(house)
            if points:
                raw += points
                reasons.append(f"{planet['planet']} in the {_ordinal(house)} ({meta['means']}) {points:+g}")
        per_house[house] = raw
        house_total += raw * meta["weight"]

    # 2. Planets on an angle, scored by how close they are.
    angle_total = 0.0
    for hit in chart["angular_planets"]:
        points = table["planet_on_angle"].get(hit["planet"], {}).get(hit["angle"])
        if not points:
            continue
        share = angle_strength(hit["orb"])
        if not share:
            continue
        earned = points * share
        angle_total += earned
        reasons.append(
            f"{hit['planet']} on the {hit['angle']} at {hit['orb']:.1f}deg {earned:+.1f}"
        )

    # 3. Where the rulers of those houses landed.
    ruler_total = 0.0
    rulers = _rulers_of(chart["houses"], planets, set(table["houses"]))
    angles = {a["planet"] for a in chart["angular_planets"] if angle_strength(a["orb"])}
    benefics = {p["planet"]: p["house"] for p in planets if p["planet"] in ("Jupiter", "Venus")}

    for house, ruler in rulers.items():
        landed = ruler.get("house")
        points = table["ruler_lands_in"].get(house, {}).get(landed)
        if points:
            ruler_total += points
            reasons.append(f"ruler of the {_ordinal(house)} ({ruler['planet']}) in the {_ordinal(landed)} {points:+g}")
        if ruler["planet"] in angles:
            ruler_total += table["ruler_angular"]
            reasons.append(f"ruler of the {_ordinal(house)} ({ruler['planet']}) on an angle +{table['ruler_angular']}")
        if landed and landed in benefics.values() and ruler["planet"] not in ("Jupiter", "Venus"):
            ruler_total += table["ruler_with_benefic"]
            reasons.append(f"ruler of the {_ordinal(house)} with Jupiter or Venus +{table['ruler_with_benefic']}")

    return {
        "purpose": purpose,
        "score": round(house_total + angle_total + ruler_total, 2),
        "from_houses": round(house_total, 2),
        "from_angles": round(angle_total, 2),
        "from_rulers": round(ruler_total, 2),
        "house_detail": {_ordinal(h): round(v, 1) for h, v in per_house.items()},
        "why": reasons,
    }
