from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

import analyze as analyze_template
import rate_limit


PORT = int(os.environ.get("PORT", "8080"))
MAX_BODY_BYTES = 32 * 1024
MAX_QUESTION_CHARS = 500
MAX_OPTION_CHARS = 500
MAX_OPTIONS = 10
ALLOWED_LANGUAGES = {"fi", "en"}


def log(message: str) -> None:
    print(message, file=sys.stdout, flush=True)


def _cors_origin(origin: str | None) -> str:
    if origin == "null":
        return "null"
    if origin == "https://pilot.kipina.digiter.fi":
        return origin
    return "*"


def _validate_payload(data: dict[str, Any]) -> tuple[dict[str, Any] | None, tuple[str, str] | None]:
    question = data.get("question")
    if not isinstance(question, str) or not question.strip():
        return None, ("validation_error", "question is required")
    question = question.strip()
    if len(question) > MAX_QUESTION_CHARS:
        return None, ("validation_error", "question must be at most 500 characters")

    options = data.get("options")
    if not isinstance(options, list) or not options:
        return None, ("validation_error", "options must contain 1-10 strings")
    if len(options) > MAX_OPTIONS:
        return None, ("validation_error", "options must contain at most 10 items")

    normalized_options = []
    for option in options:
        if not isinstance(option, str) or not option.strip():
            return None, ("validation_error", "each option must be a non-empty string")
        option = option.strip()
        if len(option) > MAX_OPTION_CHARS:
            return None, ("validation_error", "each option must be at most 500 characters")
        normalized_options.append(option)

    analysis_type = data.get("analysis_type")
    if analysis_type not in analyze_template.ALLOWED_ANALYSIS_TYPES:
        return None, ("validation_error", "analysis_type must be pros_cons, ranking, advice or summary")

    language = data.get("language", "fi")
    if language not in ALLOWED_LANGUAGES:
        return None, ("validation_error", "language must be fi or en")

    return {
        "question": question,
        "options": normalized_options,
        "analysis_type": analysis_type,
        "language": language,
    }, None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def _log_request(
        self,
        status: int,
        elapsed_ms: float,
        sandbox_id: str | None = None,
        rate_status: str | None = None,
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        path = urlparse(self.path).path
        parts = [
            timestamp,
            self.command,
            path,
            str(status),
            f"{elapsed_ms:.1f}ms",
        ]
        if sandbox_id:
            parts.append(f"sandbox_id={sandbox_id}")
        if rate_status:
            parts.append(f"rate={rate_status}")
        log(" ".join(parts))

    def _send_json(self, status: int, payload: dict[str, Any]) -> int:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self.headers.get("Origin")))
        self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)
        return status

    def _send_no_content(self, status: int = 204) -> int:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self.headers.get("Origin")))
        self.send_header("Vary", "Origin")
        self.end_headers()
        return status

    def _send_cors_preflight(self) -> int:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", _cors_origin(self.headers.get("Origin")))
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Kipina-Sandbox-Id")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Vary", "Origin")
        self.send_header("Content-Length", "0")
        self.end_headers()
        return 204

    def _read_json_body(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            return None
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

    def do_OPTIONS(self) -> None:  # noqa: N802
        start = time.perf_counter()
        status = 500
        try:
            status = self._send_cors_preflight()
        finally:
            self._log_request(status, (time.perf_counter() - start) * 1000)

    def do_GET(self) -> None:  # noqa: N802
        start = time.perf_counter()
        status = 500
        try:
            path = urlparse(self.path).path
            if path == "/api/templates/health":
                status = self._send_json(
                    200,
                    {"ok": True, "service": "kipina-template-proxy", "templates": ["analyze"]},
                )
            else:
                status = self._send_json(404, {"error": "not_found"})
        finally:
            self._log_request(status, (time.perf_counter() - start) * 1000)

    def do_POST(self) -> None:  # noqa: N802
        start = time.perf_counter()
        status = 500
        sandbox_id = self.headers.get("X-Kipina-Sandbox-Id", "").strip()
        rate_status = None
        try:
            path = urlparse(self.path).path
            if path != "/api/templates/analyze":
                status = self._send_json(404, {"error": "not_found"})
                return

            if not sandbox_id:
                status = self._send_json(
                    400,
                    {"error": "validation_error", "detail": "X-Kipina-Sandbox-Id header is required"},
                )
                return

            data = self._read_json_body()
            if data is None:
                status = self._send_json(
                    400,
                    {"error": "invalid_json", "detail": "Request body must be a JSON object"},
                )
                return

            payload, error = _validate_payload(data)
            if error:
                status = self._send_json(400, {"error": error[0], "detail": error[1]})
                return

            retry_after = rate_limit.check_global()
            if retry_after is not None:
                rate_status = "rate_limited"
                status = self._send_json(
                    429,
                    {"error": "rate_limited", "retry_after_seconds": retry_after},
                )
                return

            retry_after = rate_limit.check(sandbox_id)
            if retry_after is not None:
                rate_status = "rate_limited"
                status = self._send_json(
                    429,
                    {"error": "rate_limited", "retry_after_seconds": retry_after},
                )
                return
            rate_status = "ok"

            assert payload is not None
            result = analyze_template.analyze(
                question=payload["question"],
                options=payload["options"],
                analysis_type=payload["analysis_type"],
                language=payload["language"],
            )
            status = self._send_json(200, result)
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            status = self._send_json(
                502,
                {"error": "gemini_error", "detail": str(exc)},
            )
        finally:
            self._log_request(
                status,
                (time.perf_counter() - start) * 1000,
                sandbox_id=sandbox_id or None,
                rate_status=rate_status,
            )


def main() -> None:
    log(
        "kipina-template-proxy starting "
        f"port={PORT} project={os.environ.get('GCP_PROJECT_ID', '')} "
        f"location={os.environ.get('TEMPLATE_PROXY_LOCATION', 'us-central1')} "
        f"model={os.environ.get('TEMPLATE_GEMINI_MODEL', 'gemini-2.5-flash')}"
    )
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
