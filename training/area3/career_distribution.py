"""Calibrate both career rankings, and the timing choice, over 1,000 charts.

Three questions, all of them the same question in different clothes: does
anything here win for almost everybody? A theme, a route, or a timing window
that comes first half the time is a default rather than a reading, and that is
the failure that once put 95.8% of couples in "toxic attraction".

The timing check is the new one. Every career answer in testing opened with
the top entry of a two-year list, four answers running. So this also reports
how often the SAME window would be chosen for two different question types on
the same chart — which is the number that says whether the fix worked.

Every chart is invented: random dates, times and cities.

    ./venv/bin/python training/area3/career_distribution.py [charts]
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

os.environ.setdefault("DATABASE_PATH", os.path.join(tempfile.mkdtemp(), "d.db"))
ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from route_distribution import a_chart  # noqa: E402

from app.career_reading_service import build_career_reading  # noqa: E402
from app.chart_analysis_service import get_house_rulers  # noqa: E402
from app.earning_routes_service import ROUTES  # noqa: E402
from app.professional_themes_service import (  # noqa: E402
    THEMES, _score as theme_score, score_professional_themes,
)
from app.transit_timing_service import build_predictive_timeline  # noqa: E402

QUESTIONS = {
    "suitable_work": "What career suits me?",
    "how_they_earn": "How am I most likely to make money according to my chart?",
    "career_timing": "When is a good time to change jobs?",
    "a_specific_choice": "Should I take the offer or stay where I am?",
}


def timeline_for(chart: dict) -> dict:
    rules: dict[str, list[int]] = {}
    for record in get_house_rulers(chart["houses"], chart["planet_positions"]):
        rules.setdefault(record["ruler"], []).append(record["house"])
    return build_predictive_timeline(
        chart["planet_positions"] + (chart.get("angles") or []),
        question_type="career", rules_by_point=rules, limit=14)


def build_theme_distributions(count: int, rng: random.Random) -> None:
    """Each theme's own score spread, for the same reason the routes have one.

    The vocabulary is ten planets and the evidence is not evenly available to
    them: only one planet can rule the career point. Without this, that planet
    wins nearly every chart.
    """
    spread: dict[str, list[float]] = {planet: [] for planet in THEMES}
    for _ in range(count):
        result = score_professional_themes(a_chart(rng))
        if not result["available"]:
            continue
        for theme in result["all_themes"]:
            spread[theme["key"]].append(theme["score"])
    for planet in spread:
        spread[planet].sort()
    (ROOT / "content" / "engine" / "theme_bands.json").write_text(
        json.dumps(spread) + "\n")


def main(count: int = 1000) -> None:
    build_theme_distributions(count, random.Random(20260924))

    rng = random.Random(20260926)
    theme_first = collections.Counter()
    route_first = collections.Counter()
    theme_strong = collections.Counter()
    types_seen = collections.Counter()
    confidence = collections.defaultdict(collections.Counter)
    unclear = collections.Counter()
    same_window_across_types = 0
    charts_with_windows = 0
    window_leads = collections.Counter()
    activation = []

    for _ in range(count):
        chart = a_chart(rng)
        timeline = timeline_for(chart)
        chosen_per_type = {}
        for question_type, question in QUESTIONS.items():
            reading = build_career_reading(
                chart, question, timeline=timeline, birth_date=chart["_born"][:10])
            if not reading["available"]:
                continue
            types_seen[reading["question_type"]] += 1
            confidence[reading["question_type"]][
                reading["confidence"].split(" —")[0]] += 1
            timing = reading["timing"]
            if timing.get("timing_is_unclear"):
                unclear[reading["question_type"]] += 1
            if timing.get("windows"):
                top = timing["windows"][0]
                chosen_per_type[reading["question_type"]] = top["transit"]
                activation.append(top["activation"])
                if reading["question_type"] == "career_timing":
                    window_leads[top["transit"].split(" ")[0]] += 1
            if reading["question_type"] == "suitable_work":
                for theme in reading["professional_themes"]["themes"]:
                    if theme is reading["professional_themes"]["themes"][0]:
                        theme_first[theme["key"]] += 1
                    if theme["strong"]:
                        theme_strong[theme["key"]] += 1
            if reading["question_type"] == "how_they_earn":
                ranked = reading["earning_routes"]["ranking"]
                if ranked:
                    route_first[ranked[0]["key"]] += 1

        if len(chosen_per_type) >= 2:
            charts_with_windows += 1
            if len(set(chosen_per_type.values())) == 1:
                same_window_across_types += 1

    print(f"{count} invented charts\n")

    print("  PROFESSIONAL THEME RANKING FIRST  (even is 10%; flag over 50%)")
    total_themes = sum(theme_first.values()) or 1
    for planet, number in theme_first.most_common():
        share = number / total_themes
        flag = "   ← OVER 50%" if share > 0.5 else ""
        print(f"    {THEMES[planet]['label']:<46} {share:>5.1%}"
              f"  {'█' * round(share * 40)}{flag}")
    for planet in THEMES:
        if planet not in theme_first:
            print(f"    {THEMES[planet]['label']:<46}  0.0%   ← never first")

    print("\n  EARNING ROUTE RANKING FIRST  (even is 16.7%; flag over 50%)")
    total_routes = sum(route_first.values()) or 1
    for key, number in route_first.most_common():
        share = number / total_routes
        flag = "   ← OVER 50%" if share > 0.5 else ""
        print(f"    {ROUTES[key]['label'][:44]:<46} {share:>5.1%}"
              f"  {'█' * round(share * 40)}{flag}")
    for key in ROUTES:
        if key not in route_first:
            print(f"    {ROUTES[key]['label'][:44]:<46}  0.0%   ← never first")

    print("\n  TIMING: is the same window chosen whatever is asked?")
    if charts_with_windows:
        share = same_window_across_types / charts_with_windows
        print(f"    same top window for every question type  {share:>5.1%}")
        print("    (this was effectively 100% before: the answer led with the "
              "largest\n     transit in the two-year list whatever the question was)")
    if activation:
        print(f"    median activation of the chosen window   "
              f"{statistics.median(activation):.2f}")
    print("    which planet leads a timing question:")
    lead_total = sum(window_leads.values()) or 1
    for planet, number in window_leads.most_common(6):
        print(f"      {planet:<12} {number / lead_total:>5.1%}")

    print("\n  CONFIDENCE, BY QUESTION TYPE")
    for question_type in QUESTIONS:
        seen = types_seen[question_type] or 1
        parts = "  ".join(f"{level} {n / seen:.0%}"
                          for level, n in confidence[question_type].most_common())
        print(f"    {question_type:<20} {parts}")

    print("\n  TIMING CALLED UNCLEAR")
    for question_type in QUESTIONS:
        seen = types_seen[question_type] or 1
        print(f"    {question_type:<20} {unclear[question_type] / seen:>5.1%}")

    (HERE / "career_distribution.json").write_text(json.dumps({
        "charts": count,
        "theme_first": {k: theme_first[k] / total_themes for k in THEMES},
        "route_first": {k: route_first[k] / total_routes for k in ROUTES},
        "same_window_across_types": (same_window_across_types / charts_with_windows
                                     if charts_with_windows else None),
        "median_activation": statistics.median(activation) if activation else None,
    }, indent=1) + "\n")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
