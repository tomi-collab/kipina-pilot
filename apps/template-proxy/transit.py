from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


DIGITRANSIT_SUBSCRIPTION_KEY = os.environ.get("DIGITRANSIT_SUBSCRIPTION_KEY", "").strip()
DIGITRANSIT_ROUTING_URL = os.environ.get(
    "DIGITRANSIT_ROUTING_URL",
    "https://api.digitransit.fi/routing/v2/hsl/gtfs/v1",
)
UPSTREAM_TIMEOUT_SECONDS = 8
MAX_STOP_NAME_CHARS = 60


class TransitError(Exception):
    status = 502
    error = "upstream_error"


class TransitValidationError(TransitError):
    status = 400
    error = "validation_error"


class TransitUnavailableError(TransitError):
    status = 503
    error = "transit_unavailable"


class TransitNotFoundError(TransitError):
    status = 404
    error = "stop_not_found"


class TransitTimeoutError(TransitError):
    status = 504
    error = "upstream_timeout"


def is_configured() -> bool:
    return bool(DIGITRANSIT_SUBSCRIPTION_KEY)


def _graphql(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    if not DIGITRANSIT_SUBSCRIPTION_KEY:
        raise TransitUnavailableError("Digitransit-avain puuttuu palvelimelta. Joukkoliikenne ei ole vielä käytössä.")

    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        DIGITRANSIT_ROUTING_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "digitransit-subscription-key": DIGITRANSIT_SUBSCRIPTION_KEY,
            "User-Agent": "kipina-pilot/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=UPSTREAM_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except TimeoutError as exc:
        raise TransitTimeoutError("Digitransit request timed out") from exc
    except urllib.error.URLError as exc:
        if isinstance(getattr(exc, "reason", None), TimeoutError):
            raise TransitTimeoutError("Digitransit request timed out") from exc
        raise TransitError(str(exc)[:240]) from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise TransitError("Digitransit returned invalid JSON") from exc

    if isinstance(payload, dict) and payload.get("errors"):
        raise TransitError("Digitransit GraphQL error")
    if not isinstance(payload, dict):
        raise TransitError("Digitransit returned non-object JSON")
    return payload


def _find_stops(stop_name: str) -> list[dict[str, Any]]:
    query = """
    query FindStops($name: String!) {
      stops(name: $name) { gtfsId name }
    }
    """
    payload = _graphql(query, {"name": stop_name})
    stops = payload.get("data", {}).get("stops")
    if not isinstance(stops, list) or not stops:
        raise TransitNotFoundError(f"Pysäkkiä '{stop_name}' ei löytynyt.")
    return [stop for stop in stops[:8] if isinstance(stop, dict) and stop.get("gtfsId")]


def _departures_for_stop(gtfs_id: str) -> list[dict[str, Any]]:
    query = """
    query StopDepartures($id: String!) {
      stop(id: $id) {
        name
        stoptimesWithoutPatterns(numberOfDepartures: 3) {
          scheduledDeparture
          realtimeDeparture
          realtime
          headsign
          serviceDay
          trip { route { shortName } }
        }
      }
    }
    """
    payload = _graphql(query, {"id": gtfs_id})
    stop = payload.get("data", {}).get("stop")
    if not isinstance(stop, dict):
        return []
    departures = stop.get("stoptimesWithoutPatterns")
    return departures if isinstance(departures, list) else []


def get_departures(stop_name: str) -> dict[str, Any]:
    stop_name = stop_name.strip()
    if not stop_name or len(stop_name) > MAX_STOP_NAME_CHARS:
        raise TransitValidationError("stop_name is required and must be at most 60 characters")

    stops = _find_stops(stop_name)
    response_stop_name = str(stops[0].get("name") or stop_name)
    now_epoch = time.time()
    combined = []

    for stop in stops:
        for departure in _departures_for_stop(str(stop["gtfsId"])):
            if not isinstance(departure, dict):
                continue
            service_day = departure.get("serviceDay")
            scheduled = departure.get("scheduledDeparture")
            realtime_departure = departure.get("realtimeDeparture")
            realtime = bool(departure.get("realtime"))
            seconds_from_day_start = realtime_departure if realtime else scheduled
            if not isinstance(service_day, int) or not isinstance(seconds_from_day_start, int):
                continue
            departure_epoch = service_day + seconds_from_day_start
            minutes_until = round((departure_epoch - now_epoch) / 60)
            if minutes_until < 0:
                continue
            route = departure.get("trip", {}).get("route", {}) if isinstance(departure.get("trip"), dict) else {}
            line = route.get("shortName") if isinstance(route, dict) else None
            destination = departure.get("headsign")
            if not line or not destination:
                continue
            combined.append(
                {
                    "line": str(line),
                    "destination": str(destination),
                    "minutes_until": minutes_until,
                    "realtime": realtime,
                }
            )

    combined.sort(key=lambda item: item["minutes_until"])
    return {
        "stop": response_stop_name,
        "departures": combined[:8],
        "source": "HSL / Digitransit",
    }
