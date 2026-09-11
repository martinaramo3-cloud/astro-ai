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


def _clean_label(city: str | None, region: str | None, country: str | None, seen: set) -> str | None:
    """City and country, with a region only when it settles an ambiguity."""
    if not city or not country:
        return None
    label = f"{city}, {country}"
    if label not in seen:
        return label
    # A second Springfield earns its state; a second Tirana does not earn its
    # municipality.
    if region and region != city:
        longer = f"{city}, {region}, {country}"
        return longer if longer not in seen else None
    return None


def _suggest_geoapify(query: str, limit: int) -> list[dict]:
    if not GEOAPIFY_API_KEY:
        return []
    response = requests.get(
        "https://api.geoapify.com/v1/geocode/autocomplete",
        params={"text": query, "type": "city", "limit": limit,
                "format": "json", "apiKey": GEOAPIFY_API_KEY},
        headers={"User-Agent": USER_AGENT},
        timeout=8,
    )
    response.raise_for_status()
    return [
        {"city": p.get("city") or p.get("town") or p.get("village") or p.get("name"),
         "region": p.get("state") or p.get("county"),
         "country": p.get("country"),
         "latitude": p.get("lat"), "longitude": p.get("lon")}
        for p in response.json().get("results", [])
    ]


# What OSM stores as a city's name is sometimes the administrative body that
# shares it: "Bashkia Durrës" is the municipality, not the place anyone says
# they were born in.
_ADMIN_PREFIXES = ("bashkia ", "town of ", "city of ", "municipality of ",
                   "comune di ", "commune de ", "gemeinde ", "gmina ", "obshtina ")


def _strip_admin(name: str | None) -> str | None:
    if not name:
        return None
    lowered = name.lower()
    for prefix in _ADMIN_PREFIXES:
        if lowered.startswith(prefix):
            return name[len(prefix):].strip() or None
    return name


def _suggest_photon(query: str, limit: int) -> list[dict]:
    """Built for typing into, unlike the others.

    Nominatim's own usage policy discourages autocomplete and rate-limits hard
    — hammering it from a server is how an IP gets blocked. Photon is the same
    OpenStreetMap data served for exactly this, and needs no key.
    """
    response = requests.get(
        "https://photon.komoot.io/api/",
        params={"q": query, "limit": limit * 3, "lang": "en"},
        headers={"User-Agent": USER_AGENT},
        timeout=8,
    )
    response.raise_for_status()
    places = []
    for feature in response.json().get("features", []):
        props = feature.get("properties") or {}
        # Settlements only: no streets, no shops, no postcodes.
        if props.get("osm_key") != "place" or props.get("osm_value") not in (
            "city", "town", "village", "hamlet"
        ):
            continue
        coords = (feature.get("geometry") or {}).get("coordinates") or [None, None]
        places.append({
            "city": _strip_admin(props.get("name")),
            "region": props.get("state") or props.get("county"),
            "country": props.get("country"),
            "latitude": coords[1], "longitude": coords[0],
        })
    return places


def _suggest_nominatim(query: str, limit: int) -> list[dict]:
    """The fallback that is actually doing the work, since there is no
    Geoapify key configured. addressdetails is what makes a clean label
    possible: without it there is only the full raw string."""
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": limit * 3,
                "addressdetails": 1, "featuretype": "settlement",
                # Otherwise Sofia comes back as "София" and Tirana as "Tiranë".
                # People type and recognise their birthplace in English here.
                "accept-language": "en"},
        headers={"User-Agent": USER_AGENT},
        timeout=8,
    )
    response.raise_for_status()
    places = []
    for p in response.json():
        # Keep settlements only. Without this the results include the
        # administrative bodies that share their name — "Bashkia Tiranë",
        # "Town of Milan" — which is most of what looked wrong.
        if p.get("addresstype") not in ("city", "town", "village", "hamlet"):
            continue
        address = p.get("address") or {}
        places.append({
            "city": _strip_admin(address.get("city") or address.get("town")
                                 or address.get("village") or address.get("hamlet")),
            "region": address.get("state") or address.get("county"),
            "country": address.get("country"),
            "latitude": p.get("lat"), "longitude": p.get("lon"),
        })
    return places


def suggest_places(query: str, limit: int = 6) -> list[dict]:
    """Cities to choose from, named the way a person would name them.

    The dropdown used to show the geocoder's raw string — "Tirana, Bashkia
    Tiranë, Qarku i Tiranës, 1001, Albania". Nobody recognises their birthplace
    in that, and it is the second question the app asks.

    Same providers, and in the same order, as the geocoding that resolves the
    chart: whichever answers is the one the chart will be cast from, so what is
    offered is always something the app can actually use.
    """
    query = (query or "").strip()
    if len(query) < 2:
        return []

    raw: list[dict] = []
    # Photon before Nominatim: it is the one meant to be typed into.
    for source in (_suggest_geoapify, _suggest_photon, _suggest_nominatim):
        try:
            raw = source(query, limit)
        except Exception as exc:  # noqa: BLE001 — try the next one
            print(f"[places] {source.__name__} failed:", repr(exc))
            continue
        if raw:
            break

    seen: set[str] = set()
    coords: set[tuple] = set()
    places: list[dict] = []
    for place in raw:
        # The same city often comes back more than once, once per administrative
        # level — "Paris, France" and "Paris, Ile-de-France, France". Position
        # settles it: within about ten kilometres is the same birthplace.
        try:
            here = (round(float(place["latitude"]), 1), round(float(place["longitude"]), 1))
        except (TypeError, ValueError, KeyError):
            here = None
        if here and here in coords:
            continue

        label = _clean_label(place.get("city"), place.get("region"), place.get("country"), seen)
        if not label:
            continue
        seen.add(label)
        if here:
            coords.add(here)
        places.append({"label": label,
                       "latitude": place.get("latitude"),
                       "longitude": place.get("longitude")})
    return places[:limit]
