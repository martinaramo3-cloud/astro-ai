"""A calculation-backed relocation report that cannot lose the ranked cities.

Source labels are carried by each section and inherited by its contents.
There is no language-model fallback to substitute unrelated natal transits.
"""
from datetime import datetime
import re

from app.relocation_service import choose_return_year, rank_places_for, rank_places_to_live, _sun_longitude
from app.chart_analysis_service import get_house_rulers

FAILURE = "The solar-return city calculation didn't complete, so I can't reliably rank the locations. Please try the same request again. I won't substitute a natal-transit reading for that calculation."


def _condition(value):
    return {"domicile": "traditionally considered comfortable in this sign",
            "exaltation": "traditionally considered well-supported in this sign",
            "detriment": "traditionally interpreted as requiring more adjustment",
            "fall": "traditionally interpreted as harder to express smoothly"}.get(value, "no special sign-strength classification")


def _angle(point):
    return f"{point['degree_in_sign']:.2f}° {point['sign']}"


def render_relocation(result: dict, technical: bool = False) -> str:
    if result['status'] not in ('ok', 'partial'):
        return result.get('message', FAILURE)
    best = result['best']
    first = best[0]
    tied = sum(c['score'] == first['score'] for c in best) > 1
    lines = [f"{first['place']} {'ties for first' if tied else 'ranks first'} among the {result['calculated']} locations calculated for your {result['year']} birthday, using this {result['purpose']} comparison. These scores are an astrological interpretation, not a prediction of financial results; small differences are not a strong reason to travel."]
    if result['failed_candidates']:
        lines.append(f"{len(result['failed_candidates'])} locations could not be calculated and are excluded.")
    for city in best:
        strongest = max(city['pathway_scores'], key=city['pathway_scores'].get)
        description = f"#{city['rank']} {city['place']} — {city['score']:g} points\nStrongest scored area: {strongest}."
        if technical:
            advantages = '; '.join(city['advantages'][:1]) or 'No positive scored factor.'
            tradeoff = '; '.join(city['tradeoffs'][:1]) or 'No negative scored factor.'
            description += f"\nSupporting factor: {advantages}\nTradeoff: {tradeoff}"
        description += f"\nExact local return: {city['be_there_at']} ({city['timezone']})."
        lines.append(description)
    lines.append(f"For the top option, be physically in {first['place']} at {first['be_there_at']} ({first['timezone']}). Aim to arrive by {first['arrive_by']} for a practical buffer. Being elsewhere in the same time zone is not enough: the calculation uses the city's coordinates.")
    return '\n\n'.join(lines)


def render_places_to_live(result: dict) -> str:
    if result['status'] not in ('ok', 'partial'):
        return result.get('message', FAILURE)
    best = result['best']
    first = best[0]
    tied = sum(c['score'] == first['score'] for c in best) > 1
    lines = [
        f"{first['place']} {'ties for first' if tied else 'comes out first'} of the "
        f"{result['calculated']} places compared for living, on a {result['purpose']} reading. "
        f"{result['does_location_matter']}. This is how each city's chart sits for you if "
        f"you lived there — an astrological comparison, not a forecast of how life would go."
    ]
    for city in best:
        strongest = max(city['pathway_scores'], key=city['pathway_scores'].get)
        reason = (city['advantages'] or ['No single standout factor.'])[0]
        lines.append(f"#{city['rank']} {city['place']} — strongest for {strongest}. {reason}")
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

    if request.get('technique') == 'relocated_natal':
        # Where to live. No year, no return instant, no arrival time — the
        # chart is their own birth moment seen from somewhere else.
        try:
            count_match = re.search(r'\b(?:top|best|rank)\s+(\d{1,2})', question, re.I)
            count = max(1, min(10, int(count_match.group(1)))) if count_match else 7
            result = rank_places_to_live(
                datetime.fromisoformat(natal['utc_birth_time']),
                purpose=request['purpose'], region=request['region'], top=count,
                natal_planets=natal['planet_positions'])
        except Exception as exc:
            print('Relocation search failed:', type(exc).__name__)
            result = {'source': 'relocated_natal', 'status': 'failed', 'best': [], 'message': FAILURE}
        context = {'where_to_live': result, 'natal': natal_context,
                   'techniques': {'relocated_natal': 'the birth chart seen from another place: same planets, different houses and angles'},
                   'natal_transits': {'source': 'transit_to_natal', 'included': False,
                                      'reason': 'Not substituted for a relocation ranking.'}}
        return context, render_places_to_live(result)

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
    from app.conversation_service import astrology_requested
    return context, render_relocation(result, technical=astrology_requested(question))
