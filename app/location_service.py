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
USER_AGENT = "AstraeaStudio/1.0 (astrology chart app; github.com/martinaramo3-cloud/astro-ai)"


def get_timezone_from_coordinates(latitude: float, longitude: float) -> Optional[str]:
    try:
        return TIMEZONE_FINDER.timezone_at(lat=latitude, lng=longitude)
    except Exception:
        return None


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

    location_data = get_nominatim_location_data(clean_place)
    if location_data and location_data.get("timezone"):
        return location_data

    return geoapify_data or location_data
