"""Comparing places to live: every city calculated, each area judged apart.

What existed already was better than it looked. `rank_places_to_live` uses the
right technique — the birth chart seen from somewhere else, same planets in
the same degrees, only the houses and the angles moving — and it calculates
every candidate before ranking any of them. `combine_area_scores` normalises
each area against the best city in that area, so equal weighting is genuinely
equal rather than whichever table is most generous.

What it never got was the question. "Where would I have the best life for
career, love and happiness?" matched none of the trigger phrases, so none of
it ran and the answer came from the ordinary chat path with no city
calculated at all.

This module is the part that was missing around it: hearing the question,
carrying the comparison across a thread, adding a city to one already made,
and saying what changed and why.

------------------------------------------------------------------------------
Whose astrology is in here
------------------------------------------------------------------------------
Of the seven scoring tables in `relocation_scoring`, only MONEY was written by
the astrologer — `BY_AN_ASTROLOGER` says so and the reading passes it through.
The rest were written by analogy, and are on her list along with the
astrocartography distance bands and the happiness blend below.
"""
from __future__ import annotations

import re

from app.astrocartography_service import describe_bands, lines_for_city
from app.relocation_scoring import BY_AN_ASTROLOGER

# The three areas this question asks about, in her words, mapped onto the
# tables that exist. "Happiness" has no table of its own; MINE, on her list.
AREAS = {
    "career": {"tables": ("career",), "plain": "career"},
    "love": {"tables": ("love",), "plain": "love"},
    "day to day happiness": {"tables": ("social life", "home and family"),
                             "plain": "day-to-day happiness"},
}

ASKS_TO_COMPARE = re.compile(
    r"\bbest (?:life|place|city|country|cities|countries)\b"
    r"|\bwhere (?:would|should|could|do|can) i\b"
    r"|\bwhere (?:am i|do i) (?:meant|belong|thrive)\b"
    r"|\b(?:relocat|move to|moving to|emigrat)\w*"
    r"|\bwhich (?:city|cities|country|countries|place)\b"
    r"|\bbest for (?:my )?(?:career|love|happiness)\b"
    r"|\blive (?:abroad|overseas|somewhere else)\b", re.I)
# A follow-up that adds places to a comparison already on screen.
ADDS_CITIES = re.compile(
    r"\bwhat about\b|\bhow about\b|\badd\b|\band\b.{0,20}\bcompare\b"
    r"|\bwhat if i (?:moved|lived|went) to\b|\bcompared? (?:to|with)\b", re.I)

_AREA_WORDS = {
    "career": ("career", "work", "job", "professional", "money", "earn", "ambition"),
    "love": ("love", "relationship", "partner", "dating", "romance", "meet someone",
             "find someone", "marriage"),
    "day to day happiness": ("happy", "happiness", "happier", "day to day",
                             "day-to-day", "quality of life", "content",
                             "peace", "friends", "social", "lifestyle", "home"),
}
# "career first, then love" — the order is the weighting.
_ORDERED = re.compile(
    r"\b(?:first|most|mostly|mainly|above all|priority|matters most|care about)\b", re.I)


def asks_to_compare_places(question: str) -> bool:
    return bool(ASKS_TO_COMPARE.search(question or ""))


def areas_asked_about(question: str) -> list[str]:
    """Which of the three the question actually names, in the order named."""
    lowered = (question or "").lower()
    found = []
    for area, words in _AREA_WORDS.items():
        position = min((lowered.find(w) for w in words if w in lowered), default=-1)
        if position >= 0:
            found.append((position, area))
    return [area for _, area in sorted(found)] or []


def stated_priorities(question: str) -> dict | None:
    """The weighting the person gave, if they gave one.

    Order counts when they order it: "career first, then love" weights career
    above love. Naming several without ordering them weights them equally,
    because "career, love and happiness" is a list of what to cover, not a
    ranking of it.
    """
    areas = areas_asked_about(question)
    if not areas:
        return None
    if _ORDERED.search(question or "") and len(areas) > 1:
        # Descending weights in the order they were named.
        steps = {area: round(1.0 + (len(areas) - index - 1) * 0.5, 2)
                 for index, area in enumerate(areas)}
        return {"weights": steps, "came_from": "what you told me, in the order you said it"}
    if len(areas) == 1:
        return {"weights": {areas[0]: 1.0}, "came_from": "what you asked about"}
    return {"weights": {area: 1.0 for area in areas},
            "came_from": "what you asked about, weighted equally"}


def priorities_from_memory(memories) -> dict | None:
    """A priority they mentioned in an earlier conversation.

    Her rule: do not ask from scratch when they have already said it. Answer
    weighted by it and confirm in one line, so they can correct it.
    """
    for memory in memories or []:
        text = (memory.get("text") if isinstance(memory, dict) else str(memory)) or ""
        lowered = text.lower()
        for area, words in _AREA_WORDS.items():
            if any(word in lowered for word in words):
                return {
                    "weights": {area: 1.5, **{other: 1.0 for other in AREAS if other != area}},
                    "came_from": "what you said last time",
                    "confirm": (f"Last time you talked about {text.rstrip('.')}, so I "
                                f"weighted {AREAS[area]['plain']} most. Tell me if "
                                "that's changed."),
                }
    return None


EQUAL = {"weights": {area: 1.0 for area in AREAS},
         "came_from": "equal, because you haven't said otherwise"}


def decide_weighting(question: str, memories=None, carried: dict | None = None) -> dict:
    """Her three cases, in order: what they said, then what they said before,
    then equal — and only the last one asks a question.

    A weighting carried from earlier in the thread wins over the default but
    loses to anything they say now, so a follow-up keeps the weighting unless
    they change it.
    """
    stated = stated_priorities(question)
    if stated:
        return {**stated, "ask": None}
    if carried:
        return {**carried, "ask": None}
    remembered = priorities_from_memory(memories)
    if remembered:
        return {**remembered, "ask": None}
    return {**EQUAL, "ask": (
        "what matters most in a move — career, love, day-to-day happiness, or "
        "all of it equally")}


# ── The comparison ────────────────────────────────────────────────────────

def compare_places(natal: dict, *, places: list[dict], weighting: dict,
                   region: str = "world") -> dict:
    """Score every place given, on every area, and rank them.

    Nothing is ranked that was not calculated: the list that comes out is the
    list that went in, minus anything that failed, and the failures are named.
    """
    from datetime import datetime
    import swisseph as swe
    from app.relocation_scoring import combine_area_scores, score_every_purpose
    from app.relocation_service import chart_for

    born = datetime.fromisoformat(natal["utc_birth_time"])
    julian_day = swe.julday(born.year, born.month, born.day,
                            born.hour + born.minute / 60 + born.second / 3600)
    planets = natal["planet_positions"]

    scored, failed = [], []
    for place in places:
        try:
            chart = chart_for(born, place["latitude"], place["longitude"], planets=planets)
            chart["natal_planets"] = planets
            every = score_every_purpose(chart)
            by_area = {}
            for area, shape in AREAS.items():
                by_area[area] = sum(every[t]["score"] for t in shape["tables"]) / len(shape["tables"])
            scored.append({
                "place": place["label"],
                "by_area": by_area,
                "lines": lines_for_city(planets, julian_day, place["latitude"],
                                        place["longitude"], chart.get("angles")),
            })
        except Exception as exc:  # noqa: BLE001
            failed.append({"place": place.get("label", "?"), "why": type(exc).__name__})

    if not scored:
        return {"status": "failed", "compared": [], "failed": failed}

    combine_area_scores(scored)
    # Weighting is applied AFTER normalising, so a heavier area counts more
    # without the most generous table deciding the ranking.
    weights = weighting["weights"]
    peak = {area: max(abs(city["by_area"][area]) for city in scored) or 1.0
            for area in AREAS}
    for city in scored:
        shares = {area: city["by_area"][area] / peak[area] for area in AREAS}
        total = sum(weights.get(area, 0) for area in AREAS) or 1.0
        city["overall"] = round(
            sum(shares[area] * weights.get(area, 0) for area in AREAS) / total * 10, 2)
        city["area_rank"] = shares
    scored.sort(key=lambda c: -c["overall"])

    return {
        "status": "ok",
        "ranked": scored,
        # E: exactly what ran, so nothing can claim more than it.
        "compared": [c["place"] for c in scored],
        "how_many_calculated": len(scored),
        "region_searched": region,
        "failed": failed,
        "weighting": weighting,
        "line_bands": describe_bands(),
        "tables_by_an_astrologer": sorted(BY_AN_ASTROLOGER),
    }


# ── C: cities named in the question ───────────────────────────────────────

# Capitalised runs that look like a place. Deliberately loose — the geocoder
# decides what is real, and anything it cannot resolve is reported rather
# than dropped, so "what about Wakanda?" gets an answer instead of silence.
_CANDIDATE = re.compile(
    r"\b([A-Z][a-z]+(?:[ -][A-Z][a-z]+){0,2}(?:,\s*[A-Z][a-zA-Z ]+)?)\b")
_NOT_A_PLACE = {
    "What", "Add", "Where", "How", "And", "But", "Tell", "Should", "Would",
    "Could", "Zoli", "Thanks", "Okay", "Yes", "No", "My", "The", "This",
    "That", "For", "About", "Also", "Compare", "Career", "Love", "Happiness",
    "First", "Then", "Best", "Life", "City", "Cities", "Country",
}


def cities_named_in(question: str, resolve=None) -> tuple[list[dict], list[str]]:
    """Places the person named, resolved to coordinates.

    Both ranking functions have always accepted a list of places; nothing ever
    passed one, so "what about New York and Miami?" could not work at all.
    """
    if resolve is None:
        from app.location_service import get_location_data as resolve
    found, unresolved = [], []
    seen = set()
    for match in _CANDIDATE.finditer(question or ""):
        name = match.group(1).strip()
        # Strip leading stop-words rather than discarding the run that carries
        # them. "Add Dubai" matches as one capitalised phrase, and rejecting it
        # on the word "Add" threw the city away with it.
        words = name.split()
        while words and words[0].split(",")[0] in _NOT_A_PLACE:
            words = words[1:]
        name = " ".join(words).strip(" ,")
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        try:
            place = resolve(name)
        except Exception:  # noqa: BLE001
            place = None
        if place and place.get("latitude") is not None:
            found.append({
                "label": place.get("display_name") or name,
                "latitude": place["latitude"], "longitude": place["longitude"],
                "timezone": place.get("timezone") or "UTC",
            })
        elif len(name) > 3:
            unresolved.append(name)
    return found, unresolved


# ── D: the comparison, carried across the thread ──────────────────────────

def carried_comparison(history) -> dict | None:
    """What was already compared in this thread, and how it was weighted.

    Without this, "add Dubai" starts a new comparison with one city in it and
    silently drops everything that came before — which is also how a ranking
    gets rewritten without anyone saying so.
    """
    for turn in reversed(history or []):
        if turn.get("role") != "assistant":
            continue
        marker = turn.get("relocation_state")
        if marker:
            return marker
    return None


def what_changed(before: list[str], after: list[dict], weighting: dict) -> dict | None:
    """Why the order moved, in terms of an area rather than a number.

    Her rule: never quietly rewrite a ranking. If the leader changed, the
    answer has to say which area did it.
    """
    if not before or not after:
        return None
    was, now = before[0], after[0]["place"]
    if was == now:
        return None
    winner = after[0]
    loser = next((c for c in after if c["place"] == was), None)
    if not loser:
        return {"new_leader": now, "previous_leader": was,
                "because": "the previous leader is no longer in the comparison"}
    gaps = {area: winner["area_rank"][area] - loser["area_rank"][area] for area in AREAS}
    decisive = max(gaps, key=gaps.get)
    return {
        "new_leader": now, "previous_leader": was,
        "the_area_that_moved_it": AREAS[decisive]["plain"],
        "because": (f"{now} scores higher than {was} on "
                    f"{AREAS[decisive]['plain']}, and that is the area that "
                    "decided it under the current weighting"),
    }


# ── E, F, G: what actually reaches the prompt ─────────────────────────────

def for_the_answer(result: dict, *, changed: dict | None = None,
                   top: int = 4, technical: bool = False) -> dict | None:
    """Plain language, exact claims, and the two sources kept apart."""
    if not result or result.get("status") != "ok":
        return None
    weighting = result["weighting"]
    ranked = result["ranked"][:top]

    def city(entry):
        lines = [line for line in entry["lines"] if line["strength"] >= 0.6]
        out = {
            "city": entry["place"],
            "career": _verdict(entry, "career"),
            "love": _verdict(entry, "love"),
            "day_to_day": _verdict(entry, "day to day happiness"),
            "overall_fit": _band(entry["overall"], result["ranked"]),
            # F: this half comes from the chart and may be stated as such.
            "what_your_chart_says_about_living_there": [
                line["in_plain_words"] for line in lines[:3]],
        }
        if not out["what_your_chart_says_about_living_there"]:
            out["what_your_chart_says_about_living_there"] = [
                "nothing stands out sharply here either way"]
        return out

    compact = {
        "note": ("Every city listed was calculated before it was ranked. Build "
                 "the answer on this and do not re-rank from the raw chart."),
        # E: the exact claim that may be made, and no larger one.
        "cities_actually_compared": result["compared"],
        "how_many_were_calculated": result["how_many_calculated"],
        "you_may_say": (
            f"that you compared {result['how_many_calculated']} places"
            + (f" across {result['region_searched']}"
               if result["region_searched"] != "world" else " worldwide")),
        "you_may_not_say": (
            "anything about places not in that list. If they ask about one, "
            "say it has not been calculated yet and offer to add it."),
        "weighting": {AREAS[a]["plain"]: w for a, w in weighting["weights"].items()},
        "weighting_came_from": weighting["came_from"],
        "ranking": [city(entry) for entry in ranked],
        # F, stated as a rule rather than hoped for.
        "keep_the_two_sources_apart": (
            "What the chart says about living there is above and may be given "
            "as a chart reading. Anything about the city itself — cost, "
            "industry, weather, visas — is general knowledge and must be said "
            "as such: 'and the city itself is…'. Never present a fact about a "
            "place as something the chart told you."),
        # Hers: a move is a big decision and this is one input in it.
        "this_is_one_input": (
            "Moving country is decided by work, visas, money and the people "
            "you would be near. This is one input beside those, never the "
            "reason to go. Say so once, lightly, and do not hedge beyond it."),
        "about_love": (
            "Say what relationship life looks like there and be direct when "
            "the calculation supports it. Never promise a person: no 'you "
            "will meet someone', no 'you'll find your person there'."),
    }
    if weighting.get("ask"):
        leader = result["ranked"][0]["place"]
        compact["ask_one_short_question"] = {
            "ask": weighting["ask"],
            "but_answer_first": (
                f"If everything counts equally, {leader} leads for you. Tell me "
                "what matters most and I'll sharpen it."),
        }
    if weighting.get("confirm"):
        compact["confirm_the_weighting_in_one_line"] = weighting["confirm"]
    if changed:
        compact["the_ranking_changed"] = changed
    if result.get("failed"):
        compact["could_not_calculate"] = [f["place"] for f in result["failed"]]
    if technical:
        compact["the_chart_behind_it"] = {
            "line_distance_policy": result["line_bands"],
            "tables_written_by_an_astrologer": result["tables_by_an_astrologer"],
            "per_city": [
                {"city": e["place"],
                 "lines": [f"{l['planet']} on the {l['angle']} line, {l['km']}km "
                           f"({l['how_close']})" for l in e["lines"][:4]]}
                for e in ranked],
        }
    return compact


def _verdict(entry: dict, area: str) -> str:
    """One area for one city, in words. No numbers reach a reader."""
    share = entry["area_rank"][area]
    if share >= 0.85:
        return "one of the strongest places for this in the comparison"
    if share >= 0.6:
        return "strong here"
    if share >= 0.35:
        return "workable, without standing out"
    if share >= 0.1:
        return "not what this place is for"
    return "weak here"


def _band(overall: float, everything: list[dict]) -> str:
    """Where this city sits among the ones compared.

    By position, not by ratio. The first version divided each score by the
    leader's, and since the top cities in a large comparison sit within a few
    percent of each other it called all four of them the best one.
    """
    order = [c["overall"] for c in everything]
    place = order.index(overall) if overall in order else len(order)
    if place == 0:
        return "the best overall fit of those compared"
    spread = (order[0] - overall) / (abs(order[0]) or 1.0)
    if spread <= 0.05:
        return "effectively level with the leader"
    if place < max(3, len(order) * 0.1):
        return "just behind the leader"
    if place < len(order) * 0.35:
        return "a reasonable fit, not the strongest"
    return "not a strong fit for you overall"


# ── The entry point: one function that handles all three shapes of ask ─────

DEFAULT_SHORTLIST = 12


def build_relocation_reading(natal: dict, question: str, *, history=None,
                             memories=None, carried: dict | None = None,
                             region: str | None = None,
                             technical: bool = False) -> dict | None:
    """A fresh comparison, or a city added to one already made.

    Three shapes reach here and only the first starts from nothing:

      "Where would I have the best life for career, love and happiness?"
      "What about New York and Miami?"     — adds to the comparison on screen
      "Add Dubai."                          — same, and would otherwise have
                                              started a new comparison of one

    Her rule 5: a new city is calculated first, then compared against the
    current leader, keeping the earlier cities and the weighting.
    """
    from app.european_cities import as_places

    if not natal.get("birth_time_known") or len(natal.get("houses") or []) != 12:
        return {
            "status": "needs_birth_time",
            "say": ("Relocation moves the houses and the angles, and without a "
                    "birth time there are none to move. Add the time and I can "
                    "rank places properly."),
        }

    named, unresolved = cities_named_in(question)
    adding = bool(ADDS_CITIES.search(question or "")) or bool(named and carried)
    fresh = asks_to_compare_places(question)
    if not (fresh or (adding and carried)):
        return None

    weighting = decide_weighting(question, memories=memories,
                                 carried=(carried or {}).get("weighting"))

    if carried and (adding or not fresh):
        # Keep every city already compared, add the new ones, keep the
        # weighting. The coordinates travel WITH the state: the first version
        # re-geocoded all forty on every follow-up, was rate-limited by the
        # geocoder, and quietly dropped whichever cities came back empty —
        # so "add Dubai" silently shrank the comparison it was adding to.
        previous = [dict(place) for place in carried.get("places", [])]
        already = {p["label"].lower() for p in previous}
        places = previous + [p for p in named if p["label"].lower() not in already]
        searched = carried.get("region_searched", "the same places as before")
    elif named:
        places, searched = named, "the places you named"
    else:
        region = region or "world"
        everywhere = as_places(region)
        # A shortlist for a fresh open question: every one of these is
        # calculated, and the answer says how many.
        places, searched = everywhere, region

    result = compare_places(natal, places=places, weighting=weighting,
                            region=searched)
    if result.get("status") != "ok":
        return {"status": "failed", "say": "I couldn't calculate those places."}

    changed = what_changed(carried.get("compared") if carried else None,
                           result["ranked"], weighting)
    compact = for_the_answer(result, changed=changed, technical=technical,
                             top=DEFAULT_SHORTLIST if named else 4)
    if unresolved:
        compact["could_not_find"] = unresolved
    # What the next turn in this thread needs in order to add to this.
    # A city the person named survives whatever it ranks. The first version
    # kept the top forty, so "what about Miami?" put Miami in the comparison
    # and the next turn quietly dropped it again for placing 61st — which is
    # both the wrong answer and the kind of silent rewrite her rules forbid.
    asked_for = {p["label"] for p in named} | set(
        (carried or {}).get("asked_for", []))
    keep = [p for p in places if p["label"] in asked_for]
    keep += [p for p in places
             if p["label"] in set(result["compared"][:40])
             and p["label"] not in asked_for]
    compact["_state"] = {
        "compared": [p["label"] for p in keep],
        # Everything needed to re-run the comparison without touching a
        # network: no geocoder call, nothing to rate-limit, nothing to drop.
        "places": keep[:60],
        "asked_for": sorted(asked_for),
        "weighting": {k: v for k, v in weighting.items() if k != "ask"},
        "region_searched": result["region_searched"],
    }
    return compact


