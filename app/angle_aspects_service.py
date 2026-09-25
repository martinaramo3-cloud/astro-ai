"""Aspects to the angles and to house cusps.

The gap the career data audit found: aspects were computed between planets
only, so a planet squaring the Midheaven did not exist anywhere in the system.
For a career reading that is the largest single hole — the career point had a
sign and a ruler and nothing aspecting it.

Two things live here, both needed by the earning-route engine:

  aspects to the four angles, which are points and not bodies, so they take
  tighter orbs than a planet-to-planet aspect does

  conjunctions to an arbitrary house cusp, because the weight table awards
  points for a planet closely conjunct the SECOND cusp, which is not an angle
  and has no other way of being seen
"""
from __future__ import annotations

from app.aspect_services import ASPECTS, angle_difference

# Angles are directions, not objects, so they carry no light of their own and
# a wide aspect to one says much less than a wide aspect between two planets.
# Six degrees is the planet-to-planet orb in this codebase; five is the
# conventional tightening for an angle, and three for a cusp that is not an
# angle at all.
ANGLE_ORB = 5.0
CUSP_ORB = 3.0
# "Closely conjunct", where the weight table asks for close.
CLOSE_CONJUNCTION = 3.0


def derive_angles(ascendant: dict | None, midheaven: dict | None,
                  houses: list | None = None) -> dict[str, float]:
    """The four angles in degrees, including the two nobody stores.

    Descendant and IC are the opposite points, so they are never stored and
    are always available. An answer about work has reason to care about the
    IC — where the career axis is anchored — and nothing could see it.
    """
    found: dict[str, float] = {}
    if isinstance(ascendant, dict) and isinstance(ascendant.get("degree"), (int, float)):
        found["Ascendant"] = float(ascendant["degree"]) % 360
    if isinstance(midheaven, dict) and isinstance(midheaven.get("degree"), (int, float)):
        found["Midheaven"] = float(midheaven["degree"]) % 360
    # Fall back to the cusps when the angles were not passed separately.
    for cusp_number, name in ((1, "Ascendant"), (10, "Midheaven")):
        if name not in found:
            cusp = _cusp_degree(houses, cusp_number)
            if cusp is not None:
                found[name] = cusp
    if "Ascendant" in found:
        found["Descendant"] = (found["Ascendant"] + 180) % 360
    if "Midheaven" in found:
        found["Imum Coeli"] = (found["Midheaven"] + 180) % 360
    return found


def _cusp_degree(houses: list | None, number: int) -> float | None:
    for house in houses or []:
        if house.get("house") == number:
            for key in ("degree", "cusp", "cusp_degree", "longitude"):
                if isinstance(house.get(key), (int, float)):
                    return float(house[key]) % 360
    return None


def get_angle_aspects(planet_positions: list, *, ascendant: dict | None = None,
                      midheaven: dict | None = None, houses: list | None = None,
                      orb: float = ANGLE_ORB) -> list[dict]:
    """Every aspect between a planet and one of the four angles.

    Shaped like `get_aspects` so anything that reads planet aspects can read
    these without a special case: planet_1 is the planet, planet_2 the angle.
    """
    angles = derive_angles(ascendant, midheaven, houses)
    found = []
    for planet in planet_positions or []:
        degree = planet.get("degree")
        if not isinstance(degree, (int, float)):
            continue
        for angle_name, angle_degree in angles.items():
            separation = angle_difference(degree, angle_degree)
            closest, closest_orb = None, None
            for aspect_name, exact in ASPECTS.items():
                this_orb = abs(separation - exact)
                if this_orb <= orb and (closest_orb is None or this_orb < closest_orb):
                    closest, closest_orb = aspect_name, this_orb
            if closest:
                found.append({
                    "planet_1": planet["planet"],
                    "planet_2": angle_name,
                    "aspect": closest,
                    "angle": round(separation, 2),
                    "orb": round(closest_orb, 2),
                    "to_an_angle": True,
                })
    return sorted(found, key=lambda a: a["orb"])


def conjunct_cusp(planet_positions: list, houses: list, house_number: int,
                  orb: float = CLOSE_CONJUNCTION) -> list[dict]:
    """Planets sitting on a house cusp, for cusps that are not angles.

    The weight table awards points for a planet closely conjunct the second
    cusp. A planet can be in the 1st house and still be conjunct the 2nd cusp
    from below, which is why this asks about the cusp rather than the house.
    """
    cusp = _cusp_degree(houses, house_number)
    if cusp is None:
        return []
    on_it = []
    for planet in planet_positions or []:
        degree = planet.get("degree")
        if not isinstance(degree, (int, float)):
            continue
        separation = angle_difference(degree, cusp)
        if separation <= orb:
            on_it.append({"planet": planet["planet"], "cusp": house_number,
                          "orb": round(separation, 2)})
    return sorted(on_it, key=lambda p: p["orb"])
