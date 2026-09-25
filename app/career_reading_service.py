"""The internal career reading, produced before a word of the answer is written.

Section 6 of the co-founder's rules: an auditable object holding the question
type, the top professional themes, the top three earning routes, evidence and
counterevidence for each, confidence, the timing windows, and the reason each
window was chosen. Only then is anything written.

LIVE on career and money questions since 25 September 2026, on Martina's
call after the astrologer reviewed the blind table. Only the conclusion is
sent — see `for_the_answer`. Scores never leave this module, and the
placements and aspects go only to someone who asked how the chart says so.

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
        return ("low — the birth time is not reliable, so say what can be said from "
                "the signs and do not reach for anything that needs one")
    leads = QUESTION_TYPES[question_type]["ranking"]
    strong_theme = themes.get("available") and any(t["strong"] for t in themes["themes"])
    strong_route = routes.get("available") and any(r["strong"] for r in routes["ranking"])
    wanted = {"themes": strong_theme, "routes": strong_route,
              "both": strong_theme and strong_route}[leads]
    if not wanted:
        return ("low — the chart does not say enough about the side of this they "
                "asked about; say so plainly rather than filling the gap")
    if question_type == "career_timing" and timing.get("timing_is_unclear"):
        return ("moderate — the reading is clear but the timing is not, so give the "
                "reading and leave the date alone")
    # Confidence counts evidence; how_decided compares this chart with other
    # charts. They can honestly differ — plenty of evidence for something most
    # charts also have — but sending "high" beside "only mildly decided" is a
    # contradiction the answer would have to resolve on its own, and it would
    # resolve it in favour of the confident half.
    leading = (themes["themes"] if leads == "themes" else routes["ranking"]) or []
    if leading and leading[0]["how_unusual"] < 0.6:
        return ("moderate — well evidenced, but this chart is no more decided "
                "about it than most are; lean lightly")
    return "high" if wanted else "moderate"


def _how_decided(ranked: list[dict]) -> str:
    """How much the chart actually leans, in words rather than a number.

    The scores stay internal, but withholding them entirely left no way to
    say whether the top answer was miles ahead or a hair ahead — so an answer
    said "your strongest way of earning is X" with equal force whether the
    chart was emphatic or barely decided. That is overclaiming by omission.
    """
    if not ranked:
        return "the chart does not lean anywhere in particular"
    top = ranked[0]["how_unusual"]
    gap = top - ranked[1]["how_unusual"] if len(ranked) > 1 else 1.0
    if top < 0.6:
        return ("only mildly — this chart is less decided about it than most "
                "charts are, so hold it lightly and say so")
    if gap >= 0.2:
        return "clearly — the first one is well ahead of the rest"
    if gap <= 0.05:
        return ("the top two are close enough to be one answer rather than a "
                "ranking")
    return "moderately — the first leads, but not by a distance"


# Planets and house numbers, stripped out of a payload that is meant to have
# none. The reason survives; the machinery does not.
_PLANET = re.compile(
    r"\b(?:Sun|Moon|Mercury|Venus|Mars|Jupiter|Saturn|Uranus|Neptune|Pluto|"
    r"Chiron|North Node|Midheaven|Ascendant)\b")
_HOUSE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\b|\((\d[\d, ]*)\)")


def _plainly(reasons: list[str]) -> list[str]:
    said = []
    for reason in reasons:
        if "which this question turns on" in reason:
            said.append("it lands on exactly what this question is about")
        elif "touches a house this question turns on" in reason:
            said.append("it touches the part of life this question is about")
        elif "crossing your" in reason:
            said.append("it is moving through the area this question concerns")
        elif "year, which is where" in reason:
            said.append("it falls in the part of life this year of yours is about")
        elif "rules this year" in reason:
            said.append("it involves what this year of yours turns on")
        else:
            said.append(_HOUSE.sub("", _PLANET.sub("it", reason)).strip())
    return [s for s in dict.fromkeys(said) if s]


def for_the_answer(reading: dict, *, technical: bool = False) -> dict | None:
    """What actually goes into the prompt. Never the whole internal object.

    Plain language by default, per her section 6. The placements and aspects
    are included only when the person has explicitly asked how the chart says
    so — the existing astrology-on-request mode — and are absent otherwise, so
    a jargon-free answer is jargon-free because the jargon was never sent.

    The scores never appear in either version. They are a ranking aid and a
    consistency device; a number attached to someone's earning prospects would
    read as a probability whatever it was labelled.
    """
    if not reading.get("available"):
        return None
    themes = reading["professional_themes"]
    routes = reading["earning_routes"]
    timing = reading["timing"]

    compact: dict = {
        "note": (
            "A ranking computed from this chart BEFORE anything the person has "
            "told you was looked at. Build the answer on it. Do not re-derive a "
            "different reading from the raw chart data elsewhere in this "
            "payload, and do not mention that a ranking exists."),
        "this_question_is_about": reading["question_type"].replace("_", " "),
        "conclusion_in_plain_words": reading["plain_language"],
        "confidence": reading["confidence"],
    }

    if themes.get("available") and themes["themes"]:
        compact["what_the_work_is"] = [
            {"theme": t["label"], "in_plain_words": t["plain"],
             "looks_like": t["work"], "well_supported": t["strong"],
             # Why, without a planet or a house in it. Without this the answer
             # asserts a theme it cannot ground in anything, which is how a
             # confident reading becomes a vague one.
             "because": list(dict.fromkeys(
                 e["in_plain_words"] for e in t["evidence"]
                 if e.get("in_plain_words")))[:3],
             "but": t.get("complications") or []}
            for t in themes["themes"]]
        compact["how_decided_the_chart_is_about_the_work"] = _how_decided(
            themes["themes"])
        if themes.get("combined_reading"):
            compact["these_two_are_one_career"] = themes["combined_reading"]

    if routes.get("available") and routes["ranking"]:
        compact["how_the_money_arrives"] = [
            {"route": r["label"], "in_plain_words": r["plain"],
             "means": r["means"], "well_supported": r["strong"],
             "because": list(dict.fromkeys(
                 e["in_plain_words"] for e in r["evidence"]
                 if e.get("in_plain_words")))[:3],
             # Her rule 4: explain the complication, never delete the route.
             # The model cannot explain one it was never told about.
             "but": r.get("complications") or []}
            for r in routes["ranking"]]
        compact["how_decided_the_chart_is_about_money"] = _how_decided(
            routes["ranking"])
        if routes.get("complementary"):
            compact["top_two_routes_are_complementary"] = True
        compact["on_these_dimensions"] = {
            name: reading_["reads_as"]
            for name, reading_ in routes.get("dimensions", {}).items()}

    if timing.get("timing_is_unclear"):
        compact["timing"] = {
            "say": "the timing is not clear enough to put a date on",
            "why": "the indicators do not converge on one window",
        }
    elif timing.get("windows"):
        compact["timing"] = {
            "windows": [
                # Dates deduplicated: two passes of one transit share a window,
                # and printing it twice invited an answer that named it twice.
                {"dates": list(dict.fromkeys(p["window"] for p in w["passes"]))[:2],
                 "exact_days": w["exact_days"],
                 "this_is": w["reads_as"],
                 # Stripped of planets and house numbers. The first version
                 # sent "it lands on Venus" and "it is crossing your 1st" into
                 # a payload that was supposed to contain no astrology.
                 "chosen_because": _plainly(w["why_this_window"])}
                for w in timing["windows"][:2]],
            "note": ("Chosen for activating what this question turns on, not "
                     "for being the largest transit. Explain a window once; "
                     "after that it is a clause."),
        }

    if technical:
        from app.earning_routes_service import technical_evidence
        compact["the_chart_behind_it"] = {
            "money_ruler": reading["earning_routes"]["traced_from"]["money_house_ruler"],
            "career_point": themes.get("career_point"),
            "route_evidence": technical_evidence(routes),
            "theme_evidence": [
                f"{t['label']}: " + "; ".join(e["why"] for e in t["evidence"][:3])
                for t in themes.get("themes", [])],
            "year": reading["annual_profection"],
        }
    return compact


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
