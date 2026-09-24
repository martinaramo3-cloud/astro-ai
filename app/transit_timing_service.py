"""Predictive timing: real windows, one per pass, with importance kept separate
from exactness.

Built to Martina's specification. The engine this replaces used a single 3°
orb for everything, sampled every two days, looked eight weeks ahead, and
merged a retrograde's three passes into one smear — which is why "when"
answers were vague.

Four ideas carry the design:

  * The orb depends on the transiting planet, the aspect, and what is being
    hit. A universal orb either buries fast transits or smears slow ones across
    months.
  * Each pass of a retrograde is its own window, detected with the same orb,
    and the passes are grouped into one cycle so the language model can say
    "March begins it, July reconsiders it, December settles it".
  * Orb is not importance. Pluto on the Sun at 2.7° matters more than Mercury
    sextile Venus at 0.2°, and a list sorted by orb would put them the wrong
    way round.
  * The Moon never opens a window of its own. It is a trigger inside windows
    that slower planets have already established.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytz
import swisseph as swe

from app.astrology_engine import (
    PLANETS,
    get_julian_day_from_utc,
    _flags_for,
)

ASPECTS = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "opposition": 180.0,
}

# ── Orbs ───────────────────────────────────────────────────────────────────
# When a transit counts as active. Deliberately tighter than the orbs used for
# reading a natal chart: for prediction, a wide orb is months of noise.
BASE_ORBS: dict[str, dict[str, float]] = {
    "Moon":       {"conjunction": 1.5, "opposition": 1.5, "square": 1.25, "trine": 1.25, "sextile": 1.0},
    "Mercury":    {"conjunction": 2.0, "opposition": 2.0, "square": 1.75, "trine": 1.75, "sextile": 1.25},
    # Not in the specification, which skipped the Sun. Given the same speed as
    # Venus and the weight of a luminary, it is given Venus's orbs until told
    # otherwise.
    "Sun":        {"conjunction": 2.5, "opposition": 2.5, "square": 2.25, "trine": 2.25, "sextile": 1.75},
    "Venus":      {"conjunction": 2.5, "opposition": 2.5, "square": 2.25, "trine": 2.25, "sextile": 1.75},
    "Mars":       {"conjunction": 3.0, "opposition": 3.0, "square": 2.5, "trine": 2.5, "sextile": 2.0},
    "Jupiter":    {"conjunction": 3.5, "opposition": 3.5, "square": 3.0, "trine": 3.0, "sextile": 2.5},
    "Saturn":     {"conjunction": 3.5, "opposition": 3.5, "square": 3.0, "trine": 3.0, "sextile": 2.5},
    "Uranus":     {"conjunction": 3.0, "opposition": 3.0, "square": 2.75, "trine": 2.5, "sextile": 2.0},
    "Neptune":    {"conjunction": 3.0, "opposition": 3.0, "square": 2.75, "trine": 2.5, "sextile": 2.0},
    "Pluto":      {"conjunction": 3.0, "opposition": 3.0, "square": 2.75, "trine": 2.5, "sextile": 2.0},
    "Chiron":     {"conjunction": 2.5, "opposition": 2.5, "square": 2.0, "trine": 2.0, "sextile": 1.5},
    "North Node": {"conjunction": 2.5, "opposition": 2.5, "square": 2.0, "trine": 2.0, "sextile": 1.5},
}

# Widened slightly for the points that carry a life, tightened for the ones
# that would otherwise drown everything in generational contacts.
WIDER_TARGETS = {"Sun", "Moon", "Ascendant", "Midheaven", "Descendant", "IC"}
TIGHTER_TARGETS = {"Uranus", "Neptune", "Pluto", "Chiron", "North Node", "South Node"}


def allowed_orb(transit_planet: str, aspect: str, natal_point: str) -> float:
    """How close this particular transit has to be to count as active."""
    base = BASE_ORBS.get(transit_planet, BASE_ORBS["Mars"]).get(aspect, 2.0)
    if natal_point in WIDER_TARGETS:
        return base + 0.5
    if natal_point in TIGHTER_TARGETS:
        return max(0.5, base - 0.5)
    return base


# ── Importance, which is a different question from exactness ───────────────
TRANSIT_WEIGHT = {
    "Pluto": 1.0, "Neptune": 0.95, "Uranus": 0.95, "Saturn": 1.0, "Jupiter": 0.9,
    "Chiron": 0.6, "North Node": 0.6, "Mars": 0.55, "Sun": 0.5, "Venus": 0.45,
    "Mercury": 0.35, "Moon": 0.15,
}
TARGET_WEIGHT = {
    "Sun": 1.0, "Moon": 1.0, "Ascendant": 1.0, "Midheaven": 1.0,
    "Descendant": 0.9, "IC": 0.9,
    "Venus": 0.85, "Mars": 0.8, "Mercury": 0.7, "Saturn": 0.8, "Jupiter": 0.8,
    "Uranus": 0.5, "Neptune": 0.5, "Pluto": 0.5, "Chiron": 0.45, "North Node": 0.5,
}
ASPECT_WEIGHT = {
    "conjunction": 1.0, "opposition": 0.95, "square": 0.9,
    "trine": 0.8, "sextile": 0.6,
}

# How exact, in the bands that separate "technically active" from "this week".
BANDS = ((0.333, "exact"), (1.0, "very strong"), (2.0, "strong"))


def strength_band(orb: float) -> str:
    for limit, name in BANDS:
        if orb <= limit:
            return name
    return "background"


# ── Sampling ───────────────────────────────────────────────────────────────
# Fine enough that a fast transit cannot fall between two samples, coarse
# enough that two years of Pluto is not a million calculations.
STEP_HOURS = {
    "Moon": 2, "Mercury": 8, "Sun": 12, "Venus": 12, "Mars": 24,
    "Jupiter": 24, "Saturn": 24, "Chiron": 48, "North Node": 48,
    "Uranus": 48, "Neptune": 48, "Pluto": 48,
}
# The Moon is a trigger layer, not a forecast. Scanning it for two years would
# produce thousands of meaningless windows.
MOON_HORIZON_DAYS = 45


def _longitude(utc_dt: datetime, planet_name: str) -> tuple[float, bool]:
    """One body's ecliptic longitude, and whether it is moving backwards."""
    jd = get_julian_day_from_utc(utc_dt)
    result = swe.calc_ut(jd, PLANETS[planet_name], _flags_for(planet_name))
    return result[0][0] % 360, result[0][3] < 0


def _separation(a: float, b: float) -> float:
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def _orb_at(utc_dt: datetime, planet: str, natal_degree: float, aspect_angle: float) -> float:
    longitude, _ = _longitude(utc_dt, planet)
    return abs(_separation(longitude, natal_degree) - aspect_angle)


# A planet's retrograde loop brings it back over the same degree within a few
# months. Anything further apart than this is the planet coming round again,
# which is a different transit entirely.
SAME_LOOP_DAYS = 250


def _exact_hits(series: list[tuple]) -> list[tuple]:
    """Every moment the orb stops tightening and starts widening again.

    A window is a stretch of time the transit is active; an exact hit is a
    moment inside it. Saturn can go direct over a degree, station, come back
    over it and cross a third time without ever moving far enough away to close
    the window — three exact dates, one continuous window. Taking only the
    tightest point of the window would report that as a single pass.
    """
    if len(series) < 3:
        return [min(series, key=lambda s: s[1])] if series else []

    hits = []
    for index in range(1, len(series) - 1):
        before, here, after = series[index - 1][1], series[index][1], series[index + 1][1]
        if here <= before and here < after:
            hits.append(series[index])
    # A window that is still tightening at its edge peaks at that edge.
    if not hits:
        hits = [min(series, key=lambda s: s[1])]
    return hits


def _group_into_cycles(windows: list[dict]) -> list[list[dict]]:
    """Split crossings into cycles, so an annual return is not called a retrograde.

    The Sun conjunct a Midheaven in December 2026 and again in December 2027 is
    not "pass 1 and pass 2" of one thing — it is the Sun coming round again. A
    real multi-pass cycle happens inside one retrograde loop, which means the
    crossings are close together and at least one of them happens while the
    planet is moving backwards.
    """
    if not windows:
        return []
    groups = [[windows[0]]]
    for previous, current in zip(windows, windows[1:]):
        gap = (current["from"] - previous["to"]).days
        went_backwards = any(r for _, _, r in previous["series"]) or any(
            r for _, _, r in current["series"])
        one_loop = gap <= SAME_LOOP_DAYS and went_backwards
        if one_loop:
            groups[-1].append(current)
        else:
            groups.append([current])
    return groups


def _refine_exact(planet: str, natal_degree: float, aspect_angle: float,
                  around: datetime, span_hours: float,
                  earliest: datetime, latest: datetime) -> tuple[datetime, float]:
    """Narrow the tightest moment down from a sample to about an hour.

    The coarse scan finds the right day; this finds the right hour, so "exact
    on the 11th" is a claim rather than a rounding.
    """
    best_dt, best_orb = around, _orb_at(around, planet, natal_degree, aspect_angle)
    window = span_hours
    while window > 1:
        for offset in (-window / 2, window / 2):
            candidate = best_dt + timedelta(hours=offset)
            # The tightest moment cannot sit outside the window it belongs to —
            # unrefined, this produced windows ending before they were exact.
            if candidate < earliest or candidate > latest:
                continue
            orb = _orb_at(candidate, planet, natal_degree, aspect_angle)
            if orb < best_orb:
                best_dt, best_orb = candidate, orb
        window /= 2
    return best_dt, best_orb


def find_transit_cycles(
    natal_points: list[dict],
    months_ahead: int = 24,
    now: datetime | None = None,
    include_moon: bool = False,
    transit_bodies: set[str] | None = None,
) -> list[dict]:
    """Every transit window in the horizon, grouped into cycles.

    A cycle is one transiting planet making one aspect to one natal point. It
    holds one window per pass — three of them when a planet stations and
    crosses the same degree on the way back and again going forward.
    """
    start = now or datetime.now(pytz.utc)
    horizon_days = int(months_ahead * 30.44)
    bodies = transit_bodies or set(BASE_ORBS)
    if not include_moon:
        bodies = bodies - {"Moon"}

    cycles: list[dict] = []

    for planet in sorted(bodies):
        if planet not in PLANETS:
            continue
        step = timedelta(hours=STEP_HOURS.get(planet, 24))
        days = min(horizon_days, MOON_HORIZON_DAYS) if planet == "Moon" else horizon_days

        # One walk per planet, reused for every natal point and aspect.
        samples: list[tuple[datetime, float, bool]] = []
        when = start
        finish = start + timedelta(days=days)
        while when <= finish:
            longitude, retrograde = _longitude(when, planet)
            samples.append((when, longitude, retrograde))
            when += step

        for natal in natal_points:
            natal_name = natal["planet"]
            natal_degree = natal["degree"]

            for aspect, angle in ASPECTS.items():
                limit = allowed_orb(planet, aspect, natal_name)
                passes: list[dict] = []
                current: dict | None = None

                for when, longitude, retrograde in samples:
                    orb = abs(_separation(longitude, natal_degree) - angle)
                    if orb <= limit:
                        if current is None:
                            current = {"from": when, "to": when,
                                       "series": [(when, orb, retrograde)]}
                        else:
                            current["to"] = when
                            current["series"].append((when, orb, retrograde))
                    elif current is not None:
                        passes.append(current)
                        current = None
                if current is not None:
                    passes.append(current)

                if not passes:
                    continue

                importance = (
                    TRANSIT_WEIGHT.get(planet, 0.5)
                    * TARGET_WEIGHT.get(natal_name, 0.6)
                    * ASPECT_WEIGHT.get(aspect, 0.7)
                )

                for group in _group_into_cycles(passes):
                    hits = []
                    for window in group:
                        for at, _, retrograde in _exact_hits(window["series"]):
                            hits.append((window, at, retrograde))

                    windows = []
                    for index, (window, at, retrograde) in enumerate(hits, start=1):
                        exact_at, exact_orb = _refine_exact(
                            planet, natal_degree, angle, at,
                            STEP_HOURS.get(planet, 24) * 2,
                            window["from"], window["to"],
                        )
                        windows.append({
                            "pass": index,
                            "of": len(hits),
                            "starts": window["from"].date().isoformat(),
                            "exact": exact_at.date().isoformat(),
                            "ends": window["to"].date().isoformat(),
                            "retrograde": bool(retrograde),
                            "closest_orb": round(exact_orb, 2),
                            "strength": strength_band(exact_orb),
                            # Honest about the edges of what was scanned.
                            "already_underway": window["from"] <= start,
                            "continues_beyond": window["to"] >= finish - step,
                        })

                    # Why it comes back at all. The planet often turns
                    # retrograde between two exact hits rather than at one of
                    # them, so asking whether any single pass was retrograde
                    # misses the reason the transit repeats.
                    retrograde_involved = any(
                        r for window in group for _, _, r in window["series"]
                    )
                    cycles.append({
                        "transit_planet": planet,
                        "aspect": aspect,
                        "natal_point": natal_name,
                        "retrograde_involved": retrograde_involved,
                        "natal_sign": natal.get("sign"),
                        "natal_house": natal.get("house"),
                        "active_orb": limit,
                        "importance": round(importance, 3),
                        "passes": windows,
                        # Said once, so the model need not infer it from three
                        # dates that look like three unrelated events.
                        "note": (
                            "One transit crossing the same degree more than once in a "
                            "single retrograde loop. The first pass opens the theme, the "
                            "retrograde pass reconsiders it, the final pass settles it — "
                            "interpretive tendencies, not guaranteed events."
                        ) if len(windows) > 1 else None,
                    })

    # Importance first, and only then how soon — a wide Saturn contact to the
    # Midheaven outranks an exact Mercury sextile, which sorting by orb would
    # get backwards.
    cycles.sort(key=lambda c: (-c["importance"], c["passes"][0]["starts"]))
    return cycles


def moon_triggers(
    natal_points: list[dict],
    inside: list[dict],
    now: datetime | None = None,
    days: int = 45,
) -> list[dict]:
    """Days the Moon lights up something already established.

    Never a forecast in itself: the Moon crossing a Descendant is only worth a
    date because slower transits have already made that area live.
    """
    if not inside:
        return []

    live_points = {c["natal_point"] for c in inside}
    targets = [p for p in natal_points if p["planet"] in live_points]
    if not targets:
        return []

    cycles = find_transit_cycles(
        targets, months_ahead=days / 30.44, now=now,
        include_moon=True, transit_bodies={"Moon"},
    )
    triggers = []
    for cycle in cycles:
        for window in cycle["passes"]:
            triggers.append({
                "date": window["exact"],
                "trigger": f"Moon {cycle['aspect']} your {cycle['natal_point']}",
                "note": "A trigger day inside an existing window, not a window of its own.",
            })
    triggers.sort(key=lambda t: t["date"])
    return triggers[:12]


# How far ahead a question is worth searching. From Martina's table: a week's
# question does not want two years of Pluto, and "when will I meet someone"
# cannot be answered inside eight weeks.
HORIZON_MONTHS = {
    "relationship": 24,
    "career": 24,
    "money": 24,
    "emotional": 12,
    "general": 12,
}
NEAR_TERM_MONTHS = 3


def build_predictive_timeline(
    natal_points: list[dict],
    question_type: str | None = None,
    now: datetime | None = None,
    limit: int = 10,
    rules_by_point: dict[str, list[int]] | None = None,
) -> dict:
    """The handful of windows worth putting in a prompt.

    A full two-year scan finds several hundred cycles, which is both too much
    to send and too much to read. Two things earn a place: what is happening
    now, because that is the answer to "why does it feel like this", and what
    is most significant across the horizon, because that is the answer to
    "when".
    """
    start = now or datetime.now(pytz.utc)
    months = HORIZON_MONTHS.get(question_type or "general", 12)
    cycles = find_transit_cycles(natal_points, months_ahead=months, now=start)
    if not cycles:
        return {}

    # Choose windows for the question before trimming the scan. Otherwise a
    # major unrelated transit can crowd out every hit to the 5th/7th ruler.
    topic_houses = {
        "relationship": {5, 7}, "compatibility": {3, 5, 7, 8},
        "career": {2, 6, 8, 10, 11}, "emotional": {4, 8, 12},
    }.get(question_type, set())
    topic_points = {
        "relationship": {"Venus", "Mars", "Moon", "Jupiter", "Saturn", "Ascendant", "Descendant"},
        "compatibility": {"Mercury", "Venus", "Mars", "Moon", "Ascendant", "Descendant"},
        "career": {"Sun", "Jupiter", "Saturn", "Midheaven"},
        "emotional": {"Moon", "Neptune", "Saturn"},
    }.get(question_type, set())
    cycles = [{**c, "natal_rules_houses": (rules_by_point or {}).get(c["natal_point"], [])}
              for c in cycles]
    def relevant(cycle):
        return (cycle["natal_point"] in topic_points
                or cycle.get("natal_house") in topic_houses
                or bool(set(cycle["natal_rules_houses"]) & topic_houses))
    if topic_houses:
        cycles.sort(key=lambda c: (not relevant(c), -c["importance"]))

    today = start.date().isoformat()
    soon = (start + timedelta(days=NEAR_TERM_MONTHS * 30)).date().isoformat()

    def is_live(cycle):
        return any(w["starts"] <= today <= w["ends"] for w in cycle["passes"])

    def is_soon(cycle):
        return any(today <= w["starts"] <= soon for w in cycle["passes"])

    live = [c for c in cycles if is_live(c)][: limit // 2]
    coming = [c for c in cycles if is_soon(c) and c not in live][: limit // 3]
    major = [c for c in cycles if c not in live and c not in coming][
        : max(0, limit - len(live) - len(coming))
    ]

    chosen = live + coming + major
    return {
        "note": (
            "Calculated windows, not estimates. Each pass has its own dates and its "
            "own exact day; where a cycle has more than one pass they are the same "
            "transit crossing the same degree during one retrograde loop. Cite these "
            "dates directly. 'importance' is how much the transit matters, which is "
            "separate from how exact it is — do not lead with a tight Mercury contact "
            "over a wider Saturn one."
        ),
        "searched_months_ahead": months,
        "active_now": [_for_prompt(c) for c in live],
        "starting_soon": [_for_prompt(c) for c in coming],
        "major_ahead": [_for_prompt(c) for c in major],
        "moon_triggers": moon_triggers(natal_points, chosen, now=start),
    }


def _for_prompt(cycle: dict) -> dict:
    """Trimmed to what a reading needs: the dates, and how much it matters."""
    return {
        "transit": f"{cycle['transit_planet']} {cycle['aspect']} your {cycle['natal_point']}",
        "in_house": cycle.get("natal_house"),
        "natal_rules_houses": cycle.get("natal_rules_houses", []),
        "importance": cycle["importance"],
        "passes": [
            {
                "pass": f"{w['pass']} of {w['of']}",
                "window": f"{w['starts']} to {w['ends']}",
                "exact": w["exact"],
                "strength": w["strength"],
                "retrograde": w["retrograde"],
            }
            for w in cycle["passes"]
        ],
        "cycle_note": cycle["note"],
    }


# Which of each person's points a relationship question actually turns on.
RELATIONSHIP_POINTS = {"Sun", "Moon", "Mercury", "Venus", "Mars",
                       "Jupiter", "Saturn", "Pluto", "Ascendant", "Descendant"}


def build_relationship_timeline(
    your_planets: list[dict],
    their_planets: list[dict],
    synastry_aspects: list[dict] | None = None,
    now: datetime | None = None,
    limit: int = 6,
) -> dict:
    """When the thing between two people actually moves.

    A saved-person chat used to receive each person's transits as two separate
    eight-week lists, and the one piece the code itself calls the strongest
    evidence for timing — a transit landing where the two charts already touch
    — carried no date at all. It said a contact was lit today and stopped
    there. So "will something happen between us" had nothing datable behind it
    and came back vague.

    This scans both charts' relationship points over two years, the same way a
    solo question is scanned, and marks the windows that land on a degree where
    the charts meet. Those are the ones worth naming a date for: a transit to
    one person's Venus is their week, a transit to the exact degree where their
    Venus meets the other's Mars is the two of them.

    Kept deliberately small. Everything live now, then the most important of
    what is coming — six or so in total, not a two-year scan, because this
    travels alongside two full charts and a synastry engine.
    """
    start = now or datetime.now(pytz.utc)

    # Labelled by owner, so a window reads "your Venus" or "their Mars" rather
    # than arriving as two indistinguishable lists.
    points = (
        [{"planet": f"your {p['planet']}", "degree": p["degree"]}
         for p in your_planets if p["planet"] in RELATIONSHIP_POINTS]
        + [{"planet": f"their {p['planet']}", "degree": p["degree"]}
           for p in their_planets if p["planet"] in RELATIONSHIP_POINTS]
    )
    if not points:
        return {}

    cycles = find_transit_cycles(points, months_ahead=24, now=start)
    if not cycles:
        return {}

    # Which points are one end of a contact between the charts. A transit here
    # is doing something to the connection, not to one person's week.
    contacts: dict[str, str] = {}
    for contact in (synastry_aspects or [])[:12]:
        p1, p2 = contact.get("person_1_planet"), contact.get("person_2_planet")
        if not p1 or not p2:
            continue
        described = f"your {p1} {contact.get('aspect', 'contact')} their {p2}"
        contacts.setdefault(f"your {p1}", described)
        contacts.setdefault(f"their {p2}", described)

    for cycle in cycles:
        cycle["lights_contact"] = contacts.get(cycle["natal_point"])

    today = start.date().isoformat()
    soon = (start + timedelta(days=NEAR_TERM_MONTHS * 30)).date().isoformat()

    def live(cycle):
        return any(w["starts"] <= today <= w["ends"] for w in cycle["passes"])

    def soon_(cycle):
        return any(today <= w["starts"] <= soon for w in cycle["passes"])

    # A window on a shared degree outranks a bigger one on a single chart:
    # it is the only kind that answers "between us" rather than "to me".
    def weight(cycle):
        return (-(1 if cycle["lights_contact"] else 0), -cycle["importance"])

    # Each bucket gets its own reserved space. Letting "live" take the whole
    # budget filled it six deep and left nothing under "what's coming" — which
    # is the half that answers "will something happen", and the half someone
    # needs when they tell you he is visiting next month.
    active = sorted([c for c in cycles if live(c)], key=weight)[: max(1, limit // 2)]
    coming = sorted([c for c in cycles if soon_(c) and c not in active],
                    key=weight)[: max(1, limit // 3)]
    ahead = sorted([c for c in cycles if c not in active and c not in coming],
                   key=weight)[: max(0, limit - len(active) - len(coming))]

    return {
        "note": (
            "Calculated windows for the two of you, searched two years ahead. Each "
            "pass has its own dates and its own exact day — cite them. A window with "
            "'lights_contact' is a transit landing where the two charts already "
            "touch: that is the strongest thing here and the one to date, because it "
            "is about the connection rather than one person's week. 'importance' is "
            "how much a transit matters, separate from how exact it is."
        ),
        "searched_months_ahead": 24,
        "active_now": [_for_two(c) for c in active],
        "starting_soon": [_for_two(c) for c in coming],
        "major_ahead": [_for_two(c) for c in ahead],
    }


def _for_two(cycle: dict) -> dict:
    """Like _for_prompt, but the point already says whose it is."""
    return {
        "transit": f"{cycle['transit_planet']} {cycle['aspect']} {cycle['natal_point']}",
        **({"lights_contact": cycle["lights_contact"]} if cycle.get("lights_contact") else {}),
        "importance": cycle["importance"],
        "passes": [
            {"pass": f"{w['pass']} of {w['of']}", "window": f"{w['starts']} to {w['ends']}",
             "exact": w["exact"], "strength": w["strength"], "retrograde": w["retrograde"]}
            for w in cycle["passes"]
        ],
        "cycle_note": cycle["note"],
    }
