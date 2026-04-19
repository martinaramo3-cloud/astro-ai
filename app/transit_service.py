from datetime import datetime
import pytz

from app.astrology_engine import get_planet_positions_from_utc

TRANSIT_ASPECTS = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "opposition": 180,
}

TRANSIT_ORB = 3


def angle_difference(deg1: float, deg2: float) -> float:
    diff = abs(deg1 - deg2) % 360
    return min(diff, 360 - diff)


def get_current_transit_positions():
    now_utc = datetime.now(pytz.utc)
    return get_planet_positions_from_utc(now_utc)


def get_transit_aspects(natal_planets: list, transit_planets: list):
    active_transits = []

    for transit in transit_planets:
        for natal in natal_planets:
            diff = angle_difference(transit["degree"], natal["degree"])

            closest_aspect = None
            closest_orb = None
            closest_angle = None

            for aspect_name, aspect_angle in TRANSIT_ASPECTS.items():
                orb = abs(diff - aspect_angle)

                if orb <= TRANSIT_ORB:
                    if closest_orb is None or orb < closest_orb:
                        closest_aspect = aspect_name
                        closest_orb = orb
                        closest_angle = diff

            if closest_aspect:
                active_transits.append({
                    "transit_planet": transit["planet"],
                    "transit_sign": transit["sign"],
                    "transit_degree": transit["degree"],
                    "transit_retrograde": transit["retrograde"],
                    "natal_planet": natal["planet"],
                    "natal_sign": natal["sign"],
                    "natal_degree": natal["degree"],
                    "aspect": closest_aspect,
                    "angle": round(closest_angle, 2),
                    "orb": round(closest_orb, 2)
                })

    return sorted(active_transits, key=lambda x: x["orb"]) 