"""The internal career reading, produced before a word of the answer is written.

Section 6 of the co-founder's rules: an auditable object holding the question
type, the top professional themes, the top three earning routes, evidence and
counterevidence for each, confidence, the timing windows, and the reason each
window was chosen. Only then is anything written.

NOT WIRED INTO ANY ANSWER. Dark until she has reviewed the blind table.

------------------------------------------------------------------------------
The two things this file exists to prevent
------------------------------------------------------------------------------
Biography becoming evidence. Nothing about what the person studies, does or
wants is an argument to any function here. It cannot leak into the ranking
because it is not in the room — which is the only version of "judge the chart
first" that survives contact with a language model, since a prompt saying so
arrives in the same payload as the memory it is meant to be ignoring.

Leading with the loudest transit. Every career answer in testing opened with
the top entry of a two-year list, four answers running, because that list is
sorted by how big a transit is and nothing asked whether it touched the
question. Here a window is chosen for activating the factors THIS question
turned on, and it carries the reason it was chosen.
"""
from __future__ import annotations

import re

from app.natal_career_data import build_career_natal_data
from app.earning_routes_service import describe_routes, score_earning_routes
from app.professional_themes_service import describe_themes, score_professional_themes
from app.profection_service import annual_profection

# ── Section 1: what is the question actually asking ────────────────────────
#
# Each type leads with different chart factors. Getting this wrong is not a
# small error: "what should I do for work" answered from the 2nd house is an
# answer about money to someone who asked about meaning.
QUESTION_TYPES = {
    "suitable_work": {
        "leads_with": ("the Midheaven, its ruler, and planets closely "
                       "connected to them; then the 6th for daily work"),
        "ranking": "themes",
    },
    "how_they_earn": {
        "leads_with": ("the 2nd house and its ruler, and its connections to "
                       "the 6th, 7th, 8th, 10th and 11th"),
        "ranking": "routes",
    },
    "career_timing": {
        "leads_with": ("the natal career and income factors first, then the "
                       "timing techniques that activate those factors"),
        "ranking": "both",
    },
    "a_specific_choice": {
        "leads_with": ("the natal assessment, against which each option is "
                       "judged; the chart reading does not bend to make an "
                       "existing plan sound destined"),
        "ranking": "both",
    },
}

_TIMING = re.compile(
    r"\bwhen\b|\bwhat (?:year|month)\b|\bhow long\b|\btiming\b|\bright time\b"
    r"|\bthis year\b|\bnext year\b|\bsoon\b|\b20\d\d\b", re.I)
_CHOICE = re.compile(
    r"\bshould i\b|\bor should\b|\bwhich (?:one|of|option|job|offer|path)\b"
    r"|\b(?:take|accept|turn down|leave|quit|stay)\b.{0,30}\b(?:job|offer|role|course)\b"
    r"|\bbetter (?:to|option|choice)\b|\bworth (?:it|doing|taking)\b", re.I)
_EARNING = re.compile(
    r"\b(?:make|earn|earning)\b.{0,15}\bmoney\b|\bincome\b|\bhow (?:do|can|will) i "
    r"(?:make|earn)\b|\bmonetis|\bmonetiz|\bpaid\b|\bsalary\b|\bfinanciall?y?\b"
    r"|\brich\b|\bwealth\b|\bprofit\b|\bcharge\b", re.I)
_WORK = re.compile(
    r"\bcareer\b|\bwhat (?:work|job|profession)\b|\bsuit(?:s|ed)? me\b"
    r"|\bgood at\b|\bmeant to do\b|\bvocation\b|\bcalling\b|\bfield\b", re.I)


def classify_career_question(question: str) -> str:
    """Which of her four kinds this is.

    Order matters. A specific choice is still a specific choice when it
    mentions money, and a timing question is still a timing question when it
    mentions a career — so the narrower readings are tested first.
    """
    text = question or ""
    if _CHOICE.search(text):
        return "a_specific_choice"
    if _TIMING.search(text):
        return "career_timing"
    if _EARNING.search(text):
        return "how_they_earn"
    if _WORK.search(text):
        return "suitable_work"
    return "suitable_work"


# ── Section 5: choosing timing that answers THIS question ──────────────────

def _factors_for(question_type: str, natal: dict, themes: dict, routes: dict) -> dict:
    """The natal points and houses this question actually turned on.

    A window is then chosen for touching these, rather than for being the
    biggest transit in the next two years.
    """
    points: set[str] = set()
    houses: set[int] = set()
    if not natal.get("available"):
        return {"points": points, "houses": houses}

    rulers = natal["rulers"]
    if question_type in ("suitable_work", "career_timing", "a_specific_choice"):
        houses |= {10, 6}
        points.add("Midheaven")
        if 10 in rulers:
            points.add(rulers[10]["ruler"])
        if themes.get("available"):
            points |= {t["key"] for t in themes["themes"]}
    if question_type in ("how_they_earn", "career_timing", "a_specific_choice"):
        houses |= {2, 7, 8, 11}
        if 2 in rulers:
            points.add(rulers[2]["ruler"])
        if routes.get("available"):
            for route in routes["ranking"]:
                houses |= set(_route_houses(route["key"]))
    return {"points": points, "houses": houses}


def _ord(number) -> str:
    if not number:
        return "—"
    if number in (11, 12, 13):
        return f"{number}th"
    return f"{number}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th') }"


def _route_houses(key: str) -> tuple:
    from app.earning_routes_service import ROUTES
    return ROUTES[key]["houses"]


def choose_timing(timeline: dict, factors: dict, profection: dict,
                  limit: int = 3) -> dict:
    """Rank windows by whether they activate this question's factors.

    Her rule, and the bug it fixes: "Do not lead every answer with the
    highest-scoring transit in the next two years." That list is sorted by how
    large a transit is. Nothing in it knows what was asked.
    """
    windows = []
    for bucket in ("active_now", "starting_soon", "major_ahead"):
        for window in (timeline or {}).get(bucket, []) or []:
            windows.append({**window, "bucket": bucket})
    if not windows:
        return {"available": False,
                "reason": "no calculated windows in the searched range"}

    profected = profection.get("profected_house") if profection.get("available") else None
    time_lord = profection.get("time_lord") if profection.get("available") else None

    chosen = []
    for window in windows:
        named = window.get("transit", "")
        rules = set(window.get("natal_rules_houses") or [])
        in_house = window.get("in_house")
        reasons, activation = [], 0.0

        hit_point = next((p for p in factors["points"] if p and p in named), None)
        if hit_point:
            activation += 2.0
            reasons.append(f"it lands on {hit_point}, which this question turns on")
        if rules & factors["houses"]:
            activation += 1.5
            reasons.append("it touches a house this question turns on "
                           f"({', '.join(str(h) for h in sorted(rules & factors['houses']))})")
        if in_house in factors["houses"]:
            activation += 1.0
            reasons.append(f"it is crossing your {_ord(in_house)}")
        # Profection as CONTEXT, per her rule — it raises a window that is
        # already relevant and never establishes one on its own.
        if profected and (in_house == profected or profected in rules):
            activation += 0.75
            reasons.append(f"this is a {profected}th-house year, which is where "
                           "this year's attention sits")
        if time_lord and time_lord in named:
            activation += 0.75
            reasons.append(f"{time_lord} rules this year")

        if activation <= 0:
            continue
        exact_passes = [p for p in window.get("passes", [])
                        if p.get("strength") == "exact"]
        chosen.append({
            **window,
            "activation": round(activation, 2),
            "why_this_window": reasons,
            # Her distinction: a long process is not an event window.
            "reads_as": ("a process rather than an event"
                         if len(window.get("passes", [])) > 1 or window["bucket"] == "major_ahead"
                         else "a window in which something could land"),
            "exact_days": [p["exact"] for p in exact_passes],
        })

    # Activation first, then strength, then exactness — her order.
    chosen.sort(key=lambda w: (-w["activation"], -w.get("importance", 0),
                               -len(w["exact_days"])))
    top = chosen[:limit]

    # Her rule: when the indicators do not converge, say so rather than
    # manufacturing a date.
    #
    # Convergence is indicators AGREEING, not one window scoring highly. The
    # first version tested the top window's activation against a threshold,
    # and for a timing question — which puts both the career and the income
    # factors in play — almost every window cleared it, so "the timing is
    # unclear" never once fired on the question type that most needs it.
    #
    # So: the top window has to rest on more than one indicator, AND it has to
    # stand clear of the next one. Two windows tied at the top is precisely
    # the situation where a date should not be given.
    # The gap is 0.5 rather than a round number because activation is built
    # from coarse steps and ties at the top are common; measured over a
    # thousand charts, 0.5 calls the timing clear on roughly half of them and
    # does so evenly across all four question types. At 1.0 it converged on
    # under a fifth; with no gap at all it converged on essentially everything.
    converges = bool(top) and len(top[0]["why_this_window"]) >= 2 and (
        len(top) == 1 or top[0]["activation"] - top[1]["activation"] >= 0.5)
    return {
        "available": bool(top),
        "windows": top,
        "converges": converges,
        "timing_is_unclear": not converges,
        "how_chosen": ("ranked by whether a window activates the natal factors "
                       "this question turned on, then by strength and exactness. "
                       "Never by which transit is largest."),
        "considered": len(windows),
    }


# ── Section 6: the internal object, produced before anything is written ────

def build_career_reading(chart: dict, question: str, *, timeline: dict | None = None,
                         birth_date: str | None = None,
                         birth_time_confident: bool = True) -> dict:
    """Everything her rules require, in one auditable object.

    The person's circumstances are deliberately absent. They belong to the
    step AFTER this one, where a ranked route becomes a practical option.
    """
    question_type = classify_career_question(question)
    natal = build_career_natal_data(chart)

    # Her rule 5: without a reliable birth time, no house, Ascendant or MC
    # claim at all — which is most of this.
    if not natal.get("available"):
        return {
            "available": False,
            "question_type": question_type,
            "reason": natal.get("reason"),
            "what_can_still_be_said": natal.get("what_can_still_be_said"),
            "natal": natal,
        }

    themes = score_professional_themes(chart)
    routes = score_earning_routes(chart, birth_time_confident=birth_time_confident)
    profection = annual_profection(birth_date or chart.get("birth_date") or "",
                                   chart.get("houses"))
    factors = _factors_for(question_type, natal, themes, routes)
    timing = choose_timing(timeline or {}, factors, profection)

    leads_with = QUESTION_TYPES[question_type]["ranking"]
    confidence = _confidence(question_type, themes, routes, timing,
                             birth_time_confident)

    return {
        "available": True,
        "internal_only": (
            "Produced before the answer is written and never shown. Scores are "
            "a ranking aid, not a probability and not a promise of income."),
        "question_type": question_type,
        "leads_with": QUESTION_TYPES[question_type]["leads_with"],
        "which_ranking_leads": leads_with,
        "professional_themes": themes,
        "earning_routes": routes,
        "factors_this_question_turns_on": {
            "points": sorted(factors["points"]),
            "houses": sorted(factors["houses"]),
        },
        "annual_profection": profection,
        "timing": timing,
        "confidence": confidence,
        "natal_evidence": natal,
        "plain_language": _plain(question_type, themes, routes, timing),
        "biography_note": (
            "Nothing the person has said about their education, job or plans "
            "reached any of this. Their circumstances turn a ranked theme or "
            "route into practical options afterwards; they are never evidence "
            "for one."),
    }


def _confidence(question_type, themes, routes, timing, birth_time_confident) -> str:
    if not birth_time_confident:
        return "low — the birth time is uncertain, so nothing here may rest on a house"
    leads = QUESTION_TYPES[question_type]["ranking"]
    strong_theme = themes.get("available") and any(t["strong"] for t in themes["themes"])
    strong_route = routes.get("available") and any(r["strong"] for r in routes["ranking"])
    wanted = {"themes": strong_theme, "routes": strong_route,
              "both": strong_theme and strong_route}[leads]
    if not wanted:
        return "low — nothing reaches two independent signals on the side this question asks about"
    if question_type == "career_timing" and timing.get("timing_is_unclear"):
        return "moderate — the chart is clear, the timing indicators do not converge"
    return "high" if wanted else "moderate"


def _plain(question_type, themes, routes, timing) -> str:
    """What an answer would be built from. No houses, no planets, no scores."""
    parts = []
    leads = QUESTION_TYPES[question_type]["ranking"]
    if leads in ("themes", "both") and themes.get("available"):
        parts.append(describe_themes(themes))
    if leads in ("routes", "both") and routes.get("available"):
        parts.append(describe_routes(routes))
    if question_type == "career_timing":
        if timing.get("timing_is_unclear"):
            parts.append("The timing is not clear enough to put a date on.")
        elif timing.get("windows"):
            parts.append("There is one stretch of time that matters more than the rest.")
    return " ".join(p for p in parts if p)
