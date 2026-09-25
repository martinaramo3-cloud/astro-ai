"""What the work itself is: activities, responsibilities, subject matter.

Section 2 of the co-founder's rules, and a different question from how someone
earns. A person can be paid by an employer or by clients — that is the earning
route — while the work in either case is teaching, or building, or research.
The two rankings are separate on purpose and are produced separately here.

LIVE since 25 September 2026, through `career_reading_service`.

Her weighting, in her order: the MC and its ruler first, then the 10th ruler,
then repeated connections between those factors and other planets or houses.
The 6th describes daily tasks and working conditions and does not by itself
define a career, which here is a rule and not a preference: a theme supported
only by 6th-house evidence cannot be called strong however much of it there is.

------------------------------------------------------------------------------
Two things in this file are MINE and she should overrule them if she disagrees
------------------------------------------------------------------------------
1. The theme vocabulary. Her document says to identify themes without listing
   what they may be, so the ten below are keyed on the planets, because a
   planet is the thing in a chart that says what KIND of work something is.
   Each carries activities, responsibilities and setting, as her section 2
   asks for.

2. Under Placidus the Midheaven IS the 10th cusp, so "the MC ruler" and "the
   10th ruler" are always the same planet in this app. Her document names them
   as two factors, which they are under whole-sign houses. They are counted
   ONCE here, per her rule about not counting the same thing twice — but if
   she meant them to be two, that is a house-system decision and hers.
"""
from __future__ import annotations

import bisect
import json
import pathlib

from app.angle_aspects_service import get_angle_aspects
from app.chart_analysis_service import get_house_rulers
from app.natal_career_data import _aspects_between
from app.orb_policy import exactness, within_orb

# MINE: the vocabulary. Ten themes, one per planet, each written as the work
# rather than as the symbol.
THEMES: dict[str, dict] = {
    "Mercury": {
        "label": "Communication, analysis and information",
        "work": ("Writing, teaching, explaining, analysing, trading, "
                 "brokering, anything where the product is clarity"),
        "plain": "work built on explaining and analysing",
    },
    "Venus": {
        "label": "Design, value and relationships",
        "work": ("Aesthetics, design, mediation, negotiation, hospitality, "
                 "anything where judgement about worth or taste is the skill"),
        "plain": "work built on taste and judgement about value",
    },
    "Mars": {
        "label": "Building, technical work and competition",
        "work": ("Engineering, surgery, trades, sport, operations under "
                 "pressure, anything where execution and nerve decide it"),
        "plain": "hands-on work where execution decides it",
    },
    "Jupiter": {
        "label": "Teaching, law and advice",
        "work": ("Education, law, publishing, consulting, travel, "
                 "anything that widens what other people can see or do"),
        "plain": "work built on expertise other people come to you for",
    },
    "Saturn": {
        "label": "Structure, institutions and long-term building",
        "work": ("Administration, law, finance, architecture, craft, "
                 "anything that rewards patience and accumulates authority"),
        "plain": "work that builds slowly and holds its shape",
    },
    "Sun": {
        "label": "Leadership and being the named person",
        "work": ("Directing, performing, representing, founding, anything "
                 "where a person rather than a process carries the work"),
        "plain": "work where you are the one out in front",
    },
    "Moon": {
        "label": "Care, the public and everyday rhythm",
        "work": ("Care, health, food, housing, community, anything serving "
                 "a public whose needs repeat"),
        "plain": "work looking after people and what they need",
    },
    "Uranus": {
        "label": "Technology, reform and independence",
        "work": ("Software, invention, research and development, activism, "
                 "anything that changes how a thing is done"),
        "plain": "work that changes how something is done",
    },
    "Neptune": {
        "label": "Image, art and service",
        "work": ("Film, music, photography, therapy, charity, anything "
                 "working with what cannot be measured directly"),
        "plain": "work with images, feeling or care",
    },
    "Pluto": {
        "label": "Research, depth and what is hidden",
        "work": ("Investigation, psychology, finance, crisis work, surgery, "
                 "anything that goes where other people would rather not"),
        "plain": "work that goes deep into difficult things",
    },
}

POINTS = {
    "rules_the_mc": 5,        # the MC / 10th ruler itself
    "aspects_the_mc": 4,      # a close aspect to the career point
    "aspects_the_ruler": 4,   # a close aspect to the MC ruler
    "in_the_tenth": 3,        # standing in the house of the career
    "daily_work": 2,          # in the 6th — conditions, not the career
    "symbolism": 1,
}
SYMBOLISM_CAP = 1

# The same evidence without a planet or a house in it.
PLAIN_REASON = {
    "rules_the_mc": "this governs the part of your chart that carries your work",
    "aspects_the_mc": "it makes close contact with the point that carries your work",
    "aspects_the_ruler": "it is closely tied to whatever governs your work",
    "in_the_tenth": "it sits in the part of the chart the career belongs to",
    "daily_work": "it shows up in how your days are actually spent, which "
                  "describes conditions rather than the career itself",
    "symbolism": "the symbolism leans this way, which on its own is thin",
}
# Her rule: the 6th does not by itself define the career.
CANNOT_ESTABLISH = {"daily_work", "symbolism"}

_BANDS_FILE = (pathlib.Path(__file__).resolve().parents[1]
               / "content" / "engine" / "theme_bands.json")


def _distributions() -> dict:
    try:
        return json.loads(_BANDS_FILE.read_text())
    except (OSError, ValueError):
        return {}


def _how_unusual(planet: str, score: float, spread: dict) -> float:
    values = spread.get(planet)
    if not values:
        return 0.5
    return bisect.bisect_left(values, score) / len(values)


def score_professional_themes(chart: dict) -> dict:
    """The top one to three themes in the work itself.

    Nothing about the person's education, job or plans is an argument here,
    which is how her rule about biography never becoming chart evidence is
    kept rather than remembered.
    """
    planets = chart.get("planet_positions") or []
    houses = chart.get("houses") or []
    if not planets or len(houses) != 12 or not chart.get("birth_time_known", True):
        return {"available": False,
                "reason": ("the Midheaven and the houses need a reliable birth "
                           "time, and her rules forbid a house-, Ascendant- or "
                           "MC-based claim without one")}

    rulers = {r["house"]: r for r in get_house_rulers(houses, planets)}
    mc_ruler = rulers[10]["ruler"]
    house_of = {p["planet"]: p.get("house") for p in planets}
    aspects = _aspects_between(planets)
    to_angles = [
        a for a in get_angle_aspects(planets, ascendant=chart.get("ascendant"),
                                     midheaven=chart.get("midheaven"), houses=houses)
        if a["planet_2"] == "Midheaven"
        and within_orb(a["aspect"], a["orb"], a["planet_1"], "Midheaven")
    ]

    evidence: dict[str, list[dict]] = {planet: [] for planet in THEMES}

    def add(planet, kind, why, fact, weight=1.0):
        if planet not in evidence:
            return
        evidence[planet].append({
            "points": POINTS[kind], "kind": kind, "why": why, "fact": fact,
            "weight": round(weight, 3),
            "weighted": round(POINTS[kind] * weight, 2),
        })

    # 5 — the planet that rules the career point. Counted once: under Placidus
    # the MC is the 10th cusp, so "MC ruler" and "10th ruler" are one planet.
    add(mc_ruler, "rules_the_mc",
        f"{mc_ruler} rules your career point, from the "
        f"{_ord(house_of.get(mc_ruler))}" if house_of.get(mc_ruler)
        else f"{mc_ruler} rules your career point",
        f"rules_mc:{mc_ruler}")

    # 4 — a close aspect to the career point itself.
    for aspect in to_angles:
        add(aspect["planet_1"], "aspects_the_mc",
            f"{aspect['planet_1']} {aspect['aspect']} your career point "
            f"({aspect['orb']}°)",
            f"mc_aspect:{aspect['planet_1']}",
            exactness(aspect["aspect"], aspect["orb"], aspect["planet_1"], "Midheaven"))

    # 4 — a close aspect to the planet that rules it.
    for aspect in aspects:
        pair = (aspect["planet_1"], aspect["planet_2"])
        if mc_ruler not in pair:
            continue
        other = pair[0] if pair[1] == mc_ruler else pair[1]
        add(other, "aspects_the_ruler",
            f"{other} {aspect['aspect']} {mc_ruler}, which rules your career "
            f"point ({aspect['orb']}°)",
            f"ruler_aspect:{other}", aspect["exactness"])

    # 3 — standing in the house of the career.
    for planet, house in house_of.items():
        if house == 10:
            add(planet, "in_the_tenth", f"{planet} is in your 10th",
                f"in10:{planet}")
        elif house == 6:
            # 2 — and her caution travels with it.
            add(planet, "daily_work",
                f"{planet} is in your 6th, which is daily work and conditions "
                "rather than the career itself", f"in6:{planet}")

    # No symbolism tier here, deliberately. The sign on the career point
    # DETERMINES its ruler under traditional rulership, so "your MC is in
    # Sagittarius" and "Jupiter rules your MC" are one fact said twice, and
    # her rule is to count each fact once. Adding both let a single fact make
    # a theme look like it had two independent signals.

    spread = _distributions()
    scored = []
    for planet, items in evidence.items():
        best: dict[str, dict] = {}
        for item in items:
            # Count each aspect once, whichever description found it.
            if item["fact"] not in best or item["weighted"] > best[item["fact"]]["weighted"]:
                best[item["fact"]] = item
        items = sorted(best.values(), key=lambda i: -i["weighted"])
        score = _score(items)
        establishing = [i for i in items if i["kind"] not in CANNOT_ESTABLISH]
        scored.append({
            "key": planet,
            "label": THEMES[planet]["label"],
            "work": THEMES[planet]["work"],
            "plain": THEMES[planet]["plain"],
            "score": round(score, 2),
            "how_unusual": round(_how_unusual(planet, score, spread), 3),
            "signals": len(items),
            # Two independent signals, and the 6th cannot supply them.
            "strong": len(establishing) >= 2,
            "evidence": [{"points": i["points"], "weight": i["weight"],
                          "counts_as": i["weighted"], "why": i["why"],
                          "in_plain_words": PLAIN_REASON.get(i["kind"], "")}
                         for i in items],
            "complications": _plain_against(items, establishing),
            "counterevidence": _against(planet, items, establishing),
        })

    ordered = sorted(scored, key=lambda t: (-t["how_unusual"], -t["score"], t["key"]))
    top = [t for t in ordered if t["signals"] > 0 and t["how_unusual"] >= 0.5][:3]
    top = top or [t for t in ordered if t["signals"] > 0][:1]

    combined = None
    if len(top) >= 2 and abs(top[0]["how_unusual"] - top[1]["how_unusual"]) <= 0.05:
        # Her instruction: when two are similarly supported, say how they
        # could be one career rather than picking arbitrarily.
        combined = (f"{top[0]['plain']} and {top[1]['plain']}, which the chart "
                    "supports about equally and which read better as one job "
                    "than as a choice between two")

    return {
        "available": True,
        "career_point": {"sign": rulers[10]["cusp_sign"], "ruler": mc_ruler,
                         "ruler_in_house": rulers[10]["ruler_in_house"],
                         "ruler_dignity": rulers[10]["ruler_dignity"]},
        "note_on_the_house_system": (
            "Placidus, so the Midheaven is the 10th cusp and the MC ruler and "
            "the 10th ruler are the same planet. They are counted once. Under "
            "whole-sign houses they could differ — the astrologer's call."),
        "themes": top,
        "all_themes": ordered,
        "combined_reading": combined,
        "weights": "hers, weighted by how exact each aspect is",
    }


def _score(items) -> float:
    total = 0.0
    symbolism = 0.0
    for item in sorted(items, key=lambda i: -i["weighted"]):
        if item["kind"] == "symbolism":
            allowed = min(item["weighted"], SYMBOLISM_CAP - symbolism)
            symbolism += max(0.0, allowed)
            total += max(0.0, allowed)
        else:
            total += item["weighted"]
    return total


def _plain_against(items: list, establishing: list) -> list[str]:
    """Why this theme is less settled than it looks, without the machinery."""
    said = []
    if len(establishing) < 2:
        said.append("only one thing in the chart actually points here, so it is "
                    "a lead rather than a finding")
    if items and all(i["kind"] in CANNOT_ESTABLISH for i in items):
        said.append("this describes how the days are spent rather than what the "
                    "career is")
    weak = [i for i in items if i["weight"] < 0.45]
    if weak and len(weak) == len(items):
        said.append("every connection here is loose, so read it as a lean and "
                    "not a direction")
    return said[:3]


def _against(planet: str, items: list, establishing: list) -> list[str]:
    against = []
    if not items:
        return ["nothing in the chart points here"]
    if len(establishing) < 2:
        against.append("fewer than two signals that can establish a theme")
    if items and all(i["kind"] in CANNOT_ESTABLISH for i in items):
        against.append("only 6th-house or symbolic evidence, which describes "
                       "daily conditions rather than the career")
    weak = [i for i in items if i["weight"] < 0.45]
    if weak and len(weak) == len(items):
        against.append("every contact here is wide")
    return against


def _ord(number) -> str:
    if not number:
        return "—"
    if number in (11, 12, 13):
        return f"{number}th"
    return f"{number}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th') }"


def describe_themes(result: dict) -> str:
    """The plain sentence. No planets, no houses, no scores."""
    if not result.get("available") or not result["themes"]:
        return ""
    themes = result["themes"]
    if result.get("combined_reading"):
        return f"The work itself looks like {result['combined_reading']}."
    if len(themes) == 1:
        return f"The work itself looks like {themes[0]['plain']}."
    return (f"The work itself looks like {themes[0]['plain']}, "
            f"then {themes[1]['plain']}.")
