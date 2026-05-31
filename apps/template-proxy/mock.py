from __future__ import annotations

from datetime import date
from typing import Any


DEFAULT_WEEK_STARTS = "2026-06-01"

CALENDAR_EVENTS = [
    {"day": "ma", "time": "09:00", "title": "Matikan koe"},
    {"day": "ma", "time": "15:00", "title": "Jalkapallotreenit"},
    {"day": "ti", "time": "10:00", "title": "Ryhmätyö kirjastolla"},
    {"day": "ke", "time": "14:00", "title": "Kavereiden kanssa kahvilla"},
    {"day": "to", "time": "17:00", "title": "Soittotunti"},
    {"day": "pe", "time": "18:00", "title": "Elokuvat"},
    {"day": "la", "time": "12:00", "title": "Siivouspäivä"},
    {"day": "su", "time": "16:00", "title": "Lukupiiri"},
]

MESSAGES = [
    {"from": "Kaveri", "text": "Moi! Lähetkö huomenna treeneihin?", "time": "16:02"},
    {"from": "Minä", "text": "Joo lähden, mihin aikaan?", "time": "16:05"},
    {"from": "Kaveri", "text": "Kuudelta hallilla 👍", "time": "16:06"},
    {"from": "Minä", "text": "Selvä, nähdään siellä!", "time": "16:07"},
]


class MockError(Exception):
    status = 400
    error = "validation_error"


def get_calendar(week_starts: str | None = None) -> dict[str, Any]:
    normalized_week_starts = (week_starts or DEFAULT_WEEK_STARTS).strip()
    try:
        date.fromisoformat(normalized_week_starts)
    except ValueError as exc:
        raise MockError("week_starts must be an ISO date, for example 2026-06-01") from exc
    return {
        "week_starts": normalized_week_starts,
        "events": CALENDAR_EVENTS,
        "note": "Esimerkkidata — ei oikea kalenteri.",
        "source": "Kipinä demo-data",
    }


def get_messages() -> dict[str, Any]:
    return {
        "conversation": MESSAGES,
        "note": "Esimerkkikeskustelu — ei oikeita viestejä.",
        "source": "Kipinä demo-data",
    }
