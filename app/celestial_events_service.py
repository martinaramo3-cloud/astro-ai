"""Detecting notable sky events — lunations, eclipses, and retrograde stations.

Everything here is computed from the Swiss Ephemeris, so dates are real rather
than guessed. Events are scored for significance and, when a natal chart is
supplied, flagged when they land on one of that person's own placements.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import swisseph as swe

from app.astrology_engine import ZODIAC_SIGNS, get_zodiac_sign

# Bodies whose direction changes are worth announcing, and how loudly.
STATION_PLANETS = {
    "Mercury": (swe.MERCURY, 55),
    "Venus": (swe.VENUS, 50),
    "Mars": (swe.MARS, 48),
    "Jupiter": (swe.JUPITER, 30),
    "Saturn": (swe.SATURN, 30),
}

# Sign changes. The Moon changes sign every couple of days, so it scores low
# and mostly matters for "the mood of today"; the slow planets are rare and
# genuinely mark a change of chapter.
# The Moon is deliberately absent: it changes sign every two days, so its
# ingresses would swamp everything else, and its current sign is already
# reported in `moon`.
INGRESS_PLANETS = {
    "Sun": (swe.SUN, 48),
    "Mercury": (swe.MERCURY, 46),
    "Venus": (swe.VENUS, 48),
    "Mars": (swe.MARS, 52),
    "Jupiter": (swe.JUPITER, 70),
    "Saturn": (swe.SATURN, 75),
    "Uranus": (swe.URANUS, 80),
    "Neptune": (swe.NEPTUNE, 80),
    "Pluto": (swe.PLUTO, 85),
}

# A hit to one of these feels personal; outer planets are generational.
PERSONAL_POINTS = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Ascendant"}

# Aspects used when checking whether an event touches the natal chart.
PERSONAL_ASPECTS = {"conjunction": 0, "opposition": 180, "square": 90}
PERSONAL_ORB = 6.0


def _to_jd(dt: datetime) -> float:
    dt = dt.astimezone(timezone.utc)
    return swe.julday(
        dt.year, dt.month, dt.day, dt.hour + dt.minute / 60 + dt.second / 3600
    )


def _to_dt(jd: float) -> datetime:
    year, month, day, hour = swe.revjul(jd)
    hours = int(hour)
    minutes = int(round((hour - hours) * 60))
    if minutes == 60:  # rounding can spill over
        hours, minutes = hours + 1, 0
    base = datetime(year, month, day, tzinfo=timezone.utc)
    return base + timedelta(hours=hours, minutes=minutes)


def _longitude(jd: float, body: int) -> float:
    return swe.calc_ut(jd, body)[0][0] % 360


def _speed(jd: float, body: int) -> float:
    return swe.calc_ut(jd, body)[0][3]


def _phase_angle(jd: float) -> float:
    """Sun→Moon separation: 0° is a new moon, 180° a full moon."""
    return (_longitude(jd, swe.MOON) - _longitude(jd, swe.SUN)) % 360


def _signed_phase_offset(jd: float, target: float) -> float:
    """Distance from `target`, in (-180, 180], so it crosses zero at the event."""
    return ((_phase_angle(jd) - target + 180) % 360) - 180


def _bisect(fn, low: float, high: float, iterations: int = 40) -> float:
    """Narrow a sign change in `fn` down to roughly a minute."""
    f_low = fn(low)
    for _ in range(iterations):
        mid = (low + high) / 2
        f_mid = fn(mid)
        if (f_low < 0) == (f_mid < 0):
            low, f_low = mid, f_mid
        else:
            high = mid
    return (low + high) / 2


def describe_moon_phase(dt: datetime | None = None) -> dict:
    """Current phase name, illumination, and where the Moon is sitting."""
    dt = dt or datetime.now(timezone.utc)
    jd = _to_jd(dt)
    angle = _phase_angle(jd)

    names = [
        (0, "New Moon"), (45, "Waxing Crescent"), (90, "First Quarter"),
        (135, "Waxing Gibbous"), (180, "Full Moon"), (225, "Waning Gibbous"),
        (270, "Last Quarter"), (315, "Waning Crescent"),
    ]
    # Snap to the nearest named phase (each spans 45°, so within 22.5°).
    name = min(names, key=lambda n: abs(((angle - n[0] + 180) % 360) - 180))[1]

    moon_longitude = _longitude(jd, swe.MOON)
    return {
        "phase_angle": round(angle, 2),
        "phase_name": name,
        # Fraction of the disc lit, 0 at new and 1 at full.
        "illumination": round((1 - math.cos(math.radians(angle))) / 2, 3),
        "moon_sign": get_zodiac_sign(moon_longitude),
        "moon_degree": round(moon_longitude % 30, 2),
    }


def find_lunations(days_ahead: int = 45, start: datetime | None = None) -> list[dict]:
    """Exact new and full moons in the window, with the sign each falls in."""
    start = start or datetime.now(timezone.utc)
    start_jd = _to_jd(start)
    end_jd = start_jd + days_ahead

    events: list[dict] = []
    for target, label in ((0.0, "New Moon"), (180.0, "Full Moon")):
        def offset(jd: float, _t=target) -> float:
            return _signed_phase_offset(jd, _t)

        step = 0.25  # 6 hours; the phase moves ~3° per step
        jd = start_jd
        previous = offset(jd)
        while jd < end_jd:
            nxt = jd + step
            current = offset(nxt)
            # A genuine crossing goes negative→positive by a small amount;
            # the ±180 wrap produces a large jump, so ignore those.
            if previous < 0 <= current and abs(current - previous) < 90:
                exact = _bisect(offset, jd, nxt)
                longitude = _longitude(exact, swe.MOON)
                events.append({
                    "type": "lunation",
                    "name": label,
                    "date": _to_dt(exact).isoformat(),
                    "longitude": round(longitude, 2),
                    "sign": get_zodiac_sign(longitude),
                    "degree": round(longitude % 30, 2),
                    "significance": 65 if label == "Full Moon" else 60,
                })
            previous = current
            jd = nxt

    return events


def _solar_eclipse_kind(flags: int) -> str:
    if flags & swe.ECL_TOTAL:
        return "Total Solar Eclipse"
    if flags & swe.ECL_ANNULAR_TOTAL:
        return "Hybrid Solar Eclipse"
    if flags & swe.ECL_ANNULAR:
        return "Annular Solar Eclipse"
    return "Partial Solar Eclipse"


def _lunar_eclipse_kind(flags: int) -> str:
    if flags & swe.ECL_TOTAL:
        return "Total Lunar Eclipse"
    if flags & swe.ECL_PENUMBRAL:
        return "Penumbral Lunar Eclipse"
    return "Partial Lunar Eclipse"


def find_eclipses(days_ahead: int = 120, start: datetime | None = None) -> list[dict]:
    """Upcoming solar and lunar eclipses anywhere on Earth."""
    start = start or datetime.now(timezone.utc)
    start_jd = _to_jd(start)
    end_jd = start_jd + days_ahead

    events: list[dict] = []

    for finder, body, namer in (
        (swe.sol_eclipse_when_glob, swe.SUN, _solar_eclipse_kind),
        (swe.lun_eclipse_when, swe.MOON, _lunar_eclipse_kind),
    ):
        jd = start_jd
        # A couple of eclipse seasons is plenty for any sensible window.
        for _ in range(8):
            try:
                flags, times = finder(jd, swe.FLG_SWIEPH, 0, False)
            except Exception:
                break
            peak = times[0]
            if peak > end_jd:
                break

            longitude = _longitude(peak, body)
            events.append({
                "type": "eclipse",
                "name": namer(flags),
                "date": _to_dt(peak).isoformat(),
                "longitude": round(longitude, 2),
                "sign": get_zodiac_sign(longitude),
                "degree": round(longitude % 30, 2),
                "significance": 100,
            })
            jd = peak + 1  # step past this one to find the next

    return events


def find_retrograde_stations(days_ahead: int = 60, start: datetime | None = None) -> list[dict]:
    """Dates where a planet turns retrograde or direct."""
    start = start or datetime.now(timezone.utc)
    start_jd = _to_jd(start)
    end_jd = start_jd + days_ahead

    events: list[dict] = []
    for planet_name, (body, weight) in STATION_PLANETS.items():
        def speed(jd: float, _b=body) -> float:
            return _speed(jd, _b)

        jd = start_jd
        previous = speed(jd)
        while jd < end_jd:
            nxt = jd + 0.5
            current = speed(nxt)
            if (previous < 0) != (current < 0):
                exact = _bisect(speed, jd, nxt)
                turning_retrograde = current < 0
                longitude = _longitude(exact, body)
                events.append({
                    "type": "station",
                    "name": (
                        f"{planet_name} turns retrograde"
                        if turning_retrograde
                        else f"{planet_name} turns direct"
                    ),
                    "planet": planet_name,
                    "retrograde": turning_retrograde,
                    "date": _to_dt(exact).isoformat(),
                    "longitude": round(longitude, 2),
                    "sign": get_zodiac_sign(longitude),
                    "degree": round(longitude % 30, 2),
                    "significance": weight,
                })
            previous = current
            jd = nxt

    return events


def _sign_index(jd: float, body: int) -> int:
    return int(_longitude(jd, body) // 30)


def find_ingresses(days_ahead: int = 45, start: datetime | None = None) -> list[dict]:
    """Dates when a planet crosses into a new sign.

    A change of sign is a change of costume: the same function, expressed a
    different way. Slow planets doing it is a genuine turn of the page.
    """
    start = start or datetime.now(timezone.utc)
    start_jd = _to_jd(start)
    end_jd = start_jd + days_ahead

    events: list[dict] = []
    for planet_name, (body, weight) in INGRESS_PLANETS.items():
        # The Moon covers 30° in ~2.2 days, so it needs a finer step than Pluto.
        step = 1.0
        jd = start_jd
        previous_index = _sign_index(jd, body)
        while jd < end_jd:
            nxt = jd + step
            current_index = _sign_index(nxt, body)
            if current_index != previous_index:
                # Narrow to the first moment the new sign holds.
                low, high = jd, nxt
                for _ in range(40):
                    mid = (low + high) / 2
                    if _sign_index(mid, body) == current_index:
                        high = mid
                    else:
                        low = mid
                exact = high
                events.append({
                    "type": "ingress",
                    "name": f"{planet_name} enters {ZODIAC_SIGNS[current_index]}",
                    "planet": planet_name,
                    "date": _to_dt(exact).isoformat(),
                    "longitude": round(current_index * 30.0, 2),
                    "sign": ZODIAC_SIGNS[current_index],
                    "leaves_sign": ZODIAC_SIGNS[previous_index],
                    "degree": 0.0,
                    "retrograde": _speed(exact, body) < 0,
                    "significance": weight,
                })
                previous_index = current_index
            jd = nxt

    return events


def current_retrogrades(dt: datetime | None = None) -> list[str]:
    dt = dt or datetime.now(timezone.utc)
    jd = _to_jd(dt)
    return [
        name for name, (body, _) in STATION_PLANETS.items() if _speed(jd, body) < 0
    ]


def _personal_hits(longitude: float, natal_planets: list | None, ascendant: dict | None) -> list[dict]:
    """Natal placements the event closely aspects."""
    if not natal_planets:
        return []

    points = [
        {"name": p["planet"], "degree": p["degree"], "house": p.get("house")}
        for p in natal_planets
    ]
    if ascendant:
        points.append({"name": "Ascendant", "degree": ascendant["degree"], "house": 1})

    hits = []
    for point in points:
        separation = abs(longitude - point["degree"]) % 360
        separation = min(separation, 360 - separation)
        for aspect_name, aspect_angle in PERSONAL_ASPECTS.items():
            orb = abs(separation - aspect_angle)
            if orb <= PERSONAL_ORB:
                hits.append({
                    "natal_point": point["name"],
                    "aspect": aspect_name,
                    "orb": round(orb, 2),
                    "house": point["house"],
                    "personal": point["name"] in PERSONAL_POINTS,
                })
                break

    hits.sort(key=lambda h: (not h["personal"], h["orb"]))
    return hits


def build_cosmic_events(
    natal_planets: list | None = None,
    ascendant: dict | None = None,
    days_ahead: int = 45,
    min_significance: int = 45,
) -> dict:
    """Everything the app needs to decide whether to speak up unprompted."""
    now = datetime.now(timezone.utc)

    events = (
        find_lunations(days_ahead=days_ahead, start=now)
        + find_eclipses(days_ahead=max(days_ahead, 120), start=now)
        + find_retrograde_stations(days_ahead=days_ahead, start=now)
        + find_ingresses(days_ahead=days_ahead, start=now)
    )

    for event in events:
        hits = _personal_hits(event["longitude"], natal_planets, ascendant)
        event["natal_hits"] = hits[:3]

        # An event landing on a personal placement matters far more to *you*.
        closest = next((h for h in hits if h["personal"]), None)
        if closest:
            event["significance"] += 25 if closest["orb"] <= 3 else 15
            event["is_personal"] = True
        else:
            event["is_personal"] = False

        event["days_away"] = round(
            (datetime.fromisoformat(event["date"]) - now).total_seconds() / 86400, 1
        )

    events = [e for e in events if e["significance"] >= min_significance]
    events.sort(key=lambda e: e["date"])

    # The headline is whatever is both close in time and significant: an event
    # within three days, strongest first.
    imminent = [e for e in events if -1 <= e["days_away"] <= 3]
    headline = max(imminent, key=lambda e: e["significance"]) if imminent else None

    return {
        "generated_at": now.isoformat(),
        "moon": describe_moon_phase(now),
        "retrograde_now": current_retrogrades(now),
        "headline": headline,
        "events": events[:12],
    }
