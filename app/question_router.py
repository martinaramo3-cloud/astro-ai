import re


def _contains(text: str, terms) -> bool:
    return any(re.search(r"\b" + re.escape(term) + r"\b", text) for term in terms)


def conversational_cue(question: str) -> str | None:
    """Recognize a few standalone chat signals, not the tone of a whole message.

    Punctuation such as '?' or '...' and crying emojis can carry real meaning.
    Only isolated slash keystrokes get the tentative mistype cue.
    """
    q = (question or "").strip().lower()
    if re.fullmatch(r"[\\/]{1,3}", q):
        return "possible_mistype"
    if re.fullmatch(r"(?:(?:ha|he){2,}a*|lol+|lmao+|lmfao+|[😂🤣]+)[! .]*", q):
        return "shared_laughter"
    return None


def requested_detail(question: str) -> str | None:
    q = (question or "").lower().replace("’", "'")
    if _contains(q, ("more detail", "more detailed", "be detailed", "in detail",
                     "elaborate", "vague", "vaguely", "specific", "specifics",
                     "how who what", "how, who, what", "how, who and what", "rank", "compare",
                     "who will i date", "who is the person", "tell me how")):
        return "detailed"
    if _contains(q, ("wdym", "explain", "clarify", "simpler", "simple language",
                     "plain english", "don't understand", "dont understand",
                     "do not understand", "confused", "what do you mean",
                     "what does that mean", "what does this mean", "look like")) or q.strip(" ?!.,") in {"why", "how", "who", "when", "what happened"}:
        return "explanation"
    return None


def classify_question(question: str) -> str:
    q = question.lower()

    # Plurals are listed because the match is whole-word: "relationships" was
    # not a relationship question, which is most of how anyone phrases one.
    relationship_keywords = [
        "love", "relationship", "relationships", "dating", "partner", "partners",
        "boyfriend", "girlfriend", "crush", "crushes", "romantic", "marriage",
        "breakup", "breakups", "ex", "exes", "attraction", "situationship",
    ]

    emotional_keywords = [
        "emotional", "emotion", "emotions", "feel", "feels", "felt", "feeling",
        "feelings", "sad", "anxious", "overwhelmed", "mood", "crying",
        "sensitive", "inner", "intensive", "mental health",
    ]

    career_keywords = [
        "career", "job", "work", "success", "future", "purpose", "study",
        "school", "university", "ambition", "money", "profession",
        "business", "revenue", "profit", "profitable", "financial", "studio"
    ]

    # "us" is not in here, and must not go back in: it matches the United
    # States. One mention of the US classified a whole thread as a two-person
    # compatibility reading, so "I live in New York, but idk if it's the right
    # choice" was answered with "what have they actually said or done?".
    # The phrases below carry the same meaning without the collision.
    compatibility_keywords = [
        "compatible", "compatibility", "together", "between us", "connection",
        "relationship with", "long term", "chemistry", "about us", "us two",
        "the two of us", "me and him", "me and her", "me and them",
        "him and me", "her and me", "we two",
    ]

    if _contains(q, compatibility_keywords):
        return "compatibility"

    if _contains(q, relationship_keywords):
        return "relationship"

    if _contains(q, emotional_keywords):
        return "emotional"

    if _contains(q, career_keywords):
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
    "lol", "haha", "bye", "see you", "hi zoli", "hey zoli", "love you",
    "hi zodi", "hey zodi",  # the old name, still typed by anyone who used it before
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

# A sentence about themselves. Matched on the subject rather than on emotional
# vocabulary: "I feel so close to New York" is as much a confidence as "I feel
# awful", and the topic does not have to sound emotional for the sentence to be
# one. Listing feeling-words missed most of how people actually write — "we
# fought and honestly im done" has no feeling word in it at all.
_FIRST_PERSON = re.compile(r"\b(?:i|i'?m|i'?ve|i'?d|i'?ll|me|my|myself)\b", re.I)

# Plenty of questions arrive without a question mark — "is he thinking about
# me", "do you think he likes me", "what's going on with me". They contain a
# first person and are not confidences, so the opening word decides.
_ASKS = re.compile(
    r"^(?:but |and |so |ok,? |okay,? )*"
    r"(?:what|why|how|when|where|who|which|is|are|was|were|do|does|did|can|could|"
    r"will|would|should|shall|am|has|have|had|tell me|does he|does she)\b", re.I)

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


def _term_pattern(terms: tuple[str, ...]) -> "re.Pattern":
    """Match these terms as words, not as letters found inside other words.

    Plain substring matching sent "should I buy the next size up?" to the
    deepest, most expensive tier, because "ex" is inside "next" — and inside
    "text", "exam" and "expensive" too. Every one of those is a quick decision
    that came back as a full reading.

    Most entries are stems on purpose: "depress" has to reach "depressed", so
    they anchor only at the start. Anything shorter than four letters is a
    whole word ("ex" means a former partner) and anchors at both ends.
    """
    parts = [
        rf"\b{re.escape(t)}\b" if len(t) < 4 else rf"\b{re.escape(t)}"
        for t in terms
    ]
    return re.compile("|".join(parts), re.I)


_HEAVY_RE = _term_pattern(_HEAVY)
_LOW_STAKES_RE = _term_pattern(_LOW_STAKES)


def classify_tier(question: str, history: list | None = None) -> int | None:
    """The tier when it can be known for certain, else None.

    Stakes decide, never length: "should we go out tonight?" is a whole
    sentence and still small; "i think i met the love of my life last night"
    is thrown off casually and is not.
    """
    q = (question or "").strip().lower().rstrip("?!.,")
    words = q.split()
    heavy = bool(_HEAVY_RE.search(q))

    if conversational_cue(question):
        return TIER_GREETING

    # A request to understand more is not a one-line confirmation, even "why?".
    # Calculation requests must also keep their context, regardless of wording.
    if requested_detail(question) or detect_relocation_request(question):
        return TIER_REAL

    # A greeting is a greeting even mid-conversation.
    if q in _GREETINGS or (len(words) <= 2 and not heavy and any(
        q.startswith(g) for g in ("hi", "hey", "hello", "thank", "morning", "night")
    )):
        return TIER_GREETING

    # Short, leaning on the previous turn — keep the rhythm of the exchange
    # rather than resetting to full depth, even when the thread is heavy.
    # Anywhere in the thread is enough: if Zoli has already spoken, this is a
    # follow-up rather than an opening question.
    answered_before = any(
        (m.get("role") if isinstance(m, dict) else getattr(m, "role", None)) == "assistant"
        for m in (history or [])
    )

    # Someone telling you how they feel has not asked a question, so nothing in
    # the text asks for an answer — and they were getting eighty words of
    # agreement. "I feel so close to New York", "I'm so done with this", "I
    # keep pulling away": these are the openings of the conversations this app
    # exists for, and they arrive as statements almost every time.
    # Stakes beat position. A follow-up is not automatically small: "wait he
    # cheated??" is three words, arrives mid-thread, and is not a one-liner.
    # This sits above the follow-up rules so that content always wins.
    if heavy:
        return TIER_REAL

    if answered_before and len(words) <= 5 and q.startswith(_FOLLOWUP_STARTS):
        return TIER_FOLLOWUP

    if _LOW_STAKES_RE.search(q):
        return TIER_QUICK

    # Someone telling you about themselves has not asked a question, so nothing
    # in the text asks for an answer — and it was getting eighty words of
    # agreement. "I feel so close to New York", "we fought and honestly im
    # done", "I tend to confuse not chasing with being mean": this is how the
    # conversations this app exists for actually open, and almost none of them
    # arrive with a question mark. Checked after the small decisions, so "I
    # want the black boots tonight" stays a small decision.
    if (len(words) >= 5 and "?" not in (question or "")
            and not _ASKS.match(q) and _FIRST_PERSON.search(q)):
        return TIER_REAL

    # Short AND leaning on the last turn. Length alone was enough before, which
    # made "is he serious?" a one-liner because it happens to be three words.
    if answered_before and len(words) <= 3 and q.startswith(_FOLLOWUP_STARTS):
        return TIER_FOLLOWUP

    # Everything else is genuinely ambiguous. Guessing it from length is what
    # made real questions come back bland — "is he thinking about me" is five
    # words and matters enormously. None means "ask something that can judge".
    return None


# ── "Where should I be?" ───────────────────────────────────────────────────
# A solar return relocation question, and what it is being asked for. Detected
# in code rather than left to the model, because the answer requires a search
# over a hundred and fifty charts that has to happen before the prompt is built.

_RELOCATION_PHRASES = (
    "where should i be", "where should i go", "where to be", "where to go",
    "where should i live", "where to live", "where should i move",
    "relocat", "solar return", "solar-return", "best place", "best city", "best country",
    "which city", "which country", "spend my birthday", "travel for my birthday",
    "move to", "where would be best", "rank cities", "rank the cities",
    # Asking where a life goes is asking the same question without the word
    # "city" in it. "Where do you see me building a future" got answered as a
    # vague feeling, with a ranking of 157 places sitting right there unused.
    "where do you see me", "where do i belong", "where would i belong",
    "where would i thrive", "where do i thrive", "where would i be happiest",
    "where should i end up", "where do i end up", "where will i end up",
    "building a future", "build a future", "build my life", "start over",
    "where would i be happier", "where am i meant to be",
)

# The purposes there are scoring tables for, and the words that ask for each.
_PURPOSE_WORDS = {
    "money": ("money", "financial", "finance", "income", "rich", "wealth",
              "earn", "cash", "profit", "salary"),
    "career": ("career", "job", "work", "professional", "promotion", "business"),
    "love": ("love", "romance", "relationship", "partner", "dating", "marry",
             "marriage", "meet someone"),
    "visibility": ("visibility", "famous", "fame", "seen", "recognition",
                   "audience", "public", "launch"),
    "social life": ("friends", "social", "people", "community", "network"),
    "study": ("study", "studying", "university", "degree", "course", "learn",
              "research", "phd", "masters"),
    # "live" and "settle" are not in here on purpose. They say someone is
    # asking about moving, not what they want out of it — and while they were,
    # "where should I live?" scored the fourth house alone and answered a
    # question about a whole life as though it were only about family.
    "home and family": ("home", "family", "roots", "house", "domestic"),
}

# Nothing in the question says what it is for. Score every area and rank on the
# combination, rather than picking one and quietly answering a narrower
# question than the one asked.
PURPOSE_OVERALL = "overall"


def detect_relocation_request(question: str) -> dict | None:
    """What a "where should I be" question is asking for, or None.

    Returns the purpose and whether the search should stay in Europe. The year
    is decided by the caller, which knows the birthday.
    """
    lowered = (question or "").lower()
    # A word can sit between the question and the noun — "which european city"
    # is the same question as "which city" — so these two are matched loosely.
    loose = re.search(
        r"\b(which|what|best|top|rank)\b[\w\s]{0,24}?\b(city|cities|country|countries|place|places|location)\b",
        lowered,
    )
    if not loose and not any(phrase in lowered for phrase in _RELOCATION_PHRASES):
        return None

    # Most specific wins: "where should I be for my career" is career even
    # though it also mentions money, if it does.
    purpose = PURPOSE_OVERALL
    best = 0
    for name, words in _PURPOSE_WORDS.items():
        hits = sum(1 for word in words if word in lowered)
        if hits > best:
            purpose, best = name, hits

    europe = any(word in lowered for word in ("europe", "european", "eu "))
    return {"purpose": purpose, "region": "europe" if europe else "world",
            "technique": _relocation_technique(lowered)}


# Two different questions, two different charts, and answering one with the
# other is how "where should I live?" came back as a list of cities to spend a
# single birthday in.
_RETURN_WORDS = ("solar return", "birthday", "born day", "my return", "returns")
_LIVING_WORDS = ("live", "living", "move", "moving", "relocate", "relocating",
                 "settle", "settling", "based", "belong", "home", "aligned",
                 "suits me", "suit me", "happiest", "thrive")


def _relocation_technique(lowered: str) -> str:
    """Which chart answers this.

    A relocated solar return says where to spend one birthday. A relocated
    natal chart says how a place would suit you to live in — the planets are
    identical, the houses and angles are not, and that is the whole technique.
    """
    if any(word in lowered for word in _RETURN_WORDS):
        return "solar_return"
    if any(word in lowered for word in _LIVING_WORDS):
        return "relocated_natal"
    # "which city is best for my career" with nothing else to go on is about a
    # life, not a birthday.
    return "relocated_natal"
