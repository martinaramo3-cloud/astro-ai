"""Score a thousand fictional pairs, so the bands come from data not from me.

The existing bands put "obsessive" at 21 and let it run to 999; a real pair in
testing scored 42.5, double the floor. Nobody knows whether that is remarkable
or ordinary, because nothing has ever looked at the spread. This looks.

Every person here is invented: random dates, times and cities. Nobody's real
chart is involved.

    ./venv/bin/python training/area2/distribution.py [pairs]
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
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import pytz  # noqa: E402

from app.astrology_engine import (  # noqa: E402
    add_house_to_planets, get_houses_and_ascendant, get_planet_positions_from_utc,
)
from app.aspect_services import get_aspects  # noqa: E402
from app.compatibility_service import build_synastry_engine, get_synastry_aspects  # noqa: E402

# Spread over the world so house placements vary the way real users do.
CITIES = [
    (42.70, 23.32, "Europe/Sofia"), (45.46, 9.19, "Europe/Rome"),
    (51.51, -0.13, "Europe/London"), (40.71, -74.01, "America/New_York"),
    (-23.55, -46.63, "America/Sao_Paulo"), (35.68, 139.69, "Asia/Tokyo"),
    (-33.87, 151.21, "Australia/Sydney"), (19.08, 72.88, "Asia/Kolkata"),
    (41.33, 19.82, "Europe/Tirane"), (4.71, -74.07, "America/Bogota"),
]


def a_person(rng: random.Random) -> dict:
    lat, lon, zone = rng.choice(CITIES)
    born = datetime(1985, 1, 1) + timedelta(
        days=rng.randrange(0, 365 * 25), minutes=rng.randrange(0, 1440))
    utc = pytz.timezone(zone).localize(born).astimezone(pytz.utc)
    planets = get_planet_positions_from_utc(utc)
    houses = get_houses_and_ascendant(utc, lat, lon)
    placed = add_house_to_planets(planets, houses["houses"])
    return {
        "planet_positions": placed,
        "houses": houses["houses"],
        "ascendant": houses["ascendant"],
        "midheaven": houses.get("midheaven"),
        "angles": houses.get("angles", []),
        "aspects": get_aspects(placed),
        "birth_time_known": True,
    }


def main(count: int = 1000) -> None:
    rng = random.Random(20260924)   # reproducible
    indices = {"attraction": [], "emotional": [], "long_term": [], "toxicity": []}
    classifiers: dict[str, int] = {}
    multiple = 0

    for n in range(count):
        one, two = a_person(rng), a_person(rng)
        engine = build_synastry_engine(
            one, two, get_synastry_aspects(one["planet_positions"], two["planet_positions"]))
        for key in indices:
            indices[key].append(engine["indices"][key])
        labels = engine["relationship_classifier"]
        labels = labels if isinstance(labels, list) else [labels]
        if len(labels) > 1:
            multiple += 1
        for label in labels:
            classifiers[label] = classifiers.get(label, 0) + 1
        if (n + 1) % 200 == 0:
            print(f"  …{n + 1}", file=sys.stderr)

    def percentiles(values):
        ordered = sorted(values)
        def at(p):
            return round(ordered[min(len(ordered) - 1, int(len(ordered) * p / 100))], 1)
        return {"min": round(ordered[0], 1), "p10": at(10), "p25": at(25),
                "median": at(50), "p75": at(75), "p90": at(90), "p95": at(95),
                "p99": at(99), "max": round(ordered[-1], 1),
                "mean": round(statistics.mean(ordered), 1)}

    report = {"pairs": count,
              "indices": {k: percentiles(v) for k, v in indices.items()},
              "classifier_counts": dict(sorted(classifiers.items(), key=lambda kv: -kv[1]))}

    out = pathlib.Path(__file__).parent / "distribution.json"
    out.write_text(json.dumps(report, indent=2))

    print(f"\n{count} fictional pairs\n")
    head = f"{'index':<12}" + "".join(f"{c:>8}" for c in
                                      ("min", "p10", "p25", "med", "p75", "p90", "p95", "p99", "max"))
    print(head)
    print("-" * len(head))
    for name, stats in report["indices"].items():
        print(f"{name:<12}" + "".join(f"{stats[k]:>8}" for k in
              ("min", "p10", "p25", "median", "p75", "p90", "p95", "p99", "max")))
    print(f"\npairs matching more than one description: {multiple / count:.1%}")
    print("\nclassifier (every match kept):")
    for label, hits in report["classifier_counts"].items():
        print(f"  {hits / count:>6.1%}  {label}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
