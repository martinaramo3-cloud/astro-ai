"""Score a thousand invented charts, so the earning bands come from data.

The bands say how pronounced a lean is among charts in general. Nobody can
know that by guessing, and guessing is exactly what put 95.8% of couples in
"toxic attraction" — thresholds written for a scale the engine does not
produce. This measures the scale first and writes the thresholds after.

Every person here is invented: random dates, times and cities. No real chart
is involved.

    ./venv/bin/python training/area3/distribution.py [charts]

Writes content/engine/earning_bands.json and training/area3/distribution.json.
"""
from __future__ import annotations

import json
import os
import pathlib
import random
import statistics
import sys
import tempfile
from datetime import datetime, timedelta

os.environ.setdefault("DATABASE_PATH", os.path.join(tempfile.mkdtemp(), "d.db"))
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pytz  # noqa: E402

from app.astrology_engine import (  # noqa: E402
    add_house_to_planets, get_houses_and_ascendant, get_planet_positions_from_utc,
)
from app.earning_profile_service import POLES, score_earning_profile  # noqa: E402

# Spread over the world so house placements vary the way real users do.
CITIES = [
    (42.70, 23.32, "Europe/Sofia"), (45.46, 9.19, "Europe/Rome"),
    (51.51, -0.13, "Europe/London"), (40.71, -74.01, "America/New_York"),
    (-23.55, -46.63, "America/Sao_Paulo"), (35.68, 139.69, "Asia/Tokyo"),
    (-33.87, 151.21, "Australia/Sydney"), (19.08, 72.88, "Asia/Kolkata"),
    (41.33, 19.82, "Europe/Tirane"), (4.71, -74.07, "America/Bogota"),
]


def a_chart(rng: random.Random) -> dict:
    lat, lon, zone = rng.choice(CITIES)
    born = datetime(1985, 1, 1) + timedelta(
        days=rng.randrange(0, 365 * 25), minutes=rng.randrange(0, 1440))
    utc = pytz.timezone(zone).localize(born).astimezone(pytz.utc)
    planets = get_planet_positions_from_utc(utc)
    houses = get_houses_and_ascendant(utc, lat, lon)
    return {
        "planet_positions": add_house_to_planets(planets, houses["houses"]),
        "houses": houses["houses"],
        "ascendant": houses["ascendant"],
        "midheaven": houses.get("midheaven"),
        "angles": houses.get("angles", []),
        "birth_time_known": True,
    }


def main(count: int = 1000) -> None:
    rng = random.Random(20260924)   # reproducible
    magnitudes: dict[str, list[float]] = {name: [] for name in POLES}
    signed: dict[str, list[float]] = {name: [] for name in POLES}

    for _ in range(count):
        profile = score_earning_profile(a_chart(rng))
        for name, entry in profile["spectrums"].items():
            magnitudes[name].append(abs(entry["score"]))
            signed[name].append(entry["score"])

    # Bands are cut on the MAGNITUDE of a lean — how decided this chart is —
    # because direction is not something one can be above average at.
    bands, report = {}, {}
    for name, values in magnitudes.items():
        values.sort()
        def at(p: float) -> float:
            return round(values[min(len(values) - 1, int(len(values) * p))], 2)
        low, high, exceptional = at(0.40), at(0.75), at(0.92)
        bands[name] = [
            {"max": low, "label": "low"},
            {"max": high, "label": "typical"},
            {"max": exceptional, "label": "high"},
            {"max": 9999, "label": "exceptional"},
        ]
        pole_positive = sum(1 for v in signed[name] if v > 0) / len(signed[name])
        report[name] = {
            "poles": list(POLES[name]),
            "magnitude": {"min": values[0], "median": at(0.50), "max": values[-1],
                          "mean": round(statistics.mean(values), 2)},
            "cuts": {"low_upto": low, "typical_upto": high, "high_upto": exceptional},
            "share_leaning_to_first_pole": round(pole_positive, 3),
        }

    (ROOT / "content" / "engine" / "earning_bands.json").write_text(
        json.dumps(bands, indent=1) + "\n")
    here = pathlib.Path(__file__).resolve().parent
    (here / "distribution.json").write_text(json.dumps(
        {"charts": count, "spectrums": report}, indent=1) + "\n")

    print(f"{count} invented charts\n")
    for name, data in report.items():
        share = data["share_leaning_to_first_pole"]
        print(f"  {name}")
        print(f"    {data['poles'][0]}  {share:.0%}   |   {data['poles'][1]}  {1 - share:.0%}")
        print(f"    magnitude  median {data['magnitude']['median']}  max {data['magnitude']['max']}")
        print(f"    low ≤{data['cuts']['low_upto']}  typical ≤{data['cuts']['typical_upto']}"
              f"  high ≤{data['cuts']['high_upto']}  then exceptional\n")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
