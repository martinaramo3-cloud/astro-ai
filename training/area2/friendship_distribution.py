"""Percentiles for the friendship score, so its bands come from data too.

Same method as the four existing indices: score a thousand fictional pairs and
cut the bands at the 25th, 75th and 90th percentiles. Otherwise "high
friendship" is a number I picked.
"""
from __future__ import annotations

import json, os, pathlib, random, statistics, sys, tempfile
from datetime import datetime, timedelta

os.environ.setdefault("DATABASE_PATH", os.path.join(tempfile.mkdtemp(), "f.db"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import pytz  # noqa: E402
from app.astrology_engine import (  # noqa: E402
    add_house_to_planets, get_houses_and_ascendant, get_planet_positions_from_utc)
from app.compatibility_service import get_synastry_aspects  # noqa: E402
from app.friendship_service import score_friendship  # noqa: E402

CITIES = [(42.70, 23.32, "Europe/Sofia"), (45.46, 9.19, "Europe/Rome"),
          (51.51, -0.13, "Europe/London"), (40.71, -74.01, "America/New_York"),
          (-23.55, -46.63, "America/Sao_Paulo"), (35.68, 139.69, "Asia/Tokyo"),
          (-33.87, 151.21, "Australia/Sydney"), (19.08, 72.88, "Asia/Kolkata")]


def a_chart(rng):
    lat, lon, zone = rng.choice(CITIES)
    born = datetime(1985, 1, 1) + timedelta(days=rng.randrange(0, 365 * 25),
                                            minutes=rng.randrange(0, 1440))
    utc = pytz.timezone(zone).localize(born).astimezone(pytz.utc)
    planets = get_planet_positions_from_utc(utc)
    houses = get_houses_and_ascendant(utc, lat, lon)
    return {"planet_positions": add_house_to_planets(planets, houses["houses"]),
            "houses": houses["houses"]}


def main(count=1000):
    rng = random.Random(20260924)
    overall, per_dimension = [], {}
    for n in range(count):
        one, two = a_chart(rng), a_chart(rng)
        result = score_friendship(one, two,
                                  get_synastry_aspects(one["planet_positions"],
                                                       two["planet_positions"]))
        overall.append(result["friendship_score"])
        for name, d in result["dimensions"].items():
            per_dimension.setdefault(name, []).append(d["score"])
        if (n + 1) % 250 == 0:
            print(f"  …{n+1}", file=sys.stderr)

    def pct(values):
        s = sorted(values)
        at = lambda p: round(s[min(len(s) - 1, int(len(s) * p / 100))], 2)
        return {"min": round(s[0], 2), "p25": at(25), "median": at(50),
                "p75": at(75), "p90": at(90), "max": round(s[-1], 2),
                "mean": round(statistics.mean(s), 2)}

    report = {"pairs": count, "friendship_score": pct(overall),
              "dimensions": {k: pct(v) for k, v in per_dimension.items()}}
    pathlib.Path(__file__).parent.joinpath("friendship_distribution.json").write_text(
        json.dumps(report, indent=2))

    head = f"{'':<22}" + "".join(f"{c:>9}" for c in ("min", "p25", "med", "p75", "p90", "max"))
    print(f"\n{count} fictional pairs\n"); print(head); print("-" * len(head))
    row = lambda name, s: print(f"{name:<22}" + "".join(
        f"{s[k]:>9}" for k in ("min", "p25", "median", "p75", "p90", "max")))
    row("FRIENDSHIP", report["friendship_score"])
    print()
    for name, s in report["dimensions"].items():
        row(name, s)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
