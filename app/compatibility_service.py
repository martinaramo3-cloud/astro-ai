SYNSTRY_ASPECTS = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "opposition": 180,
}

SYNSTRY_ORB = 6

IMPORTANT_PLANETS = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Saturn"}


def angle_difference(deg1: float, deg2: float) -> float:
    diff = abs(deg1 - deg2) % 360
    return min(diff, 360 - diff)


def get_synastry_aspects(planets_1: list, planets_2: list):
    synastry_aspects = []

    for p1 in planets_1:
        for p2 in planets_2:
            diff = angle_difference(p1["degree"], p2["degree"])

            closest_aspect = None
            closest_orb = None
            closest_angle = None

            for aspect_name, aspect_angle in SYNSTRY_ASPECTS.items():
                orb = abs(diff - aspect_angle)

                if orb <= SYNSTRY_ORB:
                    if closest_orb is None or orb < closest_orb:
                        closest_aspect = aspect_name
                        closest_orb = orb
                        closest_angle = diff

            if closest_aspect:
                synastry_aspects.append({
                    "person_1_planet": p1["planet"],
                    "person_1_sign": p1["sign"],
                    "person_1_house": p1["house"],
                    "person_2_planet": p2["planet"],
                    "person_2_sign": p2["sign"],
                    "person_2_house": p2["house"],
                    "aspect": closest_aspect,
                    "angle": round(closest_angle, 2),
                    "orb": round(closest_orb, 2),
                    "is_priority": (
                        p1["planet"] in IMPORTANT_PLANETS and
                        p2["planet"] in IMPORTANT_PLANETS
                    )
                })

    return sorted(
        synastry_aspects,
        key=lambda x: (not x["is_priority"], x["orb"])
    ) 