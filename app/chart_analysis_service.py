# app/chart_analysis_service.py

from itertools import combinations
from typing import Dict, List, Optional


ASPECT_DEFINITIONS = {
    "conjunction": {"angle": 0, "orb": 8},
    "sextile": {"angle": 60, "orb": 4},
    "square": {"angle": 90, "orb": 6},
    "trine": {"angle": 120, "orb": 6},
    "opposition": {"angle": 180, "orb": 8},
    "quincunx": {"angle": 150, "orb": 3},
}

ANGLE_ORB = 5
STELLIUM_MIN_PLANETS = 3

SIGN_RULERS_MODERN = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Pluto",      # or Mars if you prefer traditional
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Uranus",    # or Saturn if traditional
    "Pisces": "Neptune",     # or Jupiter if traditional
}

def angular_distance(deg1: float, deg2: float) -> float:
    """
    Smallest angle between two points on the zodiac circle.
    Returns a value between 0 and 180.
    """
    diff = abs(deg1 - deg2) % 360
    return min(diff, 360 - diff)
def get_allowed_orb(planet1: str, planet2: str, aspect_type: str) -> float:
    """
    Allow slightly wider orb if Sun or Moon is involved.
    """
    base_orb = ASPECT_DEFINITIONS[aspect_type]["orb"]

    luminaries = {"Sun", "Moon"}
    if planet1 in luminaries or planet2 in luminaries:
        return base_orb + 1.5

    return base_orb


def calculate_aspect_between(point1: Dict, point2: Dict) -> Optional[Dict]:
    """
    point = {"name": "Venus", "longitude": 102.4}
    """
    distance = angular_distance(point1["longitude"], point2["longitude"])

    for aspect_name, config in ASPECT_DEFINITIONS.items():
        exact_angle = config["angle"]
        orb = abs(distance - exact_angle)
        allowed_orb = get_allowed_orb(point1["name"], point2["name"], aspect_name)

        if orb <= allowed_orb:
            return {
                "type": aspect_name,
                "planet1": point1["name"],
                "planet2": point2["name"],
                "angle": round(distance, 2),
                "exact_angle": exact_angle,
                "orb": round(orb, 2),
            }

    return None

def calculate_all_aspects(planets: List[Dict]) -> List[Dict]:
    aspects = []

    for p1, p2 in combinations(planets, 2):
        aspect = calculate_aspect_between(p1, p2)
        if aspect:
            aspects.append(aspect)

    return aspects 

[
    {"name": "Sun", "sign": "Leo", "house": 10, "longitude": 135.2},
    {"name": "Moon", "sign": "Sagittarius", "house": 2, "longitude": 251.7},
]

def get_chart_ruler(ascendant_sign: str, planets: List[Dict]) -> Optional[Dict]:
    ruler_name = SIGN_RULERS_MODERN.get(ascendant_sign)
    if not ruler_name:
        return None

    ruler_data = next((p for p in planets if p["name"] == ruler_name), None)
    if not ruler_data:
        return {"ruler": ruler_name, "placement": None}

    return {
        "ruler": ruler_name,
        "sign": ruler_data.get("sign"),
        "house": ruler_data.get("house"),
        "longitude": ruler_data.get("longitude"),
    }
def is_within_orb(deg1: float, deg2: float, orb: float) -> float:
    return angular_distance(deg1, deg2)


def detect_planets_near_angles(planets: List[Dict], angles: Dict[str, float], orb: float = ANGLE_ORB) -> List[Dict]:
    """
    angles = {
        "ASC": 123.4,
        "DSC": 303.4,
        "MC": 210.2,
        "IC": 30.2
    }
    """
    results = []

    for planet in planets:
        for angle_name, angle_longitude in angles.items():
            distance = is_within_orb(planet["longitude"], angle_longitude, orb)
            if distance <= orb:
                results.append({
                    "planet": planet["name"],
                    "angle": angle_name,
                    "orb": round(distance, 2),
                })

    return results
def detect_stelliums_by_sign(planets: List[Dict], min_planets: int = STELLIUM_MIN_PLANETS) -> List[Dict]:
    grouped = {}

    for planet in planets:
        sign = planet.get("sign")
        if sign:
            grouped.setdefault(sign, []).append(planet["name"])

    results = []
    for sign, members in grouped.items():
        if len(members) >= min_planets:
            results.append({
                "type": "sign_stellium",
                "sign": sign,
                "planets": members,
            })

    return results


def detect_stelliums_by_house(planets: List[Dict], min_planets: int = STELLIUM_MIN_PLANETS) -> List[Dict]:
    grouped = {}

    for planet in planets:
        house = planet.get("house")
        if house is not None:
            grouped.setdefault(house, []).append(planet["name"])

    results = []
    for house, members in grouped.items():
        if len(members) >= min_planets:
            results.append({
                "type": "house_stellium",
                "house": house,
                "planets": members,
            })

    return results
def has_aspect(aspects: List[Dict], p1: str, p2: str, aspect_type: str) -> bool:
    for aspect in aspects:
        names = {aspect["planet1"], aspect["planet2"]}
        if names == {p1, p2} and aspect["type"] == aspect_type:
            return True
    return False


def detect_grand_trines(planets: List[Dict], aspects: List[Dict]) -> List[Dict]:
    results = []

    for p1, p2, p3 in combinations(planets, 3):
        n1, n2, n3 = p1["name"], p2["name"], p3["name"]

        if (
            has_aspect(aspects, n1, n2, "trine") and
            has_aspect(aspects, n1, n3, "trine") and
            has_aspect(aspects, n2, n3, "trine")
        ):
            results.append({
                "type": "grand_trine",
                "planets": [n1, n2, n3],
            })

    return results
def detect_t_squares(planets: List[Dict], aspects: List[Dict]) -> List[Dict]:
    results = []

    for p1, p2, p3 in combinations(planets, 3):
        n1, n2, n3 = p1["name"], p2["name"], p3["name"]

        combos = [
            (n1, n2, n3),
            (n1, n3, n2),
            (n2, n3, n1),
        ]

        for opp_a, opp_b, apex in combos:
            if (
                has_aspect(aspects, opp_a, opp_b, "opposition") and
                has_aspect(aspects, opp_a, apex, "square") and
                has_aspect(aspects, opp_b, apex, "square")
            ):
                results.append({
                    "type": "t_square",
                    "planets": [opp_a, opp_b, apex],
                    "opposition": [opp_a, opp_b],
                    "apex": apex,
                })

    return results
def detect_yods(planets: List[Dict], aspects: List[Dict]) -> List[Dict]:
    results = []

    for p1, p2, p3 in combinations(planets, 3):
        n1, n2, n3 = p1["name"], p2["name"], p3["name"]

        combos = [
            (n1, n2, n3),
            (n1, n3, n2),
            (n2, n3, n1),
        ]

        for base1, base2, apex in combos:
            if (
                has_aspect(aspects, base1, base2, "sextile") and
                has_aspect(aspects, base1, apex, "quincunx") and
                has_aspect(aspects, base2, apex, "quincunx")
            ):
                results.append({
                    "type": "yod",
                    "planets": [base1, base2, apex],
                    "base": [base1, base2],
                    "apex": apex,
                })

    return results
def analyze_chart(
    planets: List[Dict],
    ascendant_sign: str,
    angles: Dict[str, float],
) -> Dict:
    aspects = calculate_all_aspects(planets)

    chart_ruler = get_chart_ruler(ascendant_sign, planets)
    angle_contacts = detect_planets_near_angles(planets, angles)
    sign_stelliums = detect_stelliums_by_sign(planets)
    house_stelliums = detect_stelliums_by_house(planets)
    grand_trines = detect_grand_trines(planets, aspects)
    t_squares = detect_t_squares(planets, aspects)
    yods = detect_yods(planets, aspects)

    return {
        "chart_ruler": chart_ruler,
        "angle_contacts": angle_contacts,
        "stelliums": sign_stelliums + house_stelliums,
        "major_patterns": grand_trines + t_squares + yods,
        "aspects": aspects,
    }
