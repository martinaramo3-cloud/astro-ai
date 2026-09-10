import os

import swisseph as swe

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Chiron is not in the ephemeris compiled into the library — it needs a data
# file. seas_18.se1 covers the asteroids from 1800 to 2400 and ships beside the
# code, so it is present wherever this runs rather than depending on something
# being installed on the machine.
_EPHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ephe")
if os.path.isdir(_EPHE_DIR):
    swe.set_ephe_path(_EPHE_DIR)


PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    # The lunar nodes: where the Moon's path crosses the ecliptic. The North
    # Node is the growth direction, the South the over-familiar comfort — and
    # since they are always exactly opposite, only the North is tracked. Any
    # aspect to one is the mirrored aspect to the other, so carrying both would
    # double every transit for no extra information.
    "North Node": swe.TRUE_NODE,
    # The old wound that becomes the thing you understand best. Needs the
    # asteroid data file above; without it this raises rather than returning
    # something wrong, which is the right failure.
    "Chiron": swe.CHIRON,
}

# The nodes travel backwards almost all the time; saying so on every reading is
# noise, not insight. Chiron would live here too — it needs an ephemeris data
# file (seas_18.se1) that the Python package does not ship.
RETROGRADE_NOT_REPORTED = {"North Node"}


def get_julian_day_from_utc(utc_dt) -> float:
    hour_decimal = (
        utc_dt.hour
        + utc_dt.minute / 60.0
        + utc_dt.second / 3600.0
        + utc_dt.microsecond / 3600000000.0
    )

    return swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        hour_decimal
    )


def get_zodiac_sign(degree: float) -> str:
    normalized_degree = degree % 360
    sign_index = int(normalized_degree // 30)
    return ZODIAC_SIGNS[sign_index]


def is_degree_between(start: float, end: float, degree: float) -> bool:
    start = start % 360
    end = end % 360
    degree = degree % 360

    if start < end:
        return start <= degree < end

    return degree >= start or degree < end


def get_planet_house(planet_degree: float, house_cusps: list) -> int:
    for i in range(12):
        current_cusp = house_cusps[i]["degree"]
        next_cusp = house_cusps[(i + 1) % 12]["degree"]

        if is_degree_between(current_cusp, next_cusp, planet_degree):
            return house_cusps[i]["house"]

    return 12


def add_house_to_planets(planets: list, houses: list) -> list:
    planets_with_houses = []

    for planet in planets:
        planet_with_house = planet.copy()
        planet_with_house["house"] = get_planet_house(
            planet["degree"],
            houses
        )
        planets_with_houses.append(planet_with_house)

    return planets_with_houses


def get_planet_positions_from_utc(utc_dt):
    julian_day = get_julian_day_from_utc(utc_dt)
    results = []

    for planet_name, planet_id in PLANETS.items():
        calc_result = swe.calc_ut(julian_day, planet_id)

        planet_degree = calc_result[0][0] % 360
        planet_speed = calc_result[0][3]
        degree_in_sign = planet_degree % 30
        is_retrograde = planet_speed < 0

        results.append({
            "planet": planet_name,
            "degree": round(planet_degree, 2),
            "sign": get_zodiac_sign(planet_degree),
            "degree_in_sign": round(degree_in_sign, 2),
            "retrograde": is_retrograde and planet_name not in RETROGRADE_NOT_REPORTED,
        })

    return results


def get_houses_and_ascendant(utc_dt, latitude: float, longitude: float):
    julian_day = get_julian_day_from_utc(utc_dt)

    houses, ascmc = swe.houses(julian_day, latitude, longitude, b'P')

    house_cusps = []
    for i, cusp in enumerate(houses[:12], start=1):
        normalized_cusp = cusp % 360
        house_cusps.append({
            "house": i,
            "degree": round(normalized_cusp, 2),
            "sign": get_zodiac_sign(normalized_cusp)
        })

    asc_degree = ascmc[0] % 360
    mc_degree = ascmc[1] % 360

    ascendant = {
        "degree": round(asc_degree, 2),
        "sign": get_zodiac_sign(asc_degree)
    }

    # The Midheaven was being calculated on the line above and discarded. It is
    # the top of the chart — career, reputation, what you become known for —
    # and a planet crossing it is one of the most strongly felt transits there
    # is, so it has to be something a transit can actually land on.
    midheaven = {
        "degree": round(mc_degree, 2),
        "sign": get_zodiac_sign(mc_degree)
    }

    return {
        "ascendant": ascendant,
        "midheaven": midheaven,
        "houses": house_cusps,
        # Shaped like planets, so the angles can be passed straight into the
        # transit search as targets rather than needing a parallel code path.
        "angles": [
            {"planet": "Ascendant", "degree": ascendant["degree"], "sign": ascendant["sign"]},
            {"planet": "Midheaven", "degree": midheaven["degree"], "sign": midheaven["sign"]},
        ],
    }