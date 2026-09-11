import os
import ssl
from typing import Optional

import certifi
import requests
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
TIMEZONE_FINDER = TimezoneFinder()
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
USER_AGENT = "Zodi/1.0 (astrology chart app; github.com/martinaramo3-cloud/astro-ai)"


def get_timezone_from_coordinates(latitude: float, longitude: float) -> Optional[str]:
    try:
        return TIMEZONE_FINDER.timezone_at(lat=latitude, lng=longitude)
    except Exception:
        return None


def describe_coordinates(latitude: float, longitude: float) -> tuple[Optional[str], str]:
    """A timezone and a readable label for a pair of coordinates, computed offline.

    Deliberately no reverse geocoding. Someone's live location is more sensitive
    than the birthplace they typed in, and it should not be handed to a third
    party just to print a city name in a heading. The IANA timezone already
    carries one — "America/New_York" becomes "New York" — and timezonefinder
    resolves it locally, so the coordinates never leave this server.
    """
    zone = get_timezone_from_coordinates(latitude, longitude)
    if not zone:
        return None, "your location"

    city = zone.split("/")[-1].replace("_", " ")
    return zone, city or "your location"


def _normalize_location_result(place_name: str, latitude: float, longitude: float, timezone: Optional[str], country: Optional[str], city: Optional[str]) -> dict:
    return {
        "place_name": place_name,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "country": country,
        "city": city,
    }


def get_nominatim_location_data(place_name: str) -> Optional[dict]:
    try:
        geolocator = Nominatim(user_agent=USER_AGENT, ssl_context=SSL_CONTEXT)
        location = geolocator.geocode(place_name, addressdetails=True, timeout=10)
        if not location:
            return None
        address = location.raw.get("address", {})
        timezone = get_timezone_from_coordinates(location.latitude, location.longitude)
        city = address.get("city") or address.get("town") or address.get("village") or address.get("municipality")
        return _normalize_location_result(
            place_name=location.address,
            latitude=location.latitude,
            longitude=location.longitude,
            timezone=timezone,
            country=address.get("country"),
            city=city,
        )
    except Exception as exc:
        print("Nominatim error:", exc)
        return None


def get_photon_location_data(place_name: str) -> Optional[dict]:
    try:
        url = "https://photon.komoot.io/api/"
        params = {"q": place_name, "limit": 1}
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        features = response.json().get("features", [])
        if not features:
            return None
        feature = features[0]
        coords = feature["geometry"]["coordinates"]
        longitude, latitude = float(coords[0]), float(coords[1])
        props = feature.get("properties", {})
        timezone = get_timezone_from_coordinates(latitude, longitude)
        city = props.get("city") or props.get("name")
        country = props.get("country")
        display = ", ".join(filter(None, [props.get("name"), props.get("city"), props.get("state"), country]))
        return _normalize_location_result(
            place_name=display or place_name,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            country=country,
            city=city,
        )
    except Exception as exc:
        print("Photon error:", exc)
        return None


def get_geoapify_location_data(place_name: str) -> Optional[dict]:
    if not GEOAPIFY_API_KEY:
        return None

    url = "https://api.geoapify.com/v1/geocode/search"
    params = {"text": place_name, "format": "json", "apiKey": GEOAPIFY_API_KEY}
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            return None

        place = results[0]
        latitude = place.get("lat")
        longitude = place.get("lon")
        timezone = (place.get("timezone") or {}).get("name")
        if not timezone and latitude is not None and longitude is not None:
            timezone = get_timezone_from_coordinates(latitude, longitude)

        return _normalize_location_result(
            place_name=place.get("formatted") or place_name,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            country=place.get("country"),
            city=place.get("city") or place.get("county"),
        )
    except Exception as exc:
        print("Geoapify error:", exc)
        return None


def get_location_data(place_name: str) -> Optional[dict]:
    if not place_name or not place_name.strip():
        return None

    clean_place = place_name.strip()

    geoapify_data = get_geoapify_location_data(clean_place)
    if geoapify_data and geoapify_data.get("timezone"):
        return geoapify_data

    nominatim_data = get_nominatim_location_data(clean_place)
    if nominatim_data and nominatim_data.get("timezone"):
        return nominatim_data

    photon_data = get_photon_location_data(clean_place)
    if photon_data and photon_data.get("timezone"):
        return photon_data

    return geoapify_data or nominatim_data or photon_data


def suggest_places(query: str, limit: int = 6) -> list[dict]:
    """Cities to choose from, named the way a person would name them.

    The dropdown used to call a different geocoder than the one that actually
    resolves the chart, and showed whatever raw string came back — "Tirana,
    Bashkia Tiranë, Qarku i Tiranës, 1001, Albania". Nobody recognises their
    birthplace in that. Worse, the two services could disagree, so the place
    picked was not necessarily the place used.

    This asks the same geocoder the chart uses, restricted to populated places,
    and builds the label from the city and country alone.
    """
    query = (query or "").strip()
    if len(query) < 2 or not GEOAPIFY_API_KEY:
        return []

    try:
        response = requests.get(
            "https://api.geoapify.com/v1/geocode/autocomplete",
            params={
                "text": query,
                # Towns and cities only: nobody is born in a restaurant, and
                # street-level results are what produced the postcodes.
                "type": "city",
                "limit": limit,
                "format": "json",
                "apiKey": GEOAPIFY_API_KEY,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=8,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
    except Exception as exc:  # noqa: BLE001 — a failed lookup is an empty list
        print("[places] suggest failed:", repr(exc))
        return []

    seen: set[str] = set()
    places: list[dict] = []
    for place in results:
        city = place.get("city") or place.get("town") or place.get("village") or place.get("name")
        country = place.get("country")
        if not city or not country:
            continue

        # A county or region is worth showing only when it tells two
        # same-named towns apart — "Springfield, Illinois" earns its keep,
        # "Tirana, Tirana County" does not.
        label = f"{city}, {country}"
        if label in seen:
            region = place.get("state") or place.get("county")
            if not region or region == city:
                continue
            label = f"{city}, {region}, {country}"
            if label in seen:
                continue
        seen.add(label)

        places.append({
            "label": label,
            "latitude": place.get("lat"),
            "longitude": place.get("lon"),
        })

    return places
