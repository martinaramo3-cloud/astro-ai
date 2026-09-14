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

# ── The other purposes ─────────────────────────────────────────────────────
# IMPORTANT: the money table above is Martina's, number for number. These six
# are mine, built by analogy from hers and from standard house meanings at her
# request, and they are drafts until an astrologer has read them. Each follows
# her structure and her two principles: Saturn is not automatically punished
# where discipline is the point, and the rulers matter as much as the tenants.
#
# One departure worth flagging. Her angle table scores only the Midheaven and
# the Ascendant. For love the Descendant is the relationship angle and for home
# the IC is the home angle, so both are scored here — if that is wrong, they
# are one line each to remove.

CAREER = {
    "label": "career",
    "houses": {
        10: {"means": "career, status and reputation", "weight": 0.40},
        6: {"means": "daily work and craft", "weight": 0.25},
        1: {"means": "how you come across", "weight": 0.20},
        2: {"means": "what the work earns", "weight": 0.15},
    },
    "planet_in_house": {
        "Sun":     {10: 5, 1: 4, 6: 2, 2: 2},
        "Jupiter": {10: 5, 1: 4, 6: 3, 2: 3},
        "Mercury": {6: 3, 10: 3, 1: 2, 2: 2},
        "Venus":   {10: 3, 1: 3, 6: 2, 2: 2},
        "Mars":    {10: 2, 6: 2, 1: 2, 2: 1},
        # The one place Saturn is an asset rather than a cost: building
        # something slowly and being trusted with it is what a career is.
        "Saturn":  {10: 1, 6: 1, 1: -2, 2: -2},
    },
    "planet_on_angle": {
        "Sun":     {"Midheaven": 6, "Ascendant": 4},
        "Jupiter": {"Midheaven": 6, "Ascendant": 4},
        "Mercury": {"Midheaven": 4, "Ascendant": 3},
        "Venus":   {"Midheaven": 4, "Ascendant": 3},
        "Mars":    {"Midheaven": 3, "Ascendant": 2},
        "Saturn":  {"Midheaven": 2, "Ascendant": 0},
    },
    "ruler_lands_in": {10: {1: 3, 2: 3, 6: 3}, 6: {10: 3}, 1: {10: 3}, 2: {10: 2}},
    "ruler_angular": 2,
    "ruler_with_benefic": 2,
}

LOVE = {
    "label": "love",
    "houses": {
        7: {"means": "partnership and who you meet", "weight": 0.40},
        5: {"means": "romance, play and being wanted", "weight": 0.30},
        8: {"means": "intimacy and depth", "weight": 0.20},
        1: {"means": "how you arrive to someone", "weight": 0.10},
    },
    "planet_in_house": {
        "Venus":   {7: 6, 5: 5, 8: 4, 1: 4},
        "Jupiter": {7: 5, 5: 4, 8: 3, 1: 3},
        "Moon":    {7: 3, 5: 3, 8: 3, 1: 2},
        "Sun":     {5: 3, 7: 3, 1: 3, 8: 1},
        "Mercury": {7: 2, 5: 2, 1: 1, 8: 1},
        # Desire and pursuit in the houses of wanting; friction in the house of
        # partnership, where it mostly shows up as argument.
        "Mars":    {5: 2, 8: 2, 1: 1, 7: 0},
        # Saturn in the 7th is not simply bad — it is also commitment and
        # seriousness — so it is only lightly marked down there, and heavily
        # in the house of play, which it genuinely flattens.
        "Saturn":  {5: -3, 8: -2, 1: -2, 7: -1},
    },
    "planet_on_angle": {
        "Venus":   {"Ascendant": 6, "Descendant": 6, "Midheaven": 3},
        "Jupiter": {"Ascendant": 5, "Descendant": 5, "Midheaven": 3},
        "Sun":     {"Ascendant": 4, "Descendant": 3, "Midheaven": 3},
        "Moon":    {"Descendant": 4, "Ascendant": 3},
        "Mars":    {"Descendant": 1, "Ascendant": 2},
        "Saturn":  {"Ascendant": 0, "Descendant": 0},
    },
    "ruler_lands_in": {7: {5: 3, 1: 3}, 5: {7: 3}, 1: {7: 3, 5: 3}, 8: {7: 2}},
    "ruler_angular": 2,
    "ruler_with_benefic": 2,
}

VISIBILITY = {
    "label": "visibility",
    "houses": {
        10: {"means": "public standing", "weight": 0.35},
        1: {"means": "presence and how you read", "weight": 0.30},
        11: {"means": "audience and network", "weight": 0.20},
        3: {"means": "voice and reach", "weight": 0.15},
    },
    "planet_in_house": {
        "Sun":     {10: 6, 1: 5, 11: 3, 3: 2},
        "Jupiter": {10: 5, 1: 5, 11: 4, 3: 3},
        "Mercury": {3: 4, 10: 3, 1: 3, 11: 3},
        "Venus":   {1: 4, 10: 3, 11: 3, 3: 2},
        "Mars":    {1: 3, 10: 2, 3: 2, 11: 1},
        "Saturn":  {1: -2, 3: -2, 11: -2, 10: 0},
    },
    "planet_on_angle": {
        "Sun":     {"Midheaven": 6, "Ascendant": 6},
        "Jupiter": {"Midheaven": 5, "Ascendant": 5},
        "Mercury": {"Midheaven": 4, "Ascendant": 4},
        "Venus":   {"Ascendant": 4, "Midheaven": 3},
        "Mars":    {"Ascendant": 3, "Midheaven": 2},
        "Saturn":  {"Midheaven": 0, "Ascendant": 0},
    },
    "ruler_lands_in": {10: {1: 3, 11: 3}, 1: {10: 3, 11: 3}, 11: {10: 3}, 3: {10: 2, 1: 2}},
    "ruler_angular": 2,
    "ruler_with_benefic": 2,
}

SOCIAL = {
    "label": "social life",
    "houses": {
        11: {"means": "friends, groups and belonging", "weight": 0.35},
        3: {"means": "everyday company and talk", "weight": 0.25},
        5: {"means": "fun and going out", "weight": 0.20},
        7: {"means": "the close one-to-one ones", "weight": 0.20},
    },
    "planet_in_house": {
        "Jupiter": {11: 5, 3: 4, 5: 4, 7: 3},
        "Venus":   {11: 4, 5: 4, 7: 3, 3: 3},
        "Mercury": {3: 4, 11: 3, 7: 2, 5: 2},
        "Sun":     {11: 3, 5: 3, 3: 2, 7: 2},
        "Moon":    {11: 2, 3: 2, 5: 2, 7: 2},
        "Mars":    {5: 2, 11: 1, 3: 1, 7: 0},
        # The one that genuinely empties a room, and a calendar.
        "Saturn":  {11: -3, 3: -2, 5: -2, 7: -1},
    },
    "planet_on_angle": {
        "Jupiter": {"Ascendant": 5, "Midheaven": 4},
        "Venus":   {"Ascendant": 5, "Midheaven": 3},
        "Mercury": {"Ascendant": 3, "Midheaven": 3},
        "Sun":     {"Ascendant": 3, "Midheaven": 3},
        "Saturn":  {"Ascendant": 0, "Midheaven": 0},
    },
    "ruler_lands_in": {11: {3: 3, 5: 3}, 3: {11: 3}, 5: {11: 3}, 7: {11: 2}},
    "ruler_angular": 2,
    "ruler_with_benefic": 2,
}

STUDY = {
    "label": "study",
    "houses": {
        9: {"means": "higher study and what widens you", "weight": 0.35},
        3: {"means": "learning, reading and thinking", "weight": 0.30},
        6: {"means": "the discipline to keep at it", "weight": 0.20},
        10: {"means": "what it qualifies you for", "weight": 0.15},
    },
    "planet_in_house": {
        "Mercury": {3: 5, 9: 4, 6: 3, 10: 2},
        "Jupiter": {9: 5, 3: 4, 10: 3, 6: 2},
        "Sun":     {9: 3, 10: 3, 3: 2, 6: 2},
        "Venus":   {9: 2, 3: 2, 6: 2, 10: 2},
        "Mars":    {6: 2, 3: 2, 9: 1, 10: 1},
        # Sitting down and doing it for years is Saturn's own work.
        "Saturn":  {9: 1, 6: 1, 3: -1, 10: 0},
    },
    "planet_on_angle": {
        "Jupiter": {"Midheaven": 5, "Ascendant": 4},
        "Mercury": {"Midheaven": 4, "Ascendant": 4},
        "Sun":     {"Midheaven": 3, "Ascendant": 3},
        "Venus":   {"Midheaven": 2, "Ascendant": 2},
        "Saturn":  {"Midheaven": 1, "Ascendant": 0},
    },
    "ruler_lands_in": {9: {3: 3, 10: 3}, 3: {9: 3}, 6: {9: 2, 3: 2}, 10: {9: 2}},
    "ruler_angular": 2,
    "ruler_with_benefic": 2,
}

HOME = {
    "label": "home and family",
    "houses": {
        4: {"means": "home, roots and family", "weight": 0.45},
        2: {"means": "what it costs and what it is built on", "weight": 0.20},
        12: {"means": "rest and privacy", "weight": 0.20},
        3: {"means": "neighbourhood and siblings", "weight": 0.15},
    },
    "planet_in_house": {
        "Moon":    {4: 5, 12: 3, 3: 2, 2: 2},
        "Jupiter": {4: 5, 2: 4, 3: 3, 12: 3},
        "Venus":   {4: 5, 2: 3, 3: 2, 12: 2},
        "Sun":     {4: 3, 2: 2, 3: 2, 12: 1},
        "Mercury": {3: 3, 4: 2, 2: 2, 12: 1},
        # Mars at home is the argument in the kitchen.
        "Mars":    {3: 1, 2: 1, 12: -1, 4: -2},
        "Saturn":  {4: -2, 12: -2, 2: -2, 3: -1},
    },
    "planet_on_angle": {
        "Moon":    {"IC": 5, "Ascendant": 3},
        "Venus":   {"IC": 5, "Ascendant": 4},
        "Jupiter": {"IC": 5, "Ascendant": 4},
        "Sun":     {"IC": 3, "Ascendant": 3},
        "Saturn":  {"IC": 0, "Ascendant": 0},
    },
    "ruler_lands_in": {4: {2: 3, 12: 3}, 2: {4: 3}, 12: {4: 2}, 3: {4: 2}},
    "ruler_angular": 2,
    "ruler_with_benefic": 2,
}

PURPOSES = {
    "money": MONEY,
    "career": CAREER,
    "love": LOVE,
    "visibility": VISIBILITY,
    "social life": SOCIAL,
    "study": STUDY,
    "home and family": HOME,
}

# Whose judgement each table carries, so a reading can say so and an astrologer
# knows which ones still need her eye.
BY_AN_ASTROLOGER = {"money"}


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
