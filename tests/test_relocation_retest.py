from datetime import datetime, timezone, timedelta
from copy import deepcopy

import pytest

from app.relocation_scoring import score_chart
from app.relocation_service import chart_for, rank_places_for, find_solar_return, choose_return_year, _sun_longitude
from tests.test_relocation import PLACES, BIRTH, SOFIA
from tests.conftest import SOFIA as BIRTH_INPUT


def test_house_points_are_only_given_for_the_actual_house():
    chart = {'planets': [{'planet': 'Jupiter', 'house': 12, 'degree': 100, 'sign': 'Cancer'}],
             'houses': [], 'angular_planets': []}
    absent = score_chart(chart)
    assert absent['from_houses'] == 0
    chart['planets'][0]['house'] = 2
    present = score_chart(chart)
    assert present['from_houses'] == 1.75  # 5 points * 35% income weight
    assert len(present['why']) == 1
    assert '2nd' in present['why'][0]


def test_latitude_changes_chart_at_same_longitude():
    south = chart_for(BIRTH, 40, 20)
    north = chart_for(BIRTH, 60, 20)
    assert south['ascendant'] != north['ascendant']
    assert south['houses'] != north['houses']
    assert [p['degree'] for p in south['planets']] == [p['degree'] for p in north['planets']]
    assert south['aspects'] == north['aspects']


def test_leap_day_birth_has_a_return_in_non_leap_year():
    sun = _sun_longitude(datetime(2000, 2, 29, tzinfo=timezone.utc))
    moment = find_solar_return(sun, 2027, 2, 29)
    assert abs((_sun_longitude(moment) - sun + 180) % 360 - 180) < 0.0001


def test_next_return_uses_exact_instant_not_birthday_calendar_day():
    sun = _sun_longitude(BIRTH)
    moment = find_solar_return(sun, 2027, 3, 2)
    assert choose_return_year(sun, 3, 2, now=moment-timedelta(minutes=1)) == 2027
    assert choose_return_year(sun, 3, 2, now=moment+timedelta(minutes=1)) == 2028
    assert choose_return_year(sun, 3, 2, requested_year=2029, now=moment) == 2029


def test_one_bad_city_does_not_destroy_ranking():
    places = PLACES + [{**PLACES[0], 'label': 'Invalid timezone', 'timezone': 'Not/A_Zone'}]
    result = rank_places_for(_sun_longitude(BIRTH), 2027, 3, 2, places=places)
    assert result['status'] == 'partial'
    assert result['calculated'] == 3
    assert result['failed_candidates'][0]['place'] == 'Invalid timezone'
    assert len(result['best']) == 3


def test_empty_search_is_explicit_failure():
    result = rank_places_for(_sun_longitude(BIRTH), 2027, 3, 2, places=[])
    assert result['status'] == 'failed'
    assert result['best'] == []


def test_each_local_time_is_the_same_global_instant_with_dst():
    result = rank_places_for(_sun_longitude(BIRTH), 2027, 3, 2, places=PLACES)
    instant = datetime.fromisoformat(result['returns_at_utc'])
    for city in result['best']:
        local = datetime.fromisoformat(city['be_there_at'])
        assert abs((local - instant).total_seconds()) < 1
        assert datetime.fromisoformat(city['arrive_by']) == local - timedelta(hours=1)
        assert city['source'] == 'relocated_solar_return'
    assert result['base_solar_return']['source'] == 'solar_return'
    assert all('house' not in p for p in result['base_solar_return']['planets'])


def test_house_rulers_match_actual_cusps():
    from app.content_repository import get_sign_rulers
    result = rank_places_for(_sun_longitude(BIRTH), 2027, 3, 2, places=PLACES)
    for city in result['best']:
        assert len(city['house_rulers']) == 12
        for ruler, cusp in zip(city['house_rulers'], city['houses']):
            assert ruler['house'] == cusp['house']
            assert ruler['cusp_sign'] == cusp['sign']
            assert ruler['ruler'] == get_sign_rulers()[cusp['sign']][0]
            assert ruler['ruler_in_house'] == city['houses_of'][ruler['ruler']]


def test_money_house_ruler_saturn_gets_no_automatic_angular_bonus():
    chart = {'planets': [{'planet': 'Saturn', 'house': 10, 'degree': 65, 'sign': 'Gemini'}],
             'houses': [{'house': 2, 'sign': 'Capricorn'}], 'angular_planets': []}
    ordinary = score_chart(chart)
    angular = deepcopy(chart)
    angular['angular_planets'] = [{'planet': 'Saturn', 'angle': 'Midheaven', 'orb': 0.1}]
    assert score_chart(angular)['score'] == ordinary['score']


def test_mc_sign_itself_does_not_add_points():
    chart = chart_for(BIRTH, *SOFIA)
    changed = deepcopy(chart)
    changed['midheaven']['sign'] = 'Pisces' if chart['midheaven']['sign'] != 'Pisces' else 'Aries'
    assert score_chart(changed)['score'] == score_chart(chart)['score']


@pytest.mark.parametrize('streaming', [False, True])
def test_failed_search_is_short_and_does_not_call_the_model(client, account, monkeypatch, streaming):
    import app.main as main
    import app.relocation_reading_service as reading
    monkeypatch.setattr(reading, 'rank_places_for', lambda *a, **kw: (_ for _ in ()).throw(ValueError('bad chart')))
    monkeypatch.setattr(main, 'generate_astrologer_answer', lambda *a, **kw: pytest.fail('No AI fallback'))
    user, headers = account()
    endpoint = '/ask-astrologer/stream' if streaming else '/ask-astrologer'
    response = client.post(endpoint, headers=headers, json={**BIRTH_INPUT, 'user_id': user['id'],
        'question': 'Rank European cities for my 2027 solar return', 'history': []})
    assert response.status_code == 200
    if streaming:
        assert 'event: done' in response.text
        assert 'city calculation' in response.text
    else:
        data = response.json()
        assert data['context']['where_to_be']['status'] == 'failed'
        assert len(data['answer'].split()) < 70
        assert 'Pluto' not in data['answer']


def test_unknown_birth_time_is_explained_instead_of_silently_skipping(client, account):
    user, headers = account(birth_time_known=False)
    response = client.post('/ask-astrologer', headers=headers, json={**BIRTH_INPUT,
        'user_id': user['id'], 'question': 'Rank European cities for my solar return', 'history': []})
    assert response.status_code == 200
    assert response.json()['context']['where_to_be']['status'] == 'needs_birth_time'
    assert 'birth time' in response.json()['answer']


def test_transits_endpoint_still_accepts_plain_birth_data(client):
    response = client.post('/transits', json=BIRTH_INPUT)
    assert response.status_code == 200
    assert 'active_transits' in response.json()


def test_full_financial_retest_question_returns_city_report_without_ai(client, account, monkeypatch):
    from pathlib import Path
    import app.main as main
    question = (Path(__file__).parent / 'fixtures' / 'relocation_financial_request.txt').read_text()
    monkeypatch.setattr(main, 'classify_answer_tier', lambda *a, **kw: pytest.fail('No model routing needed'))
    monkeypatch.setattr(main, 'extract_asked_date', lambda *a, **kw: pytest.fail('No model date extraction needed'))
    monkeypatch.setattr(main, 'generate_astrologer_answer', lambda *a, **kw: pytest.fail('No model generation needed'))
    user, headers = account()
    response = client.post('/ask-astrologer', headers=headers, json={**BIRTH_INPUT,
        'user_id': user['id'], 'question': question, 'history': []})
    assert response.status_code == 200
    data = response.json()
    result = data['context']['where_to_be']
    assert result['purpose'] == 'money'
    assert result['region'] == 'europe'
    assert result['calculated'] == result['searched'] == 81
    assert 5 <= len(result['best']) <= 10
    assert len({c['place'] for c in result['best']}) == len(result['best'])
    for city in result['best']:
        assert city['place'] in data['answer']
        assert city['be_there_at'] in data['answer']
    assert data['context']['natal']['source'] == 'natal'
    assert result['base_solar_return']['source'] == 'solar_return'


def test_solar_return_precision_does_not_use_rounded_display_longitude(monkeypatch):
    import app.relocation_reading_service as reading
    import app.main as main
    class Profile:
        birth_date = '1999-03-02'
        birth_time = '07:15'
        birth_place = 'Sofia, Bulgaria'
        birth_time_known = True
    natal = main.build_natal_chart_data(Profile())
    natal['planet_positions'][0]['degree'] = 0  # display data must not time the return
    seen = {}
    def capture(sun, *args, **kwargs):
        seen['sun'] = sun
        return {'status': 'failed', 'message': 'test'}
    monkeypatch.setattr(reading, 'rank_places_for', capture)
    reading.prepare_relocation('solar return 2027', Profile.birth_date, natal, {'purpose': 'money', 'region': 'europe'})
    expected = _sun_longitude(datetime.fromisoformat(natal['utc_birth_time']))
    assert seen['sun'] == expected
    assert seen['sun'] != round(expected, 2)


def test_real_mc_aspects_and_natal_contacts_contribute_separately():
    chart = {'planets': [{'planet': 'Venus', 'house': 12, 'degree': 120, 'sign': 'Leo'}],
             'houses': [], 'angular_planets': [], 'midheaven': {'degree': 0, 'sign': 'Aries'}}
    result = score_chart(chart)
    assert result['from_mc_contacts'] == 0.5
    chart['natal_planets'] = [{'planet': 'Jupiter', 'degree': 90}]
    assert score_chart(chart)['from_mc_contacts'] == 0.25
    assert result['from_houses'] == 0
