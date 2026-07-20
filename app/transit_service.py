from datetime import datetime, timedelta
import pytz

from app.astrology_engine import get_planet_positions_from_utc

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


def get_transit_aspects(natal_planets: list, transit_planets: list):
    active_transits = []

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
                    "orb": round(closest_orb, 2)
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

    # Tightest peaks first so a cap keeps the most meaningful activations.
    timeline.sort(key=lambda e: (e["peak_orb"], e["peaks"]))
    return timeline[:max_events]