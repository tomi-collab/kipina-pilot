from __future__ import annotations

import threading
import time
from copy import deepcopy
from typing import Any


_state: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def create_session(
    sandbox_id: str,
    session_id: str,
    concept: str,
    report: str,
    tenant_id: str | None = None,
    suggested_templates: list[str] | None = None,
) -> None:
    with _lock:
        _state[sandbox_id] = {
            "session_id": session_id,
            "tenant_id": tenant_id,
            "concept": concept,
            "report": report,
            "suggested_templates": suggested_templates or [],
            "created_at": time.time(),
            "iteration_count": 0,
            "html_history": [],
            "recent_iterations": [],
            "concept_drift_warned": False,
            "last_action": None,
        }


def get_session(sandbox_id: str) -> dict[str, Any] | None:
    with _lock:
        session = _state.get(sandbox_id)
        return deepcopy(session) if session is not None else None


def add_html_version(sandbox_id: str, html: str) -> None:
    with _lock:
        session = _state[sandbox_id]
        session["html_history"].append(html)
        session["html_history"] = session["html_history"][-20:]


def current_html(sandbox_id: str) -> str | None:
    with _lock:
        history = _state.get(sandbox_id, {}).get("html_history", [])
        return history[-1] if history else None


def pop_last_html_version(sandbox_id: str) -> str | None:
    with _lock:
        session = _state[sandbox_id]
        history = session["html_history"]
        if len(history) < 2:
            return None
        history.pop()
        return history[-1]


def increment_iteration(sandbox_id: str) -> int:
    with _lock:
        session = _state[sandbox_id]
        session["iteration_count"] += 1
        return int(session["iteration_count"])


def add_iteration(sandbox_id: str, user: str, mestari: str) -> None:
    with _lock:
        session = _state[sandbox_id]
        session["recent_iterations"].append({"user": user, "mestari": mestari})
        session["recent_iterations"] = session["recent_iterations"][-5:]


def mark_drift_warned(sandbox_id: str) -> None:
    with _lock:
        _state[sandbox_id]["concept_drift_warned"] = True


def set_last_action(sandbox_id: str, action: str) -> None:
    with _lock:
        _state[sandbox_id]["last_action"] = action


def delete_session(sandbox_id: str) -> None:
    with _lock:
        _state.pop(sandbox_id, None)
