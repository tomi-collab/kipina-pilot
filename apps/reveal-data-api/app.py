"""
reveal-data-api — Kipinä pilot

Endpoints:
  GET  /api/health       — health check (tenant_count)
  GET  /api/tenants      — list tenants (id/name/description only, no keys)
  POST /api/auth/check   — validate shared access code (KIPINA_ACCESS_CODE)
  POST /api/idea         — proxy to Reveal Engine, adds tenant_key+api_key server-side
                           body: {session_id, message, tenant_id?}
                           tenant_id defaults to first tenant if omitted
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------

ACCESS_CODE = os.environ.get("KIPINA_ACCESS_CODE", "")
REVEAL_ENGINE_BASE_URL = os.environ.get("REVEAL_ENGINE_BASE_URL", "").rstrip("/")
REVEAL_ENGINE_TIMEOUT_SECONDS = int(os.environ.get("REVEAL_ENGINE_TIMEOUT_SECONDS", "60"))

_tenants_raw = os.environ.get("KIPINA_TENANTS", "[]")
try:
    _tenants_all: list[dict[str, str]] = json.loads(_tenants_raw)
    if not isinstance(_tenants_all, list):
        raise ValueError("KIPINA_TENANTS must be a JSON array")
except (ValueError, TypeError) as exc:
    print(f"ERROR: Could not parse KIPINA_TENANTS: {exc}", file=sys.stderr, flush=True)
    _tenants_all = []

TENANTS_PUBLIC = [
    {"id": t["id"], "name": t["name"], "description": t.get("description", "")}
    for t in _tenants_all
    if isinstance(t, dict) and "id" in t and "name" in t
]

TENANTS_BY_ID: dict[str, dict[str, str]] = {
    t["id"]: t for t in _tenants_all if isinstance(t, dict) and "id" in t
}

MAX_BODY_BYTES = 64 * 1024  # 64 KB
PORT = int(os.environ.get("PORT", "8080"))


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _label_from_key(key: str) -> str:
    return key.replace("_", " ").replace("-", " ").strip().capitalize()


def _report_value_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return "\n\n".join(
            text for item in value if (text := _report_value_to_text(item))
        )
    if isinstance(value, dict):
        for key in ("text", "content", "markdown", "report", "final_report"):
            text = _report_value_to_text(value.get(key))
            if text:
                return text

        parts: list[str] = []
        for key, nested in value.items():
            text = _report_value_to_text(nested)
            if not text:
                continue
            parts.append(f"{_label_from_key(str(key))}\n{text}")
        return "\n\n".join(parts)
    return ""


def normalize_report(report: Any) -> str | None:
    text = _report_value_to_text(report).strip()
    if not text or text == "[object Object]":
        return None
    return text


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        log(f"{self.address_string()} - {format % args}")

    # -- helpers --

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0 or length > MAX_BODY_BYTES:
            return None
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        return data

    # -- routing --

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            return self._handle_health()
        if path == "/api/tenants":
            return self._handle_tenants()
        return self._write_json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/auth/check":
            return self._handle_auth_check()
        if path == "/api/idea":
            return self._handle_idea()
        return self._write_json(404, {"error": "not_found"})

    # -- GET /api/health --

    def _handle_health(self) -> None:
        self._write_json(200, {
            "ok": True,
            "service": "reveal-data-api",
            "environment": "kipina-pilot",
            "tenant_count": len(TENANTS_PUBLIC),
        })

    # -- GET /api/tenants --

    def _handle_tenants(self) -> None:
        self._write_json(200, {"ok": True, "tenants": TENANTS_PUBLIC})

    # -- POST /api/auth/check --

    def _handle_auth_check(self) -> None:
        body = self._read_json_body()
        if body is None:
            return self._write_json(400, {"error": "invalid_body"})
        code = body.get("code")
        if not isinstance(code, str) or not code:
            return self._write_json(400, {"error": "missing_code"})
        if not ACCESS_CODE:
            log("WARNING: KIPINA_ACCESS_CODE not set — rejecting all logins.")
            return self._write_json(401, {"ok": False})
        if secrets.compare_digest(code, ACCESS_CODE):
            return self._write_json(200, {"ok": True})
        return self._write_json(401, {"ok": False})

    # -- POST /api/idea --

    def _handle_idea(self) -> None:
        body = self._read_json_body()
        if body is None:
            return self._write_json(400, {"error": "invalid_body"})

        session_id = body.get("session_id")
        message = body.get("message")
        tenant_id = body.get("tenant_id")  # optional; defaults to first tenant

        if not isinstance(message, str) or not message.strip():
            return self._write_json(400, {"error": "missing_message"})

        # Resolve tenant
        if tenant_id:
            tenant = TENANTS_BY_ID.get(tenant_id)
            if tenant is None:
                return self._write_json(400, {"error": "unknown_tenant_id"})
        elif TENANTS_PUBLIC:
            tenant = _tenants_all[0]
        else:
            log("ERROR: No tenants configured in KIPINA_TENANTS.")
            return self._write_json(503, {"error": "no_tenants_configured"})

        tenant_key = tenant.get("tenant_key", "")
        api_key = tenant.get("api_key", "")

        if not REVEAL_ENGINE_BASE_URL:
            log("ERROR: REVEAL_ENGINE_BASE_URL not set.")
            return self._write_json(503, {"error": "engine_not_configured"})

        upstream_payload = {
            "tenant_id": tenant_key,
            "user_input": message,
            "session_id": session_id,
        }
        req = urllib.request.Request(
            f"{REVEAL_ENGINE_BASE_URL}/api/v1/interact",
            data=json.dumps(upstream_payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-API-Key": api_key,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=REVEAL_ENGINE_TIMEOUT_SECONDS) as resp:
                resp_body = resp.read()
                resp_status = resp.status
        except urllib.error.HTTPError as e:
            log(f"Reveal Engine HTTPError: {e.code} {e.reason}")
            return self._write_json(502, {"error": "engine_error", "status": e.code})
        except urllib.error.URLError as e:
            log(f"Reveal Engine URLError: {e.reason}")
            return self._write_json(504, {"error": "engine_timeout"})

        try:
            data = json.loads(resp_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            log("Reveal Engine returned non-JSON body")
            return self._write_json(502, {"error": "engine_invalid_response"})

        progress = data.get("progress") or {}
        safe = {
            "reply": data.get("reply", ""),
            "session_id": data.get("session_id", session_id),
            "finished": bool(progress.get("is_complete", False)),
            "turn": progress.get("current_turn", 0),
            "milestone": progress.get("milestone"),
            "report": normalize_report(data.get("report")),
        }
        return self._write_json(resp_status, safe)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    if not TENANTS_PUBLIC:
        log("WARNING: No tenants loaded from KIPINA_TENANTS — /api/idea will return 503.")
    else:
        log(f"Loaded {len(TENANTS_PUBLIC)} tenant(s): {[t['id'] for t in TENANTS_PUBLIC]}")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    log(f"reveal-data-api listening on 0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("shutting down")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
