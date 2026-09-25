"""What someone is good at, and where the same thing costs them.

The organising idea, and the reason this is an engine rather than a prompt:
a strength and a weakness are often ONE trait at two settings. Mars gives
decisiveness and it gives the argument you started a day too early. Saturn
gives things that hold and it gives the offer you turned down because it was
not ready enough. The pair shares a source, so the engine knows which
weaknesses are genuinely a strength overused and which are simply separate —
and it can refuse to force the link where it is not there.

------------------------------------------------------------------------------
Where the content comes from, and who to blame for it
------------------------------------------------------------------------------
The gifts/challenge words for Sun, Moon, Mercury, Venus and Mars come from
`interpretation_service.PLANET_SIGN_MEANINGS`. They arrived in this repo's
first commit on 19 April 2026, carry no source note, and were NOT written by
the astrologer — she has never seen them. They are flagged for her review.

Saturn and Jupiter had no entries at all, which for a weaknesses question is
the significant gap: Saturn is the planet most of this turns on. The twelve
entries each below are MINE, written in the same shape, and are on her list.

The situations — "shows up as" — are mine throughout. The existing table gives
labels ("pride, wounded ego, dependence on validation") and a label is a
diagnosis, not a reading. Nobody wants to be told they have a wounded ego.
They might recognise "taking a note about the work as a note about you", and
that is the same information offered as something they can look at.

PROMINENCE IS NOT VIRTUE. A planet in detriment is loud, not weak; it means
the same function arrives under strain, so the overuse is what shows first.
That distinction is what stops this becoming a list of compliments.
"""
from __future__ import annotations

import bisect
import re
import json
import pathlib

from app.angle_aspects_service import get_angle_aspects
from app.chart_analysis_service import get_house_rulers
from app.interpretation_service import PLANET_SIGN_MEANINGS
from app.natal_career_data import _aspects_between
from app.orb_policy import exactness, within_orb

# One trait per family, so "three distinct strengths" is true by construction
# rather than by asking. Three variations of Venus is the failure this
# prevents — taste, standards and judgment are one trait said three times.
FAMILIES: dict[str, dict] = {
    "Sun": {
        "family": "drive",
        "strength": "you take responsibility for how something turns out",
        "shows_up_as": "being the one who says what the group is actually doing",
        "overuse": "taking a note about the work as a note about you",
        "overuse_shows_up_as": (
            "a correction lands harder than it was meant to, and the next hour "
            "goes on proving something rather than on the work"),
    },
    "Moon": {
        "family": "feeling",
        "strength": "you read the temperature of a room before anyone says anything",
        "shows_up_as": "noticing someone has gone quiet before they know it themselves",
        "overuse": "answering the mood instead of the question",
        "overuse_shows_up_as": (
            "a short reply gets read as a verdict, and you go quiet to be safe "
            "rather than asking what it meant"),
    },
    "Mercury": {
        "family": "thinking",
        "strength": "you can take something tangled and make it plain",
        "shows_up_as": "being the person others ask to explain the thing again",
        "overuse": "explaining past the point where it was already understood",
        "overuse_shows_up_as": (
            "a decision that was accepted the first time gets argued for twice "
            "more, and the room starts wondering what you are worried about"),
    },
    "Venus": {
        "family": "connection",
        "strength": "you can tell what is worth having and what only looks it",
        "shows_up_as": "being asked to choose, because your choice tends to be right",
        "overuse": "keeping the peace past the point where the thing needed saying",
        "overuse_shows_up_as": (
            "the small objection goes unsaid for weeks, and arrives eventually "
            "as a much larger one"),
    },
    "Mars": {
        "family": "action",
        "strength": "you move while other people are still deciding",
        "shows_up_as": "the thing gets started, because you started it",
        "overuse": "starting the argument you could have won by waiting a day",
        "overuse_shows_up_as": (
            "a reply goes out at the moment of most heat, and takes a week to "
            "undo what a night would have settled"),
    },
    "Saturn": {
        "family": "structure",
        "strength": "what you build holds, because you build it to",
        "shows_up_as": "being trusted with the thing that cannot be allowed to fail",
        "overuse": "turning down what you wanted because it was not ready enough",
        "overuse_shows_up_as": (
            "the piece sits unfinished long after it was good, while something "
            "rougher and sooner gets the room"),
    },
    "Jupiter": {
        "family": "expansion",
        "strength": "you can see what a thing could become, not only what it is",
        "shows_up_as": "other people leave a conversation with you braver than they arrived",
        "overuse": "saying yes to the fourth thing while the second is unfinished",
        "overuse_shows_up_as": (
            "three good commitments become three late ones, and the cost lands "
            "on whoever was relying on the second"),
    },
    "temperament": {
        "family": "temperament",
        "strength": "",      # filled from the element balance
        "shows_up_as": "",
        "overuse": "",
        "overuse_shows_up_as": "",
    },
    # An aspect-pattern family was declared here and never produced, because
    # the pattern signal already feeds each planet's prominence rather than
    # standing as a trait of its own. Calibration showed it appearing in 0.0%
    # of answers, which is how a dead entry announces itself.
}

# MINE. Saturn and Jupiter had no gifts/challenge entries; these are written
# in the same shape as the existing table so they can be reviewed together.
# Words only — the situations live in FAMILIES and are also mine.
SATURN_JUPITER: dict[str, dict[str, dict]] = {
    "Saturn": {
        "Aries": {"gifts": "self-discipline, earned nerve, doing it alone when needed",
                  "challenge": "hesitation before starting, harshness with yourself"},
        "Taurus": {"gifts": "patience, staying power, building something durable",
                   "challenge": "holding on past the point of use, fear of going without"},
        "Gemini": {"gifts": "rigorous thinking, saying only what you can stand behind",
                   "challenge": "second-guessing, silence where a half-formed idea belonged"},
        "Cancer": {"gifts": "loyalty that lasts, steadiness for other people",
                   "challenge": "guardedness, carrying what was never yours to carry"},
        "Leo": {"gifts": "authority that is earned rather than claimed",
                "challenge": "withholding your own warmth until it feels deserved"},
        "Virgo": {"gifts": "precision, follow-through, work that stands inspection",
                  "challenge": "perfectionism, mistaking finished for flawless"},
        "Libra": {"gifts": "fairness under pressure, commitments that are kept",
                  "challenge": "over-weighing everyone's claim until nothing is decided"},
        "Scorpio": {"gifts": "endurance, nerve in the parts other people avoid",
                    "challenge": "control where trust would do, slowness to let go"},
        "Sagittarius": {"gifts": "convictions you have actually tested",
                        "challenge": "rigidity about what you once concluded"},
        "Capricorn": {"gifts": "long-range building, authority that accumulates",
                      "challenge": "measuring yourself only by what is finished"},
        "Aquarius": {"gifts": "principled independence, structures that outlast you",
                     "challenge": "distance, treating a feeling as a problem to solve"},
        "Pisces": {"gifts": "quiet persistence, faith that survives evidence",
                   "challenge": "vagueness about limits, obligation without an edge"},
    },
    "Jupiter": {
        "Aries": {"gifts": "confidence that starts things, appetite for a risk",
                  "challenge": "overcommitting on enthusiasm alone"},
        "Taurus": {"gifts": "generosity, an instinct for what is genuinely worth it",
                   "challenge": "excess, comfort chosen over the harder right thing"},
        "Gemini": {"gifts": "curiosity, range, learning quickly in public",
                   "challenge": "scattering, collecting interests instead of finishing one"},
        "Cancer": {"gifts": "care that expands what other people can attempt",
                   "challenge": "over-giving, taking on what was not asked of you"},
        "Leo": {"gifts": "warmth that draws people, belief in what you back",
                "challenge": "overstating, needing the backing to be visible"},
        "Virgo": {"gifts": "usefulness, improving what you are handed",
                  "challenge": "shrinking the vision to what is already manageable"},
        "Libra": {"gifts": "fairness, widening who gets a say",
                  "challenge": "agreeing too readily to keep the room easy"},
        "Scorpio": {"gifts": "depth, appetite for what others will not look at",
                    "challenge": "intensity where lightness would have worked"},
        "Sagittarius": {"gifts": "vision, honesty, an unusually wide horizon",
                        "challenge": "promising a scale you have not yet built for"},
        "Capricorn": {"gifts": "ambition with a plan under it",
                      "challenge": "postponing the good years for the finished ones"},
        "Aquarius": {"gifts": "fairness at scale, seeing past your own interest",
                     "challenge": "principle held above the person in front of you"},
        "Pisces": {"gifts": "compassion, imagination, forgiveness that is real",
                   "challenge": "boundlessness, saying yes because no feels unkind"},
    },
}

# What makes a trait LOUD in a chart. Not what makes it good — see the module
# docstring. MINE, and on the astrologer's list.
PROMINENCE = {
    "conjunct_an_angle": 5,     # standing on the Ascendant or Midheaven
    "chart_ruler": 4,           # the planet that rules the rising sign
    "angular": 3,               # in the 1st, 4th, 7th or 10th
    "dignified": 3,             # domicile or exaltation
    "strained": 3,              # detriment or fall — loud, not weak
    "in_a_pattern": 3,          # apex of a t-square, part of a stellium
    "close_aspects": 2,         # per close aspect to a personal planet, weighted
    "retrograde": 1,
}
ANGULAR = {1, 4, 7, 10}
DIGNIFIED = {"domicile", "exaltation"}
STRAINED = {"detriment", "fall"}
PERSONAL = {"Sun", "Moon", "Mercury", "Venus", "Mars"}

_BANDS_FILE = (pathlib.Path(__file__).resolve().parents[1]
               / "content" / "engine" / "trait_bands.json")


def _distributions() -> dict:
    try:
        return json.loads(_BANDS_FILE.read_text())
    except (OSError, ValueError):
        return {}


def _how_unusual(key: str, score: float, spread: dict) -> float:
    values = spread.get(key)
    if not values:
        return 0.5
    return bisect.bisect_left(values, score) / len(values)


def _words_for(planet: str, sign: str) -> dict:
    """The gifts and challenge words for this placement, from either table."""
    if planet in SATURN_JUPITER:
        return SATURN_JUPITER[planet].get(sign, {})
    entry = (PLANET_SIGN_MEANINGS.get(planet) or {}).get(sign) or {}
    return {"gifts": entry.get("gifts") or entry.get("needs") or "",
            "challenge": entry.get("challenge", "")}


def score_traits(chart: dict) -> dict:
    """Rank what is loudest in this chart, and say which way each one reads."""
    planets = chart.get("planet_positions") or []
    if not planets:
        return {"available": False, "reason": "no chart"}
    houses = chart.get("houses") or []
    has_houses = len(houses) == 12 and chart.get("birth_time_known", True)

    by_name = {p["planet"]: p for p in planets}
    rulers = {r["house"]: r for r in get_house_rulers(houses, planets)} if has_houses else {}
    chart_ruler = rulers.get(1, {}).get("ruler")
    dignity = {r["ruler"]: r.get("ruler_dignity") for r in rulers.values()}
    aspects = _aspects_between(planets)
    on_angles = set()
    if has_houses:
        on_angles = {
            a["planet_1"] for a in get_angle_aspects(
                planets, ascendant=chart.get("ascendant"),
                midheaven=chart.get("midheaven"), houses=houses)
            if a["aspect"] == "conjunction" and a["planet_2"] in ("Ascendant", "Midheaven")
            and within_orb(a["aspect"], a["orb"], a["planet_1"], a["planet_2"])}

    patterns = (chart.get("aspect_patterns")
                or (chart.get("chart_structure") or {}).get("aspect_patterns") or [])
    in_pattern = set()
    for pattern in patterns:
        in_pattern.update(pattern.get("planets") or [])
        if pattern.get("apex"):
            in_pattern.add(pattern["apex"])

    spread = _distributions()
    scored = []

    for planet in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Saturn", "Jupiter"):
        placement = by_name.get(planet)
        if not placement:
            continue
        shape = FAMILIES[planet]
        words = _words_for(planet, placement.get("sign", ""))
        loud, why = 0.0, []

        if planet in on_angles:
            loud += PROMINENCE["conjunct_an_angle"]
            why.append("it sits on one of the most visible points in your chart")
        if has_houses and placement.get("house") in ANGULAR:
            loud += PROMINENCE["angular"]
            why.append("it stands in one of the four most active parts of the chart")
        if planet == chart_ruler:
            loud += PROMINENCE["chart_ruler"]
            why.append("it is the planet that runs your whole chart")
        condition = dignity.get(planet)
        if condition in DIGNIFIED:
            loud += PROMINENCE["dignified"]
            why.append("it is at home in its sign, so this comes easily")
        if condition in STRAINED:
            loud += PROMINENCE["strained"]
            why.append("it is uncomfortable in its sign, so this arrives under strain")
        if planet in in_pattern:
            loud += PROMINENCE["in_a_pattern"]
            why.append("it is caught up in one of the chart's main tensions")
        for aspect in aspects:
            pair = (aspect["planet_1"], aspect["planet_2"])
            if planet not in pair:
                continue
            other = pair[0] if pair[1] == planet else pair[1]
            if other in PERSONAL or other in ("Saturn", "Jupiter"):
                loud += PROMINENCE["close_aspects"] * aspect["exactness"]
        if placement.get("retrograde"):
            loud += PROMINENCE["retrograde"]
            why.append("it runs backwards, so this tends to work inward first")

        # Which way it reads. Prominence is not virtue: a strained planet is
        # loud, and what shows first is the cost rather than the gift.
        leads_as = "overuse" if condition in STRAINED or planet in in_pattern else "strength"
        scored.append({
            "key": planet, "family": shape["family"],
            "strength": shape["strength"], "shows_up_as": shape["shows_up_as"],
            "overuse": shape["overuse"],
            "overuse_shows_up_as": shape["overuse_shows_up_as"],
            "leads_as": leads_as,
            "score": round(loud, 2),
            "how_unusual": round(_how_unusual(planet, round(loud, 2), spread), 3),
            "because": why[:3],
            "words": words,
            "placement": {"sign": placement.get("sign"),
                          "house": placement.get("house") if has_houses else None,
                          "dignity": condition},
        })

    scored.extend(_temperament(chart, planets, spread))
    ordered = sorted(scored, key=lambda t: (-t["how_unusual"], -t["score"], t["key"]))
    return {
        "available": True,
        "traits": ordered,
        "note": ("Ranked by how loud each is in this chart, not by how good it "
                 "is. A planet under strain is loud; what shows first is the "
                 "cost rather than the gift."),
        "provenance": PROVENANCE,
    }


def _temperament(chart: dict, planets: list, spread: dict) -> list[dict]:
    """Two more traits that are not a single planet: the chart's overall
    weather, and its loudest structural tension."""
    from collections import Counter
    from app.content_repository import get_signs
    elements = {name: data.get("element") for name, data in (get_signs() or {}).items()}
    counts = Counter(elements.get(p.get("sign")) for p in planets if p.get("sign"))
    counts.pop(None, None)
    out = []
    if counts:
        dominant, many = counts.most_common(1)[0]
        missing = [e for e in ("Fire", "Earth", "Air", "Water") if not counts.get(e)]
        shape = ELEMENT_TRAITS.get(dominant)
        if shape:
            loud = float(many) + (2.0 if missing else 0.0)
            out.append({
                "key": "temperament", "family": "temperament",
                **shape,
                "leads_as": "overuse" if missing else "strength",
                "score": round(loud, 2),
                "how_unusual": round(_how_unusual("temperament", round(loud, 2), spread), 3),
                "because": ([f"most of your chart sits in one element"]
                            + ([f"and one element is missing entirely"] if missing else [])),
                "words": {"gifts": dominant.lower(), "challenge": ""},
                "placement": {"sign": None, "house": None, "dignity": None},
            })
    return out


ELEMENT_TRAITS = {
    "Fire": {"strength": "you commit before you are certain, and that is often what moves things",
             "shows_up_as": "the plan exists because you said it out loud first",
             "overuse": "momentum spent on the thing in front of you rather than the thing that matters",
             "overuse_shows_up_as": "three started and one finished, and the finished one was the smallest"},
    "Earth": {"strength": "you deal with what is actually in front of you",
              "shows_up_as": "the practical obstacle gets named while everyone else is still enthusiastic",
              "overuse": "treating a possibility as a problem because it has no plan yet",
              "overuse_shows_up_as": "the good idea gets costed to death before anyone tries a small version"},
    "Air": {"strength": "you can hold two sides of something without needing to resolve it",
            "shows_up_as": "being the person who can argue the other position fairly",
            "overuse": "understanding a situation instead of being in it",
            "overuse_shows_up_as": "the feeling gets analysed rather than felt, and comes back later intact"},
    "Water": {"strength": "you take other people seriously without being told to",
              "shows_up_as": "someone tells you the real thing rather than the polite version",
              "overuse": "carrying what belongs to someone else",
              "overuse_shows_up_as": "their bad week becomes your bad week, and nobody decided that"},
}

PROVENANCE = (
    "The gifts/challenge words for Sun, Moon, Mercury, Venus and Mars come "
    "from this repo's first commit (19 April 2026), carry no source note, and "
    "were not written by the astrologer. Saturn and Jupiter, the situations, "
    "the prominence weights and the element traits are mine. All of it is on "
    "her review list."
)


# Tight on purpose. Career questions are a slice of traffic; "general" is most
# of it, and attaching a payload to all of it would be paid for on every chat.
ASKS_ABOUT_TRAITS = re.compile(
    r"\bstrengths?\b|\bweakness(?:es)?\b|\bflaws?\b"
    r"|\bgood at\b|\bbad at\b|\bbest and worst\b"
    r"|\bwhat (?:am|are) i like\b|\bwhat i(?:'m| am) like\b"
    r"|\bmy (?:personality|character|traits?)\b"
    r"|\bdescribe me\b|\bwhat kind of person am i\b"
    r"|\bwork on (?:about )?myself\b|\bneed to work on\b"
    r"|\bblind ?spots?\b|\bwhat holds me back\b", re.I)


def asks_about_traits(question: str) -> bool:
    return bool(ASKS_ABOUT_TRAITS.search(question or ""))


# ── B and C: three of each, all distinct, paired only where it is real ─────

def build_trait_reading(chart: dict) -> dict:
    """Three strengths and three weaknesses, none of them the same trait twice.

    Distinctness is enforced here rather than requested in the prompt. One
    family may appear once on each side and no more — which is what stops
    "taste, standards and judgment", three readings of Venus wearing different
    coats. A prompt asking for variety would lose to the chart data behind it,
    the way every prompt instruction in this app has.
    """
    scored = score_traits(chart)
    if not scored.get("available"):
        return {"available": False, "reason": scored.get("reason")}
    traits = scored["traits"]

    strengths, weaknesses = [], []
    used_strength, used_weakness = set(), set()
    # Whichever way a trait leads goes first; the other side stays available,
    # because a trait's overuse is exactly what its weakness is.
    for trait in traits:
        if trait["leads_as"] == "strength" and trait["family"] not in used_strength \
                and len(strengths) < 3:
            strengths.append(trait)
            used_strength.add(trait["family"])
        elif trait["leads_as"] == "overuse" and trait["family"] not in used_weakness \
                and len(weaknesses) < 3:
            weaknesses.append(trait)
            used_weakness.add(trait["family"])
    # Fill from the other pool if one side is short — a well-placed planet's
    # overuse is a real weakness, and a strained planet still has its gift.
    for trait in traits:
        if len(strengths) < 3 and trait["family"] not in used_strength:
            strengths.append(trait)
            used_strength.add(trait["family"])
        if len(weaknesses) < 3 and trait["family"] not in used_weakness:
            weaknesses.append(trait)
            used_weakness.add(trait["family"])

    # C: linked ONLY when it is the same trait at two settings. Nothing forced.
    strength_families = {t["family"] for t in strengths}
    pairs = [
        {"family": t["family"],
         "strength": t["strength"], "overuse": t["overuse"],
         "why_it_is_the_same_thing": (
             "the same trait at a different setting, not two separate findings")}
        for t in weaknesses if t["family"] in strength_families
    ]

    return {
        "available": True,
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
        "paired": pairs,
        "unpaired_weaknesses": [t["family"] for t in weaknesses
                                if t["family"] not in strength_families],
        "provenance": PROVENANCE,
    }


def for_the_answer(reading: dict, *, technical: bool = False) -> dict | None:
    """What reaches the prompt. Situations, not labels; possibilities, not
    diagnoses.

    The words in the underlying table are heavy — "wounded ego", "suppressed
    anger", "dependence on validation". None of them are sent. A label is a
    diagnosis of a person; the situation is the same information offered as
    something they can look at and disagree with.
    """
    if not reading.get("available"):
        return None

    def entry(trait, side):
        if side == "strength":
            return {"in_plain_words": trait["strength"],
                    "shows_up_as": trait["shows_up_as"],
                    "because": trait["because"]}
        return {"in_plain_words": trait["overuse"],
                "shows_up_as": trait["overuse_shows_up_as"],
                "because": trait["because"]}

    compact = {
        "note": (
            "Computed from the chart before anything else. Build the answer on "
            "it. Never say a ranking exists. These are three DIFFERENT things "
            "on each side by construction — do not merge them back into one."),
        "strengths": [entry(t, "strength") for t in reading["strengths"]],
        "weaknesses": [entry(t, "overuse") for t in reading["weaknesses"]],
        "these_are_one_trait_at_two_settings": [
            {"the_strength": p["strength"], "the_same_thing_overused": p["overuse"]}
            for p in reading["paired"]],
        # Deliberately describes the banned register instead of quoting an
        # example of it. Naming the exact offending words is what makes an
        # instruction land — except when the instruction travels in the same
        # payload as the answer, where the example is just the phrase, sitting
        # there, available to be repeated.
        "how_to_say_the_weaknesses": (
            "As a situation they might recognise, offered as a possibility — "
            "'this can happen when...', 'you may find that...'. Never as a "
            "verdict on who they are, never as a claim about what they fear "
            "or how stress shows up in their body, and never a clinical-sounding "
            "label for a flaw. They should be able to read it and say no."),
    }
    if not reading["paired"]:
        compact["nothing_is_paired_here"] = (
            "None of these weaknesses is one of these strengths overused. Do "
            "not force a link that is not there.")
    if technical:
        compact["the_chart_behind_it"] = [
            {"trait": t["key"], "placement": t["placement"],
             "words": t["words"], "because": t["because"]}
            for t in reading["strengths"] + reading["weaknesses"]]
    return compact


def describe_traits(reading: dict) -> str:
    """The plain sentence an answer is built on."""
    if not reading.get("available") or not reading["strengths"]:
        return ""
    first = reading["strengths"][0]["strength"]
    if reading["paired"]:
        return (f"The strongest thing about you is that {first} — and the same "
                "thing, turned up too far, is where it costs you.")
    return f"The strongest thing about you is that {first}."
