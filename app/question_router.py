def classify_question(question: str) -> str:
    q = question.lower()

    relationship_keywords = [
        "love", "relationship", "dating", "partner", "boyfriend", "girlfriend",
        "crush", "romantic", "marriage", "breakup", "ex", "attraction"
    ]

    emotional_keywords = [
        "emotional", "emotion", "feel", "feeling", "sad", "anxious", "overwhelmed",
        "mood", "crying", "sensitive", "inner", "intensive","mental health"
    ]

    career_keywords = [
        "career", "job", "work", "success", "future", "purpose", "study",
        "school", "university", "ambition", "money", "profession"
    ]

    compatibility_keywords = [
        "compatible", "compatibility", "us", "together", "between us", "connection",
        "relationship with", "long term", "chemistry"
    ]

    if any(word in q for word in compatibility_keywords):
        return "compatibility"

    if any(word in q for word in relationship_keywords):
        return "relationship"

    if any(word in q for word in emotional_keywords):
        return "emotional"

    if any(word in q for word in career_keywords):
        return "career"

    return "general"


# Which planets each kind of question actually turns on. Shared so that the
# transit timeline and house placements can be trimmed the same way the chart
# context is, instead of each having its own idea of relevance.
FOCUS_PLANETS = {
    "relationship":  {"Moon", "Venus", "Mars", "Sun"},
    "compatibility": {"Moon", "Venus", "Mars", "Sun"},
    "emotional":     {"Moon", "Sun", "Neptune", "Saturn"},
    "career":        {"Sun", "Saturn", "Jupiter", "Mars", "Mercury"},
    "general":       {"Sun", "Moon", "Mercury", "Venus", "Mars"},
}

ASPECT_PLANETS = {
    "relationship":  {"Moon", "Venus", "Mars", "Saturn", "Sun"},
    "compatibility": {"Moon", "Venus", "Mars", "Saturn", "Sun"},
    "emotional":     {"Moon", "Neptune", "Saturn", "Sun", "Mercury"},
    "career":        {"Sun", "Saturn", "Jupiter", "Mars", "Mercury"},
    "general":       {"Sun", "Moon", "Mercury", "Venus", "Mars", "Saturn"},
}


def get_focus_planets(question_type: str | None) -> set:
    return FOCUS_PLANETS.get(question_type or "general", FOCUS_PLANETS["general"])


def filter_chart_context_by_question_type(
    question_type: str,
    planets: list,
    ascendant: dict,
    aspects: list,
    transits: list | None = None
) -> dict:
    selected_planets = []
    selected_aspects = []

    focus_planets = get_focus_planets(question_type)
    aspect_planets = ASPECT_PLANETS.get(
        question_type or "general", ASPECT_PLANETS["general"]
    )

    for planet in planets:
        if planet["planet"] in focus_planets:
            selected_planets.append(planet)

    for aspect in aspects:
        if (
            aspect["planet_1"] in aspect_planets
            or aspect["planet_2"] in aspect_planets
        ):
            selected_aspects.append(aspect)

    selected_aspects = sorted(selected_aspects, key=lambda x: x["orb"])[:4]

    context = {
        "question_type": question_type,
        "ascendant": ascendant,
        "relevant_planets": selected_planets,
        "relevant_aspects": selected_aspects
    }

    if transits:
        filtered_transits = []
        for transit in transits:
            if (
                transit["natal_planet"] in focus_planets
                or transit["transit_planet"] in focus_planets
            ):
                filtered_transits.append(transit)

        context["relevant_transits"] = sorted(
            filtered_transits,
            key=lambda x: x["orb"]
        )[:4]

    return context