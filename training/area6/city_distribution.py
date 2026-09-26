"""Does one city win for everybody? The gate that decides whether this ships.

If the same place comes first for most charts, the ranking is a property of
the scoring tables rather than of the person asking — which is the failure
that put 95.8% of couples in "toxic attraction" and made one earning route win
46% of charts. Here it would be worse, because a city name sounds like an
answer: nobody reading "Lisbon" thinks to ask whether Lisbon is simply what
the engine always says.

Checked three ways, because a city can hide as a type:
  which CITY comes first
  which REGION comes first
  whether "best for career" differs from "best overall" on the same chart

Every chart is invented: random dates, times and cities of birth.

    ./venv/bin/python training/area6/city_distribution.py [charts]
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import random
import sys
import tempfile

os.environ.setdefault("DATABASE_PATH", os.path.join(tempfile.mkdtemp(), "d.db"))
ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "training" / "area3"))

from route_distribution import a_chart  # noqa: E402

from app.european_cities import as_places  # noqa: E402
from app.relocation_compare_service import AREAS, EQUAL, compare_places  # noqa: E402

CEILING = 0.50


def _region(place: dict, by_label: dict) -> str:
    zone = by_label.get(place, "")
    return zone.split("/")[0] if zone else "?"


def main(count: int = 1000) -> None:
    places = as_places("world")
    by_label = {p["label"]: p["timezone"] for p in places}
    # A shortlist keeps the run tractable: 157 cities x 1000 charts x 7 tables
    # is not a calibration, it is a weekend. Forty spread across every region
    # answers the question this gate asks.
    rng = random.Random(20260928)
    shortlist = rng.sample(places, 40)

    first_city = collections.Counter()
    first_region = collections.Counter()
    career_differs = 0
    love_differs = 0
    usable = 0

    charts = random.Random(20260929)
    for _ in range(count):
        natal = _natal(a_chart(charts))
        if not natal:
            continue
        result = compare_places(natal, places=shortlist, weighting=EQUAL)
        if result.get("status") != "ok":
            continue
        usable += 1
        leader = result["ranked"][0]["place"]
        first_city[leader] += 1
        first_region[_region(leader, by_label)] += 1
        # "Best for career" and "best overall" must be able to differ.
        best_career = max(result["ranked"], key=lambda c: c["area_rank"]["career"])
        best_love = max(result["ranked"], key=lambda c: c["area_rank"]["love"])
        career_differs += best_career["place"] != leader
        love_differs += best_love["place"] != leader

    total = usable or 1
    print(f"{usable} invented charts, {len(shortlist)} cities each\n")

    print(f"  WHICH CITY COMES FIRST   (gate: no city over {CEILING:.0%})")
    worst_city = _table(first_city, total, 8)
    print(f"\n  WHICH REGION COMES FIRST (gate: no region over {CEILING:.0%})")
    worst_region = _table(first_region, total, 8)

    print("\n  DO THE AREAS DISAGREE WITH THE OVERALL?")
    print(f"    best for career is a different city   {career_differs / total:>6.1%}")
    print(f"    best for love is a different city     {love_differs / total:>6.1%}")
    print(f"    distinct cities that ever come first  {len(first_city)}")

    passes = (worst_city <= CEILING and worst_region <= CEILING
              and career_differs / total > 0.2)
    print(f"\n  GATE: {'PASSES — may go live' if passes else 'FAILS — stays dark'}")
    print(f"    loudest city {worst_city:.1%}, loudest region {worst_region:.1%}")

    (HERE / "city_distribution.json").write_text(json.dumps({
        "charts": usable, "cities_per_chart": len(shortlist),
        "first_city": {c: n / total for c, n in first_city.most_common()},
        "first_region": {r: n / total for r, n in first_region.most_common()},
        "career_differs_from_overall": career_differs / total,
        "love_differs_from_overall": love_differs / total,
        "distinct_leaders": len(first_city),
        "passes": passes,
    }, indent=1) + "\n")


def _natal(chart: dict) -> dict | None:
    """The calibration charts come as relocation candidates; this engine wants
    a natal record with a birth moment."""
    from datetime import datetime
    born = chart.get("_born")
    if not born:
        return None
    return {
        "utc_birth_time": datetime.fromisoformat(born).isoformat(),
        "planet_positions": chart["planet_positions"],
        "houses": chart["houses"],
        "birth_time_known": True,
    }


def _table(counter, total, limit) -> float:
    worst = 0.0
    for name, number in counter.most_common(limit):
        share = number / total
        worst = max(worst, share)
        flag = "   ← OVER THE GATE" if share > CEILING else ""
        print(f"    {name[:34]:<36} {share:>6.1%}  {'█' * round(share * 40)}{flag}")
    if len(counter) > limit:
        print(f"    … and {len(counter) - limit} more")
    return worst


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
