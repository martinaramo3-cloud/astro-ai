"""Score a thousand invented charts against the earning-route framework.

The question this answers: does any one route win for almost everybody? That
is the failure that put 95.8% of couples in "toxic attraction" — thresholds
and weights written for a scale nobody had measured. Six routes over a large
random sample should land somewhere near even; a route at 60% is not a
reading, it is a default.

It also reports the three numbers that are mine rather than the co-founder's,
so they can be set from data:

  how often a close 2nd-ruler / 10th-ruler link actually fires
  what the tenancy cap does to the spread
  the gap between first and second place, which decides "complementary"

Every person here is invented: random dates, times and cities.

    ./venv/bin/python training/area3/route_distribution.py [charts]
"""
from __future__ import annotations

import collections
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
from app.earning_routes_service import (  # noqa: E402
    ROUTES, score_earning_routes,
)

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
        "_born": born.isoformat(timespec="minutes"),
        "_where": zone,
    }


def build_distributions(count: int, rng: random.Random) -> dict:
    """Each route's own score spread, which is what ranking compares against.

    Written before anything is ranked, because the ranking reads this file.
    Her weights are untouched — this only makes one route's 14 comparable
    with another's.
    """
    from app.earning_routes_service import _evidence_for, _facts, _score
    spread: dict[str, list[int]] = {key: [] for key in ROUTES}
    for _ in range(count):
        facts = _facts(a_chart(rng))
        if facts is None:
            continue
        for key in ROUTES:
            spread[key].append(_score(_evidence_for(key, facts)))
    for key in spread:
        spread[key].sort()
    (ROOT / "content" / "engine" / "earning_route_bands.json").write_text(
        json.dumps(spread) + "\n")
    return spread


def main(count: int = 1000) -> None:
    # Two independent samples: one to measure the spread, one to test the
    # ranking that uses it. Measuring and testing on the same charts would
    # flatter the result.
    build_distributions(count, random.Random(20260924))
    rng = random.Random(20260925)
    first = collections.Counter()
    top_three = collections.Counter()
    strong = collections.Counter()
    scores = collections.defaultdict(list)
    gaps, confidences, links, complementary = [], collections.Counter(), 0, 0
    dimension_leans = collections.defaultdict(collections.Counter)

    for _ in range(count):
        result = score_earning_routes(a_chart(rng))
        if not result["available"]:
            continue
        ranked = result["ranking"]
        if ranked:
            first[ranked[0]["key"]] += 1
            for route in ranked:
                top_three[route["key"]] += 1
        for route in result["all_routes"]:
            scores[route["key"]].append(route["score"])
            if route["strong"]:
                strong[route["key"]] += 1
        if len(ranked) >= 2:
            # The gap that decides "complementary" is the one ranking uses,
            # which is the percentile and not the raw score. Reporting the raw
            # gap here gave a negative lower quartile, because first place can
            # legitimately carry the smaller raw number.
            gaps.append(round(ranked[0]["how_unusual"] - ranked[1]["how_unusual"], 3))
        confidences[result["confidence"].split(" —")[0]] += 1
        complementary += bool(result["complementary"])
        if result["traced_from"]["money_ruler_meets_career_ruler"]:
            links += 1
        for name, reading in result["dimensions"].items():
            dimension_leans[name][reading["reads_as"]] += 1

    print(f"{count} invented charts\n")
    print("  RANKS FIRST  (even would be 17% each; anything near 50% is a default,")
    print("               not a reading)\n")
    for key, _ in first.most_common():
        share = first[key] / count
        bar = "█" * round(share * 40)
        print(f"    {ROUTES[key]['label']:<44} {share:>5.1%}  {bar}")
    missing = [k for k in ROUTES if k not in first]
    for key in missing:
        print(f"    {ROUTES[key]['label']:<44}  0.0%   ← never wins")

    print("\n  REACHES THE TOP THREE")
    for key in ROUTES:
        print(f"    {ROUTES[key]['label']:<44} {top_three[key] / count:>5.1%}")

    print("\n  CALLED STRONG  (two independent signals, one on the money house)")
    for key in ROUTES:
        print(f"    {ROUTES[key]['label']:<44} {strong[key] / count:>5.1%}")

    print("\n  SCORE SPREAD")
    for key in ROUTES:
        values = sorted(scores[key])
        print(f"    {ROUTES[key]['label']:<44} "
              f"median {statistics.median(values):>4.1f}   max {values[-1]:>3}")

    print("\n  THE NUMBERS THAT ARE MINE, NOT HERS")
    print(f"    a close money-ruler / career-ruler link fires in   {links / count:>5.1%}")
    print(f"    top two within the complementary gap               {complementary / count:>5.1%}")
    if gaps:
        gaps.sort()
        print(f"    percentile gap, 1st to 2nd: median {statistics.median(gaps):.3f}, "
              f"lower quartile {gaps[len(gaps) // 4]:.3f}")

    print("\n  CONFIDENCE")
    for level, number in confidences.most_common():
        print(f"    {level:<44} {number / count:>5.1%}")

    print("\n  DIMENSIONS")
    for name, counts in dimension_leans.items():
        total = sum(counts.values())
        parts = "   ".join(f"{reading[:34]} {n / total:.0%}"
                           for reading, n in counts.most_common())
        print(f"    {name:<20} {parts}")

    report = {
        "charts": count,
        "ranks_first": {k: first[k] / count for k in ROUTES},
        "reaches_top_three": {k: top_three[k] / count for k in ROUTES},
        "called_strong": {k: strong[k] / count for k in ROUTES},
        "median_score": {k: statistics.median(scores[k]) for k in ROUTES},
        "close_link_fires": links / count,
        "complementary": complementary / count,
        "gap_median": statistics.median(gaps) if gaps else None,
        "confidence": {k: v / count for k, v in confidences.items()},
    }
    (pathlib.Path(__file__).resolve().parent / "route_distribution.json").write_text(
        json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
