"""Birthplace suggestions, named the way people say them.

The second question the app asks is where you were born, and it used to answer
with "Tirana, Bashkia Tiranë, Qarku i Tiranës, 1001, Albania". These tests pin
the shaping, not the lookup — the providers are stubbed, so a run stays offline
and never rate-limits anyone.
"""
import pytest

import app.location_service as places


def photon(features):
    """A Photon response, shaped as the real one is."""
    return {"features": [
        {"geometry": {"coordinates": [lon, lat]},
         "properties": {"osm_key": key, "osm_value": value, "name": name,
                        "state": state, "country": country}}
        for name, state, country, lat, lon, key, value in features
    ]}


@pytest.fixture
def from_photon(monkeypatch):
    def use(features):
        class Response:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return photon(features)
        monkeypatch.setattr(places.requests, "get", lambda *a, **k: Response())
        monkeypatch.setattr(places, "GEOAPIFY_API_KEY", None)
    return use


def test_a_city_is_named_city_then_country(from_photon):
    from_photon([("Tirana", "Tirana County", "Albania", 41.33, 19.82, "place", "city")])
    assert [p["label"] for p in places.suggest_places("tirana")] == ["Tirana, Albania"]


def test_the_administrative_body_is_not_the_birthplace(from_photon):
    """OSM stores some cities under the municipality that shares their name."""
    from_photon([("Bashkia Durrës", "Durrës County", "Albania", 41.32, 19.45, "place", "city")])
    assert [p["label"] for p in places.suggest_places("durres")] == ["Durrës, Albania"]


@pytest.mark.parametrize("stored, expected", [
    ("Bashkia Tiranë", "Tiranë"),
    ("Town of Milan", "Milan"),
    ("City of London", "London"),
    ("Comune di Roma", "Roma"),
    ("Paris", "Paris"),
])
def test_administrative_prefixes_are_stripped(stored, expected):
    assert places._strip_admin(stored) == expected


def test_streets_and_shops_are_not_offered(from_photon):
    """This is where the postcodes and random addresses were coming from."""
    from_photon([
        ("Tirana", "Tirana County", "Albania", 41.33, 19.82, "place", "city"),
        ("Tirana Street", "Some County", "Albania", 41.30, 19.80, "highway", "residential"),
        ("Hotel Tirana", "Tirana County", "Albania", 41.31, 19.81, "tourism", "hotel"),
    ])
    assert [p["label"] for p in places.suggest_places("tirana")] == ["Tirana, Albania"]


def test_the_same_city_is_not_offered_twice(from_photon):
    """It comes back once per administrative level; position settles it."""
    from_photon([
        ("Paris", "Ile-de-France", "France", 48.8566, 2.3522, "place", "city"),
        ("Paris", None, "France", 48.8570, 2.3530, "place", "city"),
    ])
    assert [p["label"] for p in places.suggest_places("paris")] == ["Paris, France"]


def test_two_different_places_with_one_name_both_appear(from_photon):
    """A region earns its place only when it tells them apart."""
    from_photon([
        ("Springfield", "Illinois", "United States", 39.78, -89.65, "place", "city"),
        ("Springfield", "Missouri", "United States", 37.21, -93.29, "place", "city"),
    ])
    labels = [p["label"] for p in places.suggest_places("springfield")]
    assert labels == ["Springfield, United States", "Springfield, Missouri, United States"]


def test_nothing_is_offered_for_a_single_letter():
    assert places.suggest_places("t") == []


def test_a_provider_failure_is_an_empty_list_not_an_error(monkeypatch):
    def explode(*a, **k):
        raise RuntimeError("provider down")
    monkeypatch.setattr(places.requests, "get", explode)
    monkeypatch.setattr(places, "GEOAPIFY_API_KEY", None)
    assert places.suggest_places("tirana") == []


def test_the_endpoint_answers_without_an_account(client, monkeypatch):
    """It is needed on the signup screen and on an invite page."""
    monkeypatch.setattr(places, "suggest_places", lambda q, limit=6: [{"label": "Tirana, Albania"}])
    import app.main as main
    monkeypatch.setattr(main, "suggest_places", lambda q, limit=6: [{"label": "Tirana, Albania"}])
    response = client.get("/places/suggest?q=tirana")
    assert response.status_code == 200
    assert response.json()["places"][0]["label"] == "Tirana, Albania"
