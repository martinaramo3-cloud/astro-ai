"""A month read across a whole life, and split into the parts of it that differ.

Asked what a month holds, Zoli picked the loudest transit, went deep on that
one area, and left the rest of the life unmentioned — so "what should I focus
on this month" came back as a paragraph about relationships and nothing about
work, money, health or anyone's friends. It also treated the month as one
undifferentiated block, when the first ten days and the last ten are often
opposites.

This builds the other shape: every area of life scored for the month, and the
month cut at the days the picture actually changes.

The mapping from houses to areas of life, and which transits count as support
rather than pressure, are astrological judgements. They are written plainly
here so an astrologer can correct them without reading any code.
"""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta

import pytz

from app.transit_timing_service import find_transit_cycles

# Which houses speak for which part of a life. A house appears in more than one
# area on purpose: the 8th is money and intimacy both, and the 6th is work and
# health both.
AREA_HOUSES: dict[str, tuple[int, ...]] = {
    "love and relationships": (5, 7, 8),
    "work and career": (6, 10),
    "money": (2, 8),
    "friends and social life": (3, 11),
    "home and family": (4,),
    "health and routine": (6,),
    "travel and study": (3, 9),
    "yourself": (1, 12),
}

# Whether a transit helps or presses. Split from the planet, because a Saturn
# trine and a Saturn square are not the same month.
ASPECT_VALENCE = {
    "trine": 1.0, "sextile": 0.7,
    "conjunction": 0.0,          # takes its sign from the planet
    "square": -1.0, "opposition": -0.8,
}
PLANET_VALENCE = {
    "Jupiter": 1.0, "Venus": 0.8, "Sun": 0.4, "Mercury": 0.2, "North Node": 0.3,
    "Moon": 0.0,
    "Mars": -0.5, "Saturn": -0.6, "Chiron": -0.3,
    "Uranus": -0.3, "Neptune": -0.4, "Pluto": -0.5,
}


def _valence(cycle: dict) -> float:
    """Positive is support, negative is pressure, and a conjunction takes its
    character entirely from the planet making it."""
    aspect = ASPECT_VALENCE.get(cycle["aspect"], 0.0)
    planet = PLANET_VALENCE.get(cycle["transit_planet"], 0.0)
    if cycle["aspect"] == "conjunction":
        return planet
    # A hard aspect from a benefic still presses; a soft one from a malefic
    # still helps. Averaging keeps both facts.
    return (aspect + planet) / 2


def _areas_for(cycle: dict) -> set[str]:
    """Which parts of life a transit lands in.

    Two routes: the house the natal point sits in, and the houses that point
    rules. A transit to the ruler of the 10th is about work even when the
    planet itself sits in the 4th.
    """
    houses = set()
    if cycle.get("natal_house"):
        houses.add(cycle["natal_house"])
    houses.update(cycle.get("natal_rules_houses") or [])

    # The angles speak for their own territory whatever house they head.
    named = {"Midheaven": "work and career", "Ascendant": "yourself"}
    areas = {named[cycle["natal_point"]]} if cycle["natal_point"] in named else set()

    for area, area_houses in AREA_HOUSES.items():
        if houses & set(area_houses):
            areas.add(area)
    return areas


def build_month_outlook(
    natal_points: list[dict],
    year: int,
    month: int,
    rules_by_point: dict[str, list[int]] | None = None,
    now: datetime | None = None,
) -> dict:
    """Every area of life scored for one month, and the month cut into parts."""
    first = datetime(year, month, 1, tzinfo=pytz.utc)
    last_day = calendar.monthrange(year, month)[1]
    last = datetime(year, month, last_day, 23, 59, tzinfo=pytz.utc)

    # Search from a little before, so a transit already under way is included.
    cycles = find_transit_cycles(
        natal_points, months_ahead=3,
        now=(now or first) - timedelta(days=40),
    )

    # Carry rulership through, so a transit can reach the area it governs.
    for cycle in cycles:
        if rules_by_point:
            cycle["natal_rules_houses"] = rules_by_point.get(cycle["natal_point"], [])

    in_month = []
    for cycle in cycles:
        for window in cycle["passes"]:
            if window["starts"] <= last.date().isoformat() and window["ends"] >= first.date().isoformat():
                in_month.append((cycle, window))

    # ── Every area, scored ────────────────────────────────────────────────
    areas: dict[str, dict] = {
        name: {"support": 0.0, "pressure": 0.0, "transits": []} for name in AREA_HOUSES
    }
    for cycle, window in in_month:
        valence = _valence(cycle) * cycle["importance"]
        for area in _areas_for(cycle):
            bucket = areas[area]
            if valence >= 0:
                bucket["support"] += valence
            else:
                bucket["pressure"] += -valence
            bucket["transits"].append({
                "transit": f"{cycle['transit_planet']} {cycle['aspect']} your {cycle['natal_point']}",
                "exact": window["exact"],
                "strength": window["strength"],
                "helps": valence >= 0,
                "weight": abs(valence),
                # A slow transit can run all month and be exact either side of
                # it. Still active, but calling it October's news would be a lie.
                "ongoing": not (first.date().isoformat() <= window["exact"] <= last.date().isoformat()),
            })

    scored = []
    for name, bucket in areas.items():
        if not bucket["transits"]:
            continue
        net = bucket["support"] - bucket["pressure"]
        scored.append({
            "area": name,
            "verdict": "supported" if net > 0.1 else "under pressure" if net < -0.1 else "mixed",
            "net": round(net, 2),
            # The ones that actually produced the verdict, not the earliest.
            # Sorting by date showed positives under an area marked "under
            # pressure", which reads as a contradiction.
            "transits": sorted(bucket["transits"], key=lambda t: -t["weight"])[:3],
        })
    scored.sort(key=lambda a: -abs(a["net"]))

    return {
        "month": f"{calendar.month_name[month]} {year}",
        "note": (
            "The whole month, across a whole life, rather than whichever transit "
            "is loudest. 'supported' and 'under pressure' are calculated from the "
            "aspects and planets involved. The periods below are the days the "
            "picture actually changes — say what each stretch is good for, not "
            "only what to be careful of."
        ),
        "areas": scored,
        "periods": _periods(first, last, in_month),
    }


def _periods(first: datetime, last: datetime, in_month: list) -> list[dict]:
    """Cut the month where something is actually exact.

    A month is rarely one thing. Splitting at the exact dates of the transits
    that matter gives stretches that genuinely differ, instead of arbitrary
    thirds that all read the same.
    """
    marks = sorted({
        window["exact"] for cycle, window in in_month
        if first.date().isoformat() <= window["exact"] <= last.date().isoformat()
        and cycle["importance"] >= 0.3
    })

    if not marks:
        return []

    # At most three cuts, so the month stays readable.
    if len(marks) > 3:
        step = len(marks) / 3
        marks = [marks[int(i * step)] for i in range(3)]

    edges = [first.date().isoformat()] + marks + [last.date().isoformat()]
    periods = []
    for index, (start, end) in enumerate(zip(edges, edges[1:])):
        if start == end:
            continue
        # What is exact inside this stretch — the thing that makes it different
        # from the one before it. Listing everything still in orb made every
        # period identical, which is the opposite of splitting a month up.
        peaking = [
            {
                "transit": f"{c['transit_planet']} {c['aspect']} your {c['natal_point']}",
                "exact": w["exact"],
                "helps": _valence(c) >= 0,
                "areas": sorted(_areas_for(c)),
            }
            for c, w in in_month
            # Start exclusive after the first period, or a transit exact on a
            # cut date is reported twice, in both stretches either side of it.
            # The first period still needs a floor, or anything exact before
            # the month began falls into it.
            if (w["exact"] > start or (index == 0 and w["exact"] >= start))
            and w["exact"] <= end
            and c["importance"] >= 0.3
        ]
        if not peaking:
            continue
        helping = sum(1 for t in peaking if t["helps"])
        periods.append({
            "from": start,
            "to": end,
            "character": "mostly supportive" if helping > len(peaking) / 2 else "mostly pressured",
            "peaking_now": sorted(peaking, key=lambda t: t["exact"])[:4],
        })
    return periods
