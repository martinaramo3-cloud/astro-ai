"""The sky as it actually looked, from where someone stood.

A chart wheel is a diagram: it flattens the sky into a circle and throws away
where anything really was. This puts it back — altitude above the horizon and
compass bearing, for one place and one moment. It is the same ephemeris the
readings are built on, asked a different question.

Nothing here calls a model, so it costs nothing to show.
"""
from __future__ import annotations

import swisseph as swe

from app.astrology_engine import PLANETS, get_zodiac_sign

# Swiss Ephemeris measures azimuth from due south, turning west. Everyone else
# — compasses, phone sensors, the word "northeast" — measures from north,
# turning east. Verified against solar noon in Sofia: the Sun's highest point
# comes out at 180.33 with this correction, and 0.33 with it.
def _compass(swe_azimuth: float) -> float:
    return (swe_azimuth + 180) % 360


# Rough naked-eye brightness, for sizing a dot on screen. Real magnitudes vary
# with distance and phase; swe.pheno_ut gives the exact value where it can, and
# these are the fallback so a body always has something to draw with.
FALLBACK_MAGNITUDE = {
    "Sun": -26.7, "Moon": -12.7, "Mercury": -0.4, "Venus": -4.1, "Mars": 0.7,
    "Jupiter": -2.2, "Saturn": 0.5, "Uranus": 5.7, "Neptune": 7.8, "Pluto": 14.4,
}

# Beyond this, nobody has ever seen it without a telescope. Worth saying so
# rather than drawing Pluto as though it were a visible star.
NAKED_EYE_LIMIT = 6.5

def _horizontal(jd: float, lat: float, lon: float, ecl: tuple) -> tuple[float, float]:
    """Ecliptic position -> (compass bearing, altitude) for this place and time."""
    azimuth, true_altitude = swe.azalt(
        jd, swe.ECL2HOR, (lon, lat, 0), 1013.25, 15, (ecl[0], ecl[1], ecl[2])
    )[:2]
    return _compass(azimuth), true_altitude


def _magnitude(jd: float, body: int, name: str) -> float:
    try:
        # pheno_ut returns phase angle, phase, elongation, diameter, magnitude
        return round(swe.pheno_ut(jd, body, swe.FLG_SWIEPH)[4], 2)
    except Exception:
        return FALLBACK_MAGNITUDE.get(name, 6.0)


def build_sky_view(utc_dt, latitude: float, longitude: float) -> dict:
    """Where every chart body actually sat in the sky, from this spot."""
    jd = swe.julday(
        utc_dt.year, utc_dt.month, utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600,
    )

    bodies = []
    for name, body in PLANETS.items():
        values, _ = swe.calc_ut(jd, body)
        longitude_ecl, latitude_ecl, distance, speed = values[0], values[1], values[2], values[3]
        bearing, altitude = _horizontal(jd, latitude, longitude, (longitude_ecl, latitude_ecl, distance))
        magnitude = _magnitude(jd, body, name)

        bodies.append({
            "name": name,
            "altitude": round(altitude, 2),
            "azimuth": round(bearing, 2),
            "above_horizon": altitude > 0,
            "sign": get_zodiac_sign(longitude_ecl),
            "degree_in_sign": round(longitude_ecl % 30, 2),
            "retrograde": speed < 0,
            "magnitude": magnitude,
            "naked_eye": magnitude <= NAKED_EYE_LIMIT,
        })

    # The ecliptic is the line every planet travels along. Drawn across the sky
    # it is the single most explanatory mark on the picture: it shows why the
    # planets are strung out in an arc rather than scattered.
    ecliptic = []
    sun_distance = swe.calc_ut(jd, swe.SUN)[0][2]
    for degree in range(0, 361, 5):
        bearing, altitude = _horizontal(jd, latitude, longitude, (float(degree), 0.0, sun_distance))
        ecliptic.append({
            "longitude": degree,
            "azimuth": round(bearing, 2),
            "altitude": round(altitude, 2),
            "sign": get_zodiac_sign(degree),
        })

    sun = next(b for b in bodies if b["name"] == "Sun")
    moon = next(b for b in bodies if b["name"] == "Moon")

    # Being above the horizon is not the same as being visible. In daylight the
    # sky outshines everything but the Moon, so listing Mars as "visible" at
    # breakfast would be a picture of the sky nobody could have seen.
    if sun["altitude"] > -6:
        visible = [moon] if moon["above_horizon"] else []
    else:
        visible = [
            b for b in bodies
            if b["above_horizon"] and b["naked_eye"] and b["name"] != "Sun"
        ]

    return {
        "observer": {"latitude": latitude, "longitude": longitude},
        "moment_utc": utc_dt.isoformat(),
        "bodies": bodies,
        "ecliptic": ecliptic,
        "daylight": sun["altitude"] > -0.833,          # upper limb still up
        "twilight": -18 < sun["altitude"] <= -0.833,   # sky not yet fully dark
        "sun_altitude": sun["altitude"],
        "moon_illumination": _moon_illumination(jd),
        "visible_count": len(visible),
        "visible_names": [b["name"] for b in visible],
    }


def _moon_illumination(jd: float) -> float:
    """Lit fraction of the Moon's disc, 0 to 1."""
    try:
        return round(swe.pheno_ut(jd, swe.MOON, swe.FLG_SWIEPH)[1], 3)
    except Exception:
        return 0.5
