/**
 * Zodi's definitions — the astrology words, explained.
 *
 * Zodi speaks like an astrologer because that is what makes it feel real, but
 * "your Venus is square Saturn" means nothing to most people and nobody wants
 * to have to ask. So the words explain themselves on a tap, and the writing
 * never has to stop and define itself mid-sentence.
 *
 * Written by Martina. To add a term, add an entry: `title` is the heading on
 * the card, `body` the explanation, and `match` every spelling and inflection
 * that should light up in an answer ("square", "squares", "squaring").
 */
export type GlossaryEntry = {
  title: string;
  body: string;
  match: string[];
  /**
   * How badly this word needs explaining. Nearly everyone knows roughly what
   * Venus or Scorpio is about; almost nobody knows "detriment", "quincunx" or
   * "chart ruler". When an answer has more terms than can be marked without
   * turning into a textbook, the obscure ones win.
   */
  weight: number;
};

const COMMON = 1;   // planets and signs — recognised, if not precisely understood
const JARGON = 2;   // the words that actually stop someone reading

const E = (title: string, body: string, ...match: string[]): GlossaryEntry => ({
  title,
  body,
  match: match.length ? match : [title.toLowerCase()],
  weight: JARGON,
});

const common = (entry: GlossaryEntry): GlossaryEntry => ({ ...entry, weight: COMMON });

export const ENTRIES: GlossaryEntry[] = [
  // ── Zodiac signs ───────────────────────────────────────────────────────
  common(E("Aries", "Fire sign. Direct, impulsive, competitive, independent, and action-oriented. Aries energy wants to move first and figure things out later, and can become impatient when things feel slow or passive.")),
  common(E("Taurus", "Earth sign. Stable, sensual, loyal, stubborn, comfort-oriented, and security-driven. Taurus wants consistency and something solid to hold onto, but can resist change even when change is necessary.")),
  common(E("Gemini", "Air sign. Curious, social, adaptable, witty, restless, and mentally quick. Gemini needs constant mental stimulation and variety, and tends to process life by talking, questioning, and gathering information.")),
  common(E("Cancer", "Water sign. Emotional, protective, intuitive, nostalgic, sensitive, and attachment-oriented. Cancer needs emotional security and familiarity, and often protects its vulnerability by retreating or becoming defensive.")),
  common(E("Leo", "Fire sign. Expressive, confident, warm, proud, creative, and recognition-oriented. Leo wants to feel special and appreciated, and usually needs a strong sense of personal identity and self-expression.")),
  common(E("Virgo", "Earth sign. Analytical, practical, observant, perfectionistic, helpful, and detail-oriented. Virgo notices what could be improved and often expresses care by fixing problems, helping, or making itself useful.")),
  common(E("Libra", "Air sign. Charming, diplomatic, romantic, social, aesthetic, and relationship-oriented. Libra naturally thinks in terms of other people and different perspectives, but can struggle with indecision or avoiding conflict.")),
  common(E("Scorpio", "Water sign. Intense, private, perceptive, loyal, suspicious, emotionally deep, and transformative. Scorpio wants depth and truth rather than surface-level connection, and can become obsessive or controlling when it feels unsafe.")),
  common(E("Sagittarius", "Fire sign. Adventurous, optimistic, blunt, independent, curious, and freedom-oriented. Sagittarius needs movement, growth, new experiences, and a sense that life is expanding rather than restricting them.")),
  common(E("Capricorn", "Earth sign. Ambitious, disciplined, controlled, realistic, responsible, and achievement-oriented. Capricorn tends to take life seriously and wants to build something lasting, often becoming more comfortable and confident with age.")),
  common(E("Aquarius", "Air sign. Independent, unconventional, intellectual, detached, rebellious, and future-oriented. Aquarius needs freedom to think and live differently, and can care deeply about people while still seeming emotionally distant one-on-one.")),
  common(E("Pisces", "Water sign. Sensitive, imaginative, romantic, intuitive, empathetic, and idealistic. Pisces absorbs emotions and atmosphere easily, and can blur the line between reality, fantasy, intuition, and projection.")),

  // ── Planets ────────────────────────────────────────────────────────────
  common(E("Sun", "Your Sun represents your core identity, ego, vitality, and the person you are developing into. It describes what makes you feel most like yourself and where you naturally want to shine.")),
  common(E("Moon", "Your Moon represents your emotional needs, instincts, habits, comfort, and private self. It shows what makes you feel emotionally safe and how you react before you have time to think logically.")),
  common(E("Mercury", "Mercury represents communication, thinking, learning, perception, and how your mind works. Its sign and house show how you process information and express what is going on inside your head.")),
  common(E("Venus", "Venus represents love, attraction, affection, beauty, pleasure, values, and what you are drawn toward. In relationships it describes how you love, what makes you feel wanted, and what kind of people or dynamics naturally attract you.")),
  common(E("Mars", "Mars represents desire, sex drive, anger, motivation, aggression, pursuit, and how you go after what you want. In attraction it can show what turns you on and how you pursue someone once you want them.")),
  common(E("Jupiter", "Jupiter represents expansion, luck, opportunity, beliefs, confidence, wisdom, and growth. It shows where life tends to open up for you and where you learn by experiencing more rather than restricting yourself.")),
  common(E("Saturn", "Saturn represents responsibility, fear, limitations, discipline, maturity, boundaries, and long-term lessons. Its placement often feels difficult earlier in life but can eventually become one of your greatest areas of strength.")),
  common(E("Uranus", "Uranus represents rebellion, freedom, disruption, originality, sudden change, and breaking established patterns. It shows where you resist being controlled and where your life may develop in unconventional or unpredictable ways.")),
  common(E("Neptune", "Neptune represents dreams, fantasy, spirituality, intuition, idealization, illusion, and blurred boundaries. It can show enormous imagination and sensitivity, but also where you are most likely to romanticize something or see what you want to see.")),
  common(E("Pluto", "Pluto represents power, obsession, control, destruction, rebirth, transformation, and psychological intensity. Its placement shows where experiences can affect you extremely deeply and force you to change rather than simply move on.")),

  // ── Points ─────────────────────────────────────────────────────────────
  E("Ascendant", "Your Ascendant is the zodiac sign rising on the eastern horizon at the exact moment you were born. It represents how you approach life, how other people initially experience you, and the basic style through which the rest of your chart expresses itself.", "ascendant", "rising sign", "rising"),
  E("Descendant", "The Descendant is directly opposite your Ascendant and begins your 7th house. It describes qualities you tend to seek, attract, or encounter through close relationships and partnerships."),
  E("Midheaven", "The Midheaven represents career, reputation, ambition, public image, and what you may become known for. It is less about your private personality and more about the direction you are building toward in the outside world.", "midheaven", "mc"),
  E("IC", "The IC is opposite the Midheaven and represents home, family, roots, childhood foundations, and your most private self. It can describe where you come from emotionally and what you need when nobody else is watching.", "ic"),
  E("North Node", "The North Node represents qualities, experiences, and patterns you are being pushed toward developing. It can initially feel unfamiliar or uncomfortable because it requires moving beyond what already comes naturally.", "north node"),
  E("South Node", "The South Node represents familiar patterns, abilities, and behaviors that come naturally but can become limiting when overused. It is not necessarily something you need to abandon, but something you need to balance with the North Node.", "south node"),
  E("Chiron", "Chiron represents a sensitive psychological wound or insecurity that can become an important source of understanding and growth. Its placement often shows something you are particularly sensitive about, even when other people do not realize it."),
  E("Lilith", "Lilith represents suppressed desire, independence, taboo, shame, rebellion, and parts of yourself that refuse to be controlled. In attraction and relationships it can show where desire feels especially raw, complicated, magnetic, or socially uncomfortable.", "lilith", "black moon lilith"),
  E("Vertex", "The Vertex is a calculated point often associated with encounters that feel unusually significant or outside your control. It is especially looked at in synastry, because contacts to it can make meeting someone feel strangely important or meant to happen."),
  E("Part of Fortune", "The Part of Fortune is a calculated point associated with natural flow, fulfillment, and circumstances where different parts of the chart work together easily. Its sign and house can describe areas where things feel particularly natural or rewarding.", "part of fortune"),

  // ── Houses ─────────────────────────────────────────────────────────────
  E("1st house — self", "The 1st house represents identity, appearance, personality, behavior, and the way you approach the world. Planets here become very visible parts of your personality and often strongly affect how other people experience you.", "1st house", "first house"),
  E("2nd house — money and values", "The 2nd house represents money, possessions, material security, self-worth, and personal values. It describes what makes you feel secure and how you relate to what you own, earn, and consider valuable.", "2nd house", "second house"),
  E("3rd house — communication", "The 3rd house represents communication, thinking, everyday learning, siblings, neighbors, and your immediate environment. It describes how you gather information and interact with the world around you on a daily basis.", "3rd house", "third house"),
  E("4th house — home and family", "The 4th house represents home, family, roots, childhood, privacy, and emotional foundations. It describes where you come from psychologically and what you need in order to feel genuinely at home.", "4th house", "fourth house"),
  E("5th house — romance and pleasure", "The 5th house represents dating, flirting, sex as pleasure, creativity, fun, attention, self-expression, and children. In relationship readings it can describe crushes and romantic excitement, before the commitment and partnership themes of the 7th house.", "5th house", "fifth house"),
  E("6th house — routine and work", "The 6th house represents daily routines, work, responsibilities, health habits, organization, and self-improvement. It describes the small repeated things that structure your everyday life.", "6th house", "sixth house"),
  E("7th house — relationships", "The 7th house represents committed relationships, marriage, partnerships, contracts, and one-to-one dynamics. The sign on the Descendant, its ruler, and planets inside this house can say a lot about who you attract and how you behave in serious relationships.", "7th house", "seventh house"),
  E("8th house — intimacy and transformation", "The 8th house represents deep intimacy, vulnerability, shared resources, psychological entanglement, power, trust, loss, and transformation. In relationships it can describe bonds that feel consuming, exposing, sexually intense, or difficult to remain emotionally detached from.", "8th house", "eighth house"),
  E("9th house — beliefs and expansion", "The 9th house represents travel, higher education, philosophy, religion, worldview, foreign cultures, and the search for meaning. It describes how you expand beyond the environment and ideas you already know.", "9th house", "ninth house"),
  E("10th house — career and reputation", "The 10th house represents career, status, achievement, authority, reputation, and your public life. Planets here often become especially visible to other people and can strongly influence what you want to accomplish.", "10th house", "tenth house"),
  E("11th house — friendships and future", "The 11th house represents friendships, groups, communities, networks, social circles, hopes, and long-term goals. It describes the people and communities you connect with beyond intimate one-to-one relationships.", "11th house", "eleventh house"),
  E("12th house — subconscious and hidden life", "The 12th house represents the unconscious, isolation, hidden emotions, secrets, endings, spirituality, escapism, and things that are difficult to see clearly about yourself. Planets here can operate privately or unconsciously, and sometimes take longer for the person to fully understand.", "12th house", "twelfth house"),

  // ── Aspects ────────────────────────────────────────────────────────────
  E("Conjunction — 0°", "A conjunction happens when two planets are very close together and their energies become strongly blended. Whether this feels easy or difficult depends heavily on which planets are involved.", "conjunction", "conjunct"),
  E("Opposition — 180°", "An opposition creates tension between two opposite energies that need to learn how to coexist. It frequently plays out through relationships, because another person can seem to embody the side of the opposition you are struggling to integrate.", "opposition", "opposing", "opposes"),
  E("Square — 90°", "A square creates friction, pressure, and conflict between two planets. It is challenging but extremely motivating, because the discomfort pushes you to act, develop, and change.", "square", "squares", "squaring"),
  E("Trine — 120°", "A trine represents an easy and natural flow between two planets. The qualities involved usually work together without much effort, although this ease can sometimes mean the ability is taken for granted.", "trine", "trines", "trining"),
  E("Sextile — 60°", "A sextile represents compatibility and opportunity between two planets. Unlike a trine, it often becomes more powerful when you consciously choose to use the potential it provides.", "sextile", "sextiles"),
  E("Quincunx — 150°", "A quincunx connects energies that do not naturally understand each other and therefore require constant adjustment. It can create a feeling that fixing one side somehow throws the other side out of balance.", "quincunx", "inconjunct"),

  // ── The mechanics ──────────────────────────────────────────────────────
  E("Degrees", "Every sign contains 30 degrees, so a planet's exact degree gives a much more precise location than simply knowing its sign. Degrees become especially important when determining aspects, synastry contacts, transits, and how tightly two planets interact.", "degree", "degrees"),
  E("Orb", "An orb is the number of degrees separating an aspect from being exact. Generally, the tighter the orb, the stronger and more noticeable the aspect tends to be.", "orb"),
  E("House ruler", "The ruler of a house is the planet that rules the zodiac sign sitting on that house's cusp. Looking at where that planet is placed connects the topics of the house it rules with the house and sign where the ruler actually sits.", "house ruler", "house rulers"),
  E("Chart ruler", "The chart ruler is the planet that rules your Ascendant sign. Because the Ascendant structures the entire house system, the chart ruler's sign, house, and aspects can become especially important in understanding the overall chart.", "chart ruler"),
  E("Retrograde", "A retrograde planet appears to move backward from Earth's perspective, although it is not physically moving backward through space. Astrologically, its themes are usually more internalized, reflective, complicated, or expressed differently from the usual outward pattern.", "retrograde", "retrogrades"),
  E("Stellium", "A stellium is a strong concentration of multiple planets in the same sign or house. It makes that particular sign or area of life disproportionately important in the chart.", "stellium"),
  E("Element", "The signs are divided into fire, earth, air, and water, representing different basic ways of operating. Fire emphasizes action and inspiration, earth practicality and stability, air thought and communication, and water emotion and intuition.", "element", "elements"),
  E("Modality", "The signs are also divided into cardinal, fixed, and mutable, based on how they respond to change and action. Cardinal signs initiate, fixed signs sustain and resist change, and mutable signs adapt and transition.", "modality", "cardinal", "mutable"),
  E("Synastry", "Synastry compares two natal charts by looking at the aspects one person's planets make to the other person's planets and houses. It can show attraction, compatibility, conflict, emotional impact, communication patterns, and which person activates particular parts of the other's chart.", "synastry"),
  E("Composite chart", "A composite chart mathematically combines two charts to create a chart representing the relationship itself, rather than either individual person. It is used to examine the overall identity, strengths, problems, and patterns of the relationship.", "composite chart", "composite"),
  E("Transit", "A transit compares the planets' current positions in the sky with the positions in a natal chart. It is used to examine periods when certain themes, opportunities, pressures, or changes may become more prominent.", "transit", "transits", "transiting"),
  E("Natal chart", "A natal chart is a map of the sky calculated for the exact date, time, and location of your birth. The signs describe how energies express themselves, the planets describe what is being expressed, the houses describe where it happens, and the aspects describe how those parts interact.", "natal chart", "natal", "birth chart"),
];

/** Every matchable spelling, pointing at its entry. */
const BY_MATCH = new Map<string, GlossaryEntry>();
for (const entry of ENTRIES) {
  for (const m of entry.match) BY_MATCH.set(m.toLowerCase(), entry);
}

const escape = (t: string) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/**
 * One expression matching any known term on a word boundary, longest first so
 * "north node" wins over "node" and "7th house" over "house".
 *
 * Built once at module load: this runs over every answer as it renders.
 */
export const TERM_PATTERN = new RegExp(
  `\\b(${[...BY_MATCH.keys()].sort((a, b) => b.length - a.length).map(escape).join("|")})\\b`,
  "gi",
);

export function lookup(text: string): GlossaryEntry | undefined {
  return BY_MATCH.get(text.toLowerCase());
}
