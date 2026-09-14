"""Solar returns, and the same chart seen from somewhere else.

Two related ideas, both of which the app could not do.

Relocation is nearly free and was simply never asked for: a birth chart cast
for a different place keeps every planet exactly where it was — same moment,
same sky — and moves only the Ascendant, the Midheaven and the house cusps,
because those depend on where on Earth you were standing. Venus in the 1st in
Sofia is Venus in the 2nd in London, and the 2nd house is money.

A solar return is the moment each year when the Sun comes back to the exact
degree it occupied at birth. It is a chart in its own right, cast for wherever
the person actually is at that moment — which is why people travel for it, and
why "where should I be on my birthday" is a real question rather than a
superstition.

The astronomy here is settled. What counts as a *good* solar return for a given
purpose is an astrological judgement, and lives outside this module.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytz
import swisseph as swe

from app.astrology_engine import (
    PLANETS,
    _flags_for,
    add_house_to_planets,
    get_houses_and_ascendant,
    get_julian_day_from_utc,
    get_planet_positions_from_utc,
)

ANGLE_NAMES = ("Ascendant", "Midheaven", "Descendant", "IC")


def _sun_longitude(moment: datetime) -> float:
    jd = get_julian_day_from_utc(moment)
    return swe.calc_ut(jd, PLANETS["Sun"], _flags_for("Sun"))[0][0] % 360


def _signed_gap(a: float, b: float) -> float:
    """How far a is ahead of b, as a value between -180 and 180."""
    return (a - b + 180) % 360 - 180


def find_solar_return(natal_sun_longitude: float, year: int,
                      birth_month: int, birth_day: int) -> datetime:
    """The exact moment the Sun returns to its natal degree, to the minute.

    Bracketed around the birthday and then bisected. The Sun moves about a
    degree a day, so being a few hours out moves the returned chart's
    Ascendant by degrees — which is the whole thing a solar return turns on.
    """
    # Start a week either side of the anniversary: enough to contain the
    # return whatever the leap-year drift.
    start = datetime(year, birth_month, birth_day, tzinfo=pytz.utc) - timedelta(days=7)
    end = start + timedelta(days=14)

    low, high = start, end
    for _ in range(60):                     # to well under a minute
        middle = low + (high - low) / 2
        if _signed_gap(_sun_longitude(middle), natal_sun_longitude) < 0:
            low = middle
        else:
            high = middle
    return low + (high - low) / 2


def chart_for(moment: datetime, latitude: float, longitude: float) -> dict:
    """A full chart for one moment seen from one place."""
    planets = get_planet_positions_from_utc(moment)
    houses = get_houses_and_ascendant(moment, latitude, longitude)
    placed = add_house_to_planets(planets, houses["houses"])

    ascendant = houses["ascendant"]["degree"]
    midheaven = houses["midheaven"]["degree"]
    angles = {
        "Ascendant": ascendant,
        "Midheaven": midheaven,
        "Descendant": (ascendant + 180) % 360,
        "IC": (midheaven + 180) % 360,
    }

    return {
        "moment_utc": moment.isoformat(),
        "ascendant": houses["ascendant"],
        "midheaven": houses["midheaven"],
        "houses": houses["houses"],
        "planets": placed,
        "angles": angles,
        "angular_planets": _angular(placed, angles),
    }


def _angular(planets: list[dict], angles: dict[str, float], orb: float = 5.0) -> list[dict]:
    """Planets sitting on an angle, which is where a planet shouts.

    A planet within a few degrees of the Ascendant or Midheaven runs the chart
    it is in. For a relocated solar return this is most of what moving is for.
    """
    found = []
    for planet in planets:
        for name, degree in angles.items():
            separation = abs((planet["degree"] - degree + 180) % 360 - 180)
            if separation <= orb:
                found.append({
                    "planet": planet["planet"],
                    "angle": name,
                    "orb": round(separation, 2),
                })
    return sorted(found, key=lambda a: a["orb"])


def solar_return_for_places(
    natal_sun_longitude: float,
    year: int,
    birth_month: int,
    birth_day: int,
    places: list[dict],
) -> dict:
    """The same solar return moment, cast for each candidate place.

    The moment is fixed — the Sun returns when it returns, wherever anyone is
    standing — so the planets and their aspects are identical everywhere. Only
    the houses and angles differ, and that is the entire basis on which one
    city can be better than another.
    """
    moment = find_solar_return(natal_sun_longitude, year, birth_month, birth_day)

    charts = []
    for place in places:
        chart = chart_for(moment, place["latitude"], place["longitude"])
        charts.append({
            "place": place["label"],
            "local_time": moment.astimezone(
                pytz.timezone(place["timezone"])
            ).strftime("%Y-%m-%d %H:%M") if place.get("timezone") else None,
            "ascendant": f"{chart['ascendant']['sign']} {chart['ascendant']['degree'] % 30:.1f}",
            "midheaven": f"{chart['midheaven']['sign']} {chart['midheaven']['degree'] % 30:.1f}",
            "angular_planets": chart["angular_planets"],
            "houses_of": {
                p["planet"]: p["house"]
                for p in chart["planets"]
                if p["planet"] in ("Sun", "Moon", "Venus", "Jupiter", "Saturn", "Mars", "Pluto")
            },
        })

    return {
        "returns_at_utc": moment.isoformat(),
        "note": (
            "One moment, seen from several places. Every planet and every aspect "
            "between them is identical in each — only the houses and the angles "
            "change, which is the whole of what relocating does."
        ),
        "places": charts,
    }


def rank_places_for(
    natal_sun_longitude: float,
    year: int,
    birth_month: int,
    birth_day: int,
    purpose: str = "money",
    places: list[dict] | None = None,
    top: int = 7,
    region: str = "world",
) -> dict:
    """Where to be for the solar return, ranked, with the reasoning shown.

    The return moment is the same everywhere — the Sun comes back when it comes
    back — so every chart here has identical planets and identical aspects
    between them. Only the houses and the angles differ, and that is the whole
    of what choosing a city can change.
    """
    from app.european_cities import as_places
    from app.relocation_scoring import BY_AN_ASTROLOGER, PURPOSES, score_chart, _ordinal

    candidates = places or as_places(region)
    moment = find_solar_return(natal_sun_longitude, year, birth_month, birth_day)

    scored = []
    for place in candidates:
        chart = chart_for(moment, place["latitude"], place["longitude"])
        result = score_chart(chart, purpose)
        local = None
        if place.get("timezone"):
            local = moment.astimezone(pytz.timezone(place["timezone"])).strftime("%d %B %Y, %H:%M")
        scored.append({
            "place": place["label"],
            "score": result["score"],
            "be_there_at": local,
            "ascendant": f"{chart['ascendant']['sign']} {chart['ascendant']['degree'] % 30:.0f}",
            "midheaven": f"{chart['midheaven']['sign']} {chart['midheaven']['degree'] % 30:.0f}",
            "from_houses": result["from_houses"],
            "from_angles": result["from_angles"],
            "from_rulers": result["from_rulers"],
            "why": result["why"][:6],
        })

    scored.sort(key=lambda p: -p["score"])
    table = PURPOSES.get(purpose)

    # How much the choice is worth at all. In some years the planets fall such
    # that most of a continent gives the same chart, and in others where you
    # stand changes it completely. Ranking eighty cities implies the first
    # meaningfully beats the seventh, which in a flat year is untrue — and
    # saying so is more useful than a confident list.
    spread = (scored[0]["score"] - scored[-1]["score"]) if len(scored) > 1 else 0.0
    distinct = len({p["score"] for p in scored})
    on_angles = sum(1 for p in scored if p["from_angles"])
    if spread < 3 or distinct <= 5:
        verdict = "barely — most of Europe gives nearly the same chart this year"
    elif spread < 8:
        verdict = "somewhat — there is a real but modest difference between the best and worst"
    else:
        verdict = "a great deal — the best and worst places are meaningfully different charts"

    # Cities on nearly the same longitude get the same chart, so presenting
    # them as first, second and third is a ranking of nothing.
    grouped: list[dict] = []
    for place in scored:
        if grouped and abs(grouped[-1]["score"] - place["score"]) < 0.01:
            grouped[-1]["also"].append(place["place"])
        else:
            grouped.append({**place, "also": []})

    return {
        "purpose": purpose,
        # Whose astrology this is. The money table came from an astrologer; the
        # others were written by analogy and are marked so a reading can be
        # appropriately confident and no more.
        "scoring_reviewed_by_astrologer": purpose in BY_AN_ASTROLOGER,
        "returns_at_utc": moment.isoformat(),
        "searched": len(candidates),
        "region": region,
        "note": (
            "One moment seen from many places. The planets and the aspects between "
            "them are identical everywhere — only the houses and the angles change, "
            "which is the whole of what relocating does. Scores come from an "
            "astrologer's table, and 'why' shows the working: give the reasoning, "
            "not the number, and say plainly that they have to physically be there "
            "at the local time given. Read "
            "'does_location_matter_this_year' first and say so honestly — in a flat "
            "year, telling someone to fly somewhere is selling them a difference "
            "that isn't there. Cities listed under 'also' share the same chart and "
            "are equal, not ranked."
        ),
        "houses_that_count": (
            {_ordinal(h): meta["means"] for h, meta in table["houses"].items()} if table else {}
        ),
        "does_location_matter_this_year": verdict,
        "score_spread": round(spread, 2),
        "cities_with_a_planet_on_an_angle": on_angles,
        # Grouped, so equally-placed cities read as equal rather than ranked.
        "best": grouped[:top],
        "worst": scored[-3:][::-1],
    }
