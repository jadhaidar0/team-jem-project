"""
api_client.py
All communication with the Radio Browser API lives in this module.
Routes never call `requests` directly; they call the functions below.
"""

import logging

import requests
import random
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Configuration
# ---------------------------------------------------------------------------
BASE_URL = "https://de1.api.radio-browser.info/json/"
TIMEOUT = 5  # seconds
HEADERS = {"User-Agent": "RadioPassport/1.0 (GIN446 Group 06)"}
PAGE_SIZE = 30

# The only station fields the app uses.
STATION_FIELDS = (
    "stationuuid", "name", "url_resolved", "favicon", "country",
    "countrycode", "tags", "language", "codec", "bitrate", "votes",
    "clickcount", "lastcheckok", "homepage",
)


# ---------------------------------------------------------------------------
# 2. Custom error
# ---------------------------------------------------------------------------
class ApiError(Exception):
    """Raised when the Radio Browser API cannot be reached or answers badly."""


# ---------------------------------------------------------------------------
# 3. Private helpers
# ---------------------------------------------------------------------------
def _get(path, params=None):
    """Send one GET request to the API and return the decoded JSON."""
    url = BASE_URL + path.lstrip("/")
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.Timeout as exc:
        raise ApiError("The radio service took too long to answer.") from exc
    except requests.ConnectionError as exc:
        raise ApiError("Could not connect to the radio service.") from exc
    except requests.HTTPError as exc:
        raise ApiError(f"The radio service returned an error ({response.status_code}).") from exc
    except (requests.RequestException, ValueError) as exc:
        raise ApiError("The radio service sent an unexpected answer.") from exc


def _clean_station(raw):
    """Keep only the fields listed in STATION_FIELDS."""
    return {field: raw.get(field) for field in STATION_FIELDS}


# ---------------------------------------------------------------------------
# 4. Public functions
# ---------------------------------------------------------------------------
def search_stations(name=None, countrycode=None, tag=None, page=1,
                    order="votes", reverse=True):
    """Return one page (up to 30) of working, https stations."""
    params = {
        "name": name or None,
        "countrycode": countrycode.upper() if countrycode else None,
        "tag": tag or None,
        "is_https": "true",
        "hidebroken": "true",
        "order": order,
        "reverse": "true" if reverse else "false",
        "limit": PAGE_SIZE,
        "offset": (page - 1) * PAGE_SIZE,
    }
    data = _get("stations/search", params)
    return [_clean_station(s) for s in data]


def get_countries():
    """Return all countries, most stations first: [{name, code, stationcount}]."""
    data = _get("countries", {"order": "stationcount", "reverse": "true"})
    return [
        {"name": c.get("name"), "code": c.get("iso_3166_1"),
         "stationcount": c.get("stationcount", 0)}
        for c in data
        if c.get("iso_3166_1")
    ]


def get_genres():
    """Return the 50 most popular genres: [{name, stationcount}]."""
    data = _get("tags", {
        "order": "stationcount",
        "reverse": "true",
        "hidebroken": "true",
        "limit": 50,
    })
    return [{"name": t.get("name"), "stationcount": t.get("stationcount", 0)}
            for t in data]


def get_station(uuid):
    """Return one station dict, or None if the UUID is unknown."""
    data = _get(f"stations/byuuid/{uuid}")
    if not data:
        return None
    return _clean_station(data[0])


def register_click(uuid):
    """Tell the API a station was played. Never raises; returns True/False."""
    try:
        data = _get(f"url/{uuid}")
        return bool(data.get("ok"))
    except ApiError as exc:
        logger.warning("register_click failed for %s: %s", uuid, exc)
        return False


def get_random_station():
    """Return one random working https station, or None."""
    data = _get("stations/search", {
        "is_https": "true",
        "hidebroken": "true",
        "order": "random",
        "limit": 100,
    })
    if not data:
        return None
    return _clean_station(random.choice(data))