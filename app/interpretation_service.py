from __future__ import annotations

from collections import Counter
from typing import Any

from app.content_repository import (
    get_aspects,
    get_houses,
    get_planets,
    get_sign_rulers,
    get_signs,
)


PLANETS = get_planets()
SIGNS = get_signs()
HOUSES = get_houses()
ASPECTS = get_aspects()

# More detailed placement-specific meanings

# These are not meant to replace the system — only enrich it.
PLANET_SIGN_MEANINGS = {
    "Sun": {
        "Aries": {
            "core": "You express your identity in a bold, direct, and initiating way. You are meant to trust your instincts and lead with courage.",
            "gifts": "initiative, self-trust, bravery, independence",
            "challenge": "impulsiveness, impatience, over-identifying with action",
            "growth": "Learn how to lead without forcing, and how to keep your fire steady rather than reactive.",
        },
        "Taurus": {
            "core": "Your identity grows through stability, consistency, and building something real. You are here to embody value rather than rush.",
            "gifts": "groundedness, loyalty, endurance, calm strength",
            "challenge": "stubbornness, over-attachment, resistance to change",
            "growth": "Develop flexibility without losing your center.",
        },
        "Gemini": {
            "core": "You shine through curiosity, ideas, language, and versatility. Your identity develops by learning, connecting, and staying mentally alive.",
            "gifts": "adaptability, wit, communication, curiosity",
            "challenge": "scattered focus, nervous overactivity, inconsistency",
            "growth": "Move from collecting information to developing your own clear voice.",
        },
        "Cancer": {
            "core": "Your identity is shaped by emotional intelligence, care, memory, and protection. You grow by honoring sensitivity as strength.",
            "gifts": "nurturance, intuition, loyalty, emotional depth",
            "challenge": "defensiveness, retreating, overprotection",
            "growth": "Create safety without hiding who you are.",
        },
        "Leo": {
            "core": "You are meant to shine through self-expression, creativity, warmth, and courage of heart. Recognition matters because visibility is part of your path.",
            "gifts": "charisma, creativity, generosity, presence",
            "challenge": "pride, wounded ego, dependence on validation",
            "growth": "Express yourself from authenticity, not only from the need to be seen.",
        },
        "Virgo": {
            "core": "Your identity develops through refinement, service, discernment, and mastery of detail. You shine when you improve what you touch.",
            "gifts": "precision, intelligence, humility, usefulness",
            "challenge": "perfectionism, self-criticism, anxiety",
            "growth": "Let improvement serve life, not become a reason to feel inadequate.",
        },
        "Libra": {
            "core": "You discover yourself through balance, relationship, beauty, and fairness. Identity grows through conscious connection with others.",
            "gifts": "diplomacy, elegance, social intelligence, harmony",
            "challenge": "indecision, over-accommodation, conflict avoidance",
            "growth": "Build real balance by including your own needs, not only other people's.",
        },
        "Scorpio": {
            "core": "You carry a deep, intense, and transformative sense of self. Your identity is shaped through emotional truth, power, and inner regeneration.",
            "gifts": "depth, magnetism, resilience, insight",
            "challenge": "control, secrecy, extremes, mistrust",
            "growth": "Use your intensity for healing and truth, not defense or domination.",
        },
        "Sagittarius": {
            "core": "Your identity grows through freedom, exploration, meaning, and vision. You are meant to move toward possibility and live from conviction.",
            "gifts": "optimism, honesty, openness, inspiration",
            "challenge": "restlessness, excess, bluntness, avoidance of limits",
            "growth": "Turn freedom into wisdom rather than escape.",
        },
        "Capricorn": {
            "core": "You define yourself through achievement, structure, responsibility, and steady ambition. You grow by building something meaningful over time.",
            "gifts": "discipline, authority, endurance, realism",
            "challenge": "rigidity, seriousness, emotional suppression, overwork",
            "growth": "Allow your humanity and vulnerability to exist alongside competence.",
        },
        "Aquarius": {
            "core": "You express yourself through originality, independence, and a future-facing perspective. Your path is to stay true to what is uniquely yours.",
            "gifts": "innovation, objectivity, originality, vision",
            "challenge": "detachment, rebellion for its own sake, emotional distance",
            "growth": "Balance individuality with heart-level connection.",
        },
        "Pisces": {
            "core": "Your identity is imaginative, empathetic, and spiritually sensitive. You grow when you trust intuition without losing form or boundaries.",
            "gifts": "compassion, creativity, intuition, receptivity",
            "challenge": "confusion, escapism, porous boundaries",
            "growth": "Give your sensitivity structure so it becomes a gift, not overwhelm.",
        },
    },
    "Moon": {
        "Aries": {
            "core": "Your emotions arise fast and directly. You tend to feel first and process later, and emotional honesty matters deeply to you.",
            "needs": "space to act, quick release, autonomy, movement",
            "challenge": "reactivity, impatience, emotional impulsiveness",
            "growth": "Learn how to stay with feelings long enough to understand them, not only discharge them.",
        },
        "Taurus": {
            "core": "You need stability, predictability, comfort, and sensory peace in order to feel emotionally safe.",
            "needs": "security, calm, routine, physical comfort, trust",
            "challenge": "emotional inertia, resistance to change, attachment",
            "growth": "Allow necessary emotional change without losing your grounding.",
        },
        "Gemini": {
            "core": "You process emotions through thought, language, and movement. Naming your feelings helps you regulate them.",
            "needs": "conversation, stimulation, perspective, variety",
            "challenge": "intellectualizing emotions, restlessness, inconsistency",
            "growth": "Let thoughts support your feelings without replacing them.",
        },
        "Cancer": {
            "core": "Your emotional world is strong, sensitive, and deeply connected to belonging, memory, and protection.",
            "needs": "safety, closeness, family feeling, emotional trust",
            "challenge": "moodiness, overprotection, withdrawal",
            "growth": "Create emotional security without over-clinging to the past.",
        },
        "Leo": {
            "core": "You need warmth, heartfelt connection, recognition, and emotional generosity to feel nourished.",
            "needs": "love, appreciation, playfulness, expression",
            "challenge": "hurt pride, emotional drama, needing validation",
            "growth": "Let your heart stay open even when you are not being mirrored back immediately.",
        },
        "Virgo": {
            "core": "You regulate emotions through order, clarity, usefulness, and careful observation.",
            "needs": "reliability, organization, competence, practical care",
            "challenge": "worry, overanalysis, self-criticism",
            "growth": "Not every feeling has to be fixed before it can be felt.",
        },
        "Libra": {
            "core": "You feel best when life is balanced, relationships are peaceful, and emotional exchange is mutual.",
            "needs": "harmony, fairness, companionship, aesthetic calm",
            "challenge": "people-pleasing, indecision, avoiding honest conflict",
            "growth": "Real peace comes from truth, not only pleasantness.",
        },
        "Scorpio": {
            "core": "Your emotional life is intense, private, penetrating, and transformative. You feel deeply and rarely superficially.",
            "needs": "trust, loyalty, emotional honesty, depth, privacy",
            "challenge": "suspicion, control, defensiveness, emotional extremes",
            "growth": "Use emotional depth for intimacy and healing rather than protection alone.",
        },
        "Sagittarius": {
            "core": "You need emotional freedom, hope, movement, and meaning. You recover by widening your perspective.",
            "needs": "space, optimism, exploration, truth",
            "challenge": "avoiding heavier emotions, restlessness, inconsistency",
            "growth": "Freedom also includes the freedom to stay present with discomfort.",
        },
        "Capricorn": {
            "core": "You may process emotions in a contained, responsible, or serious way, often feeling safer when life is under control.",
            "needs": "structure, competence, loyalty, respect, self-control",
            "challenge": "emotional inhibition, loneliness, over-responsibility",
            "growth": "Vulnerability is not weakness; it is part of real strength.",
        },
        "Aquarius": {
            "core": "You process feelings through distance, reflection, or uniqueness. Emotions may move through thought before they move through your body.",
            "needs": "space, perspective, freedom, authenticity",
            "challenge": "detachment, unpredictability, emotional distance",
            "growth": "Stay intellectually clear without disconnecting from feeling itself.",
        },
        "Pisces": {
            "core": "You are deeply sensitive, porous, intuitive, and emotionally absorbent. You often feel more than you can easily explain.",
            "needs": "gentleness, retreat, inspiration, compassion, spiritual nourishment",
            "challenge": "overwhelm, confusion, blurred emotional boundaries",
            "growth": "Learn what is yours to feel and what belongs to others.",
        },
    },
    "Mercury": {
        "Aries": {
            "core": "Your mind is fast, direct, and decisive. You think independently and often speak before over-editing yourself.",
            "gifts": "clarity, courage, quick response, initiative in speech",
            "challenge": "impatience, bluntness, mental haste",
            "growth": "Sharpen your truth without losing tact.",
        },
        "Taurus": {
            "core": "Your mind works steadily and practically. You prefer useful, grounded ideas that can be applied in real life.",
            "gifts": "common sense, patience, consistency, solid judgment",
            "challenge": "mental rigidity, slow adaptation, fixed opinions",
            "growth": "Stay grounded without closing off new information.",
        },
        "Gemini": {
            "core": "You are mentally curious, verbal, and highly adaptable. Your mind thrives on variety and connection.",
            "gifts": "wit, versatility, communication, fast learning",
            "challenge": "distraction, nervousness, superficiality",
            "growth": "Develop depth as well as range.",
        },
        "Cancer": {
            "core": "You think with memory, intuition, and emotional intelligence. Your communication often carries feeling even when subtle.",
            "gifts": "sensitivity, memory, intuitive perception, care in speech",
            "challenge": "subjectivity, defensiveness, mood-colored thinking",
            "growth": "Trust feeling-informed thinking without letting emotion distort everything.",
        },
        "Leo": {
            "core": "You communicate with confidence, warmth, style, and conviction. Your words want to leave an impression.",
            "gifts": "expressiveness, charisma, dramatic storytelling, confidence",
            "challenge": "pride in opinions, inflexibility, talking over others",
            "growth": "Let communication be radiant, not performative.",
        },
        "Virgo": {
            "core": "Your mind is analytical, precise, observant, and detail-oriented. You naturally notice what needs improvement.",
            "gifts": "discernment, accuracy, organization, practical intelligence",
            "challenge": "overthinking, criticism, perfectionism",
            "growth": "Use precision in service of clarity, not anxiety.",
        },
        "Libra": {
            "core": "You communicate diplomatically and seek fairness, nuance, and mutual understanding in dialogue.",
            "gifts": "balance, social intelligence, tact, perspective-taking",
            "challenge": "indecision, over-editing, avoiding directness",
            "growth": "Harmony is strongest when it includes honesty.",
        },
        "Scorpio": {
            "core": "You think deeply, strategically, and perceptively. You notice what lies beneath the surface.",
            "gifts": "insight, focus, psychological intelligence, investigation",
            "challenge": "suspicion, obsession, withholding",
            "growth": "Use your depth to understand, not only to protect or control.",
        },
        "Sagittarius": {
            "core": "You think broadly and speak honestly. Your mind is drawn to meaning, philosophy, and larger patterns.",
            "gifts": "vision, candor, wisdom-seeking, enthusiasm",
            "challenge": "overgeneralizing, bluntness, skipping details",
            "growth": "Keep the big picture while respecting complexity.",
        },
        "Capricorn": {
            "core": "Your communication is serious, clear, strategic, and purposeful. You value substance over noise.",
            "gifts": "discipline, realism, authority, practical planning",
            "challenge": "pessimism, rigidity, guarded communication",
            "growth": "Let structure support communication without making it emotionally closed.",
        },
        "Aquarius": {
            "core": "Your thinking is inventive, independent, and future-oriented. You often see patterns others miss.",
            "gifts": "innovation, originality, objectivity, conceptual thinking",
            "challenge": "detachment, contrarianism, inconsistency in attention",
            "growth": "Make your originality understandable and usable for others.",
        },
        "Pisces": {
            "core": "Your mind is intuitive, imaginative, symbolic, and nonlinear. You often understand through impression before logic.",
            "gifts": "creativity, intuition, empathy, poetic perception",
            "challenge": "fuzziness, mental overwhelm, vagueness",
            "growth": "Give shape to your intuition so others can follow it.",
        },
    },
    "Venus": {
        "Aries": {
            "core": "You love directly, passionately, and with strong desire. Attraction is often immediate and energetic.",
            "gifts": "bold affection, spontaneity, enthusiasm",
            "challenge": "impatience, chasing intensity, short-lived interest",
            "growth": "Let desire mature into devotion.",
        },
        "Taurus": {
            "core": "You value loyalty, pleasure, touch, beauty, and steadiness in love. You seek what feels safe and lasting.",
            "gifts": "sensuality, devotion, consistency, appreciation of beauty",
            "challenge": "possessiveness, resistance to change, over-comfort",
            "growth": "Allow love to stay steady without becoming stagnant.",
        },
        "Gemini": {
            "core": "You connect through words, humor, curiosity, and mental chemistry. Stimulation is part of attraction.",
            "gifts": "playfulness, charm, wit, flexibility",
            "challenge": "inconsistency, emotional lightness, split attention",
            "growth": "Build depth alongside variety.",
        },
        "Cancer": {
            "core": "You love protectively and emotionally. Affection is linked with safety, care, and emotional memory.",
            "gifts": "nurturance, tenderness, loyalty, devotion",
            "challenge": "clinginess, indirectness, sensitivity to rejection",
            "growth": "Love deeply without overprotecting yourself or others.",
        },
        "Leo": {
            "core": "You express love warmly, proudly, generously, and romantically. You want love to feel alive and wholehearted.",
            "gifts": "generosity, loyalty, romance, warmth",
            "challenge": "need for admiration, pride, dramatization",
            "growth": "Let love be radiant without making it dependent on applause.",
        },
        "Virgo": {
            "core": "You show love through thoughtfulness, help, detail, and practical care. Devotion often appears in small acts.",
            "gifts": "reliability, sincerity, care, discernment",
            "challenge": "over-analysis, criticism, guardedness",
            "growth": "Let tenderness be imperfect and human.",
        },
        "Libra": {
            "core": "You seek balance, harmony, beauty, and mutuality in love. Partnership is a major path of growth.",
            "gifts": "grace, diplomacy, romantic awareness, fairness",
            "challenge": "people-pleasing, indecision, idealization",
            "growth": "Choose real connection over perfect aesthetics.",
        },
        "Scorpio": {
            "core": "You love intensely, deeply, and all-or-nothing. Trust and emotional honesty are central to your bonds.",
            "gifts": "depth, loyalty, magnetism, devotion",
            "challenge": "jealousy, control, fear of betrayal",
            "growth": "Let intimacy be deep without becoming possessive.",
        },
        "Sagittarius": {
            "core": "You are attracted to freedom, adventure, honesty, and growth. Love must feel expansive, not confining.",
            "gifts": "openness, enthusiasm, optimism, generosity",
            "challenge": "avoidance of heaviness, restlessness, inconsistency",
            "growth": "Learn that commitment and freedom do not have to cancel each other out.",
        },
        "Capricorn": {
            "core": "You take love seriously and value loyalty, maturity, and long-term substance in relationships.",
            "gifts": "commitment, steadiness, reliability, discernment",
            "challenge": "emotional reserve, caution, fear of vulnerability",
            "growth": "Let emotional warmth support your loyalty.",
        },
        "Aquarius": {
            "core": "You value freedom, authenticity, friendship, and individuality in relationships.",
            "gifts": "acceptance, openness, originality, respect for space",
            "challenge": "distance, inconsistency, emotional coolness",
            "growth": "Stay free without becoming unavailable.",
        },
        "Pisces": {
            "core": "You love with softness, compassion, idealism, and emotional imagination. You often see the soul behind the person.",
            "gifts": "empathy, romance, devotion, tenderness",
            "challenge": "idealization, sacrifice, blurred boundaries",
            "growth": "Keep compassion without abandoning discernment.",
        },
    },
    "Mars": {
        "Aries": {
            "core": "Your drive is direct, immediate, and assertive. You move quickly when motivated and prefer action over delay.",
            "gifts": "courage, initiative, decisiveness",
            "challenge": "impulsiveness, anger, impatience",
            "growth": "Use force with direction, not just speed.",
        },
        "Taurus": {
            "core": "Your action style is steady, persistent, and physically grounded. Once committed, you are hard to stop.",
            "gifts": "endurance, patience, strength",
            "challenge": "stubbornness, passive resistance, slow change",
            "growth": "Know when persistence serves you and when it traps you.",
        },
        "Gemini": {
            "core": "Your energy moves through ideas, speech, multitasking, and quick adaptation.",
            "gifts": "mental agility, cleverness, versatility",
            "challenge": "scattered energy, inconsistency, argumentativeness",
            "growth": "Choose direction before spending energy in ten places at once.",
        },
        "Cancer": {
            "core": "Your drive is emotionally responsive and protective. You act strongly when something matters personally.",
            "gifts": "defensiveness in service of care, loyalty, emotional courage",
            "challenge": "indirect anger, mood-driven action, defensiveness",
            "growth": "Express needs directly instead of only protectively.",
        },
        "Leo": {
            "core": "You pursue what you want with pride, warmth, confidence, and creative force.",
            "gifts": "boldness, charisma, creative drive",
            "challenge": "ego conflicts, dramatization, stubborn pride",
            "growth": "Lead with heart, not only with the need to win.",
        },
        "Virgo": {
            "core": "Your drive is precise, useful, and strategic. You prefer efficient effort over chaotic action.",
            "gifts": "skill, focus, discipline, practical problem-solving",
            "challenge": "over-control, criticism, paralysis by analysis",
            "growth": "Act before everything is perfect.",
        },
        "Libra": {
            "core": "You assert yourself through balance, timing, diplomacy, and relationship awareness.",
            "gifts": "strategy, social intelligence, measured action",
            "challenge": "hesitation, indirectness, passive aggression",
            "growth": "Learn to act clearly even when harmony is at stake.",
        },
        "Scorpio": {
            "core": "Your drive is intense, strategic, powerful, and emotionally charged. You commit deeply and rarely halfway.",
            "gifts": "focus, resilience, strength, determination",
            "challenge": "control struggles, suppressed anger, extremes",
            "growth": "Use power consciously rather than defensively.",
        },
        "Sagittarius": {
            "core": "Your action style is adventurous, spontaneous, freedom-seeking, and ideal-driven.",
            "gifts": "enthusiasm, boldness, optimism",
            "challenge": "recklessness, impatience with limits, overextension",
            "growth": "Aim your fire so it becomes progress rather than scattered effort.",
        },
        "Capricorn": {
            "core": "Your drive is disciplined, strategic, patient, and achievement-oriented.",
            "gifts": "ambition, stamina, self-control, productivity",
            "challenge": "hardness, suppression, overwork",
            "growth": "Let achievement remain human and sustainable.",
        },
        "Aquarius": {
            "core": "You act independently, unconventionally, and according to your own logic and principles.",
            "gifts": "innovation, independence, courage to differ",
            "challenge": "detachment, unpredictability, resistance to authority",
            "growth": "Make rebellion meaningful, not automatic.",
        },
        "Pisces": {
            "core": "Your energy can move subtly, intuitively, and compassionately. Motivation often rises from feeling rather than force.",
            "gifts": "imagination, empathy, adaptability",
            "challenge": "diffuse will, avoidance, unclear direction",
            "growth": "Give your sensitivity a clear channel for action.",
        },
    },
}


PLANET_HOUSE_MEANINGS = {
    "Sun": {
        1: "Your identity is highly visible. Self-expression, confidence, and presence are central themes in life.",
        2: "Your sense of self is tied to values, money, stability, and self-worth. Building lasting value strengthens identity.",
        3: "You shine through communication, learning, teaching, and sharing ideas. Your voice matters.",
        4: "Your identity is deeply shaped by home, roots, family, and emotional foundations.",
        5: "You express yourself creatively, dramatically, romantically, and through joy.",
        6: "Your vitality grows through meaningful work, routines, skill, and self-improvement.",
        7: "Relationships strongly shape your identity; partnership mirrors you back to yourself.",
        8: "Your identity is intense, private, and transformed through deep emotional or life-altering experiences.",
        9: "You shine through travel, philosophy, education, and the search for meaning.",
        10: "Your identity is strongly connected to career, achievement, recognition, and public life.",
        11: "You express yourself through community, friendship, collective ideals, and future-oriented goals.",
        12: "Your identity has a private, inner, spiritual, or hidden dimension and may unfold through solitude or deep self-reflection.",
    },
    "Moon": {
        1: "Your emotions are visible and shape your whole presence. People often feel your moods and sensitivity immediately.",
        2: "Emotional safety comes from stability, comfort, predictability, and a strong sense of self-worth.",
        3: "You process feelings through words, thought, conversation, and everyday exchange.",
        4: "Your emotional life is rooted in home, family, belonging, memory, and inner safety.",
        5: "You express feelings creatively, romantically, playfully, and through heartfelt self-expression.",
        6: "You need emotional order, practical usefulness, and healthy routines to feel balanced.",
        7: "Relationships strongly affect your emotional state, and emotional mirroring matters deeply.",
        8: "Your feelings are deep, private, intense, and often transformative.",
        9: "You need meaning, freedom, growth, or hope in order to feel emotionally alive.",
        10: "Your emotional life is connected to achievement, recognition, reputation, and life direction.",
        11: "You feel nourished by friendship, community, shared ideals, and a sense of belonging to something bigger.",
        12: "Your emotional life is private, sensitive, intuitive, and often difficult to explain fully.",
    },
    "Mercury": {
        1: "You come across as thoughtful, verbal, curious, or observant. The mind is part of your identity.",
        2: "Your thinking tends to focus on practical matters, security, values, and resource management.",
        3: "This is a strong Mercury placement: learning, speaking, writing, and mental exchange are emphasized.",
        4: "Your mind is shaped by family, roots, memory, and private reflection.",
        5: "You communicate creatively and can express ideas with flair, humor, or artistry.",
        6: "Your mind is organized around work, analysis, skill, systems, and practical problem-solving.",
        7: "Conversation, negotiation, and one-to-one communication are major themes in relationships.",
        8: "You think deeply, privately, and psychologically; your mind goes beneath the surface.",
        9: "You are drawn to philosophy, teaching, big ideas, travel, and meaning-making.",
        10: "Communication, strategy, or intellect may play a major role in your public path or career.",
        11: "Your mind is future-oriented and thrives in groups, networks, and shared ideas.",
        12: "Your thinking may be private, intuitive, symbolic, or difficult to express directly at times.",
    },
    "Venus": {
        1: "Charm, beauty, affection, and social grace are part of how you naturally present yourself.",
        2: "Love, pleasure, and self-worth are connected to comfort, values, material stability, and appreciation.",
        3: "You express affection through words, conversation, humor, and mental connection.",
        4: "You seek love that feels safe, familiar, emotionally secure, and rooted.",
        5: "Romance, pleasure, beauty, play, and creativity are major themes in your love nature.",
        6: "You show love through care, helpfulness, consistency, and daily devotion.",
        7: "Partnership is one of the strongest areas of love and attraction in your chart.",
        8: "You love deeply, intensely, and with emotional or psychological depth.",
        9: "You are attracted to growth, adventure, meaning, and shared beliefs in love.",
        10: "Love, beauty, or charm may influence your public image, vocation, or life direction.",
        11: "You value friendship, openness, equality, and shared ideals in relationships.",
        12: "Your love nature can be private, dreamy, hidden, sacrificial, or highly idealized.",
    },
    "Mars": {
        1: "You act directly and are often seen as energetic, assertive, or strong-willed.",
        2: "You pursue security, money, and values with determination and persistence.",
        3: "Your energy moves through speech, ideas, debate, learning, and a busy mental environment.",
        4: "Action is tied to home, family, emotional roots, and inner security needs.",
        5: "You pursue pleasure, romance, creativity, and risk with passion and force.",
        6: "You work hard, move actively, and put energy into routines, productivity, and improvement.",
        7: "Partnerships activate desire, conflict, passion, and the need to assert yourself with others.",
        8: "Your drive is intense, strategic, and transformative; power dynamics may be a major life theme.",
        9: "You pursue truth, travel, belief, and experience with conviction and force.",
        10: "Ambition, competition, career drive, and achievement are strongly emphasized.",
        11: "Your energy is drawn toward group causes, community efforts, and future goals.",
        12: "Your drive may be hidden, internalized, indirect, or connected with inner struggles and spiritual work.",
    },
}


GENERIC_ASPECT_MEANINGS = {
    "conjunction": "These two energies are fused together and act as one concentrated theme in the personality.",
    "sextile": "These two parts of the chart can cooperate productively when consciously developed.",
    "square": "These energies create inner tension that pushes growth, effort, and self-awareness.",
    "trine": "These energies flow together naturally and support one another with ease.",
    "opposition": "These themes pull in opposite directions and require balance, awareness, and integration.",
}


ASPECT_MEANINGS = {
    ("Sun", "Moon", "trine"): "Your identity and emotions tend to work together harmoniously, creating inner coherence and emotional flow.",
    ("Sun", "Moon", "square"): "You may feel tension between what you consciously want and what you emotionally need. Growth comes through integrating will and feeling.",
    ("Sun", "Moon", "opposition"): "You may experience a push-pull between identity and emotional needs, often learning balance through relationships and self-awareness.",
    ("Venus", "Saturn", "square"): "Love may feel serious, cautious, or connected to lessons about trust, vulnerability, timing, and self-worth.",
    ("Mercury", "Jupiter", "conjunction"): "Your mind is broad, optimistic, and drawn to big ideas, teaching, philosophy, and possibility.",
    ("Mars", "Pluto", "trine"): "You have powerful drive, resilience, and deep inner intensity that can be used with great focus and strength.",
}


SIGN_RULERS = {sign: rulers[0] for sign, rulers in get_sign_rulers().items()}


def get_planet_sign_interpretation(planet: str, sign: str) -> dict[str, Any] | None:
    return PLANET_SIGN_MEANINGS.get(planet, {}).get(sign)


def get_planet_house_interpretation(planet: str, house: int) -> str | None:
    return PLANET_HOUSE_MEANINGS.get(planet, {}).get(house)


def get_aspect_interpretation(planet_1: str, planet_2: str, aspect: str) -> str | None:
    direct_key = (planet_1, planet_2, aspect)
    reverse_key = (planet_2, planet_1, aspect)

    if direct_key in ASPECT_MEANINGS:
        return ASPECT_MEANINGS[direct_key]
    if reverse_key in ASPECT_MEANINGS:
        return ASPECT_MEANINGS[reverse_key]

    return None


def build_generic_planet_sign_interpretation(planet: str, sign: str) -> dict[str, str] | None:
    planet_data = PLANETS.get(planet)
    sign_data = SIGNS.get(sign)

    if not planet_data or not sign_data:
        return None

    return {
        "core": (
            f"{planet} describes {planet_data['function']}. In {sign}, it is expressed in a "
            f"{sign_data['style']} way. This often gives a tone of {sign_data['element']} "
            f"energy and {sign_data['modality'].lower()} style."
        ),
        "gifts": f"Potential strengths include {', '.join(sign_data['strengths'])}.",
        "challenge": f"Potential challenges include {', '.join(sign_data['shadow'])}.",
        "growth": (
            f"Growth comes from expressing {planet}'s function with the best of {sign} "
            f"without becoming trapped in its shadow."
        ),
    }


def build_generic_planet_house_interpretation(planet: str, house: int) -> str | None:
    planet_data = PLANETS.get(planet)
    house_data = HOUSES.get(house)

    if not planet_data or not house_data:
        return None

    return (
        f"{planet} in the {house}th house focuses {planet_data['function']} into the area of "
        f"{house_data['area']}."
    )


def build_generic_aspect_interpretation(planet_1: str, planet_2: str, aspect: str) -> str | None:
    p1 = PLANETS.get(planet_1)
    p2 = PLANETS.get(planet_2)
    aspect_data = ASPECTS.get(aspect)

    if not p1 or not p2 or not aspect_data:
        return None

    return (
        f"{planet_1} ({p1['function']}) and {planet_2} ({p2['function']}) form a {aspect}, "
        f"which suggests {aspect_data['meaning']}"
    )


def summarize_element_balance(planets: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter()

    for p in planets:
        sign = p.get("sign")
        if sign in SIGNS:
            counts[SIGNS[sign]["element"]] += 1

    dominant = counts.most_common(1)[0][0] if counts else None
    lacking = [e for e in ["Fire", "Earth", "Air", "Water"] if counts.get(e, 0) == 0]

    return {
        "counts": dict(counts),
        "dominant": dominant,
        "lacking": lacking,
        "interpretation": build_element_balance_interpretation(counts),
    }


def build_element_balance_interpretation(counts: Counter) -> str:
    parts = []

    fire = counts.get("Fire", 0)
    earth = counts.get("Earth", 0)
    air = counts.get("Air", 0)
    water = counts.get("Water", 0)

    if fire:
        parts.append(f"Fire emphasizes drive, passion, confidence, and spontaneity ({fire}).")
    if earth:
        parts.append(f"Earth emphasizes practicality, stability, and realism ({earth}).")
    if air:
        parts.append(f"Air emphasizes thought, communication, and perspective ({air}).")
    if water:
        parts.append(f"Water emphasizes feeling, intuition, and emotional depth ({water}).")

    missing = [e for e in ["Fire", "Earth", "Air", "Water"] if counts.get(e, 0) == 0]
    if missing:
        parts.append(
            f"A missing or very weak element may point to qualities that need more conscious development: {', '.join(missing)}."
        )

    return " ".join(parts) if parts else "Element balance could not be determined."


def summarize_modality_balance(planets: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter()

    for p in planets:
        sign = p.get("sign")
        if sign in SIGNS:
            counts[SIGNS[sign]["modality"]] += 1

    dominant = counts.most_common(1)[0][0] if counts else None

    return {
        "counts": dict(counts),
        "dominant": dominant,
        "interpretation": build_modality_balance_interpretation(counts),
    }


def build_modality_balance_interpretation(counts: Counter) -> str:
    parts = []

    cardinal = counts.get("Cardinal", 0)
    fixed = counts.get("Fixed", 0)
    mutable = counts.get("Mutable", 0)

    if cardinal:
        parts.append(f"Cardinal emphasis suggests initiative, leadership, and a tendency to start things ({cardinal}).")
    if fixed:
        parts.append(f"Fixed emphasis suggests consistency, loyalty, endurance, and persistence ({fixed}).")
    if mutable:
        parts.append(f"Mutable emphasis suggests flexibility, adaptability, and responsiveness to change ({mutable}).")

    return " ".join(parts) if parts else "Modality balance could not be determined."


def build_big_three_summary(planets: list[dict[str, Any]], angles: dict[str, str] | None = None) -> str:
    lookup = {p["planet"]: p for p in planets}
    parts = []

    sun = lookup.get("Sun")
    moon = lookup.get("Moon")
    asc = angles.get("Ascendant") if angles else None

    if sun:
        parts.append(
            f"Sun in {sun['sign']} in the {sun['house']}th house suggests a core identity expressed through "
            f"{SIGNS[sun['sign']]['style']} qualities in the life area of {HOUSES[sun['house']]['area']}."
        )

    if moon:
        parts.append(
            f"Moon in {moon['sign']} in the {moon['house']}th house suggests emotional needs shaped by "
            f"{SIGNS[moon['sign']]['style']} qualities, especially around {HOUSES[moon['house']]['area']}."
        )

    if asc:
        sign_data = SIGNS.get(asc)
        if sign_data:
            parts.append(
                f"Ascendant in {asc} suggests you approach life in a {sign_data['style']} way and are often read by others through that style."
            )

    return " ".join(parts)


def build_planet_entry(planet_data: dict[str, Any]) -> dict[str, Any]:
    planet = planet_data["planet"]
    sign = planet_data["sign"]
    house = planet_data["house"]

    sign_interp = get_planet_sign_interpretation(planet, sign)
    if not sign_interp:
        sign_interp = build_generic_planet_sign_interpretation(planet, sign)

    house_interp = get_planet_house_interpretation(planet, house)
    if not house_interp:
        house_interp = build_generic_planet_house_interpretation(planet, house)

    sign_meta = SIGNS.get(sign, {})
    ruler = SIGN_RULERS.get(sign)

    return {
        "planet": planet,
        "sign": sign,
        "house": house,
        "element": sign_meta.get("element"),
        "modality": sign_meta.get("modality"),
        "ruler": ruler,
        "sign_interpretation": sign_interp,
        "house_interpretation": house_interp,
        "priority": "high" if planet in {"Sun", "Moon"} else "normal",
    }


def build_aspect_entry(aspect_data: dict[str, Any]) -> dict[str, Any]:
    planet_1 = aspect_data["planet_1"]
    planet_2 = aspect_data["planet_2"]
    aspect = aspect_data["aspect"]

    meaning = get_aspect_interpretation(planet_1, planet_2, aspect)
    if not meaning:
        meaning = build_generic_aspect_interpretation(planet_1, planet_2, aspect)

    return {
        "planet_1": planet_1,
        "planet_2": planet_2,
        "aspect": aspect,
        "orb": aspect_data.get("orb"),
        "meaning": meaning,
        "tone": ASPECTS.get(aspect, {}).get("tone"),
    }


def build_chart_synthesis(
    planets: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
    angles: dict[str, str] | None = None,
) -> list[str]:
    synthesis: list[str] = []

    lookup = {p["planet"]: p for p in planets}

    if "Sun" in lookup and "Moon" in lookup:
        synthesis.append(
            f"Your chart begins with the relationship between Sun in {lookup['Sun']['sign']} and "
            f"Moon in {lookup['Moon']['sign']}: this describes how identity and emotional needs may support or challenge one another."
        )

    if angles and angles.get("Ascendant"):
        synthesis.append(
            f"Ascendant in {angles['Ascendant']} adds an outer style and first-impression layer that modifies how the rest of the chart is expressed."
        )

    if angles and angles.get("MC"):
        synthesis.append(
            f"MC in {angles['MC']} adds a career and public-direction theme that should be considered when interpreting ambition, vocation, and social role."
        )

    element_balance = summarize_element_balance(planets)
    if element_balance["dominant"]:
        synthesis.append(
            f"The chart has a strong {element_balance['dominant']} emphasis, which colors the overall personality tone."
        )

    modality_balance = summarize_modality_balance(planets)
    if modality_balance["dominant"]:
        synthesis.append(
            f"The chart leans toward {modality_balance['dominant']} energy, shaping how change, action, and consistency are handled."
        )

    if aspects:
        hard_aspects = [a for a in aspects if a["aspect"] in {"square", "opposition"}]
        soft_aspects = [a for a in aspects if a["aspect"] in {"trine", "sextile"}]

        if hard_aspects:
            synthesis.append(
                "Hard aspects show where growth comes through tension, friction, and internal conflict."
            )
        if soft_aspects:
            synthesis.append(
                "Soft aspects show where strengths, talents, and natural ease are already present."
            )

    return synthesis


def build_chart_interpretation(
    planets: list[dict[str, Any]],
    aspects: list[dict[str, Any]],
    angles: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    planets example:
    [
        {"planet": "Sun", "sign": "Leo", "house": 10},
        {"planet": "Moon", "sign": "Scorpio", "house": 1},
        {"planet": "Mercury", "sign": "Virgo", "house": 10},
    ]

    aspects example:
    [
        {"planet_1": "Sun", "planet_2": "Moon", "aspect": "square", "orb": 3.2},
        {"planet_1": "Mercury", "planet_2": "Jupiter", "aspect": "conjunction", "orb": 4.0},
    ]

    angles example:
    {
        "Ascendant": "Sagittarius",
        "MC": "Virgo",
        "Descendant": "Gemini",
        "IC": "Pisces"
    }
    """
    planet_interpretations = [build_planet_entry(p) for p in planets]
    aspect_interpretations = [build_aspect_entry(a) for a in aspects]

    return {
        "big_three_summary": build_big_three_summary(planets, angles),
        "angles": angles or {},
        "planets": planet_interpretations,
        "aspects": aspect_interpretations,
        "element_balance": summarize_element_balance(planets),
        "modality_balance": summarize_modality_balance(planets),
        "synthesis": build_chart_synthesis(planets, aspects, angles),
    } 