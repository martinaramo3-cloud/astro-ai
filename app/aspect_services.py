ASPECTS = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "opposition": 180,
}

ASPECT_ORB = 6


def angle_difference(deg1: float, deg2: float) -> float:
    diff = abs(deg1 - deg2) % 360
    return min(diff, 360 - diff)


def get_aspects(planet_positions):
    aspects_found = []

    for i in range(len(planet_positions)):
        for j in range(i + 1, len(planet_positions)):
            p1 = planet_positions[i]
            p2 = planet_positions[j]

            diff = angle_difference(p1["degree"], p2["degree"])

            closest_aspect = None
            closest_orb = None

            for aspect_name, aspect_angle in ASPECTS.items():
                orb = abs(diff - aspect_angle)

                if orb <= ASPECT_ORB:
                    if closest_orb is None or orb < closest_orb:
                        closest_aspect = aspect_name
                        closest_orb = orb

            if closest_aspect:
                aspects_found.append({
                    "planet_1": p1["planet"],
                    "planet_2": p2["planet"],
                    "aspect": closest_aspect,
                    "angle": round(diff, 2),
                    "orb": round(closest_orb, 2)
                })

    return sorted(aspects_found, key=lambda x: x["orb"])