import swisseph as swe

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

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
}


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
            "retrograde": is_retrograde
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

    ascendant = {
        "degree": round(asc_degree, 2),
        "sign": get_zodiac_sign(asc_degree)
    }

    return {
        "ascendant": ascendant,
        "houses": house_cusps
    }