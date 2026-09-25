"""Friendship as its own reading, on its own axis.

Written from the co-founder's theory document. The single most important idea
in it: friendship and attraction are two separate axes, not two ends of one
scale. Low attraction does not make a pair friends, and high attraction does
not make them a couple. A pair can have excellent conversation and no spark,
powerful chemistry and nothing to talk about, or both at once — and the
engine has to be able to say each of those.

Six dimensions, each read in BOTH directions, because a friendship one person
experiences and the other doesn't is a real and common shape:

  social ease         do they enjoy each other's company
  mental connection   can they talk, and stay curious
  emotional intimacy  can hard feelings be said without being dismissed
  reciprocity         is it the same friendship from both sides
  durability          what carries it through changed circumstances
  conflict and repair what the friction is about, and whether it mends

Equal weights for now. The co-founder adjusts them from the calibration table
rather than in the abstract.

Nothing here decides what a relationship IS. It describes what these two
charts can build, and the person living it knows things no chart contains.
"""
from __future__ import annotations

from app.chart_analysis_service import get_house_rulers
from app.compatibility_service import _bucketize_index

# Which planets speak for each dimension, per her document. A planet can serve
# more than one: Venus is affection in a friendship as much as in a romance.
DIMENSION_PLANETS: dict[str, set[str]] = {
    "social_ease": {"Sun", "Venus", "Jupiter"},
    "mental_connection": {"Mercury"},
    "emotional_intimacy": {"Moon"},
    "durability": {"Saturn", "Mercury", "Jupiter"},
    "conflict_and_repair": {"Mars", "Mercury", "Moon"},
}

# Which of the receiving person's houses a planet landing there speaks for.
DIMENSION_HOUSES: dict[str, set[int]] = {
    "social_ease": {5, 11},
    "mental_connection": {3},
    "emotional_intimacy": {4, 8, 12},
    "durability": {7, 11},
    "conflict_and_repair": set(),
}

# Whose experience a contact lands on. Someone's Moon met by another's Saturn
# feels it far more than the Saturn person does.
PERSONAL = {"Sun", "Moon", "Mercury", "Venus", "Mars"}
HEAVY = {"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "Chiron"}

EASY = {"trine", "sextile", "conjunction"}
HARD = {"square", "opposition"}

# A contact is worth more the closer it is. Nothing here is a verdict — an
# aspect's closeness says how strongly the interaction operates, not whether
# it is pleasant.
def _closeness(orb: float | None) -> float:
    if orb is None:
        return 0.3
    return max(0.15, 1.0 - (orb / 8.0))


def _friendship_houses(chart: dict) -> dict[str, list[int]]:
    """Which houses each planet rules, so the 11th's RULER can be followed.

    Counting planets sitting in the 11th is the crude version her document
    warns about. What matters is the ruler of that house and where it goes.
    """
    houses, planets = chart.get("houses") or [], chart.get("planet_positions") or []
    if len(houses) != 12:
        return {}
    rules: dict[str, list[int]] = {}
    for record in get_house_rulers(houses, planets):
        rules.setdefault(record["ruler"], []).append(record["house"])
    return rules


def score_friendship(person_1_chart: dict, person_2_chart: dict,
                     synastry_aspects: list[dict],
                     overlays: list[dict] | None = None) -> dict:
    """The six dimensions, each scored from both sides."""
    rules_1 = _friendship_houses(person_1_chart)
    rules_2 = _friendship_houses(person_2_chart)

    dimensions = {name: {"toward_1": 0.0, "toward_2": 0.0, "evidence": []}
                  for name in DIMENSION_PLANETS}

    for contact in synastry_aspects or []:
        p1, p2 = contact.get("person_1_planet"), contact.get("person_2_planet")
        aspect, orb = contact.get("aspect"), contact.get("orb")
        if not p1 or not p2:
            continue
        weight = _closeness(orb)
        # An 11th-house ruler carries extra weight: a contact to it reaches
        # that person's own pattern of friendship, not just a planet.
        if 11 in rules_1.get(p1, []):
            weight *= 1.4
        if 11 in rules_2.get(p2, []):
            weight *= 1.4

        for name, planets in DIMENSION_PLANETS.items():
            if p1 not in planets and p2 not in planets:
                continue
            if name == "conflict_and_repair":
                # This dimension measures friction and whether it mends, so a
                # hard aspect raises it and an easy one is the repair.
                value = weight if aspect in HARD else -0.4 * weight
            elif aspect in EASY:
                value = weight
            elif aspect in HARD:
                # Tension is not failure. It costs a dimension something, but
                # far less than ease adds — two people who argue about how they
                # talk still talk.
                value = -0.5 * weight
            else:
                continue
            # Direction. A synastry aspect is one aspect, so splitting it
            # evenly made reciprocity exactly zero for every pair on earth.
            # The real asymmetry is who is being acted upon: when one person's
            # personal planet is met by the other's heavy one, the personal
            # side is the one who feels it. That is what makes a friendship
            # one person is inside and the other is merely near.
            toward_1, toward_2 = value, value
            if p1 in PERSONAL and p2 in HEAVY:
                toward_1, toward_2 = value, value * 0.5
            elif p2 in PERSONAL and p1 in HEAVY:
                toward_1, toward_2 = value * 0.5, value
            dimensions[name]["toward_1"] += toward_1
            dimensions[name]["toward_2"] += toward_2
            dimensions[name]["evidence"].append(
                f"{p1} {aspect} {p2}" + (f" ({orb:.1f}°)" if orb is not None else ""))

    # Overlays are directional and need the receiving chart's birth time.
    for overlay in overlays or []:
        house = overlay.get("house")
        direction = overlay.get("direction", "")
        if not house:
            continue
        toward = "toward_2" if direction == "person_1_to_person_2" else "toward_1"
        for name, houses in DIMENSION_HOUSES.items():
            if house in houses:
                dimensions[name][toward] += 0.8
                dimensions[name]["evidence"].append(
                    f"{overlay.get('planet')} in their {house}th")

    scored = {}
    for name, parts in dimensions.items():
        both = (parts["toward_1"] + parts["toward_2"]) / 2
        # How lopsided it is. One person feeling a friendship the other does
        # not is the thing reciprocity exists to notice.
        gap = abs(parts["toward_1"] - parts["toward_2"])
        scored[name] = {"score": round(both, 2), "imbalance": round(gap, 2),
                        "evidence": parts["evidence"][:4]}

    # Reciprocity is not scored from its own planets — it is how evenly the
    # other five land on each side.
    # Scored so that even is good: a friendship both people are equally inside
    # scores near zero, and a lopsided one goes negative.
    imbalance = sum(d["imbalance"] for d in scored.values()) / max(len(scored), 1)
    scored["reciprocity"] = {
        "score": round(-imbalance, 2),
        "imbalance": round(imbalance, 2),
        "evidence": ["measured from how evenly the other dimensions fall on each side"],
    }

    overall = round(sum(d["score"] for d in scored.values()) / len(scored), 2)
    return {
        "dimensions": scored,
        "friendship_score": overall,
        "friendship_band": _bucketize_index("friendship", overall),
        "weights": "equal — pending review",
        "note": (
            "Friendship on its own axis, not the opposite of attraction. Six "
            "dimensions from the theory document, each read in both directions. "
            "House overlays are included only where the receiving chart has a "
            "birth time. Nothing here decides what the relationship IS; it "
            "describes what these two could build, and the person living it "
            "knows things no chart contains."
        ),
    }


def describe_lean(friendship_score: float, friendship_band: str,
                  attraction_band: str) -> dict:
    """Where this pair sits on two axes at once.

    Deliberately not a single friendship-to-romance slider. The four shapes
    below are the ones her document names, and "mixed" is a real answer rather
    than a failure to decide.
    """
    strong_friend = friendship_band in ("high", "exceptional")
    strong_pull = attraction_band in ("high", "exceptional")
    weak_friend = friendship_band == "low"
    weak_pull = attraction_band == "low"

    if strong_friend and weak_pull:
        lean = "a friendship, with little romantic emphasis"
    elif strong_friend and strong_pull:
        lean = "a friendship that also carries attraction"
    elif strong_pull and weak_friend:
        lean = "strong attraction on a thin friendship base"
    elif strong_friend:
        lean = "mostly a friendship, with some pull"
    elif strong_pull:
        lean = "mostly attraction, with a workable friendship"
    else:
        lean = "mixed — the charts alone do not settle what this is"
    return {
        "lean": lean,
        "friendship_band": friendship_band,
        "attraction_band": attraction_band,
        "caution": (
            "Two axes, not one scale. Low attraction does not make people "
            "friends and high attraction does not make them a couple. The "
            "charts cannot establish anyone's orientation, intentions or "
            "choices — where the user knows the real situation, that wins."
        ),
    }
