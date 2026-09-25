"""How a chart earns, from the co-founder's earning-route framework.

NOT WIRED INTO ANY ANSWER. Built, tested and calibrated; dark until she has
reviewed the blind table in `training/area3/`. Same arrangement as the
friendship engine, for the same reason: the mechanism is mine, the astrology
is hers.

This replaces an earlier engine of mine that scored five invented spectrums.
Everything below — the six routes, the weight table, the five dimensions and
the six rules — comes from her document. Where I had to make a call she did
not cover, the call is marked MINE in a comment and listed in the provenance
the engine returns, so nothing of mine can be mistaken for hers.

------------------------------------------------------------------------------
Why it is a separate, auditable step
------------------------------------------------------------------------------
Her instruction: before any career or money answer is drafted, produce a
private ranking with its evidence, its counterevidence and its confidence.
The score never reaches the reader. It exists so that the same chart produces
the same reading twice, and so that a reading can be checked against the chart
it claims to come from — a consistency device, not a probability.

This is also the only way to satisfy "judge the chart first". A prompt cannot
do it: the person's own facts arrive in the same payload as the chart, and an
instruction that competes with the data behind it loses. So the ranking is
computed here, with nothing about their life in scope, and their life is
applied afterwards — to turn a route into practical options, never to become
evidence for it.
"""
from __future__ import annotations

import bisect
import json
import pathlib

from app.angle_aspects_service import conjunct_cusp, get_angle_aspects
from app.chart_analysis_service import get_house_rulers
from app.natal_career_data import _aspects_between
from app.orb_policy import TO_CUSP, exactness, within_orb

# ── Her six routes ─────────────────────────────────────────────────────────
#
# `houses` are the houses her "strongest chart evidence" column names for that
# route. `natural` are the planets that signify it by symbolism alone, which
# her weight table caps at a single point however many of them turn up.
ROUTES: dict[str, dict] = {
    "employment": {
        "label": "Employment and advancement within an organisation",
        "means": ("Paid for a role, responsibilities and advancement inside "
                  "an organisation"),
        "plain": "a role inside an organisation",
        "houses": (6, 10),
        "natural": {"Saturn"},
    },
    "independent_expertise": {
        "label": "Independent expertise, advice or personal services",
        "means": ("Paid for advice, judgment, specialist knowledge or a "
                  "personal service"),
        "plain": "specialist advice for clients",
        "houses": (1, 7, 9, 10),
        "natural": {"Mercury", "Jupiter"},
    },
    "business_products": {
        "label": "Products, intellectual property or a scalable business",
        "means": ("Earns through something sold repeatedly, distributed, "
                  "licensed or built into a business"),
        "plain": "building something that sells more than once",
        "houses": (3, 5, 7, 10, 11),
        "natural": {"Mercury", "Venus"},
    },
    "partnerships_deals": {
        "label": "Direct clients, partnerships and negotiated deals",
        "means": ("Money depends substantially on direct agreements with "
                  "other people"),
        "plain": "deals and agreements with particular people",
        "houses": (7,),
        "natural": {"Venus"},
    },
    "others_assets": {
        "label": "Professional work managing other people's resources",
        "means": ("Finance, tax, insurance, funding, investment management, "
                  "or administering shared resources"),
        "plain": "handling money that belongs to other people",
        "houses": (8, 10),
        "natural": {"Pluto", "Saturn"},
    },
    "owned_assets": {
        "label": "Income from assets or ownership",
        "means": "Earns from property, equity, royalties or owned assets",
        "plain": "owning things that pay you",
        "houses": (4, 5, 8, 11),
        "natural": {"Venus", "Jupiter"},
    },
}

# ── Her weight table ───────────────────────────────────────────────────────
POINTS = {
    "second_ruler_placement": 5,   # 2nd ruler's house placement or rulership
    "second_tenth_link": 5,        # 2nd ruler and 10th ruler, close connection
    "ruler_connects": 4,           # a relevant house ruler connects to 2nd/10th ruler
    "on_cusp": 3,                  # planet closely conjunct the 2nd cusp or MC
    "planet_in_house": 2,          # a planet in the relevant house
    "symbolism": 1,                # sign, element, modality, natural symbolism
}
# "1 maximum" — however many natural significators a route has.
SYMBOLISM_CAP = 1

# MINE, not hers: how close "a relevant, close connection" is. Her document
# says close without giving a number, and every orb in this codebase is
# explicit, so it had to become one. Four degrees is tight enough to mean
# something and loose enough to occur; the calibration run reports how often
# it fires.
CLOSE_LINK_ORB = 4.0

# Her weight table is applied exactly as written, with no ceiling of mine on
# top of it. A ceiling was tried and removed: the problem it was meant to
# solve turned out not to be tenancy at all. See RANKING below.
TENANCY_CAP = None

# Rule 2: what may serve as the required signal. At least one piece of
# evidence for a "strong" route must involve the 2nd house or its ruler, or a
# direct link between career and income.
QUALIFYING = {"second_ruler_placement", "second_tenth_link"}

DIFFICULT = {"detriment", "fall"}
EASY_DIGNITY = {"domicile", "exaltation"}
MALEFIC = {"Saturn", "Mars"}
ANGULAR, SUCCEDENT = {1, 4, 7, 10}, {2, 5, 8, 11}


def _ord(number: int) -> str:
    """1st, 2nd, 3rd — not "1th", which is what a bare f-string produces."""
    if number in (11, 12, 13):
        return f"{number}th"
    return f"{number}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th') }"


def _aspect_index(aspects: list[dict]) -> dict:
    """Every aspect, findable from either end."""
    index: dict[frozenset, dict] = {}
    for aspect in aspects:
        pair = frozenset((aspect["planet_1"], aspect["planet_2"]))
        if len(pair) == 2 and (pair not in index or aspect["orb"] < index[pair]["orb"]):
            index[pair] = aspect
    return index


def _condition(planet: str, chart_facts: dict) -> dict:
    """How well placed a planet is — rule 4's "condition before confidence".

    This changes how a route WORKS, never whether it exists. An afflicted
    ruler still describes the route; it describes it as harder to use.
    """
    dignity = chart_facts["dignity"].get(planet)
    house = chart_facts["house_of"].get(planet)
    afflicted = [
        other for other in MALEFIC
        if other != planet
        and (aspect := chart_facts["aspects"].get(frozenset((planet, other))))
        and aspect["aspect"] in ("square", "opposition")
    ]
    notes = []
    if dignity in EASY_DIGNITY:
        notes.append(f"{planet} is strong by sign")
    if dignity in DIFFICULT:
        notes.append(f"{planet} is awkwardly placed by sign ({dignity})")
    if house and house not in ANGULAR | SUCCEDENT:
        notes.append(f"{planet} is in a quiet part of the chart (the {_ord(house)})")
    for other in afflicted:
        notes.append(f"{planet} is under pressure from {other}")
    if chart_facts["retrograde"].get(planet):
        notes.append(f"{planet} is retrograde, so this tends to arrive by a second attempt")
    return {
        "planet": planet,
        "dignity": dignity,
        "house": house,
        "easy": dignity in EASY_DIGNITY and not afflicted,
        "complicated": bool(afflicted) or dignity in DIFFICULT,
        "notes": notes,
    }


def _facts(chart: dict) -> dict | None:
    planets = chart.get("planet_positions") or []
    houses = chart.get("houses") or []
    if not planets or len(houses) != 12:
        return None
    rulers = get_house_rulers(houses, planets)
    ruler_of = {r["house"]: r["ruler"] for r in rulers}
    rules_houses: dict[str, list[int]] = {}
    for record in rulers:
        rules_houses.setdefault(record["ruler"], []).append(record["house"])
    angle_aspects = get_angle_aspects(
        planets, ascendant=chart.get("ascendant"),
        midheaven=chart.get("midheaven"), houses=houses)
    return {
        "planets": planets,
        "houses": houses,
        "ruler_of": ruler_of,
        "rules_houses": rules_houses,
        "house_of": {p["planet"]: p.get("house") for p in planets},
        "dignity": {r["ruler"]: r.get("ruler_dignity") for r in rulers},
        "retrograde": {p["planet"]: p.get("retrograde") for p in planets},
        "aspects": _aspect_index(_aspects_between(planets)),
        "angle_aspects": angle_aspects,
        # Her rules document widens this from her PDF: "a close relevant
        # ASPECT to the MC or 2nd cusp", not only a conjunction to it. A
        # square to the career point is evidence about the career.
        "mc_aspect": {
            a["planet_1"]: {**a, "exactness": exactness(
                a["aspect"], a["orb"], a["planet_1"], "Midheaven")}
            for a in angle_aspects
            if a["planet_2"] == "Midheaven"
            and within_orb(a["aspect"], a["orb"], a["planet_1"], "Midheaven")},
        "on_second_cusp": {p["planet"]: p
                           for p in conjunct_cusp(planets, houses, 2, orb=TO_CUSP)},
        "in_house": _tenants(planets),
    }


def _tenants(planets: list) -> dict[int, list[str]]:
    tenants: dict[int, list[str]] = {}
    for planet in planets:
        if planet.get("house"):
            tenants.setdefault(planet["house"], []).append(planet["planet"])
    return tenants


def _connected(one: str, two: str, facts: dict) -> dict | None:
    """The aspect between two planets, if there is one."""
    return facts["aspects"].get(frozenset((one, two))) if one != two else None


def _evidence_for(route_key: str, facts: dict) -> list[dict]:
    """Every piece of evidence this chart offers for one route.

    Each item carries the fact it rests on, so rule 3 — never count the same
    aspect twice — is enforced by deduplicating on that key rather than by
    remembering to.
    """
    route = ROUTES[route_key]
    relevant = set(route["houses"])
    second, tenth = facts["ruler_of"][2], facts["ruler_of"][10]
    found: list[dict] = []

    def add(kind, why, fact, qualifies=None, weight=1.0):
        weight = max(0.0, min(1.0, weight))
        found.append({
            "points": POINTS[kind], "kind": kind, "why": why, "fact": fact,
            # Her section 4: closer aspects weigh more. A placement has no orb
            # and so weighs its full value.
            "weight": round(weight, 3),
            "counts_as": round(POINTS[kind] * weight, 2),
            "qualifies": QUALIFYING.__contains__(kind) if qualifies is None else qualifies,
        })

    # 5 — the 2nd ruler's own placement or rulership. Rule 1: money is traced
    # from here before anything else is looked at.
    if facts["house_of"].get(second) in relevant:
        add("second_ruler_placement",
            f"what rules your money house sits in the {_ord(facts['house_of'][second])}",
            f"place:{second}")
    for ruled in facts["rules_houses"].get(second, []):
        if ruled in relevant:
            add("second_ruler_placement",
                f"what rules your money house also rules the {_ord(ruled)}",
                f"rules:{second}:{ruled}")

    # 5 — a close connection between the money ruler and the career ruler,
    # counted for this route when the houses those two occupy or rule are
    # houses this route is about.
    link = _connected(second, tenth, facts)
    if link and link["orb"] <= CLOSE_LINK_ORB:
        touching = {facts["house_of"].get(second), facts["house_of"].get(tenth)}
        touching |= set(facts["rules_houses"].get(second, []))
        touching |= set(facts["rules_houses"].get(tenth, []))
        if touching & relevant:
            add("second_tenth_link",
                f"your money ruler and your career ruler are in close contact "
                f"({link['aspect']}, {link['orb']}°)",
                f"aspect:{'-'.join(sorted((second, tenth)))}",
                weight=link.get("exactness", 1.0))

    # 4 — a relevant house ruler in direct contact with the money or career
    # ruler. The 2nd–10th aspect itself is excluded: it was already counted.
    for house in sorted(relevant):
        house_ruler = facts["ruler_of"].get(house)
        if not house_ruler:
            continue
        for anchor, anchor_name in ((second, "money"), (tenth, "career")):
            if {house_ruler, anchor} == {second, tenth}:
                continue
            contact = _connected(house_ruler, anchor, facts)
            if contact and contact["orb"] <= CLOSE_LINK_ORB:
                add("ruler_connects",
                    f"what rules your {_ord(house)} is in contact with your "
                    f"{anchor_name} ruler ({contact['aspect']}, {contact['orb']}°)",
                    f"aspect:{'-'.join(sorted((house_ruler, anchor)))}",
                    qualifies=(anchor == second),
                    weight=contact.get("exactness", 1.0))

    # 3 — a planet closely conjunct the 2nd cusp or the Midheaven, where that
    # planet is relevant to this route.
    for planet in sorted(set(facts["on_second_cusp"]) | set(facts["mc_aspect"])):
        rules_relevant = set(facts["rules_houses"].get(planet, [])) & relevant
        if not (rules_relevant or planet in route["natural"]):
            continue
        if planet in facts["on_second_cusp"]:
            contact = facts["on_second_cusp"][planet]
            add("on_cusp", f"{planet} sits right on your money house cusp "
                           f"({contact['orb']}°)",
                f"cusp:{planet}:second", qualifies=True,
                weight=1.0 - (contact["orb"] / (TO_CUSP * 2)))
        else:
            contact = facts["mc_aspect"][planet]
            add("on_cusp", f"{planet} {contact['aspect']} your career point "
                           f"({contact['orb']}°)",
                f"cusp:{planet}:mc", qualifies=False,
                weight=contact["exactness"])

    # 2 — a planet standing in a relevant house. The weakest evidence in the
    # table, and the one her rules single out as unable to establish a route
    # on its own.
    for house in sorted(relevant):
        for planet in facts["in_house"].get(house, []):
            tied = _connected(planet, second, facts) or _connected(planet, tenth, facts)
            add("planet_in_house",
                f"{planet} is in your {_ord(house)}"
                + (", and in contact with your money or career ruler" if tied else ""),
                f"in:{planet}:{house}", qualifies=False)

    # 1 maximum — symbolism on its own.
    natural = sorted(route["natural"] & set(facts["house_of"]))
    if natural:
        add("symbolism",
            f"{' and '.join(natural)} naturally {'signify' if len(natural) > 1 else 'signifies'}"
            f" this kind of earning",
            f"symbol:{route_key}", qualifies=False)

    # Rule 3: one underlying fact is one piece of evidence, whichever
    # description it arrived under. Keep the highest-weighted reading of it.
    best: dict[str, dict] = {}
    for item in found:
        if item["fact"] not in best or item["counts_as"] > best[item["fact"]]["counts_as"]:
            best[item["fact"]] = item
    return sorted(best.values(), key=lambda i: -i["counts_as"])


def _counterevidence(route_key: str, facts: dict, evidence: list[dict]) -> list[str]:
    """What argues against the route, or complicates it.

    Rule 4: a complication is explained, never used to delete a route.
    """
    route = ROUTES[route_key]
    relevant = set(route["houses"])
    second, tenth = facts["ruler_of"][2], facts["ruler_of"][10]
    against: list[str] = []

    if not any(item["qualifies"] for item in evidence):
        against.append("nothing here ties it to the money house or links income "
                       "to career directly, so it cannot be called strong")
    if len(evidence) < 2:
        against.append("only one independent signal")
    weak_only = evidence and all(item["kind"] in ("planet_in_house", "symbolism")
                                 for item in evidence)
    if weak_only:
        against.append("the evidence is placement and symbolism only")
    if route_key in ("others_assets", "owned_assets"):
        eighth_or_eleventh = [i for i in evidence
                              if i["fact"].startswith("in:") and i["fact"].rsplit(":", 1)[-1]
                              in ("8", "11")]
        if eighth_or_eleventh and len(evidence) == len(eighth_or_eleventh):
            against.append("a planet in the 8th or 11th cannot establish a route "
                           "on its own")
    # The condition of the planets the route rests on.
    for planet in {second, tenth} | {facts["ruler_of"][h] for h in relevant
                                     if facts["ruler_of"].get(h)}:
        condition = _condition(planet, facts)
        if condition["complicated"]:
            against.extend(condition["notes"])
    # Where the money ruler actually points, when it points away.
    elsewhere = facts["house_of"].get(second)
    if elsewhere and elsewhere not in relevant:
        against.append(f"your money ruler sits in the {_ord(elsewhere)}, which is not "
                       "one of this route's houses")
    return list(dict.fromkeys(against))[:6]


def _score(evidence: list[dict]) -> float:
    """Sum her weights, each scaled by how exact its aspect is.

    Her section 4: closer aspects weigh more, and an 8° conjunction must not
    quietly count as a 1° one. A placement has no orb and keeps its full
    value. Her symbolism cap applies to the scaled value.
    """
    total = 0.0
    symbolism_spent = 0.0
    tenancy_spent = 0.0
    for item in sorted(evidence, key=lambda i: -i["counts_as"]):
        value = item["counts_as"]
        if item["kind"] == "symbolism":
            allowed = min(value, SYMBOLISM_CAP - symbolism_spent)
            symbolism_spent += max(0.0, allowed)
            total += max(0.0, allowed)
        elif item["kind"] == "planet_in_house" and TENANCY_CAP is not None:
            allowed = min(value, TENANCY_CAP - tenancy_spent)
            tenancy_spent += max(0.0, allowed)
            total += max(0.0, allowed)
        else:
            total += value
    return round(total, 2)


# ── Her five dimensions ────────────────────────────────────────────────────
#
# Each is a spectrum with two readings. The evidence is hers, including the
# qualifiers that matter most: visibility counts only when it is connected to
# the income or career rulers, and what-is-sold is read through the 2nd ruler.
DIMENSIONS = {
    "visibility": {
        "poles": ("a public name and reputation", "a specialist working behind the scenes"),
        "for": (1, 10), "against": (8, 12),
        "through_rulers": True,
    },
    "customer_structure": {
        "poles": ("a few substantial clients", "a broad customer base"),
        "for": (7,), "against": (3, 11),
        "through_rulers": False,
    },
    "what_is_sold": {
        "poles": ("expertise or time", "repeatable output, a product, or intellectual property"),
        "for": (6, 7, 9), "against": (3, 5, 11),
        "through_rulers": True,
    },
    "delivery": {
        "poles": ("work you deliver personally",
                  "growth through a team or a network"),
        "for": (1, 6), "against": (10, 11),
        "through_rulers": False,
    },
}


def _dimension_reading(spec: dict, facts: dict) -> dict:
    second, tenth = facts["ruler_of"][2], facts["ruler_of"][10]
    def weight(houses):
        total, why = 0, []
        for house in houses:
            house_ruler = facts["ruler_of"].get(house)
            # Her qualifier: it counts when it is connected to the income or
            # career rulers, not merely present.
            if house_ruler:
                for anchor in (second, tenth):
                    contact = _connected(house_ruler, anchor, facts)
                    if contact and contact["orb"] <= CLOSE_LINK_ORB:
                        total += 2
                        why.append(f"what rules your {_ord(house)} contacts your "
                                   f"{'money' if anchor == second else 'career'} ruler")
                        break
            if facts["house_of"].get(second) == house:
                total += 3
                why.append(f"your money ruler is in the {_ord(house)}")
            if not spec["through_rulers"]:
                for planet in facts["in_house"].get(house, []):
                    total += 1
                    why.append(f"{planet} is in your {_ord(house)}")
        return total, why
    one, why_one = weight(spec["for"])
    two, why_two = weight(spec["against"])
    # Per house, not in total. The same opportunity artefact the routes hit:
    # customer structure weighs one house against two, so counting totals said
    # "a broad customer base" for 65% of all charts. Divided by the number of
    # houses on each side it reads near even, which is what a spectrum should
    # do over a random population.
    one /= len(spec["for"])
    two /= len(spec["against"])
    lean = spec["poles"][0] if one > two else spec["poles"][1] if two > one else None
    return {
        "poles": list(spec["poles"]),
        "reads_as": lean or "genuinely between the two",
        "margin": round(abs(one - two), 2),
        "evidence": (why_one if one > two else why_two)[:3],
    }


def _income_rhythm(facts: dict) -> dict:
    """Her fifth dimension, which is built differently from the other four.

    The condition of the 2nd ruler, repeated Saturn / Jupiter / Uranus
    contacts, and whether the route depends on a stable role, on projects, or
    on transactions.
    """
    second = facts["ruler_of"][2]
    condition = _condition(second, facts)
    steady, variable, why = 0, 0, []
    for planet, direction in (("Saturn", "steady"), ("Jupiter", "variable"),
                              ("Uranus", "variable")):
        contact = _connected(second, planet, facts)
        if contact and contact["orb"] <= CLOSE_LINK_ORB:
            why.append(f"your money ruler is in contact with {planet} "
                       f"({contact['aspect']}, {contact['orb']}°)")
            if direction == "steady":
                steady += 2
            else:
                variable += 2
    if facts["house_of"].get(second) in SUCCEDENT:
        steady += 1
        why.append("your money ruler is in a house that accumulates")
    if facts["house_of"].get(second) in ANGULAR:
        variable += 1
        why.append("your money ruler is in an active, outward part of the chart")
    if condition["complicated"]:
        variable += 1
    return {
        "poles": ["regular and cumulative", "variable, project based, or episodic"],
        "reads_as": ("regular and cumulative" if steady > variable else
                     "variable, project based, or episodic" if variable > steady else
                     "genuinely between the two"),
        "margin": abs(steady - variable),
        "evidence": why[:3],
    }


# ── The result ─────────────────────────────────────────────────────────────

def score_earning_routes(chart: dict, *, birth_time_confident: bool = True) -> dict:
    """The private, auditable ranking. Nothing about the person goes in.

    Rule 1 in structure as well as in order: everything starts from the 2nd
    house and its ruler, and the person's degree, job and Sun sign are not
    arguments to this function.
    """
    facts = _facts(chart)
    if facts is None:
        return {"available": False,
                "reason": "needs a full chart with houses, so a birth time is required"}

    second, tenth = facts["ruler_of"][2], facts["ruler_of"][10]
    spread = _distributions()
    scored = {}
    for key in ROUTES:
        evidence = _evidence_for(key, facts)
        signals = len(evidence)
        qualifying = any(item["qualifies"] for item in evidence)
        score = _score(evidence)
        scored[key] = {
            "key": key,
            "label": ROUTES[key]["label"],
            "means": ROUTES[key]["means"],
            "plain": ROUTES[key]["plain"],
            # Hers, exactly as her table produces it. This is the auditable
            # number; it is not what the routes are sorted on. See RANKING.
            "score": score,
            "how_unusual": round(_how_unusual(key, score, spread), 3),
            "signals": signals,
            # Rule 2: two independent signals, one of which reaches the money
            # house or links career to income directly.
            "strong": signals >= 2 and qualifying,
            "has_qualifying_signal": qualifying,
            "evidence": [{"points": i["points"], "weight": i["weight"],
                          "counts_as": i["counts_as"], "why": i["why"]}
                         for i in evidence],
            "counterevidence": _counterevidence(key, facts, evidence),
        }

    ordered = sorted(scored.values(),
                     key=lambda r: (-r["how_unusual"], -r["score"], -r["signals"], r["key"]))
    # Rule 5: rank no more than three, and only routes the chart actually says
    # something about. Below the median the chart says LESS about a route than
    # it does for a typical chart, so listing it second is manufacturing a
    # ranking rather than reporting one — which is the thing rule 5 says to
    # replace with lower confidence. The floor is the median rather than a
    # number of mine: it means "more than the average chart says".
    speaks = [r for r in ordered if r["signals"] > 0 and r["how_unusual"] >= 0.5][:3]
    # Never return nothing when the chart does offer something; say it quietly.
    ranked = speaks or [r for r in ordered if r["signals"] > 0][:1]
    complementary = bool(
        len(ranked) >= 2
        and ranked[0]["how_unusual"] - ranked[1]["how_unusual"] <= COMPLEMENTARY_GAP)

    condition = _condition(second, facts)
    confidence = _confidence(ranked, condition, birth_time_confident)

    dimensions = {name: _dimension_reading(spec, facts) for name, spec in DIMENSIONS.items()}
    dimensions["income_rhythm"] = _income_rhythm(facts)

    return {
        "available": True,
        "internal_only": ("Scores and evidence never reach the reader. They exist so the "
                          "same chart reads the same way twice and so a reading can be "
                          "checked against the chart it claims to come from. The score is "
                          "a consistency device, not a probability."),
        # Rule 1, visible in the output: money is traced from here.
        "traced_from": {
            "money_house_ruler": {
                "planet": second, "sits_in_house": facts["house_of"].get(second),
                "also_rules": sorted(h for h in facts["rules_houses"].get(second, []) if h != 2),
                "condition": condition,
            },
            "career_ruler": {
                "planet": tenth, "sits_in_house": facts["house_of"].get(tenth),
                "also_rules": sorted(h for h in facts["rules_houses"].get(tenth, []) if h != 10),
            },
            "money_ruler_meets_career_ruler": _connected(second, tenth, facts),
        },
        "ranking": ranked,
        "all_routes": ordered,
        "complementary": complementary,
        "confidence": confidence,
        "dimensions": dimensions,
        "how_it_works": condition["notes"],
        "weights": "her weight table, unchanged",
        "provenance": PROVENANCE,
    }


# ── RANKING: why the raw score is not what the routes are sorted on ────────
#
# Her weights produce an auditable number per route, and that number is what
# the audit trail shows. It cannot be used to compare one route against
# another, and the calibration run is what showed it: over a thousand charts,
# "business, products or scalable output" ranked first 46% of the time and
# "partnerships, clients and deals" never ranked first at all. Employment —
# the commonest way people on earth earn money — came first 3% of the time.
#
# That is not the astrology. It is arithmetic. Her evidence column names five
# houses for business and one for partnerships, so business has five chances
# for the 5-point evidence and partnerships has one. Ranking on the raw total
# ranks the breadth of each route's definition rather than the chart in front
# of it. Capping the weak evidence did not touch it; nor did scoring only the
# best few items. The opportunity is what differs, not the count.
#
# So routes are ranked on how unusual a score is FOR THAT ROUTE, measured
# against a thousand invented charts — the same fix that took the toxicity
# band from 95.8% to 4.7%. A 14 for partnerships is a far rarer statement
# than a 14 for business, and now reads as one. Her weights are untouched;
# only the comparison between routes changed. With it the six routes rank
# first 14–21% of the time each, and every one of them can win.
_BANDS_FILE = (pathlib.Path(__file__).resolve().parents[1]
               / "content" / "engine" / "earning_route_bands.json")

# MINE: how close two routes have to be to call them complementary, in
# percentile points. Set from the calibration run — this fires on about a
# fifth of charts. At the first value tried it fired on two in five, which
# makes the word mean nothing.
COMPLEMENTARY_GAP = 0.03


def _distributions() -> dict:
    try:
        return json.loads(_BANDS_FILE.read_text())
    except (OSError, ValueError):
        return {}


def _how_unusual(route_key: str, score: int, spread: dict) -> float:
    """Where this score sits among charts in general, for this route.

    Returns 0.0 to 1.0. Uncalibrated, everything is 0.5 and the raw score
    breaks the tie — worse, but never silently wrong.
    """
    values = spread.get(route_key)
    if not values:
        return 0.5
    return bisect.bisect_left(values, score) / len(values)

PROVENANCE = (
    "Routes, weight table, dimensions and rules are the co-founder's, applied "
    "exactly as written. Two numbers are mine and are marked in the code: what "
    "counts as a close connection (4°) and how close two routes must be to read "
    "as complementary. One method is mine: routes are ranked on how unusual a "
    "score is for that route rather than on the raw total, because her evidence "
    "column names five houses for one route and one house for another, and the "
    "raw total ranked that breadth instead of the chart. Both numbers and the "
    "ranking method were set from a thousand-chart calibration run."
)


def _confidence(ranked: list[dict], condition: dict, birth_time_confident: bool) -> str:
    """Rule 5: thin evidence or an uncertain birth time lowers confidence
    rather than producing a precise ranking nobody can stand behind."""
    if not birth_time_confident:
        return "low — the birth time is uncertain, and houses move quickly"
    if not ranked or not ranked[0]["strong"]:
        return "low — no route reaches two independent signals with one on the money house"
    if ranked[0]["how_unusual"] < 0.5:
        return "low — the chart does not lean to any route more than an average chart does"
    if len(ranked) == 1 or ranked[0]["signals"] < 3:
        return "moderate — the strongest route is clear but the evidence is thin"
    if condition["complicated"]:
        return "moderate — the route is clear, its ruler is not straightforward"
    return "high"


def describe_routes(result: dict) -> str:
    """The one plain-language sentence an answer would be built on.

    No houses, no planets, no scores — her requirement that the technical
    evidence stays internal unless the person asks for it.
    """
    if not result.get("available") or not result["ranking"]:
        return ""
    ranked = result["ranking"]
    first = ranked[0]["plain"]
    if len(ranked) == 1:
        return f"Your strongest way of earning looks like {first}."
    second = ranked[1]["plain"]
    if result["complementary"]:
        return (f"Your strongest ways of earning look like {first} and {second}, "
                "and they work together rather than competing.")
    return f"Your strongest way of earning looks like {first}, followed by {second}."


def technical_evidence(result: dict) -> list[str]:
    """The placements and aspects behind the ranking, for the one case where
    they are allowed out: the person explicitly asked how the chart says so.

    Reached only through the existing astrology_on_request mode. Every other
    answer gets `describe_routes` and nothing else.
    """
    if not result.get("available"):
        return []
    lines = []
    for route in result["ranking"]:
        lines.append(route["label"] + ":")
        lines.extend(f"  {item['why']}" for item in route["evidence"][:4])
        if route["counterevidence"]:
            lines.append(f"  against it: {route['counterevidence'][0]}")
    return lines
