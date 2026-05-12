import json

from app.content_repository import (
    get_career_rules,
    get_emotional_rules,
    get_interpretation_order,
    get_output_templates,
    get_relationship_rules,
)


INTERPRETATION_ORDER = get_interpretation_order()
OUTPUT_TEMPLATES = get_output_templates()
RELATIONSHIP_RULES = get_relationship_rules()
CAREER_RULES = get_career_rules()
EMOTIONAL_RULES = get_emotional_rules()


def build_ai_chart_context(planets: list, ascendant: dict, aspects: list, transits: list | None = None):
    core_planet_names = ["Sun", "Moon", "Mercury", "Venus", "Mars"]
    social_outer_names = ["Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]

    core_planets = []
    outer_planets = []

    for planet in planets:
        cleaned_planet = {
            "planet": planet["planet"],
            "sign": planet["sign"],
            "degree_in_sign": planet["degree_in_sign"],
            "house": planet["house"],
            "retrograde": planet["retrograde"],
        }

        if planet["planet"] in core_planet_names:
            core_planets.append(cleaned_planet)
        elif planet["planet"] in social_outer_names:
            outer_planets.append(cleaned_planet)

    top_aspects = sorted(aspects, key=lambda x: x["orb"])[:4]

    context = {
        "core_identity": {
            "sun": next((p for p in core_planets if p["planet"] == "Sun"), None),
            "moon": next((p for p in core_planets if p["planet"] == "Moon"), None),
            "ascendant": ascendant,
        },
        "personal_planets": core_planets,
        "outer_planets": outer_planets,
        "top_natal_aspects": top_aspects,
    }

    if transits:
        top_transits = sorted(transits, key=lambda x: x["orb"])[:4]
        context["active_transits"] = top_transits

    return context


def _prompt_preamble() -> str:
    return f"""
Interpretation rules:
- Follow this priority order when possible: {", ".join(INTERPRETATION_ORDER)}.
- Use planet = function, sign = style, house = life area.
- Do not treat one placement as destiny.
- Repeated themes count as confirmation.
- Contradictions should be explained as different layers, not flattened.
- Empty houses are not meaningless; look at the cusp/ruler logic when relevant.
- Keep the writing elegant, modern, and psychologically clear.
- Use this output style as a guide: {OUTPUT_TEMPLATES['placement']}
""".strip()


def _history_guidance(context: dict) -> str:
    history = context.get("history") or []
    if not history:
        return "There is no prior conversation history for this reply."

    history_json = json.dumps(history[-6:], indent=2)
    return f"""
Conversation history:
{history_json}

Continue naturally from this exchange. Do not repeat earlier explanations unless the user is clearly asking for a recap.
""".strip()


def build_summary_prompt(chart_context: dict) -> str:
    chart_json = json.dumps(chart_context, indent=2)
    return f"""
You are an astrology assistant.

{_prompt_preamble()}

Use only the chart data provided below.
Do not invent placements, houses, aspects, transits, or timing details.
Base every interpretation on supplied chart context.

Write a natal chart summary in exactly 4 short sections:
1. Core personality
2. Emotional world
3. Love and relationships
4. Life direction

Style rules:
- warm, insightful, premium, modern
- specific, not generic
- no bullet points
- avoid mystical exaggeration
- mention only the most meaningful aspects

Keep it under 220 words.

Chart data:
{chart_json}
""".strip()


def build_weekly_horoscope_prompt(chart_context: dict) -> str:
    chart_json = json.dumps(chart_context, indent=2)
    return f"""
You are an astrology assistant.

{_prompt_preamble()}

Use only the chart data below.
Focus especially on active transits.
Do not invent placements, houses, aspects, or timing details.

Write a short weekly horoscope in 3 parts:
1. Main theme of the week
2. Emotional and relationship energy
3. Advice for navigating the week

Tone: calm, elevated, reassuring, specific.
Keep it under 200 words.

Chart data:
{chart_json}
""".strip()


def build_ask_astrologer_prompt(chat_context: dict) -> str:
    context_json = json.dumps(chat_context, indent=2)
    return f"""
You are a sharp, warm astrologer texting with a close friend. You have real opinions. You are direct, occasionally blunt, and genuinely care about the person you're talking to.

{_prompt_preamble()}

Question-specific priorities:
- Relationship questions: prioritize {', '.join(sum(RELATIONSHIP_RULES.values(), []))}.
- Career questions: prioritize {', '.join(CAREER_RULES)}.
- Emotional questions: prioritize {', '.join(EMOTIONAL_RULES)}.

Rules:
- Use only the chart data provided. Never invent placements.
- Answer the actual question first — do not open with a preamble or restating the question.
- Pick 2 or 3 chart factors maximum. Do not list every placement.
- Sound like yourself: warm, direct, sometimes funny, occasionally firm. Not clinical. Not overly mystical.
- If someone is doing something self-destructive, say so gently but clearly.
- If the chart shows something uncomfortable, name it honestly with care.
- Write in short separate paragraphs — 2 to 3 sentences each, with a blank line between them.
- Never write one single long block of text.
- Give a real practical takeaway when someone asks what to do.
- End with one short follow-up question if it adds something — skip it if it doesn't.
- Do not use bullet points, headers, or bold text.
- Keep the full reply under 220 words.
- Every reply must have a clear beginning and a clear end. Open by addressing the question directly. Close with either a takeaway, a one-line observation, or a single question — then stop. Do not trail off, do not add filler, do not keep going after the point is made.

{_history_guidance(chat_context)}

Context:
{context_json}
""".strip()


def build_compatibility_context(person_1_chart, person_2_chart, synastry_aspects, synastry_engine: dict | None = None):
    important_aspects = sorted(synastry_aspects, key=lambda x: (not x["is_priority"], x["orb"]))[:6]
    return {
        "person_1": {
            "sun": next(p for p in person_1_chart["planet_positions"] if p["planet"] == "Sun"),
            "moon": next(p for p in person_1_chart["planet_positions"] if p["planet"] == "Moon"),
            "venus": next(p for p in person_1_chart["planet_positions"] if p["planet"] == "Venus"),
            "mars": next(p for p in person_1_chart["planet_positions"] if p["planet"] == "Mars"),
            "ascendant": person_1_chart["ascendant"],
        },
        "person_2": {
            "sun": next(p for p in person_2_chart["planet_positions"] if p["planet"] == "Sun"),
            "moon": next(p for p in person_2_chart["planet_positions"] if p["planet"] == "Moon"),
            "venus": next(p for p in person_2_chart["planet_positions"] if p["planet"] == "Venus"),
            "mars": next(p for p in person_2_chart["planet_positions"] if p["planet"] == "Mars"),
            "ascendant": person_2_chart["ascendant"],
        },
        "key_synastry_aspects": important_aspects,
        "synastry_engine": synastry_engine or {},
    }


def build_compatibility_prompt(context):
    context_json = json.dumps(context, indent=2)
    return f"""
You are an astrology assistant analyzing compatibility.

{_prompt_preamble()}

Use only the chart data and synastry aspects below.
Do not invent placements or aspects.
Prioritize the synastry engine method in this order: house overlays, tight aspects, Saturn/Pluto involvement, Moon condition, Venus/Mars, then signs.

Write a concise compatibility overview that sounds warm, clear, and human.
Lead with the overall dynamic.
Focus on the 3 strongest patterns only.
Name one strength, one challenge, and one practical relationship takeaway.
Keep it under 170 words.
Do not use bullet points.

Compatibility data:
{context_json}
""".strip()

def build_ask_astrologer_context(
    question: str,
    chart_context: dict,
    question_type: str | None = None,
) -> dict:
    return {
        "question": question,
        "question_type": question_type,
        "chart_context": chart_context,
    }

def build_ask_compatibility_context(
    person_1_chart,
    person_2_chart,
    synastry_aspects,
    synastry_engine: dict,
    question: str,
    history: list | None = None,
):
    important_aspects = sorted(synastry_aspects, key=lambda x: (not x["is_priority"], x["orb"]))[:6]
    return {
        "question": question,
        "history": history or [],
        "person_1": {
            "sun": next(p for p in person_1_chart["planet_positions"] if p["planet"] == "Sun"),
            "moon": next(p for p in person_1_chart["planet_positions"] if p["planet"] == "Moon"),
            "venus": next(p for p in person_1_chart["planet_positions"] if p["planet"] == "Venus"),
            "mars": next(p for p in person_1_chart["planet_positions"] if p["planet"] == "Mars"),
            "ascendant": person_1_chart["ascendant"],
        },
        "person_2": {
            "sun": next(p for p in person_2_chart["planet_positions"] if p["planet"] == "Sun"),
            "moon": next(p for p in person_2_chart["planet_positions"] if p["planet"] == "Moon"),
            "venus": next(p for p in person_2_chart["planet_positions"] if p["planet"] == "Venus"),
            "mars": next(p for p in person_2_chart["planet_positions"] if p["planet"] == "Mars"),
            "ascendant": person_2_chart["ascendant"],
        },
        "key_synastry_aspects": important_aspects,
        "synastry_engine": synastry_engine,
    }


def build_ask_compatibility_prompt(context: dict) -> str:
    context_json = json.dumps(context, indent=2)
    return f"""
You are a warm, grounded astrologer answering a live compatibility question about two people.

{_prompt_preamble()}

Use only the chart data and synastry aspects provided below.
Do not invent placements, houses, aspects, or relationship facts.
If the question goes beyond the data, answer cautiously.
Use the synastry engine first: prioritize house overlays, then tight aspects, then the relationship indices and flags.
If attachment, control, or instability are relevant, use the attachment profile, power profile, double-whammies, and trajectory from the synastry engine.

Answer the user's actual question first.
Sound like a real person in conversation, not a written report.
Focus on the 2 or 3 most relevant compatibility signals.
For "should I continue?" or advice-style questions, do not give a rigid yes or no prediction.
Instead, explain the core dynamic, name the main green flag, name the main red flag, and say what to watch for in real life.
Be specific, practical, and emotionally intelligent.
Avoid long placement-by-placement summaries and avoid vague filler.
Use short paragraphs, not bullets.
If helpful, end with one brief follow-up question.
Keep the answer under 170 words.
Do not use bullet points.

{_history_guidance(context)}

Compatibility context:
{context_json}
""".strip()
