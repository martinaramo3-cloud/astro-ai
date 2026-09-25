from app.astrology_engine import add_house_to_planets
from app.content_repository import get_synastry_rules

SYNSTRY_ASPECTS = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "opposition": 180,
}

RULES = get_synastry_rules()
SYNSTRY_ORB = RULES["orb_rules"]["default_max"]

IMPORTANT_PLANETS = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Saturn"}
PERSONAL_PLANETS = {"Sun", "Moon", "Mercury", "Venus", "Mars"}
OUTER_PLANETS = {"Uranus", "Neptune", "Pluto"}
SOFT_ASPECTS = {"trine", "sextile"}
HARD_ASPECTS = {"square", "opposition"}
EMOTIONAL_PLANETS = {"Moon", "Venus"}


def angle_difference(deg1: float, deg2: float) -> float:
    diff = abs(deg1 - deg2) % 360
    return min(diff, 360 - diff)


def _get_max_orb(planet_1: str, planet_2: str) -> float:
    if planet_1 in OUTER_PLANETS or planet_2 in OUTER_PLANETS:
        return RULES["orb_rules"]["outer_planet_max"]
    if planet_1 in {"Sun", "Moon"} or planet_2 in {"Sun", "Moon"}:
        return RULES["orb_rules"]["luminary_max"]
    return RULES["orb_rules"]["default_max"]


def _get_orb_strength(orb: float) -> dict:
    for band in RULES["orb_rules"]["strength_bands"]:
        if orb <= band["max_orb"]:
            return band

    return {
        "label": "ignored",
        "multiplier": 0
    }


def _pair_key(planet_1: str, planet_2: str) -> tuple[str, str]:
    return tuple(sorted((planet_1, planet_2)))


def _sum_effects(base: dict, extra: dict, multiplier: float = 1.0) -> dict:
    for key, value in extra.items():
        base[key] = base.get(key, 0) + round(value * multiplier, 2)
    return base


def _match_pair_rule(aspect: dict, pair_rule: dict) -> bool:
    if _pair_key(aspect["person_1_planet"], aspect["person_2_planet"]) != tuple(sorted(pair_rule["planets"])):
        return False

    allowed_aspects = pair_rule.get("allowed_aspects")
    if allowed_aspects and aspect["aspect"] not in allowed_aspects:
        return False

    return True


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
                max_orb = _get_max_orb(p1["planet"], p2["planet"])

                if orb <= max_orb:
                    if closest_orb is None or orb < closest_orb:
                        closest_aspect = aspect_name
                        closest_orb = orb
                        closest_angle = diff

            if closest_aspect:
                strength = _get_orb_strength(round(closest_orb, 2))
                planet_weight = (
                    RULES["planet_weights"].get(p1["planet"], 0) +
                    RULES["planet_weights"].get(p2["planet"], 0)
                )
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
                    "orb_strength": strength["label"],
                    "orb_multiplier": strength["multiplier"],
                    "priority_score": round(planet_weight * strength["multiplier"], 2),
                    "is_priority": (
                        p1["planet"] in IMPORTANT_PLANETS and
                        p2["planet"] in IMPORTANT_PLANETS
                    )
                })

    return sorted(
        synastry_aspects,
        key=lambda x: (not x["is_priority"], -x["priority_score"], x["orb"])
    )


def get_house_overlays(person_1_chart: dict, person_2_chart: dict):
    overlays = []

    overlay_sets = [
        ("person_1_to_person_2", person_1_chart["planet_positions"], person_2_chart["houses"]),
        ("person_2_to_person_1", person_2_chart["planet_positions"], person_1_chart["houses"])
    ]

    for direction, planets, houses in overlay_sets:
        # An overlay drops one person's planets into the other's houses, so it
        # needs the *receiving* chart to have houses. Without a birth time on
        # that side there are none, and the direction is simply skipped —
        # aspects between the two charts still carry the reading.
        if len(houses) != 12:
            continue

        overlaid_planets = add_house_to_planets(planets, houses)
        for planet in overlaid_planets:
            house_key = str(planet["house"])
            house_rule = RULES["house_overlay_rules"].get(house_key)
            if not house_rule:
                continue

            overlays.append({
                "direction": direction,
                "planet": planet["planet"],
                "sign": planet["sign"],
                "house": planet["house"],
                "tier": house_rule["tier"],
                "keywords": house_rule["keywords"],
                "scores": house_rule["scores"],
                "priority_score": (
                    (5 - house_rule["tier"]) * 10 +
                    RULES["planet_weights"].get(planet["planet"], 0)
                )
            })

    return sorted(
        overlays,
        key=lambda x: (-x["priority_score"], x["house"], x["planet"])
    )


def _apply_generic_effects(aspect: dict, effects: dict) -> dict:
    planets = {aspect["person_1_planet"], aspect["person_2_planet"]}
    aspect_name = aspect["aspect"]
    multiplier = aspect["orb_multiplier"]

    for pair_rule in RULES["pair_rules"]:
        if _match_pair_rule(aspect, pair_rule):
            _sum_effects(effects, pair_rule["effects"], multiplier)

    if "Pluto" in planets and aspect_name in HARD_ASPECTS and planets & PERSONAL_PLANETS:
        _sum_effects(effects, {"toxicity": 7, "attraction": 2}, multiplier)

    if "Neptune" in planets and aspect_name in HARD_ASPECTS and planets & {"Moon", "Venus", "Mercury"}:
        _sum_effects(effects, {"toxicity": 6}, multiplier)

    if "Uranus" in planets and aspect_name in HARD_ASPECTS and planets & {"Moon", "Venus"}:
        _sum_effects(effects, {"toxicity": 5}, multiplier)

    if "Saturn" in planets and aspect_name in HARD_ASPECTS:
        _sum_effects(effects, {"long_term": -4, "toxicity": 2}, multiplier)

    return effects


def _bucketize_index(index_name: str, value: float) -> str:
    thresholds = RULES["index_thresholds"].get(index_name, [])
    for threshold in thresholds:
        if value <= threshold["max"]:
            return threshold["label"]
    return "mixed"


def _detect_double_whammies(aspects: list[dict]) -> list[dict]:
    grouped = {}
    for aspect in aspects:
        key = (
            _pair_key(aspect["person_1_planet"], aspect["person_2_planet"]),
            aspect["aspect"]
        )
        grouped.setdefault(key, []).append(aspect)

    results = []
    for (planets, aspect_name), matches in grouped.items():
        if len(matches) < 2:
            continue

        directions = {match["person_1_planet"] for match in matches}
        if len(directions) < 2:
            continue

        results.append({
            "planets": list(planets),
            "aspect": aspect_name,
            "count": len(matches),
            "label": f"{'/'.join(planets)} {aspect_name} double whammy"
        })

    return results


def _count_planet_hits(aspects: list[dict], source_prefix: str, target_planet: str) -> int:
    count = 0
    for aspect in aspects:
        source_planet = aspect[f"{source_prefix}_planet"]
        target_key = "person_2_planet" if source_prefix == "person_1" else "person_1_planet"
        target = aspect[target_key]
        if target != target_planet:
            continue
        if source_planet in {"Sun", "Moon", "Venus", "Mars", "Pluto", "Saturn"}:
            count += 1
    return count


def _overlay_hits(overlays: list[dict], direction: str, house: int) -> int:
    return sum(1 for overlay in overlays if overlay["direction"] == direction and overlay["house"] == house)


def _build_attachment_profile(aspects: list[dict], overlays: list[dict]) -> dict:
    person_1_activation = (
        _count_planet_hits(aspects, "person_2", "Moon") * 3 +
        _count_planet_hits(aspects, "person_2", "Venus") * 2 +
        _overlay_hits(overlays, "person_2_to_person_1", 7) * 2
    )
    person_2_activation = (
        _count_planet_hits(aspects, "person_1", "Moon") * 3 +
        _count_planet_hits(aspects, "person_1", "Venus") * 2 +
        _overlay_hits(overlays, "person_1_to_person_2", 7) * 2
    )

    if person_1_activation > person_2_activation:
        attaches_first = "person_1"
    elif person_2_activation > person_1_activation:
        attaches_first = "person_2"
    else:
        attaches_first = "balanced"

    return {
        "person_1_activation": person_1_activation,
        "person_2_activation": person_2_activation,
        "attaches_first": attaches_first
    }


def _build_power_profile(aspects: list[dict]) -> dict:
    person_1_power = 0
    person_2_power = 0
    person_1_illusion = 0
    person_2_illusion = 0

    for aspect in aspects:
        p1 = aspect["person_1_planet"]
        p2 = aspect["person_2_planet"]
        if p1 == "Pluto" and p2 in PERSONAL_PLANETS:
            person_1_power += 3
        if p2 == "Pluto" and p1 in PERSONAL_PLANETS:
            person_2_power += 3
        if p1 == "Saturn" and p2 in PERSONAL_PLANETS:
            person_1_power += 2
        if p2 == "Saturn" and p1 in PERSONAL_PLANETS:
            person_2_power += 2
        if p1 == "Neptune" and p2 in PERSONAL_PLANETS | {"Mercury"}:
            person_1_illusion += 2
        if p2 == "Neptune" and p1 in PERSONAL_PLANETS | {"Mercury"}:
            person_2_illusion += 2

    if person_1_power > person_2_power:
        power_holder = "person_1"
    elif person_2_power > person_1_power:
        power_holder = "person_2"
    else:
        power_holder = "balanced"

    return {
        "person_1_power": person_1_power,
        "person_2_power": person_2_power,
        "power_holder": power_holder,
        "person_1_illusion_pressure": person_1_illusion,
        "person_2_illusion_pressure": person_2_illusion
    }


def _build_trajectory(indices: dict) -> dict:
    if indices["toxicity"] >= 13 and indices["long_term"] <= 5:
        likely_outcome = "intense but unstable"
    elif indices["long_term"] >= 10 and indices["toxicity"] <= 12:
        likely_outcome = "can stabilize with maturity"
    elif indices["attraction"] >= 13 and indices["long_term"] < 10:
        likely_outcome = "strong chemistry, unclear staying power"
    else:
        likely_outcome = "mixed trajectory"

    dominant_phase = "initiation"
    if indices["emotional"] >= 8:
        dominant_phase = "bonding"
    if indices["attraction"] >= 13:
        dominant_phase = "intensification"
    if indices["long_term"] >= 10:
        dominant_phase = "test toward commitment"

    return {
        "dominant_phase": dominant_phase,
        "likely_outcome": likely_outcome
    }


# Where a pair sits inside its own band, so two "typical" scores can still be
# ranked against each other. Without this an ordinary pair — four in five of
# them — has nothing to lead with, and "nothing stands out" becomes "it could
# be anything", which is the one thing a reading must never be.
def _relative_position(index_name: str, value: float) -> float:
    """Roughly what fraction of pairs this beats, from the banded cut points."""
    cuts = [t["max"] for t in RULES["index_thresholds"].get(index_name, [])][:3]
    if len(cuts) < 3:
        return 0.5
    low, typical, high = cuts                    # p25, p75, p90
    if value <= low:
        return 0.25 * max(0.0, value / low) if low else 0.0
    if value <= typical:
        return 0.25 + 0.50 * (value - low) / max(typical - low, 1e-9)
    if value <= high:
        return 0.75 + 0.15 * (value - typical) / max(high - typical, 1e-9)
    return min(1.0, 0.90 + 0.10 * (value - high) / max(high, 1e-9))


# What each index is, in words a person would use.
AREA_IN_WORDS = {
    "attraction": "pull and chemistry",
    "emotional": "emotional closeness",
    "long_term": "staying power",
    "toxicity": "friction",
}


def _relative_shape(indices: dict) -> dict:
    """Which of the three strengths leads for this pair, and which trails.

    Friction is deliberately not eligible to "lead": a high score there is not
    something a pair is good at, and offering it as their standout quality is
    how an ordinary connection gets read back as a warning.
    """
    strengths = {name: _relative_position(name, indices[name])
                 for name in ("attraction", "emotional", "long_term")}
    leading = max(strengths, key=strengths.get)
    trailing = min(strengths, key=strengths.get)
    friction = _relative_position("toxicity", indices["toxicity"])
    return {
        "leads_on": AREA_IN_WORDS[leading],
        "leads_on_key": leading,
        "trails_on": AREA_IN_WORDS[trailing],
        "friction_position": round(friction, 2),
        "spread": round(max(strengths.values()) - min(strengths.values()), 2),
        "note": (
            "Where this pair sits against pairs in general, area by area. Use "
            "'leads_on' to give an ordinary pair something specific to be — "
            "'mostly a talking connection', 'more steady than exciting' — "
            "rather than saying nothing stands out. A small 'spread' means the "
            "three really are level, which is itself a description: even, "
            "unremarkable, no single thing carrying it."
        ),
    }


def _classify_relationship(indices: dict) -> list[str]:
    """Every description that fits, not the first one in the file.

    A pair can genuinely have strong long-term potential *and* high friction.
    Returning whichever happened to be listed first threw away half the
    reading and made the answer depend on dictionary order.
    """
    matched = []
    for classifier in RULES["classifiers"].values():
        conditions = classifier["conditions"]
        if "attraction_min" in conditions and indices["attraction"] < conditions["attraction_min"]:
            continue
        if "attraction_max" in conditions and indices["attraction"] > conditions["attraction_max"]:
            continue
        if "long_term_min" in conditions and indices["long_term"] < conditions["long_term_min"]:
            continue
        if "long_term_max" in conditions and indices["long_term"] > conditions["long_term_max"]:
            continue
        if "toxicity_min" in conditions and indices["toxicity"] < conditions["toxicity_min"]:
            continue
        if "toxicity_max" in conditions and indices["toxicity"] > conditions["toxicity_max"]:
            continue
        matched.append(classifier["label"])

    return matched or ["nothing that stands out either way"]


def build_synastry_engine(person_1_chart: dict, person_2_chart: dict, synastry_aspects: list | None = None):
    aspects = synastry_aspects or get_synastry_aspects(
        person_1_chart["planet_positions"],
        person_2_chart["planet_positions"]
    )
    overlays = get_house_overlays(person_1_chart, person_2_chart)
    indices = {
        "attraction": 0.0,
        "emotional": 0.0,
        "long_term": 0.0,
        "toxicity": 0.0
    }
    red_flags = set()
    green_flags = set()
    neutral_markers = set()

    for overlay in overlays:
        _sum_effects(indices, overlay["scores"])
        if overlay["house"] in {5, 7}:
            green_flags.add(f"{overlay['planet']} overlay in house {overlay['house']}")
        if overlay["house"] == 12:
            red_flags.add("12th house overlay")
        if overlay["house"] == 8:
            # Not a point in its favour. Intensity describes how deep an
            # exchange goes, not whether it is enjoyable, mutual or
            # sustainable — and counting it as good is how a difficult
            # entanglement gets read back to someone as a strength.
            neutral_markers.add("8th house depth — read it by the rest of the chart")

    scored_aspects = []
    for aspect in aspects:
        effects = _apply_generic_effects(aspect, {})
        _sum_effects(indices, effects)
        aspect_with_effects = aspect | {"engine_effects": effects}
        scored_aspects.append(aspect_with_effects)

        planets = {aspect["person_1_planet"], aspect["person_2_planet"]}
        if planets == {"Venus", "Mars"}:
            green_flags.add("Venus-Mars chemistry")
        if planets == {"Sun", "Moon"}:
            green_flags.add("Sun-Moon compatibility")
        if planets == {"Moon", "Moon"} and aspect["aspect"] in SOFT_ASPECTS | {"conjunction"}:
            green_flags.add("Moon harmony")
        if "Neptune" in planets and aspect["aspect"] in HARD_ASPECTS:
            red_flags.add("Neptune hard aspect")
        if "Pluto" in planets and aspect["aspect"] in HARD_ASPECTS:
            red_flags.add("Pluto hard aspect")
        if "Saturn" in planets and aspect["aspect"] in HARD_ASPECTS:
            red_flags.add("Harsh Saturn contact")

    for key in indices:
        indices[key] = round(indices[key], 2)

    double_whammies = _detect_double_whammies(scored_aspects)
    if double_whammies:
        green_flags.add("double whammy reinforcement")

    net_score = round(
        indices["attraction"] + indices["emotional"] + indices["long_term"] - indices["toxicity"],
        2
    )
    attachment_profile = _build_attachment_profile(scored_aspects, overlays)
    power_profile = _build_power_profile(scored_aspects)
    trajectory = _build_trajectory(indices)

    return {
        "method": {
            "layers": RULES["interpretation_layers"],
            "priority": RULES["interpretation_priority"]
        },
        "top_house_overlays": overlays[:8],
        "top_aspects": scored_aspects[:10],
        "indices": {
            **indices,
            # All four are banded now. Bands say where a pair sits among pairs
            # in general — low, typical, high, exceptional — cut from the
            # percentiles of a thousand fictional pairs rather than from
            # numbers nobody had checked against real output.
            **{f"{name}_band": _bucketize_index(name, indices[name])
               for name in ("attraction", "emotional", "long_term", "toxicity")},
            "band_meaning": "where this pair sits among pairs in general, not a verdict on the people",
            "net_score": net_score
        },
        "relative_shape": _relative_shape(indices),
        "double_whammies": double_whammies,
        "attachment_profile": attachment_profile,
        "power_profile": power_profile,
        "trajectory": trajectory,
        "relationship_classifier": _classify_relationship(indices),
        "green_flags": sorted(green_flags),
        "red_flags": sorted(red_flags),
        "neutral_markers": sorted(neutral_markers)
    }
