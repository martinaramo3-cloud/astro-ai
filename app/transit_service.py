from datetime import datetime, timedelta
import pytz

from app.astrology_engine import get_planet_house, get_planet_positions_from_utc

TRANSIT_ASPECTS = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "opposition": 180,
}

TRANSIT_ORB = 3


def angle_difference(deg1: float, deg2: float) -> float:
    diff = abs(deg1 - deg2) % 360
    return min(diff, 360 - diff)


def get_current_transit_positions():
    now_utc = datetime.now(pytz.utc)
    return get_planet_positions_from_utc(now_utc)


def get_transit_houses(
    transit_planets: list,
    natal_houses: list,
    focus_planets: set | None = None,
) -> list[dict]:
    """Which of the person's houses each transiting planet is currently crossing.

    An aspect says what is being touched; the house says which part of their
    life it is happening in. "Saturn is in your 7th" is a statement about
    relationships that no aspect alone conveys.
    """
    # No birth time means no house cusps, so there is no life area to name.
    # Better to say nothing than to place a transit in a house we invented.
    if not natal_houses:
        return []

    results = []
    for transit in transit_planets:
        # The slow planets are always worth reporting — a Saturn or Pluto
        # crossing is a multi-year fact about a life area regardless of the
        # question. The fast ones only matter when the question turns on them.
        if focus_planets is not None:
            slow = transit["planet"] in {"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
            if not slow and transit["planet"] not in focus_planets:
                continue

        house = get_planet_house(transit["degree"], natal_houses)
        results.append({
            "transit_planet": transit["planet"],
            "sign": transit["sign"],
            "degree_in_sign": transit["degree_in_sign"],
            "retrograde": transit["retrograde"],
            "in_natal_house": house,
        })
    return results


def get_transit_aspects(natal_planets: list, transit_planets: list, when=None):
    """Active transits, each labelled as applying (building) or separating (fading).

    Orb alone says how strong a transit is but not whether it is arriving or
    leaving — the difference between "this peaks next week" and "you're already
    through it". Direction is found by re-measuring the orb slightly later and
    seeing whether it tightened.
    """
    active_transits = []

    reference = when or datetime.now(pytz.utc)
    # Far enough ahead that even slow planets move measurably.
    later_positions = {
        p["planet"]: p["degree"]
        for p in get_planet_positions_from_utc(reference + timedelta(hours=12))
    }

    for transit in transit_planets:
        for natal in natal_planets:
            diff = angle_difference(transit["degree"], natal["degree"])

            closest_aspect = None
            closest_orb = None
            closest_angle = None

            for aspect_name, aspect_angle in TRANSIT_ASPECTS.items():
                orb = abs(diff - aspect_angle)

                if orb <= TRANSIT_ORB:
                    if closest_orb is None or orb < closest_orb:
                        closest_aspect = aspect_name
                        closest_orb = orb
                        closest_angle = diff

            if closest_aspect:
                # Compare the orb now with the orb shortly after: tightening
                # means the transit is still building toward exact.
                later_degree = later_positions.get(transit["planet"])
                motion = None
                if later_degree is not None:
                    later_orb = abs(
                        angle_difference(later_degree, natal["degree"])
                        - TRANSIT_ASPECTS[closest_aspect]
                    )
                    motion = "applying" if later_orb < closest_orb else "separating"

                active_transits.append({
                    "transit_planet": transit["planet"],
                    "transit_sign": transit["sign"],
                    "transit_degree": transit["degree"],
                    "transit_retrograde": transit["retrograde"],
                    "natal_planet": natal["planet"],
                    "natal_sign": natal["sign"],
                    "natal_degree": natal["degree"],
                    "aspect": closest_aspect,
                    "angle": round(closest_angle, 2),
                    "orb": round(closest_orb, 2),
                    "motion": motion,
                })

    return sorted(active_transits, key=lambda x: x["orb"])


# The Moon completes an aspect in hours, so it adds noise to a multi-week
# timeline; every slower body is worth tracking.
TIMELINE_TRANSIT_PLANETS = {
    "Sun", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
}


def build_upcoming_transit_timeline(
    natal_planets: list,
    weeks_ahead: int = 8,
    step_days: int = 2,
    max_events: int = 14,
    focus_planets: set | None = None,
):
    """Sample the ephemeris over the coming weeks and return transit events
    with real calendar dates: when each aspect starts, peaks (tightest orb),
    and fades. This is what lets the AI talk timing without inventing dates."""
    now = datetime.now(pytz.utc)
    events: dict = {}

    for day_offset in range(0, weeks_ahead * 7 + 1, step_days):
        sample_dt = now + timedelta(days=day_offset)
        positions = get_planet_positions_from_utc(sample_dt)

        for transit in positions:
            if transit["planet"] not in TIMELINE_TRANSIT_PLANETS:
                continue
            for natal in natal_planets:
                diff = angle_difference(transit["degree"], natal["degree"])

                for aspect_name, aspect_angle in TRANSIT_ASPECTS.items():
                    orb = abs(diff - aspect_angle)
                    if orb > TRANSIT_ORB:
                        continue

                    key = (transit["planet"], natal["planet"], aspect_name)
                    event = events.get(key)
                    if event is None:
                        events[key] = {
                            "first": sample_dt,
                            "last": sample_dt,
                            "peak_orb": orb,
                            "peak_date": sample_dt,
                            "retrograde_at_peak": transit["retrograde"],
                            "natal_sign": natal["sign"],
                            "natal_house": natal.get("house"),
                        }
                    else:
                        event["last"] = sample_dt
                        if orb < event["peak_orb"]:
                            event["peak_orb"] = orb
                            event["peak_date"] = sample_dt
                            event["retrograde_at_peak"] = transit["retrograde"]

    timeline = [
        {
            "transit_planet": transit_planet,
            "aspect": aspect_name,
            "natal_planet": natal_planet,
            "natal_sign": event["natal_sign"],
            "natal_house": event["natal_house"],
            "starts": event["first"].date().isoformat(),
            "peaks": event["peak_date"].date().isoformat(),
            "fades": event["last"].date().isoformat(),
            "peak_orb": round(event["peak_orb"], 2),
            "retrograde_at_peak": event["retrograde_at_peak"],
        }
        for (transit_planet, natal_planet, aspect_name), event in events.items()
    ]

    # Keep only what the question turns on, judged by the natal end of the
    # transit — that is the part of the person being touched.
    if focus_planets is not None:
        timeline = [e for e in timeline if e["natal_planet"] in focus_planets]

    # Tightest peaks first so a cap keeps the most meaningful activations.
    timeline.sort(key=lambda e: (e["peak_orb"], e["peaks"]))
    return timeline[:max_events]

# What a relationship question turns on. Uranus and Neptune are left out: they
# are too slow to explain "why this week", and they tempt an answer toward the
# cosmic when the question is about a person.
RELATIONSHIP_PLANETS = {"Sun", "Moon", "Venus", "Mars", "Jupiter", "Saturn", "Pluto"}


def build_relationship_timing(
    person_1_planets: list,
    person_2_planets: list,
    synastry_aspects: list,
    max_each: int = 5,
) -> dict:
    """What the sky is currently doing to two people and to the thing between them.

    Synastry says what two charts are like together — permanently. It cannot say
    why something is happening this month, which is what people actually ask.
    That needs transits, and the third list below is the one that earns its
    place: a transit landing on a degree where their two charts already touch
    each other is the difference between "you two have a Venus-Mars square" and
    "Saturn is sitting on it right now".
    """
    transits = get_current_transit_positions()

    def hits(natal: list) -> list:
        found = get_transit_aspects(natal_planets=natal, transit_planets=transits)
        found = [t for t in found if t["natal_planet"] in RELATIONSHIP_PLANETS]
        # Compact deliberately. The full record carries both bodies' signs and
        # absolute degrees, none of which is read here — the prompt needs to
        # know what is hitting what, how close, and which way it is moving.
        return [
            {
                "transit": t["transit_planet"],
                "aspect": t["aspect"],
                "natal": t["natal_planet"],
                "orb": t["orb"],
                "motion": t["motion"],
                **({"retrograde": True} if t["transit_retrograde"] else {}),
            }
            for t in found[:max_each]
        ]

    yours = hits(person_1_planets)
    theirs = hits(person_2_planets)

    # A synastry contact is "live" when a transiting planet is within orb of
    # either end of it. Both ends being lit is rarer and stronger, so it sorts
    # first.
    activated = []
    for contact in synastry_aspects[:12]:
        p1, p2 = contact.get("person_1_planet"), contact.get("person_2_planet")
        touching_yours = [t for t in yours if t["natal"] == p1]
        touching_theirs = [t for t in theirs if t["natal"] == p2]
        if not touching_yours and not touching_theirs:
            continue

        activated.append({
            "contact": f"your {p1} {contact['aspect']} their {p2}",
            "contact_orb": contact.get("orb"),
            "lit_on_your_side": [
                f"{t['transit']} {t['aspect']}, orb {t['orb']}, {t['motion']}"
                for t in touching_yours[:2]
            ],
            "lit_on_their_side": [
                f"{t['transit']} {t['aspect']}, orb {t['orb']}, {t['motion']}"
                for t in touching_theirs[:2]
            ],
            "both_sides": bool(touching_yours and touching_theirs),
        })

    activated.sort(key=lambda a: (not a["both_sides"], a["contact_orb"] or 99))

    return {
        "note": (
            "Current transits. Synastry says what the two charts are like; these say "
            "why now. 'activated_contacts' is the strongest evidence for timing — a "
            "transit landing where their charts already touch."
        ),
        "to_your_chart": yours,
        "to_their_chart": theirs,
        "activated_contacts": activated[:3],
        "upcoming_for_you": [
            {
                "when": f"{e['starts']} to {e['fades']}, peaks {e['peaks']}",
                "what": f"{e['transit_planet']} {e['aspect']} your {e['natal_planet']}",
                "peak_orb": e["peak_orb"],
            }
            for e in build_upcoming_transit_timeline(
                person_1_planets, max_events=4, focus_planets=RELATIONSHIP_PLANETS
            )
        ],
    }
