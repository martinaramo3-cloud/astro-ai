"""
book_knowledge.py
-----------------
Astrology interpretations sourced directly from your book.
These override or enrich the generic interpretations in planets.py.

Structure:
  BOOK_HOUSE_COMBOS      — paired 4th/10th, 5th/11th, 6th/12th house readings
  BOOK_SIGN_EXTENDED     — richer sign descriptions from book
  BOOK_PLANET_DIGNITIES  — how each planet feels in each sign (ruler/exalt/detriment/fall)
  BOOK_ELEMENTS          — element philosophy from book
  BOOK_MODALITIES        — modality philosophy from book
"""

# ---------------------------------------------------------------------------
# PAIRED HOUSE COMBINATIONS (IC/MC axis, 5th/11th axis, 6th/12th axis)
# Sourced directly from book chapters on house axes.
# Usage: BOOK_HOUSE_COMBOS[(4, sign_4th, sign_10th)] -> interpretation dict
# ---------------------------------------------------------------------------

BOOK_HOUSE_COMBOS = {

    # ── 4th / 10th AXIS ─────────────────────────────────────────────────────
    # The 4th house (IC) = your roots, origin, deepest emotional needs.
    # The 10th house (MC) = your calling, public image, what you give society.

    ("4_10", "Aries", "Libra"): {
        "ic": (
            "You grew up in a family with a lot of tension and pressure, but they taught you "
            "courage, honesty, and self-reliance. There was little comfort zone at home — "
            "you were constantly pushed and challenged, which made you ambitious."
        ),
        "mc": (
            "Because of that family tension, in the world you try to be diplomatic, liberal, "
            "and balanced — offering exactly what was missing at home. Your calling is to bring "
            "empathy and compromise, helping people meet in the middle."
        ),
    },

    ("4_10", "Taurus", "Scorpio"): {
        "ic": (
            "You had a calm, abundant childhood — material comfort, warmth, and support. "
            "Your family let you be yourself. There was financial stability and a sense that "
            "something solid would always remain for you."
        ),
        "mc": (
            "That stable foundation gives you the strength to offer the world something "
            "transformative. You can dismantle painful patterns others can't see. People share "
            "with you their deepest things; your direct honesty may sting but ultimately heals. "
            "Scorpio on the 10th means at least one radical career transformation in your life."
        ),
    },

    ("4_10", "Gemini", "Sagittarius"): {
        "ic": (
            "A lively, fun family but without deep emotional grounding — more mental support "
            "than heartfelt warmth. Constant movement, possibly two homes, lighthearted chaos."
        ),
        "mc": (
            "Your calling is expanding consciousness — teaching, traveling, working abroad, "
            "studying. After growing up in chaos, you need a clear goal and the courage to "
            "follow it all the way. Coaching, international work, and dynamic roles fit well."
        ),
    },

    ("4_10", "Cancer", "Capricorn"): {
        "ic": (
            "A loving, supportive family that honors tradition and gives you a strong sense "
            "of belonging and identity. You feel close to your relatives and act freely within "
            "that safety. However, parental pressure about social image may also be present."
        ),
        "mc": (
            "You are suited to serious, responsible positions — this placement is associated "
            "with state structures and major responsibilities. Things develop slowly here but "
            "your calling reveals itself fully and clearly — the key questions are: what do "
            "you truly want to do, and what responsibility would you carry without it feeling heavy?"
        ),
    },

    ("4_10", "Leo", "Aquarius"): {
        "ic": (
            "You grew up in a warm, loving, artistically rich family — plenty of affection. "
            "There may have been dramatic moments (raised voices, packed bags) but always "
            "followed by deep love. You feel genuinely cherished."
        ),
        "mc": (
            "Your calling is connected to freedom, equality, friendship, and forming groups "
            "in society. Social media, robotics, astrology, astronomy, science, and technology "
            "all fit. You want to spread knowledge across humanity — you are a communicator "
            "of ideas to the collective."
        ),
    },

    ("4_10", "Virgo", "Pisces"): {
        "ic": (
            "A very critical upbringing, though full of care. Nothing was ever quite enough "
            "no matter how hard you tried. You were taught thorough domestic responsibility "
            "and learned to give care — but the weight of criticism was real."
        ),
        "mc": (
            "Tired of purely material and physical care, you want to serve humanity in an "
            "intangible way — art, psychology, esotericism, mental health, large-scale global "
            "causes. You are a good business person because you navigate complexity well; "
            "attention to finances keeps things stable."
        ),
    },

    ("4_10", "Libra", "Aries"): {
        "ic": (
            "A balanced, careful, calm family environment. Relationships were discussed openly; "
            "you were given a good model for being a fair and attentive partner."
        ),
        "mc": (
            "That balanced upbringing gave you the tools to be independent and create something "
            "of your own. You need significant freedom in your work even when employed by others. "
            "Sports, physical activity, and roles requiring boldness are well suited."
        ),
    },

    ("4_10", "Scorpio", "Taurus"): {
        "ic": (
            "A family environment with tension, possible conflict or emotional insecurity — "
            "an unstable foundation that has left its mark."
        ),
        "mc": (
            "Your life goal is to reach abundance — material, relational, and in freedom and "
            "leisure. Investment work, work with material and beautiful objects, or business "
            "all work well. Many prefer working for someone else to secure stability rather "
            "than taking entrepreneurial risk."
        ),
    },

    ("4_10", "Sagittarius", "Gemini"): {
        "ic": (
            "A fun, traveling family that was also quite demanding. High expectations, a focus "
            "on success and happiness without wasted energy. They required focus from you."
        ),
        "mc": (
            "Because of that training you can handle two things at once — you learned to focus "
            "and navigate well, but personally you have far more flexibility than your parents. "
            "You love learning and traveling, enjoy being around young people, dislike heavy "
            "responsibilities, and thrive with short-term projects and trade or business."
        ),
    },

    ("4_10", "Capricorn", "Cancer"): {
        "ic": (
            "Very demanding parents — emotional toughness rather than warmth. They showed love "
            "through actions and responsibility rather than words, ensuring your future through "
            "strictness rather than tenderness."
        ),
        "mc": (
            "Because of that strictness you seek emotional fulfillment through your work, "
            "becoming a kind of parent to everyone around you. You work best in a team, often "
            "with people who depend on you — a nurturing, healing role. A healing or caregiving "
            "vocation suits this placement."
        ),
    },

    ("4_10", "Aquarius", "Leo"): {
        "ic": (
            "You grew up with a lot of freedom in a friendly environment, but without being "
            "the center of attention. Parents were somewhat detached, focused on their own "
            "things rather than on you specifically."
        ),
        "mc": (
            "You choose a calling or profession that places you under the spotlight. People "
            "recognize you as a strong authority; they want to support you. You become a role "
            "model in your field. You give a lot of energy to society and it comes back to you. "
            "Being well-known in your sphere is important — you are among the best performers."
        ),
    },

    ("4_10", "Pisces", "Virgo"): {
        "ic": (
            "A murky childhood — possibly separated parents, emotional neglect, violence, or "
            "simply a chaotic but loving home where someone drank, or parents who came home "
            "late as artists. The next day you had to manage on your own."
        ),
        "mc": (
            "Because of that chaos you choose an extremely structured profession — precise, "
            "orderly, with a strict schedule. You learn precision and careful attention to "
            "process. Roles of physical service to others: hairdresser, pharmacist, healer, "
            "herbalist — people who care for others in a hands-on, bodily way."
        ),
    },

    # ── 5th / 11th AXIS ─────────────────────────────────────────────────────
    # 5th house = joy, romance, children, creativity, what you fall in love with.
    # 11th house = chosen community, friends, hopes, relationship with the future.

    ("5_11", "Aries", "Libra"): {
        "fifth": (
            "An excellent placement — fire in a fire house. You enjoy being in the spotlight. "
            "Strong position for athletes, especially if Aries also appears in the 6th. "
            "Possible tension with children but an active and energizing bond with them. "
            "You fall in love with decisive, bold, athletic, courageous people."
        ),
        "eleventh": (
            "Your best friend is often your partner. Be careful not to cling too tightly — "
            "the 11th house needs freedom even within close bonds."
        ),
    },

    ("5_11", "Taurus", "Scorpio"): {
        "fifth": (
            "Exceptionally stable and warm relationships with your children. The sign of "
            "abundance may bring many children. Joy comes through peace, comfort, pleasure, "
            "and sensuality. You fall in love with calm, grounded, materially secure people "
            "who bring zero tension. Artistic gifts, likely connected to music or visual beauty."
        ),
        "eleventh": (
            "You rarely trust people easily — your circle of friends is small but fiercely loyal. "
            "Either someone is willing to jump into fire for you or they are not your friend."
        ),
    },

    ("5_11", "Leo", "Aquarius"): {
        "fifth": (
            "Outstanding placement — excellent artistic talents. You love spending time with "
            "your children and truly enjoy it. You can meet them on their own level without "
            "enforcing harsh authority. You fall in love with magnetic, talented, beautiful, "
            "charismatic, positive people."
        ),
        "eleventh": (
            "Aquarius is at home here — freedom and equality define friendship for you. "
            "It is important not to judge friends and to stay objective. Even if you disappear "
            "for a while it does not mean the friendship is over."
        ),
    },

    ("5_11", "Scorpio", "Taurus"): {
        "fifth": (
            "You fall in love devastatingly — passion is everything. You are drawn to magnetic, "
            "mysterious, sexually powerful people. Their power is deeply attractive to you. "
            "One child is typical; conception can be difficult when passion is not strong enough. "
            "You tend to be protective and even controlling with your children."
        ),
        "eleventh": (
            "Relaxed, calm friendships without confrontation. You need to meet regularly "
            "and build shared routine — closeness grows through consistency."
        ),
    },

    ("5_11", "Aquarius", "Leo"): {
        "fifth": (
            "You see your children as equals and friends — freedom and equality shape the bond. "
            "You fall in love with intellectual, future-oriented, friendly people who connect "
            "with you soul-to-soul rather than through traditional roles. Online connections "
            "are common for this placement."
        ),
        "eleventh": (
            "Your children can become your best friends. The people you fall in love with "
            "may later become friends. You enjoy laughing together and doing productive things."
        ),
    },

    # ── 6th / 12th AXIS ─────────────────────────────────────────────────────
    # 6th house = daily health, work style, routine, colleagues.
    # 12th house = sleep, subconscious, karma, spiritual life.

    ("6_12", "Aries", "Libra"): {
        "sixth": (
            "Mandatory physical exercise — a lot of it. You need spontaneity in your work "
            "process and cannot stand being micro-managed. Aries rules the head — stay "
            "grounded, present, and goal-focused without over-structuring. Watch your head and face for health."
        ),
        "twelfth": None,
    },

    ("6_12", "Taurus", "Scorpio"): {
        "sixth": (
            "Stable, calm routine. Do not work outside working hours. Work environment should "
            "feel welcoming, cozy, and pleasant. Health focus: the throat and neck — if you "
            "have throat problems, ask yourself whether you are expressing what needs to be said. "
            "Not naturally athletic but benefits from gentle movement."
        ),
        "twelfth": None,
    },

    ("6_12", "Gemini", "Sagittarius"): {
        "sixth": (
            "Walking is essential — and breathing exercises. Rules the hands and lungs; "
            "smoking is strongly contraindicated. No fixed routine — full creative chaos, "
            "and that is fine. Multitasking and seeing many people is the natural work style. "
            "Do not overload the nervous system in the evenings."
        ),
        "twelfth": None,
    },

    ("6_12", "Leo", "Aquarius"): {
        "sixth": (
            "Athletics — especially track and field. Rules the solar plexus and heart. "
            "No externally imposed routine; you set your own schedule and judge it yourself. "
            "The work environment must be positive and fun, allowing you to express yourself "
            "and shine with your artistic abilities."
        ),
        "twelfth": None,
    },

    ("6_12", "Capricorn", "Cancer"): {
        "sixth": (
            "Structure is essential — clear routine, well-defined responsibilities, no lateness. "
            "A hierarchical, pyramid structure works best. Reputation matters greatly. "
            "Mountain sports suit this placement. Health: knees, spine, and skin — watch sugar "
            "intake as it triggers inflammatory responses. Avoid taking on too much: back tension follows."
        ),
        "twelfth": None,
    },
}


# ---------------------------------------------------------------------------
# EXTENDED SIGN DESCRIPTIONS from book
# Adds depth beyond standard keyword lists, especially for nuanced signs.
# ---------------------------------------------------------------------------

BOOK_SIGN_EXTENDED = {
    "Aquarius": {
        "core_book": (
            "The sign of vast information. Ruler: Uranus — the planet of genius. "
            "Aquarians are often genuinely brilliant. Uranus is the castrated God, the first "
            "deity before bodies existed, and therefore has no gender — which gives Aquarius "
            "its androgynous quality. Aquarius must be strange in some way, and precisely "
            "because of that strangeness they are tolerant of others."
        ),
        "society": (
            "Aquarius is the sign of society. Every system that speaks of equality — socialism, "
            "communism — was born in the Aquarian era. The meaning of Aquarius is equality, "
            "brotherhood, freedom. For the past 100 years we have been in the Age of Aquarius, "
            "which is immediately visible in the internet and social networks — the very essence "
            "of Aquarius — which unite us."
        ),
        "shadow": (
            "Aquarians often simply disappear from people's lives. They have no real sense of time. "
            "They are the aliens and the strange ones. But Aquarius says: everyone is strange "
            "and special, and everyone must contribute in their own way to society or the collective."
        ),
        "uranus_note": (
            "Uranus catches things from every direction but especially sideways. "
            "It is the higher octave of Mercury: vast information arriving from other worlds. "
            "Intuition that comes through thought. Uranus is the coldest planet and Aquarius "
            "the coldest sign — because it must remain objective."
        ),
    },

    "Pisces": {
        "core_book": (
            "The last and most complex sign, which unifies all twelve signs within itself. "
            "Pisces absorb information from everywhere and transform it into matter. "
            "The glyph shows two arcs — the visible and invisible worlds — one fish always "
            "somewhere in the beyond."
        ),
        "spiritual": (
            "Here it is crucial to dissolve the ego and release everything in life without "
            "clinging, because clinging would mean having no faith in the divine plan. "
            "Pisces connects with people in vulnerable positions, with charity, with isolation "
            "from the world, and with art."
        ),
        "shadow": (
            "Venus is exalted in Pisces — when the world is not perfect they are crushed, "
            "wanting to escape, and this is precisely where addictions are born. "
            "The most karmic sign, connected to reincarnation. Neptune is the higher octave of Venus. "
            "Neptune is furious at humans for violating natural laws — and Pisces feels the same "
            "rage at the world when they witness cruelty; they want to protect the weak."
        ),
        "empathy": (
            "Pisces have extraordinarily strong empathy, which can become self-destructive. "
            "Neptune rules the hormones of the human body — Pisces can fall very deeply in love "
            "on a hormonal level."
        ),
    },
}


# ---------------------------------------------------------------------------
# PLANETARY DIGNITIES — how each planet feels in each sign
# From the book's chapter on planetary strength.
# Values: "ruler" | "exaltation" | "detriment" | "fall" | None
# ---------------------------------------------------------------------------

PLANETARY_DIGNITIES = {
    "Sun":     {"Leo": "ruler", "Aries": "exaltation", "Aquarius": "detriment", "Libra": "fall"},
    "Moon":    {"Cancer": "ruler", "Taurus": "exaltation", "Capricorn": "detriment", "Scorpio": "fall"},
    "Mercury": {"Gemini": "ruler", "Virgo": "ruler", "Sagittarius": "detriment", "Pisces": "detriment"},
    "Venus":   {"Taurus": "ruler", "Libra": "ruler", "Pisces": "exaltation", "Scorpio": "detriment", "Aries": "detriment", "Virgo": "fall"},
    "Mars":    {"Aries": "ruler", "Scorpio": "ruler", "Capricorn": "exaltation", "Libra": "detriment", "Taurus": "detriment", "Cancer": "fall"},
    "Jupiter": {"Sagittarius": "ruler", "Cancer": "exaltation", "Gemini": "detriment", "Capricorn": "fall"},
    "Saturn":  {"Capricorn": "ruler", "Aquarius": "ruler", "Libra": "exaltation", "Cancer": "detriment", "Leo": "detriment", "Aries": "fall"},
    "Uranus":  {"Aquarius": "ruler", "Scorpio": "exaltation", "Leo": "detriment", "Taurus": "fall"},
    "Neptune": {"Pisces": "ruler", "Virgo": "detriment"},
    "Pluto":   {"Scorpio": "ruler", "Aquarius": "fall"},
}

DIGNITY_INTERPRETATIONS = {
    "ruler": (
        "This planet is in its home sign and expresses itself fully and authentically. "
        "Its energy flows without obstruction — this is one of the strongest possible placements."
    ),
    "exaltation": (
        "This planet is in a sign where its energy is intensified and elevated to its most "
        "positive and powerful expression. A very strong placement — though the intensity can "
        "occasionally tip toward excess."
    ),
    "detriment": (
        "This planet is in the opposite sign from its home and does not feel comfortable here. "
        "Its natural expression is challenged — there is friction between the planet's needs "
        "and the sign's style. Growth comes from consciously working with this tension."
    ),
    "fall": (
        "This is the most challenging dignity — the planet's energy is at its most difficult "
        "and suppressed expression. This does not mean failure, but it does mean the themes "
        "of this planet require extra awareness, patience, and inner work."
    ),
}


def get_dignity(planet: str, sign: str) -> str | None:
    """Returns the dignity status of a planet in a sign, or None if neutral."""
    return PLANETARY_DIGNITIES.get(planet, {}).get(sign)


def get_dignity_interpretation(planet: str, sign: str) -> str | None:
    """Returns a full dignity interpretation string if a dignity exists, else None."""
    dignity = get_dignity(planet, sign)
    if dignity:
        base = DIGNITY_INTERPRETATIONS[dignity]
        return f"{planet} in {sign} is in {dignity}. {base}"
    return None


# ---------------------------------------------------------------------------
# ELEMENTS — philosophy from book
# ---------------------------------------------------------------------------

BOOK_ELEMENTS = {
    "Fire": {
        "signs": ["Aries", "Leo", "Sagittarius"],
        "tarot": "Wands",
        "book_description": (
            "Aries carries the first spark in the universe — raw, instinctual fire. "
            "Leo holds the full solar fire — complete, radiant, self-sufficient. "
            "Sagittarius carries Jupiterian fire — the kind that constantly expands by "
            "traveling, seeing the whole world, removing all conservatism, and wanting to "
            "experience how everything operates."
        ),
        "collective": (
            "Fire signs are role models in society — leaders whose gaze is always on them. "
            "We admire them, want to resemble them. Passionate, enthusiastic, athletic, "
            "they know where they are going, are spontaneous, adventurous, and full of life. "
            "Fire signs learn and accumulate through lived experience, not theory. "
            "They do not like to wait and act quickly."
        ),
    },
    "Earth": {
        "signs": ["Taurus", "Virgo", "Capricorn"],
        "tarot": "Pentacles",
        "book_description": (
            "Taurus (Venus) represents the fertile soil of spring — wanting to sculpt some "
            "form in nature; the financial dimension. "
            "Virgo (Mercury) takes what Taurus shaped and perfects it — studies all matter "
            "and applies it; our level of specialization. "
            "Capricorn (Saturn) is the culmination of perfection, wisdom, and the skillful "
            "use of resources — our vocation."
        ),
        "collective": (
            "Practical, stable, materially oriented, striving for abundance and perfection. "
            "They value stability deeply. Hardworking — the three signs most associated with "
            "professional processes. Very critical."
        ),
    },
    "Air": {
        "signs": ["Gemini", "Libra", "Aquarius"],
        "tarot": "Swords",
        "book_description": (
            "Gemini (Mercury) is the most chaotic air — everywhere at once, wanting to learn "
            "as much as possible and pass it on; curiosity and sociability for their own sake. "
            "Libra (Venus) is not interested in basic communication in all directions — it "
            "concentrates communication with one specific person; in dialogue with you, truth "
            "about me will emerge; you become my mirror. "
            "Aquarius (Uranus) is the most abstract, the vastest air — the sky, the atmosphere; "
            "very abstract people who want to talk about the most philosophical themes."
        ),
        "shadow": (
            "Air is very dynamic. Unstable like fire (except Leo/Sun). The most ephemeral element. "
            "Very inconsistent. Does not hold to its word as reliably as earth. "
            "When we over-intellectualize our emotions and do not allow direct emotional contact "
            "— sitting in the world of logic without empathy — we reach a point of genuine, "
            "deep wounding. This is why the swords in tarot carry such heavy themes: grief, "
            "betrayal, pain."
        ),
    },
    "Water": {
        "signs": ["Cancer", "Scorpio", "Pisces"],
        "tarot": "Cups",
        "book_description": (
            "Cancer (Moon) — strong protectors of family, oriented toward home and comfort; "
            "deeply connected to the physical body because water rules water in the whole body. "
            "Scorpio (Pluto) — powerful destructive energy that is also creative; sexual energy; "
            "very strong intuition that reaches directly into the other person and pulls out "
            "all their fears and wounds — wanting to heal through transformation. "
            "Pisces (Neptune) — all beings on this planet are connected."
        ),
        "collective": (
            "Intuition, sensitivity, empathy. Emotionally nurturing. They create warmth, comfort, "
            "and a sense of belonging with great ease. Water brings out authentic emotional "
            "expression — what is genuinely felt inside."
        ),
    },
}


# ---------------------------------------------------------------------------
# MODALITIES — philosophy from book
# ---------------------------------------------------------------------------

BOOK_MODALITIES = {
    "Cardinal": {
        "signs": ["Aries", "Cancer", "Libra", "Capricorn"],
        "book_description": (
            "Cardinal signs open each new season — something very significant begins with them. "
            "They divide the year into four parts. They make a breakthrough, start something new. "
            "They are leaders who initiate very powerful processes — but their energy is "
            "inconsistent at the start of those processes. They get bored quickly. "
            "These are people who constantly start new things and rarely finish them. "
            "Often writers who produce short works. Long-term projects are not natural for them. "
            "They start and create something, then leave the rest for others — for the fixed signs."
        ),
    },
    "Fixed": {
        "signs": ["Taurus", "Leo", "Scorpio", "Aquarius"],
        "book_description": (
            "Fixed signs act more calmly — someone else has already started, and they continue "
            "and develop it. They dislike leaving their comfort zone. They dislike change. "
            "Exception: Scorpio is connected to change — it is fixed in change, constantly "
            "wanting to transform. Fixed signs often think something significant is changing "
            "when in reality it is not, because they are afraid of real change. Routine matters "
            "greatly to them."
        ),
    },
    "Mutable": {
        "signs": ["Gemini", "Virgo", "Sagittarius", "Pisces"],
        "book_description": (
            "Gemini–Sagittarius: the axis of movement, change, travel, and learning. "
            "Virgo–Pisces: the axis of daily life and rest, fantasy and perfection. "
            "Mutable signs are connected to perfection and refinement. They presuppose "
            "flexibility and adaptability. They can adjust to different circumstances and "
            "tense moments with ease. Very good experts and analysts. "
            "People who can easily put an end to things and walk away. They close seasons."
        ),
    },
}