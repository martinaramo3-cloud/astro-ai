"""A calculation-backed relocation report that cannot lose the ranked cities.

Source labels are carried by each section and inherited by its contents.
There is no language-model fallback to substitute unrelated natal transits.
"""
from datetime import datetime
import re

from app.relocation_service import choose_return_year, rank_places_for, _sun_longitude
from app.chart_analysis_service import get_house_rulers

FAILURE = "The solar-return city calculation didn't complete, so I can't reliably rank the locations. Please try the same request again. I won't substitute a natal-transit reading for that calculation."


def _condition(value):
    return {"domicile": "traditionally considered comfortable in this sign",
            "exaltation": "traditionally considered well-supported in this sign",
            "detriment": "traditionally interpreted as requiring more adjustment",
            "fall": "traditionally interpreted as harder to express smoothly"}.get(value, "no special sign-strength classification")


def _angle(point):
    return f"{point['degree_in_sign']:.2f}° {point['sign']}"


def render_relocation(result: dict) -> str:
    if result['status'] not in ('ok', 'partial'):
        return result.get('message', FAILURE)
    best = result['best']
    first = best[0]
    tied = len([c for c in best if c['score'] == first['score']]) > 1
    lines = [f"I calculated your {result['year']} solar return for {result['calculated']} of {result['searched']} candidate cities in {"Europe" if result['region'] == "europe" else "the worldwide catalogue"}. {first['place']} {'ties for first' if tied else 'ranks first'} under this {result['purpose']} scoring model.",
        "A solar return is the instant the Sun reaches the position it had at your birth. It is the same instant worldwide. Changing city changes the chart's houses (sections associated with areas of life) and angles, not the planets' zodiac positions or their relationships to each other.",
        "Scores are comparison points from a draft astrology model, not percentages or predictions of earnings. Small differences and ties should not be treated as decisive reasons to travel.",
        "How to read the ranking: the Ascendant (ASC) is the rising point, associated with how you approach the year. The Midheaven (MC) is associated with work and public reputation. Jupiter represents growth; Venus represents values and cooperation; Saturn represents limits, responsibility and sustained effort. A planet close to an angle gets more emphasis, which does not automatically make it helpful.",
        "The 2nd house concerns personal income, the 8th shared money and funding, the 10th career, and the 11th gains and networks. A house ruler is the planet assigned to the sign at the start of that house. Its position links those two areas. For example, the income ruler in the career house connects earnings with work; it does not promise a pay rise."]
    lines.append("Mercury represents thinking and communication, the Moon feelings and familiar needs, and the Sun identity and direction. Traditional planet-in-sign classifications describe how easily those themes are expressed within astrology; they are not judgments about your ability. House numbers below refer to chart sections, and degrees measure position, not score.")
    if result['failed_candidates']:
        lines.append(f"{len(result['failed_candidates'])} candidate calculations failed and were excluded. This ranking covers only the successfully calculated cities.")
    for city in best:
        pathways = city['pathway_scores']
        strongest = max(pathways, key=pathways.get)
        conditions = []
        for planet in city['planet_conditions']:
            near = ', '.join(f"{a['angle']} ({a['orb']:.2f}° away)" for a in planet['angularity']) or 'no angle within 5°'
            conditions.append(f"{planet['planet']}: house {planet['house']}; {near}")
        rulers = '; '.join(f"{r['house']}H {r['cusp_sign']} → {r['ruler']} in house {r['ruler_in_house']}" for r in city['house_rulers'] if r['house'] in (2, 8, 10, 11))
        saturn = next(p for p in city['planet_conditions'] if p['planet'] == 'Saturn')
        aspects = '; '.join(f"{a['planet_1']} {a['aspect']} {a['planet_2']} ({a['orb']:.2f}° from exact)" for a in saturn['aspects'][:2]) or 'no major planetary aspects within the configured range'
        advantages = '; '.join(city['advantages'][:2]) or 'No positive scored factor; this is a relative ranking only.'
        downside = '; '.join(city['tradeoffs'][:2]) or 'No negative factor in this scoring model; that does not mean there is no risk.'
        lines.append(f"#{city['rank']} {city['place']} — {city['score']:g} points\n"
                     f"Strongest scored area: {strongest}.\n"
                     f"ASC: {_angle(city['ascendant'])}; MC: {_angle(city['midheaven'])}.\n"
                     + '\n'.join(conditions) + '\n'
                     f"Financial house rulers: {rulers}.\n"
                     f"Saturn: {saturn['sign']} ({_condition(saturn['dignity'])}); rules houses {', '.join(map(str, saturn['rules_houses'])) or 'none'}; {aspects}.\n"
                     f"Main advantages: {advantages}\nMain downside: {downside}\n"
                     f"Exact local return: {city['be_there_at']} ({city['timezone']}).")
    lines.append("In the details above, a conjunction means two points are close together; a trine or sextile is traditionally read as cooperation, while a square or opposition is read as tension. For Saturn, this is about how responsibilities and limits interact with the other planet. A positive or negative point adjustment is the model's interpretation, not an event it knows will happen.")
    if result['best_by_financial_pathway']:
        lines.append('Best by financial area (comparing house occupants and rulers):\n' + '\n'.join(
            f"- {name}: {', '.join(info['places'][:3])}" + (f" and {len(info['places'])-3} other tied cities" if len(info['places'])>3 else '')
            for name, info in result['best_by_financial_pathway'].items()))
    lines.append(f"For the overall top-ranked option, be physically in {first['place']} at {first['be_there_at']} ({first['timezone']}). Aim to arrive by {first['arrive_by']}; the one-hour buffer is practical advice, not an astrological requirement. Both latitude and longitude were used, so being in the same time zone is not enough.")
    return '\n\n'.join(lines)


def prepare_relocation(question: str, birth_date: str, natal: dict, request: dict) -> tuple[dict, str]:
    natal_context = {'source': 'natal', 'house_system': 'Placidus', 'rulership_system': 'traditional',
                     'house_rulers': get_house_rulers(natal['houses'], natal['planet_positions'])}
    if not natal['birth_time_known']:
        result = {'source': 'relocated_solar_return', 'status': 'needs_birth_time', 'best': [],
                  'message': "I need your birth time to calculate an accurate solar-return instant and rank the cities. Your profile marks it as unknown. Add the time if you know it; I won't give precise relocated angles from an assumed birth time."}
        return {'where_to_be': result, 'natal': natal_context}, result['message']
    years = set(re.findall(r'\b(?:19|20|21)\d{2}\b', question))
    if len(years) > 1:
        result = {'source': 'relocated_solar_return', 'status': 'needs_year', 'best': [],
                  'message': 'Which solar-return year should I compare? Your question contains more than one year.'}
        return {'where_to_be': result, 'natal': natal_context}, result['message']
    born = datetime.fromisoformat(birth_date)
    try:
        # Do not use the two-decimal display longitude to time an exact return.
        sun = _sun_longitude(datetime.fromisoformat(natal['utc_birth_time']))
        year = choose_return_year(sun, born.month, born.day, int(next(iter(years))) if years else None)
        count_match = re.search(r'\b(?:top|best|rank)\s+(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?', question, re.I)
        count = max(1, min(10, int(count_match.group(2) or count_match.group(1)))) if count_match else 7
        result = rank_places_for(sun, year, born.month, born.day, purpose=request['purpose'],
                                 region=request['region'], top=count, natal_planets=natal['planet_positions'])
    except Exception as exc:
        # Keep the internal cause in server logs, never silently lose the result.
        print('Relocation search failed:', type(exc).__name__)
        result = {'source': 'relocated_solar_return', 'status': 'failed', 'best': [], 'message': FAILURE}
    context = {'where_to_be': result, 'natal': natal_context,
               'techniques': {'solar_return': 'fixed return planets and mutual aspects',
                              'relocated_solar_return': 'city-specific houses, angles and rulerships',
                              'natal': 'birth-chart reference only; not return-house rulers'},
               'natal_transits': {'source': 'transit_to_natal', 'included': False,
                                  'reason': 'Not substituted for a solar-return ranking.'}}
    return context, render_relocation(result)
