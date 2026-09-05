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


# The chat classifies questions by subject; the predictive engine thinks in its
# own topics. This is the join between them.
PREDICTIVE_TOPIC_BY_QUESTION_TYPE = {
    "relationship":  "relationships",
    "compatibility": "relationships",
    "emotional":     "inner_life",
    "career":        "career",
}


def predictive_topic_for(question_type: str | None) -> str | None:
    """Which life area the predictive engine should assess, if we can tell.

    None means "work it out from the chart" — the engine ranks every topic and
    picks the loudest, which is the right answer to "what is going on with me".
    """
    return PREDICTIVE_TOPIC_BY_QUESTION_TYPE.get(question_type or "general")


# ── How much answer does this deserve? ─────────────────────────────────────
# Deciding this in code, before the prompt is built, is the only thing that
# works. Asking a model to reply in one line while handing it three thousand
# tokens of chart data is a losing argument: the data wins every time. So the
# tier decides what gets sent, not just what the instructions ask for.

TIER_GREETING = 1     # hello, thanks, one word
TIER_QUICK = 2        # a small decision — an outfit, a purchase, going out
TIER_FOLLOWUP = 3     # mid-thread, already answered, keep the rhythm
TIER_REAL = 4         # heartbreak, love, fear, feeling stuck

_GREETINGS = {
    "hi", "hii", "hiii", "hey", "heyy", "hello", "yo", "sup", "morning",
    "good morning", "good evening", "goodnight", "good night", "night",
    "thanks", "thank you", "ty", "thx", "ok", "okay", "k", "cool", "nice",
    "lol", "haha", "bye", "see you", "hi zodi", "hey zodi", "love you",
}

# A follow-up is short and leans on what was just said.
_FOLLOWUP_STARTS = (
    "so ", "and ", "wait", "really", "ok but", "okay but", "but ", "why",
    "and the", "so yes", "so no", "then ", "what about", "seriously",
)

# Things that are decisions but not weight.
_LOW_STAKES = (
    "wear", "outfit", "jacket", "boots", "shoes", "dress", "buy", "purchase",
    "order", "eat", "dinner", "lunch", "coffee", "go out", "going out",
    "tonight", "haircut", "hair", "nails", "colour", "color", "book",
    "trip", "watch", "cook", "gym", "workout",
)

# Things that are never small, whatever they look like.
_HEAVY = (
    "ex", "love", "heartbreak", "heart broken", "broke up", "breakup",
    "cheat", "betray", "crazy", "anxious", "anxiety", "depress", "stuck",
    "lost", "hurt", "hurts", "miss him", "miss her", "miss them", "jealous",
    "does he", "does she", "mean it", "meant it", "ghost", "ignoring",
    "why do i", "am i", "should i text", "should i reach out", "feel like",
    "feeling", "afraid", "scared", "alone", "lonely", "cry", "crying",
    "marry", "commit", "future", "career", "quit", "fired", "purpose",
)


def classify_tier(question: str, history: list | None = None) -> int:
    """Pick the size of answer this question deserves.

    Stakes decide, never length: "should we go out tonight?" is a whole
    sentence and still small; "i think i met the love of my life last night"
    is thrown off casually and is not.
    """
    q = (question or "").strip().lower().rstrip("?!.,")
    words = q.split()
    heavy = any(term in q for term in _HEAVY)

    # A greeting is a greeting even mid-conversation.
    if q in _GREETINGS or (len(words) <= 2 and not heavy and any(
        q.startswith(g) for g in ("hi", "hey", "hello", "thank", "morning", "night")
    )):
        return TIER_GREETING

    # Short, leaning on the previous turn — keep the rhythm of the exchange
    # rather than resetting to full depth, even when the thread is heavy.
    # Anywhere in the thread is enough: if Zodi has already spoken, this is a
    # follow-up rather than an opening question.
    answered_before = any(
        (m.get("role") if isinstance(m, dict) else getattr(m, "role", None)) == "assistant"
        for m in (history or [])
    )
    if answered_before and len(words) <= 5 and (
        q.startswith(_FOLLOWUP_STARTS) or len(words) <= 3
    ):
        return TIER_FOLLOWUP

    if heavy:
        return TIER_REAL

    if any(term in q for term in _LOW_STAKES):
        return TIER_QUICK

    # Ambiguous goes shorter: a brief answer invites another question, a long
    # one ends the conversation.
    return TIER_QUICK if len(words) <= 8 else TIER_REAL
