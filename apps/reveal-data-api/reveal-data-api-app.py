"""
reveal-data-api — Kipinä pilot

Endpointit:
  GET  /api/health       — health check
  POST /api/auth/check   — tarkistaa jaetun pääsykoodin (KIPINA_ACCESS_CODE env)
  POST /api/idea         — proxy Reveal Engineen (lisää tenant_key + api_key palvelinpuolella)

Ei web-frameworkkia: pelkkä http.server, sama kuvio kuin Reveal Platformissa.
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

# --- Ympäristömuuttujat ---

ACCESS_CODE = os.environ.get("KIPINA_ACCESS_CODE", "")
REVEAL_ENGINE_BASE_URL = os.environ.get(
    "REVEAL_ENGINE_BASE_URL", ""
).rstrip("/")
REVEAL_ENGINE_TENANT_KEY = os.environ.get("REVEAL_ENGINE_TENANT_KEY", "")
REVEAL_ENGINE_API_KEY = os.environ.get("REVEAL_ENGINE_API_KEY", "")
REVEAL_ENGINE_TIMEOUT_SECONDS = int(
    os.environ.get("REVEAL_ENGINE_TIMEOUT_SECONDS", "60")
)

# Maksimi pyyntöjen koko — estää pahoja törkypyyntöjä
MAX_BODY_BYTES = 64 * 1024  # 64 KB
PORT = int(os.environ.get("PORT", "8080"))


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


class Handler(BaseHTTPRequestHandler):
    # Hiljennetään BaseHTTPRequestHandlerin verbose-loggaus
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        log(f"{self.address_string()} - {format % args}")

    # ----- Apurit -----

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

    # ----- Reitit -----

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        if self.path == "/api/health":
            return self._write_json(
                200,
                {
                    "ok": True,
                    "service": "reveal-data-api",
                    "environment": "kipina-pilot",
                },
            )
        return self._write_json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/auth/check":
            return self._handle_auth_check()
        if self.path == "/api/idea":
            return self._handle_idea()
        return self._write_json(404, {"error": "not_found"})

    # ----- /api/auth/check -----

    def _handle_auth_check(self) -> None:
        body = self._read_json_body()
        if body is None:
            return self._write_json(400, {"error": "invalid_body"})

        code = body.get("code")
        if not isinstance(code, str) or not code:
            return self._write_json(400, {"error": "missing_code"})

        if not ACCESS_CODE:
            log(
                "WARNING: KIPINA_ACCESS_CODE not set — auth check disabled, "
                "rejecting all logins."
            )
            return self._write_json(401, {"ok": False})

        # secrets.compare_digest = ajallinen vakio, estää ajoitushyökkäykset
        if secrets.compare_digest(code, ACCESS_CODE):
            return self._write_json(200, {"ok": True})

        return self._write_json(401, {"ok": False})

    # ----- /api/idea -----

    def _handle_idea(self) -> None:
        body = self._read_json_body()
        if body is None:
            return self._write_json(400, {"error": "invalid_body"})

        session_id = body.get("session_id")
        message = body.get("message")

        if not isinstance(session_id, str) or not session_id:
            return self._write_json(400, {"error": "missing_session_id"})
        if not isinstance(message, str) or not message.strip():
            return self._write_json(400, {"error": "missing_message"})

        # Konfiguraatio palvelimelta
        if not REVEAL_ENGINE_BASE_URL or not REVEAL_ENGINE_TENANT_KEY or not REVEAL_ENGINE_API_KEY:
            log(
                "ERROR: Reveal Engine config missing (base_url/tenant_key/api_key)."
            )
            return self._write_json(503, {"error": "engine_not_configured"})

        # Soitto Cloud Runiin
        upstream_payload = {
            "session_id": session_id,
            "message": message,
            "tenant_key": REVEAL_ENGINE_TENANT_KEY,
            "api_key": REVEAL_ENGINE_API_KEY,
        }
        upstream_url = f"{REVEAL_ENGINE_BASE_URL}/chat"
        req = urllib.request.Request(
            upstream_url,
            data=json.dumps(upstream_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                req, timeout=REVEAL_ENGINE_TIMEOUT_SECONDS
            ) as resp:
                resp_body = resp.read()
                resp_status = resp.status
        except urllib.error.HTTPError as e:
            log(f"Reveal Engine HTTPError: {e.code} {e.reason}")
            return self._write_json(
                502, {"error": "engine_error", "status": e.code}
            )
        except urllib.error.URLError as e:
            log(f"Reveal Engine URLError: {e.reason}")
            return self._write_json(504, {"error": "engine_timeout"})

        try:
            data = json.loads(resp_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            log("Reveal Engine returned non-JSON body")
            return self._write_json(502, {"error": "engine_invalid_response"})

        # Suodatetaan vastaus — frontend ei tarvitse api_key/tenant_key takaisin
        # vaikka Cloud Run ei niitä palauta, varmistus.
        safe = {
            "reply": data.get("reply", ""),
            "session_id": data.get("session_id", session_id),
            "turn": data.get("turn", 0),
            "finished": bool(data.get("finished", False)),
            "report": data.get("report"),
        }
        return self._write_json(resp_status, safe)


def main() -> None:
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
