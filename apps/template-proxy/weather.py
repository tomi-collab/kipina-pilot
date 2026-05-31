from __future__ import annotations

import math
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any


FMI_WFS_URL = "https://opendata.fmi.fi/wfs"
UPSTREAM_TIMEOUT_SECONDS = 8
PLACE_RE = re.compile(r"^[A-Za-zÅÄÖåäö\s-]{1,60}$")


class WeatherError(Exception):
    status = 502
    error = "upstream_error"


class WeatherValidationError(WeatherError):
    status = 400
    error = "validation_error"


class WeatherNotFoundError(WeatherError):
    status = 404
    error = "place_not_found"


class WeatherTimeoutError(WeatherError):
    status = 504
    error = "upstream_timeout"


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _child_text(element: ET.Element, name: str) -> str | None:
    for child in element.iter():
        if _local_name(child.tag) == name and child.text:
            return child.text.strip()
    return None


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    if math.isnan(parsed):
        return None
    return parsed


def _parse_observations(xml_bytes: bytes, place: str) -> dict[str, Any]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise WeatherError("FMI returned invalid XML") from exc

    if _local_name(root.tag) == "ExceptionReport":
        raise WeatherNotFoundError(f"Paikkakuntaa '{place}' ei löytynyt.")

    latest: dict[str, tuple[str, float | None]] = {}
    for element in root.iter():
        if _local_name(element.tag) != "BsWfsElement":
            continue
        parameter = _child_text(element, "ParameterName")
        value = _parse_float(_child_text(element, "ParameterValue"))
        observed_at = _child_text(element, "Time")
        if not parameter or not observed_at:
            continue
        current = latest.get(parameter)
        if current is None or observed_at > current[0]:
            latest[parameter] = (observed_at, value)

    if not latest:
        raise WeatherNotFoundError(f"Paikkakuntaa '{place}' ei löytynyt.")

    temperature = latest.get("t2m", ("", None))[1]
    if temperature is None:
        raise WeatherError("FMI response did not include temperature")

    observed_at = max(item[0] for item in latest.values() if item[0])
    return {
        "place": place,
        "temperature_c": temperature,
        "wind_ms": latest.get("ws_10min", ("", None))[1],
        "humidity_pct": latest.get("rh", ("", None))[1],
        "wind_direction_deg": latest.get("wd_10min", ("", None))[1],
        "observed_at": observed_at,
        "source": "Ilmatieteen laitos / avoin data",
    }


def get_current_weather(place: str) -> dict[str, Any]:
    place = place.strip()
    if not PLACE_RE.fullmatch(place):
        raise WeatherValidationError("place must contain only letters, spaces and hyphens, max 60 characters")

    starttime = (datetime.now(timezone.utc) - timedelta(minutes=30)).replace(microsecond=0)
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "getFeature",
        "storedquery_id": "fmi::observations::weather::simple",
        "place": place,
        "parameters": "t2m,ws_10min,rh,wd_10min",
        "starttime": starttime.isoformat().replace("+00:00", "Z"),
    }
    url = f"{FMI_WFS_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=UPSTREAM_TIMEOUT_SECONDS) as response:
            return _parse_observations(response.read(), place)
    except TimeoutError as exc:
        raise WeatherTimeoutError("FMI request timed out") from exc
    except urllib.error.HTTPError as exc:
        if exc.code == 400:
            raise WeatherNotFoundError(f"Paikkakuntaa '{place}' ei löytynyt.") from exc
        raise WeatherError(str(exc)[:240]) from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise WeatherTimeoutError("FMI request timed out") from exc
        raise WeatherError(str(exc)[:240]) from exc
