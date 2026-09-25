"""The natal evidence a career or money question needs, calculated in full.

Section 4 of the co-founder's rules, which is a data requirement rather than
an interpretive one. Four things were missing or truncated:

  ALL aspects involving the rulers of the 2nd, 6th, 7th, 8th, 10th and 11th —
  not the four tightest aspects in the whole chart, which is what a career
  question used to receive and which routinely contained none of them.

  Aspects to the MC and the Ascendant, with exact orbs. These did not exist
  anywhere in the system until the earning-route work.

  Planets IN those houses kept separate from planets CONJUNCT their cusps.
  A planet at the end of the 1st, conjunct the 2nd cusp, is a different claim
  from a planet sitting in the 2nd, and one list cannot say both.

  The full condition of the 2nd and 10th rulers: sign, house, dignity,
  retrograde status, and their own aspects.

Every orb here is measured against the documented policy in `orb_policy`, and
every aspect carries how exact it is, so nothing downstream has to treat an 8°
conjunction as it would treat a 1° one.
"""
from __future__ import annotations

from app.angle_aspects_service import conjunct_cusp, derive_angles, get_angle_aspects
from app.aspect_services import ASPECTS, angle_difference
from app.chart_analysis_service import get_house_rulers
from app.orb_policy import TO_CUSP, describe, exactness, within_orb

# The houses a career or money question turns on, per her section 4.
CAREER_HOUSES = (2, 6, 7, 8, 10, 11)


def _aspects_between(points: list[dict], policy_points: bool = True) -> list[dict]:
    """Every aspect among these points, measured against the orb policy.

    `aspect_services.get_aspects` uses one flat six-degree rule for everything.
    That is fine for the rest of the app and wrong here: it drops a 7°
    conjunction to the Sun, which the policy admits, and keeps a 6° sextile,
    which the policy does not.
    """
    found = []
    for index, one in enumerate(points):
        for two in points[index + 1:]:
            if not isinstance(one.get("degree"), (int, float)):
                continue
            if not isinstance(two.get("degree"), (int, float)):
                continue
            separation = angle_difference(one["degree"], two["degree"])
            for name, exact in ASPECTS.items():
                orb = round(abs(separation - exact), 2)
                if not within_orb(name, orb, one["planet"], two["planet"]):
                    continue
                found.append({
                    "planet_1": one["planet"], "planet_2": two["planet"],
                    "aspect": name, "orb": orb,
                    "exactness": exactness(name, orb, one["planet"], two["planet"]),
                })
                break
    return sorted(found, key=lambda a: a["orb"])


def build_career_natal_data(chart: dict) -> dict:
    """Everything section 4 asks to be calculated and passed through.

    Returns `available: False` when there is no birth time. Her rule 5: with
    an unknown or unreliable birth time, no house, Ascendant or MC claim may
    be made at all — so this refuses to produce one rather than producing a
    weaker one.
    """
    planets = chart.get("planet_positions") or []
    houses = chart.get("houses") or []
    if not planets:
        return {"available": False, "reason": "no chart"}
    if len(houses) != 12 or not chart.get("birth_time_known", True):
        return {
            "available": False,
            "reason": ("no reliable birth time, so nothing here may rest on a "
                       "house, the Ascendant or the Midheaven"),
            "what_can_still_be_said": "planets by sign, and aspects between them",
            "aspects_between_planets": _aspects_between(planets),
        }

    rulers = {record["house"]: record for record in get_house_rulers(houses, planets)}
    by_name = {planet["planet"]: planet for planet in planets}
    angles = derive_angles(chart.get("ascendant"), chart.get("midheaven"), houses)

    # Every aspect in the chart, then the ones that involve a career ruler.
    all_aspects = _aspects_between(planets)
    career_rulers = {rulers[house]["ruler"] for house in CAREER_HOUSES if house in rulers}
    ruler_aspects = [
        {**aspect,
         "involves": sorted(
             {f"{house}th ruler" for house in CAREER_HOUSES
              if house in rulers
              and rulers[house]["ruler"] in (aspect["planet_1"], aspect["planet_2"])})}
        for aspect in all_aspects
        if career_rulers & {aspect["planet_1"], aspect["planet_2"]}
    ]

    angle_aspects = [
        {**aspect, "exactness": exactness(aspect["aspect"], aspect["orb"],
                                          aspect["planet_1"], aspect["planet_2"])}
        for aspect in get_angle_aspects(
            planets, ascendant=chart.get("ascendant"),
            midheaven=chart.get("midheaven"), houses=houses)
        if aspect["planet_2"] in ("Midheaven", "Ascendant")
        and within_orb(aspect["aspect"], aspect["orb"],
                       aspect["planet_1"], aspect["planet_2"])
    ]

    # In the house, and on the cusp — two different claims, two lists.
    occupants = {house: [] for house in CAREER_HOUSES}
    for planet in planets:
        if planet.get("house") in occupants:
            occupants[planet["house"]].append(planet["planet"])
    on_cusps = {house: conjunct_cusp(planets, houses, house, orb=TO_CUSP)
                for house in CAREER_HOUSES}

    def condition_of(house: int) -> dict:
        record = rulers.get(house)
        if not record:
            return {}
        name = record["ruler"]
        planet = by_name.get(name, {})
        return {
            "house_ruled": house,
            "planet": name,
            "sign": record["ruler_in_sign"],
            "in_house": record["ruler_in_house"],
            "dignity": record["ruler_dignity"],
            "retrograde": bool(planet.get("retrograde")),
            "aspects": [a for a in all_aspects
                        if name in (a["planet_1"], a["planet_2"])],
            "aspects_to_angles": [a for a in angle_aspects if a["planet_1"] == name],
        }

    return {
        "available": True,
        "orb_policy": describe(),
        "houses_this_question_turns_on": list(CAREER_HOUSES),
        "rulers": {
            house: {
                "cusp_sign": rulers[house]["cusp_sign"],
                "ruler": rulers[house]["ruler"],
                "ruler_in_sign": rulers[house]["ruler_in_sign"],
                "ruler_in_house": rulers[house]["ruler_in_house"],
                "ruler_dignity": rulers[house]["ruler_dignity"],
            }
            for house in CAREER_HOUSES if house in rulers
        },
        # The requirement that was quietly being violated: all of them, not
        # the four tightest in the chart.
        "aspects_involving_those_rulers": ruler_aspects,
        "aspects_to_the_midheaven_and_ascendant": angle_aspects,
        "planets_in_those_houses": occupants,
        "planets_conjunct_those_cusps": on_cusps,
        "second_ruler": condition_of(2),
        "tenth_ruler": condition_of(10),
        "midheaven": {"sign": (chart.get("midheaven") or {}).get("sign"),
                      "degree": angles.get("Midheaven")},
        "ascendant": {"sign": (chart.get("ascendant") or {}).get("sign"),
                      "degree": angles.get("Ascendant")},
        "note": ("Planets IN a house and planets CONJUNCT its cusp are listed "
                 "separately because they are different claims. Every aspect "
                 "carries its exact orb and how exact it is; closer counts for "
                 "more, per the orb policy above."),
    }
