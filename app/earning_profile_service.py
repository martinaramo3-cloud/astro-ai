"""How a chart earns — judged before anything the person has told us.

NOT WIRED INTO ANY ANSWER. Built, tested and calibrated; dark until the
co-founder has reviewed the dimensions and the weights. The same arrangement
as `friendship_service`, for the same reason: the mechanism is mine to build
and the astrology is hers to decide.

------------------------------------------------------------------------------
Why this exists at all
------------------------------------------------------------------------------
The brief was: judge the chart first, independently, and rank what it points
at BEFORE looking at what the person studies or does. That is impossible to do
with a prompt instruction, because the memory saying "studies law" arrives in
the same payload as the chart, and an instruction that competes with the data
behind it loses — three separate bugs in this app have now been that.

So the chart gets scored here, in code, with nothing about the person's life
in scope. What comes out is a small ranked reading that an answer can be built
on rather than talked into.

------------------------------------------------------------------------------
What it measures
------------------------------------------------------------------------------
Five spectrums, not five scores. Each has two poles and a chart sits somewhere
between them; a chart near the middle of one is genuinely undecided there, and
saying so is a real answer.

  named or behind        the named person, or the one making it work
  few or many            a few clients paid properly, or reach
  own or others' money   what you make, or what you are trusted with
  judgement or craft     sold as advice, or sold as a thing
  steady or waves        accumulates, or arrives in bursts

Deliberately none of these is "how much". There is no scale on which a chart
says someone will be rich, and building one would be the most attractive lie
in the product.

------------------------------------------------------------------------------
Where the content came from, honestly
------------------------------------------------------------------------------
The house weights in EARNING_HOUSE come from the co-founder's own money table
in `relocation_scoring.py` — the one table in this codebase an astrologer
actually wrote. Everything else below (which houses pull which way, the planet
tilts) is mine, assembled by analogy, and is the part waiting on her review.
It is marked in the output so no answer can ever present it as settled.

Bands are calibrated: `training/area3/distribution.py` scores a thousand
invented charts and writes the percentiles. Guessed thresholds are what put
95.8% of couples in "toxic attraction", and money is not the place to repeat
that.
"""
from __future__ import annotations

import json
import pathlib

from app.chart_analysis_service import get_house_rulers

# Each spectrum's two poles, in the order (positive score, negative score).
POLES: dict[str, tuple[str, str]] = {
    "named_or_behind": ("the named person doing the work",
                        "the one who makes it work, out of view"),
    "few_or_many": ("a few clients, paid properly",
                    "many buyers, at scale"),
    "own_money_or_others": ("money you make yourself",
                            "money other people put in your hands"),
    "judgement_or_craft": ("judgement, sold as advice",
                           "a thing, sold as a product"),
    "steady_or_waves": ("a steady build",
                        "work that arrives in waves"),
}

# Which houses pull a spectrum which way, and how hard. A planet sitting in
# the house, and a house ruler landing in it, both count — the second is what
# stops this being merely "who has Jupiter in the second".
HOUSE_PULL: dict[str, dict[int, float]] = {
    "named_or_behind": {10: 1.0, 1: 0.8, 5: 0.6, 12: -1.0, 6: -0.7, 8: -0.5},
    "few_or_many": {7: 0.9, 8: 0.7, 6: 0.5, 11: -1.0, 9: -0.7, 3: -0.5},
    "own_money_or_others": {2: 1.0, 6: 0.6, 1: 0.4, 8: -1.0, 7: -0.6, 11: -0.5},
    "judgement_or_craft": {9: 0.9, 3: 0.6, 10: 0.5, 6: -0.9, 5: -0.6, 2: -0.4},
    "steady_or_waves": {2: 0.7, 6: 0.8, 10: 0.5, 8: -0.6, 11: -0.6, 9: -0.5},
}

# What a planet adds on its own, and only while it is standing in a house that
# spectrum already cares about. Applied unconditionally these would be
# identical for every chart on earth — everybody has all ten.
PLANET_TILT: dict[str, dict[str, float]] = {
    "named_or_behind": {"Sun": 0.5, "Jupiter": 0.3, "Mars": 0.2,
                        "Neptune": -0.4, "Saturn": -0.2},
    "few_or_many": {"Pluto": 0.4, "Saturn": 0.3, "Jupiter": -0.4, "Uranus": -0.3},
    "own_money_or_others": {"Venus": 0.3, "Mars": 0.2, "Pluto": -0.5, "Neptune": -0.3},
    "judgement_or_craft": {"Mercury": 0.5, "Jupiter": 0.5, "Saturn": 0.4,
                           "Venus": -0.5, "Mars": -0.4},
    "steady_or_waves": {"Saturn": 0.9, "Uranus": -0.9, "Jupiter": -0.4, "Neptune": -0.4},
}

# How loudly each planet speaks about work and money at all. The outer three
# are quiet on purpose: they describe a generation as much as a person.
PLANET_VOICE: dict[str, float] = {
    "Sun": 1.0, "Moon": 0.6, "Mercury": 0.8, "Venus": 0.8, "Mars": 0.8,
    "Jupiter": 1.0, "Saturn": 1.0, "Uranus": 0.5, "Neptune": 0.4, "Pluto": 0.5,
}

# Which houses are about earning, and how much each matters. The first four
# numbers are the co-founder's, lifted from the money table she wrote for the
# city rankings; the 6th and 7th are mine, at low weight, because work done and
# work contracted have to count for something.
EARNING_HOUSE: dict[int, float] = {2: 0.35, 10: 0.30, 11: 0.25, 8: 0.10,
                                   6: 0.15, 7: 0.15}

# A planet this close to the Midheaven or Ascendant is doing its talking in
# public whatever house the maths files it under.
ANGLE_ORB = 8.0

_BANDS_FILE = pathlib.Path(__file__).resolve().parents[1] / "content" / "engine" / "earning_bands.json"


def _bands() -> dict:
    try:
        return json.loads(_BANDS_FILE.read_text())
    except (OSError, ValueError):
        return {}


def _separation(one: float, two: float) -> float:
    gap = abs(one - two) % 360
    return min(gap, 360 - gap)


def _angles(chart: dict) -> dict[str, float]:
    found = {}
    for angle in chart.get("angles") or []:
        if angle.get("planet") in ("Midheaven", "Ascendant"):
            found[angle["planet"]] = angle["degree"]
    if "Ascendant" not in found and isinstance(chart.get("ascendant"), dict):
        found["Ascendant"] = chart["ascendant"].get("degree")
    if "Midheaven" not in found and isinstance(chart.get("midheaven"), dict):
        found["Midheaven"] = chart["midheaven"].get("degree")
    return {name: deg for name, deg in found.items() if isinstance(deg, (int, float))}


def score_earning_profile(chart: dict) -> dict:
    """Score one chart's five spectrums. Nothing about the person goes in."""
    planets = chart.get("planet_positions") or []
    houses = chart.get("houses") or []
    if not planets or len(houses) != 12:
        return {"available": False,
                "reason": "needs a full chart with houses, so a birth time is required"}

    scores = {name: 0.0 for name in POLES}
    evidence: dict[str, list[str]] = {name: [] for name in POLES}
    angles = _angles(chart)

    # 1. Planets, by the house they stand in.
    for planet in planets:
        name, house = planet.get("planet"), planet.get("house")
        if not name or not house:
            continue
        voice = PLANET_VOICE.get(name, 0.0)
        if not voice:
            continue
        # On an angle it speaks louder, and it speaks in public.
        on_angle = next(
            (a for a, degree in angles.items()
             if _separation(planet.get("degree", 0.0), degree) <= ANGLE_ORB),
            None)
        loudness = voice * (1.6 if on_angle else 1.0)
        for spectrum, pull in HOUSE_PULL.items():
            if house not in pull:
                continue
            value = pull[house] * loudness
            value += PLANET_TILT[spectrum].get(name, 0.0) * loudness
            scores[spectrum] += value
            evidence[spectrum].append(
                f"{name} in the {house}th" + (f", on the {on_angle}" if on_angle else ""))
        # No extra push toward "named" for being on an angle. It was there, and
        # it counted the same fact three times — the planet is already in the
        # 10th or 1st, which already pulls that way, and already at 1.6x for
        # being on the angle. The result was a 63/37 skew: the engine told
        # nearly two thirds of all charts they were the visible one, which is
        # how a spectrum quietly stops being a reading.

    # 2. Where the rulers of the earning houses land. This is the half that
    #    describes the route rather than the furniture.
    for record in get_house_rulers(houses, planets):
        ruled, lands_in = record.get("house"), record.get("ruler_in_house")
        if ruled not in EARNING_HOUSE or not lands_in:
            continue
        weight = EARNING_HOUSE[ruled]
        for spectrum, pull in HOUSE_PULL.items():
            if lands_in not in pull:
                continue
            scores[spectrum] += pull[lands_in] * weight * 2.0
            evidence[spectrum].append(
                f"what rules your {ruled}th sits in the {lands_in}th")

    bands = _bands()
    out = {}
    for spectrum, raw in scores.items():
        positive, negative = POLES[spectrum]
        out[spectrum] = {
            "score": round(raw, 2),
            "leans": positive if raw > 0 else negative,
            # How pronounced, against charts in general — not how good.
            "band": _band(spectrum, abs(raw), bands),
            # The same magnitude measured against this spectrum's own spread,
            # so the five can be compared with each other at all.
            "how_decided": round(_relative(spectrum, abs(raw), bands), 2),
            "evidence": sorted(set(evidence[spectrum]))[:4],
        }

    # The ranking is the point: which of the five this chart is most decided
    # about. A chart with nothing pronounced ranks nothing, and that is a
    # truthful outcome rather than a failure.
    #
    # Ranked on the relative figure, never the raw one. The five spectrums do
    # not share a scale — the widest has half again the spread of the
    # narrowest — so sorting by raw score ranked the scale rather than the
    # chart, and "steady or waves" came first for 9% of charts instead of 20%.
    # This is the same mistake that gave every saved person the same dates:
    # sorting by a number that does not discriminate.
    ranked = sorted(out, key=lambda s: out[s]["how_decided"], reverse=True)
    pronounced = [s for s in ranked if out[s]["band"] in ("high", "exceptional")]

    return {
        "available": True,
        "spectrums": out,
        "ranked": ranked,
        "most_pronounced": pronounced,
        "band_meaning": ("how pronounced this lean is among charts in general. "
                         "Not a verdict, and never a quantity of money — there "
                         "is no scale here on which a chart says someone will "
                         "be rich."),
        "weights": "equal within each spectrum — pending the co-founder's review",
        "provenance": ("house weights from the co-founder's money table; the "
                       "pulls and planet tilts assembled by analogy and not yet "
                       "reviewed"),
    }


def _band(spectrum: str, magnitude: float, bands: dict) -> str:
    for step in bands.get(spectrum, []):
        if magnitude <= step["max"]:
            return step["label"]
    return "unbanded"


def _relative(spectrum: str, magnitude: float, bands: dict) -> float:
    """This lean's size as a multiple of a typical lean on the same spectrum.

    1.0 means as decided as the middle chart is about this. Uncalibrated, it
    falls back to the raw magnitude, which is wrong in the way described at
    the call site but is at least not zero.
    """
    typical = next((s["max"] for s in bands.get(spectrum, []) if s["label"] == "typical"), 0)
    return magnitude / typical if typical else magnitude


def describe_profile(profile: dict, limit: int = 3) -> list[str]:
    """The ranked leans as plain sentences. No jargon, no houses, no planets.

    What an answer would be built from, if this were live. It isn't.
    """
    if not profile.get("available"):
        return []
    lines = []
    for spectrum in profile["ranked"][:limit]:
        entry = profile["spectrums"][spectrum]
        if entry["band"] == "low":
            lines.append(f"genuinely undecided between {POLES[spectrum][0]} "
                         f"and {POLES[spectrum][1]}")
        else:
            strength = "strongly" if entry["band"] == "exceptional" else "clearly"
            lines.append(f"{strength} {entry['leans']}")
    return lines
