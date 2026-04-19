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


def filter_chart_context_by_question_type(
    question_type: str,
    planets: list,
    ascendant: dict,
    aspects: list,
    transits: list | None = None
) -> dict:
    selected_planets = []
    selected_aspects = []

    if question_type == "relationship":
        focus_planets = {"Moon", "Venus", "Mars", "Sun"}
        aspect_planets = {"Moon", "Venus", "Mars", "Saturn", "Sun"}

    elif question_type == "emotional":
        focus_planets = {"Moon", "Sun", "Neptune", "Saturn"}
        aspect_planets = {"Moon", "Neptune", "Saturn", "Sun", "Mercury"}

    elif question_type == "career":
        focus_planets = {"Sun", "Saturn", "Jupiter", "Mars", "Mercury"}
        aspect_planets = {"Sun", "Saturn", "Jupiter", "Mars", "Mercury"}

    else:
        focus_planets = {"Sun", "Moon", "Mercury", "Venus", "Mars"}
        aspect_planets = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Saturn"}

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