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
