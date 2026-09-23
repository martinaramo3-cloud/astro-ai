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
import calendar

from app.aspect_services import get_aspects
from app.chart_analysis_service import get_house_rulers, get_dignity

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
    start = datetime(year, birth_month, min(birth_day, calendar.monthrange(year, birth_month)[1]), tzinfo=pytz.utc) - timedelta(days=7)
    end = start + timedelta(days=14)

    low, high = start, end
    for _ in range(60):                     # to well under a minute
        middle = low + (high - low) / 2
        if _signed_gap(_sun_longitude(middle), natal_sun_longitude) < 0:
            low = middle
        else:
            high = middle
    return low + (high - low) / 2


def chart_for(moment: datetime, latitude: float, longitude: float, *, planets: list[dict] | None = None) -> dict:
    """A full chart for one moment seen from one place."""
    planets = [dict(p) for p in planets] if planets is not None else get_planet_positions_from_utc(moment)
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
        "aspects": get_aspects(placed),
        "house_system": "Placidus",
        "rulership_system": "traditional",
        "house_rulers": get_house_rulers(houses["houses"], placed),
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


def choose_return_year(natal_sun: float, month: int, day: int, requested_year: int | None = None,
                       now: datetime | None = None) -> int:
    if requested_year is not None:
        if not 1900 <= requested_year <= 2100:
            raise ValueError("Requested return year is outside the supported range")
        return requested_year
    now = now or datetime.now(pytz.utc)
    moment = find_solar_return(natal_sun, now.year, month, day)
    return now.year if moment >= now else now.year + 1


def _point(point: dict) -> dict:
    return {"sign": point["sign"], "longitude": point["degree"],
            "degree_in_sign": round(point["degree"] % 30, 2)}


def rank_places_for(
    natal_sun_longitude: float, year: int, birth_month: int, birth_day: int,
    purpose: str = "money", places: list[dict] | None = None, top: int = 7,
    region: str = "world", natal_planets: list[dict] | None = None,
) -> dict:
    """Compare distinct locations at a single return instant; never merge charts
    because they tie under a finite scoring model. Failed candidates are reported.
    """
    from app.european_cities import as_places
    from app.relocation_scoring import (
        OVERALL, PURPOSES, combine_area_scores, score_chart, score_every_purpose)
    if purpose != OVERALL and purpose not in PURPOSES:
        raise ValueError("No scoring method for the requested purpose")
    if not 1 <= top <= 10:
        raise ValueError("Request between one and ten ranked cities")
    candidates = places if places is not None else as_places(region)
    moment = find_solar_return(natal_sun_longitude, year, birth_month, birth_day)
    # Calculate these once. Every candidate receives copies of the same positions.
    planets = get_planet_positions_from_utc(moment)
    fixed_aspects = get_aspects(planets)
    scored, failed = [], []
    for place in candidates:
        try:
            chart = chart_for(moment, place["latitude"], place["longitude"], planets=planets)
            zone = pytz.timezone(place["timezone"])
            local = moment.astimezone(zone)
            chart["natal_planets"] = natal_planets or []
            if purpose == OVERALL:
                every = score_every_purpose(chart)
                by_area = {area: every[area]["score"] for area in every}
                result = every[max(by_area, key=by_area.get)]
            else:
                by_area = None
                result = score_chart(chart, purpose)
            rulers = chart["house_rulers"]
            conditions = []
            for name in ("Jupiter", "Venus", "Saturn"):
                planet = next(p for p in chart["planets"] if p["planet"] == name)
                conditions.append({**planet, "dignity": get_dignity(name, planet["sign"]),
                    "rules_houses": [r["house"] for r in rulers if r["ruler"] == name],
                    "angularity": [a for a in chart["angular_planets"] if a["planet"] == name],
                    "aspects": [a for a in fixed_aspects if name in (a["planet_1"], a["planet_2"])]})
            mc_ruler = next(r for r in rulers if r["house"] == 10)
            angle_points = [{"planet": name, "degree": degree} for name, degree in chart["angles"].items()]
            angle_aspects = [a for a in get_aspects(chart["planets"] + angle_points)
                             if a["planet_2"] in chart["angles"] and a["planet_1"] not in chart["angles"]]
            natal_contacts = []
            if natal_planets:
                for angle in angle_points:
                    for natal in natal_planets:
                        for aspect in get_aspects([angle, {**natal, "planet": "natal " + natal["planet"]}]):
                            natal_contacts.append({**aspect, "source": "relocated_solar_return_to_natal"})
            scored.append({
                **({"by_area": by_area} if by_area is not None else {}),
                "source": "relocated_solar_return", "place": place["label"],
                "latitude": place["latitude"], "longitude": place["longitude"],
                "house_system": "Placidus", "rulership_system": "traditional",
                "score": result["score"], "score_unit": "heuristic points, not a percentage or probability",
                "be_there_at": local.isoformat(timespec="seconds"), "timezone": place["timezone"],
                "arrival_buffer_minutes": 60,
                "arrive_by": (moment - timedelta(minutes=60)).astimezone(zone).isoformat(timespec="seconds"),
                "ascendant": _point(chart["ascendant"]), "midheaven": _point(chart["midheaven"]),
                "houses": chart["houses"], "house_rulers": rulers, "mc_ruler": mc_ruler,
                "planet_conditions": conditions, "houses_of": {p["planet"]: p["house"] for p in chart["planets"]},
                "angular_planets": chart["angular_planets"], "angle_aspects": angle_aspects,
                "natal_contacts": natal_contacts,
                **{key: result[key] for key in ("from_houses", "from_angles", "from_rulers", "from_mc_contacts", "why", "advantages", "tradeoffs", "pathway_scores")},
            })
        except (ValueError, KeyError, StopIteration, swe.Error, pytz.UnknownTimeZoneError) as exc:
            failed.append({"place": place.get("label", "Unknown candidate"), "reason": type(exc).__name__})
    if not scored:
        return {"source": "relocated_solar_return", "status": "failed", "searched": len(candidates),
                "calculated": 0, "failed_candidates": failed, "best": [],
                "message": "The city calculation failed. I cannot rank locations from natal transits instead."}
    if purpose == OVERALL:
        combine_area_scores(scored)
    scored.sort(key=lambda p: (-p["score"], p["place"]))
    # Ties get the same rank but retain independent coordinates, houses and times.
    rank = 0
    for index, candidate in enumerate(scored):
        if index == 0 or candidate["score"] != scored[index - 1]["score"]:
            rank = index + 1
        candidate["rank"] = rank
    spread = round(scored[0]["score"] - scored[-1]["score"], 2)
    # Only money reports its sub-pathways, and only money can: under an overall
    # ranking each city's breakdown comes from whichever area it scored best
    # in, so the keys differ from one city to the next.
    winners = {}
    if purpose == "money":
        for pathway in scored[0]["pathway_scores"]:
            best_score = max(p["pathway_scores"][pathway] for p in scored)
            winners[pathway] = {"score": best_score, "places": [p["place"] for p in scored if p["pathway_scores"][pathway] == best_score]}
    return {
        "source": "relocated_solar_return", "status": "partial" if failed else "ok",
        "purpose": purpose, "year": year, "region": region,
        "searched": len(candidates), "calculated": len(scored), "failed_candidates": failed,
        "returns_at_utc": moment.isoformat(),
        "base_solar_return": {"source": "solar_return", "scope": "location-independent planetary positions and mutual aspects only",
                              "moment_utc": moment.isoformat(), "planets": planets, "aspects": fixed_aspects},
        "scoring_version": "relocation-v2",
        "scoring_reviewed_by_astrologer": False,
        "score_unit": "heuristic points, not /100, financial returns or success probabilities",
        "scoring_note": "Existing house/angle weights with corrected occupancy and draft ruler-condition/aspect modifiers. MC sign has no direct score. Close MC aspects add/subtract 0.5 points; MC or its ruler contacts to natal personal/social planets add/subtract 0.25. Conjunctions receive no extra aspect bonus; current planet-angle conjunctions use the angular table. Subgoal scores compare occupants and rulers of each financial house, with MC contacts included for career; they are not separate validated forecasts.",
        "note": "One global instant, expressed in each city's local timezone including daylight saving. Both latitude and longitude determine houses and angles. Planetary zodiacal positions and mutual aspects are identical everywhere. Tied scores do not mean identical charts. Arrival buffer is practical scheduling advice, not an astronomical calculation.",
        "does_location_matter_this_year": "No score difference under this model" if spread == 0 else "Scores differ under this model; the spread is not a prediction of financial outcomes",
        "score_spread": spread,
        "cities_with_a_planet_on_an_angle": sum(bool(p["angular_planets"]) for p in scored),
        "best": scored[:top], "best_by_financial_pathway": winners if purpose == "money" else {},
        "worst": scored[-3:][::-1],
    }


def rank_places_to_live(
    birth_moment: datetime, purpose: str = "money", places: list[dict] | None = None,
    top: int = 7, region: str = "world", natal_planets: list[dict] | None = None,
) -> dict:
    """Where a place would suit someone to live, from the relocated natal chart.

    The other ranking in this file answers a different question. A relocated
    solar return says where to spend one birthday; this says how a city would
    sit under you if you lived in it. Same birth moment, same planets in the
    same degrees — only the houses and the angles move, because those depend on
    where on Earth you were standing. Venus in the 1st in Sofia is Venus in the
    2nd in London, and that is the entire technique.

    Answering "where should I live?" with the solar return produced a list of
    cities to be in for a single evening, complete with an arrival time.
    """
    from app.european_cities import as_places
    from app.relocation_scoring import (
        OVERALL, PURPOSES, combine_area_scores, score_chart, score_every_purpose)

    if purpose != OVERALL and purpose not in PURPOSES:
        raise ValueError("No scoring method for the requested purpose")
    if not 1 <= top <= 10:
        raise ValueError("Request between one and ten ranked cities")

    candidates = places if places is not None else as_places(region)
    # One moment, one set of planets, computed once and shared by every city.
    planets = get_planet_positions_from_utc(birth_moment)

    scored, failed = [], []
    for place in candidates:
        try:
            chart = chart_for(birth_moment, place["latitude"], place["longitude"], planets=planets)
            chart["natal_planets"] = natal_planets or []
            if purpose == OVERALL:
                # Every area, so an unqualified question gets a whole answer.
                # The combined figure needs the full field to normalise
                # against, so it is filled in after the loop.
                every = score_every_purpose(chart)
                by_area = {area: every[area]["score"] for area in every}
                result = every[max(by_area, key=by_area.get)]
            else:
                by_area = None
                result = score_chart(chart, purpose)
            scored.append({
                **({"by_area": by_area} if by_area is not None else {}),
                "source": "relocated_natal", "place": place["label"],
                "latitude": place["latitude"], "longitude": place["longitude"],
                "timezone": place.get("timezone"),
                "house_system": "Placidus", "rulership_system": "traditional",
                "score": result["score"],
                "score_unit": "heuristic points, not a percentage or probability",
                "ascendant": _point(chart["ascendant"]), "midheaven": _point(chart["midheaven"]),
                "houses_of": {p["planet"]: p["house"] for p in chart["planets"]},
                "angular_planets": chart["angular_planets"],
                **{key: result[key] for key in
                   ("from_houses", "from_angles", "from_rulers", "from_mc_contacts",
                    "why", "advantages", "tradeoffs", "pathway_scores")},
            })
        except (ValueError, KeyError, StopIteration, swe.Error, pytz.UnknownTimeZoneError) as exc:
            failed.append({"place": place.get("label", "Unknown candidate"), "reason": type(exc).__name__})

    if not scored:
        return {"source": "relocated_natal", "status": "failed", "searched": len(candidates),
                "calculated": 0, "failed_candidates": failed, "best": [],
                "message": "The relocation calculation failed. I cannot rank places from natal transits instead."}

    if purpose == OVERALL:
        combine_area_scores(scored)
    scored.sort(key=lambda p: (-p["score"], p["place"]))
    rank = 0
    for index, candidate in enumerate(scored):
        if index == 0 or candidate["score"] != scored[index - 1]["score"]:
            rank = index + 1
        candidate["rank"] = rank
    spread = round(scored[0]["score"] - scored[-1]["score"], 2)

    return {
        "source": "relocated_natal", "status": "partial" if failed else "ok",
        "purpose": purpose, "region": region,
        "searched": len(candidates), "calculated": len(scored), "failed_candidates": failed,
        "scoring_version": "relocation-v2",
        "scoring_reviewed_by_astrologer": False,
        "score_unit": "heuristic points, not /100 and not a probability",
        "note": (
            ("Nothing in the question said what it was for, so every area was "
             "scored and the ranking is the combination — each area normalised "
             "so none outvotes the others by having a bigger table. "
             "'by_area' holds the real per-area figures and 'strongest_areas' "
             "the two each city leads on: say what a place is good FOR, not "
             "just that it ranked. A city can top the list and still be the "
             "weakest of them for one thing, and that is worth saying. "
             if purpose == "overall" else "") +
            "Give the reason, never a placement or a score. 'good_for' and "
            "'costs' are already in plain words and are what to say; naming a "
            "planet or a house here is the one thing that gets the whole "
            "ranking thrown out and replaced with a bare report. "
            "How each city's relocated birth chart scores for this purpose — a "
            "place to live in, not a birthday to travel for. The planets and the "
            "aspects between them are identical everywhere; only the houses and "
            "angles change. There is no date and no arrival time attached to "
            "this: say what the top places offer and which one you would pick, "
            "never a schedule. Tied scores are equal, not ranked. Say plainly "
            "how much the choice is worth — in a flat year telling someone to "
            "move is selling a difference that is not there."
        ),
        "does_location_matter": (
            "Barely — the scores are close enough that this is not a strong reason to move"
            if spread < 6 else
            "Somewhat — there is a real but modest difference between the best and worst"
            if spread < 14 else
            "A great deal — the best and worst places are meaningfully different charts"
        ),
        "score_spread": spread,
        "cities_with_a_planet_on_an_angle": sum(bool(p["angular_planets"]) for p in scored),
        "best": scored[:top],
        "worst": scored[-3:][::-1],
    }
