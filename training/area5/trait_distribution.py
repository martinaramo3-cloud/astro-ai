"""Calibrate the trait engine, and decide whether it may go live.

Two gates, both Martina's, and the engine stays dark unless both pass:

  no trait ranks first for more than half of charts
  three different charts get answers that are not interchangeable

The first is the failure that put 95.8% of couples in "toxic attraction" and
that made one earning route win 46% of charts. The second is the one this
question actually suffers from: every answer defaulting to taste, standards
and judgment, whoever asked.

Every chart is invented: random dates, times and cities.

    ./venv/bin/python training/area5/trait_distribution.py [charts]
"""
from __future__ import annotations

import collections
import itertools
import json
import os
import pathlib
import random
import statistics
import sys
import tempfile

os.environ.setdefault("DATABASE_PATH", os.path.join(tempfile.mkdtemp(), "d.db"))
ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "training" / "area3"))

from route_distribution import a_chart  # noqa: E402

from app.trait_profile_service import (  # noqa: E402
    FAMILIES, build_trait_reading, score_traits,
)

CEILING = 0.50   # no trait may rank first for more than half of charts


def build_distributions(count: int, rng: random.Random) -> None:
    """Each trait's own loudness spread, for the reason every other ranking in
    this codebase has one: the sources are not equally available to them. Only
    one planet can rule the chart."""
    spread: dict[str, list[float]] = collections.defaultdict(list)
    for _ in range(count):
        scored = score_traits(a_chart(rng))
        if not scored.get("available"):
            continue
        for trait in scored["traits"]:
            spread[trait["key"]].append(trait["score"])
    for key in spread:
        spread[key].sort()
    (ROOT / "content" / "engine" / "trait_bands.json").write_text(
        json.dumps(dict(spread)) + "\n")


def main(count: int = 1000) -> None:
    build_distributions(count, random.Random(20260925))

    rng = random.Random(20260927)
    first_strength = collections.Counter()
    first_weakness = collections.Counter()
    appears = collections.Counter()
    paired = []
    families_per_answer = []
    readings = []

    for _ in range(count):
        reading = build_trait_reading(a_chart(rng))
        if not reading.get("available"):
            continue
        readings.append(reading)
        if reading["strengths"]:
            first_strength[reading["strengths"][0]["family"]] += 1
        if reading["weaknesses"]:
            first_weakness[reading["weaknesses"][0]["family"]] += 1
        for trait in reading["strengths"] + reading["weaknesses"]:
            appears[trait["family"]] += 1
        paired.append(len(reading["paired"]))
        families_per_answer.append(
            len({t["family"] for t in reading["strengths"]})
            + len({t["family"] for t in reading["weaknesses"]}))

    total = len(readings) or 1
    families = sorted({shape["family"] for shape in FAMILIES.values()})
    even = 1 / len(families)

    print(f"{count} invented charts\n")
    print(f"  RANKS FIRST AS A STRENGTH   (even is {even:.0%}; gate is {CEILING:.0%})")
    worst_strength = _table(first_strength, total)
    print(f"\n  RANKS FIRST AS A WEAKNESS   (even is {even:.0%}; gate is {CEILING:.0%})")
    worst_weakness = _table(first_weakness, total)

    print("\n  APPEARS ANYWHERE IN AN ANSWER")
    for family in families:
        print(f"    {family:<16} {appears[family] / total:>6.1%}")

    print("\n  DISTINCTNESS")
    print(f"    six different families per answer: "
          f"{sum(1 for n in families_per_answer if n == 6) / total:>6.1%}")
    print(f"    strength/weakness pairs found:     "
          f"{statistics.mean(paired):.2f} per answer "
          f"(0 is a valid answer — nothing forced)")

    # Gate 2: are three charts actually different from each other?
    print("\n  ARE DIFFERENT CHARTS DIFFERENT?")
    sample = readings[:3]
    for number, reading in enumerate(sample, start=1):
        print(f"    chart {number}: strengths {[t['family'] for t in reading['strengths']]}"
              f"  weaknesses {[t['family'] for t in reading['weaknesses']]}")
    overlaps = []
    for one, two in itertools.combinations(sample, 2):
        shared = len({t["family"] for t in one["strengths"]}
                     & {t["family"] for t in two["strengths"]})
        overlaps.append(shared)
    identical = sum(1 for one, two in itertools.combinations(readings[:200], 2)
                    if [t["family"] for t in one["strengths"]]
                    == [t["family"] for t in two["strengths"]])
    pairs = len(list(itertools.combinations(readings[:200], 2))) or 1
    print(f"    the three sampled share at most {max(overlaps) if overlaps else 0}/3 strengths")
    print(f"    identical strength trios across 200 charts: {identical / pairs:.1%}")

    passes = (worst_strength <= CEILING and worst_weakness <= CEILING
              and (max(overlaps) if overlaps else 0) < 3)
    print(f"\n  GATE: {'PASSES — may go live' if passes else 'FAILS — stays dark'}")
    print(f"    loudest first-strength {worst_strength:.1%}, "
          f"loudest first-weakness {worst_weakness:.1%}")

    (HERE / "trait_distribution.json").write_text(json.dumps({
        "charts": count,
        "first_strength": {f: first_strength[f] / total for f in families},
        "first_weakness": {f: first_weakness[f] / total for f in families},
        "identical_trios": identical / pairs,
        "passes": passes,
    }, indent=1) + "\n")
    return passes


def _table(counter, total) -> float:
    worst = 0.0
    for family, number in counter.most_common():
        share = number / total
        worst = max(worst, share)
        flag = "   ← OVER THE GATE" if share > CEILING else ""
        print(f"    {family:<16} {share:>6.1%}  {'█' * round(share * 40)}{flag}")
    return worst


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
