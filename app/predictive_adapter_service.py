from __future__ import annotations

from typing import Optional

from app.book_knowledge import get_dignity
from app.content_repository import get_sign_rulers
from app.predictive_astrology_engine import (
    Activation,
    AspectType,
    ChartContext,
    NatalPlanet,
    NatalPromise,
    PredictiveAstrologyEngine,
    PredictiveMethod,
    PredictionOutput,
    TOPIC_HOUSE_MAP,
    TOPIC_PLANET_MAP,
    Topic,
)

ANGULAR_HOUSES = {1, 4, 7, 10}
AFFLICTING_PLANETS = {"Saturn", "Mars", "Pluto"}
SUPPORTIVE_PLANETS = {"Venus", "Jupiter", "Sun"}
SIGN_RULERS = {sign: rulers[0] for sign, rulers in get_sign_rulers().items()}


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, round(value, 2)))


def _to_topic(topic_value: str | None) -> Optional[Topic]:
    if not topic_value:
        return None

    normalized = topic_value.strip().lower().replace(" ", "_")
    for topic in Topic:
        if topic.value == normalized:
            return topic
    return None


def _to_aspect_type(value: str | None) -> AspectType | None:
    if not value:
        return None

    for aspect in AspectType:
        if aspect.value == value:
            return aspect
    return None


def _houses_ruled_by_planet(planet_name: str, houses: list[dict]) -> list[int]:
    ruled = []
    for house in houses:
        if SIGN_RULERS.get(house["sign"]) == planet_name:
            ruled.append(house["house"])
    return ruled


def _planet_strength(planet: dict, natal_aspects: list[dict]) -> float:
    strength = 0.5

    dignity = get_dignity(planet["planet"], planet["sign"])
    if dignity == "domicile":
        strength += 0.22
    elif dignity == "exaltation":
        strength += 0.16
    elif dignity == "detriment":
        strength -= 0.14
    elif dignity == "fall":
        strength -= 0.2

    if planet["house"] in ANGULAR_HOUSES:
        strength += 0.12
    if planet.get("retrograde"):
        strength -= 0.05

    supportive_hits = 0
    difficult_hits = 0
    for aspect in natal_aspects:
        if planet["planet"] not in {aspect["planet_1"], aspect["planet_2"]}:
            continue

        other = aspect["planet_2"] if aspect["planet_1"] == planet["planet"] else aspect["planet_1"]
        if aspect["aspect"] in {"trine", "sextile"} and other in SUPPORTIVE_PLANETS:
            supportive_hits += 1
        if aspect["aspect"] in {"square", "opposition"} and other in AFFLICTING_PLANETS:
            difficult_hits += 1

    strength += supportive_hits * 0.05
    strength -= difficult_hits * 0.08
    return _clamp_score(strength)


def build_natal_planet_map(natal_chart: dict) -> dict[str, NatalPlanet]:
    natal_aspects = natal_chart.get("aspects", [])
    houses = natal_chart.get("houses", [])
    result: dict[str, NatalPlanet] = {}

    for planet in natal_chart["planet_positions"]:
        dignity = get_dignity(planet["planet"], planet["sign"])
        afflicted = False
        for aspect in natal_aspects:
            if planet["planet"] not in {aspect["planet_1"], aspect["planet_2"]}:
                continue
            other = aspect["planet_2"] if aspect["planet_1"] == planet["planet"] else aspect["planet_1"]
            if aspect["aspect"] in {"square", "opposition"} and other in AFFLICTING_PLANETS:
                afflicted = True
                break

        result[planet["planet"]] = NatalPlanet(
            planet=planet["planet"],
            sign=planet["sign"],
            house=planet["house"],
            strength=_planet_strength(planet, natal_aspects),
            dignified=dignity in {"domicile", "exaltation"},
            angular=planet["house"] in ANGULAR_HOUSES,
            retrograde=planet.get("retrograde", False),
            afflicted=afflicted,
            houses_ruled=_houses_ruled_by_planet(planet["planet"], houses),
        )

    return result


def estimate_natal_promise(natal_chart: dict) -> NatalPromise:
    natal_planets = build_natal_planet_map(natal_chart)
    topic_scores: dict[Topic, float] = {}
    notes: dict[Topic, list[str]] = {}

    for topic in Topic:
        score = 0.1
        topic_notes: list[str] = []
        relevant_houses = set(TOPIC_HOUSE_MAP[topic])
        relevant_planets = set(TOPIC_PLANET_MAP[topic])

        for planet in natal_planets.values():
            if planet.house in relevant_houses:
                boost = 0.18 if planet.angular else 0.12
                score += boost
                topic_notes.append(
                    f"Natal {planet.planet} in house {planet.house} directly supports {topic.value}."
                )

            if planet.planet in relevant_planets:
                score += 0.08 * planet.strength
                if planet.strength >= 0.7:
                    topic_notes.append(
                        f"Natal {planet.planet} is strong and relevant for {topic.value}."
                    )

            if any(h in relevant_houses for h in planet.houses_ruled):
                score += 0.06
                topic_notes.append(
                    f"Natal {planet.planet} rules one of the key {topic.value} houses."
                )

        topic_scores[topic] = _clamp_score(score)
        notes[topic] = topic_notes[:4]

    return NatalPromise(topic_scores=topic_scores, notes=notes)


def build_chart_context(natal_chart: dict) -> ChartContext:
    return ChartContext(
        natal_planets=build_natal_planet_map(natal_chart),
        natal_promise=estimate_natal_promise(natal_chart),
    )


def _candidate_topics_for_transit(transit: dict, natal_planets: dict[str, NatalPlanet]) -> list[Topic]:
    topics = set()
    target_planet = transit["natal_planet"]
    activated_house = natal_planets[target_planet].house if target_planet in natal_planets else None

    for topic in Topic:
        if target_planet in TOPIC_PLANET_MAP[topic]:
            topics.add(topic)
        if transit["transit_planet"] in TOPIC_PLANET_MAP[topic]:
            topics.add(topic)
        if activated_house in TOPIC_HOUSE_MAP[topic]:
            topics.add(topic)

    return sorted(topics, key=lambda item: item.value)


def build_activations_from_transits(
    transit_aspects: list[dict],
    natal_chart: dict,
) -> list[Activation]:
    natal_planets = build_natal_planet_map(natal_chart)
    activations: list[Activation] = []

    for transit in transit_aspects:
        activated_house = natal_planets[transit["natal_planet"]].house
        exact = transit["orb"] <= 1
        aspect_type = _to_aspect_type(transit["aspect"])
        candidate_topics = _candidate_topics_for_transit(transit, natal_planets)

        base_note = (
            f"{transit['transit_planet']} {transit['aspect']} natal {transit['natal_planet']} "
            f"activates house {activated_house}."
        )
        if transit.get("transit_retrograde"):
            base_note += " Transit planet is retrograde."

        for topic in candidate_topics:
            activations.append(
                Activation(
                    method=PredictiveMethod.TRANSIT,
                    topic=topic,
                    activating_planet=transit["transit_planet"],
                    target_planet=transit["natal_planet"],
                    activated_house=activated_house,
                    aspect=aspect_type,
                    orb=transit["orb"],
                    exact=exact,
                    angular=activated_house in ANGULAR_HOUSES,
                    notes=[base_note],
                )
            )

    return activations


def run_predictive_engine(
    natal_chart: dict,
    transit_aspects: list[dict],
    requested_topic: str | None = None,
) -> PredictionOutput:
    chart_context = build_chart_context(natal_chart)
    activations = build_activations_from_transits(transit_aspects, natal_chart)
    engine = PredictiveAstrologyEngine(chart_context)
    topic = _to_topic(requested_topic)
    return engine.predict(activations, requested_topic=topic)
