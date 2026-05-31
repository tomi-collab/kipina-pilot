from __future__ import annotations

import concurrent.futures
import json
import os
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import unquote, urlparse

import mestari
import sandbox_state


PORT = int(os.environ.get("PORT", "8080"))
CORS_ORIGIN = "https://pilot.kipina.digiter.fi"
TEMPLATES_PATH = os.environ.get("TEMPLATES_PATH", "/app/templates.json")
MAX_BODY_BYTES = 160 * 1024
MAX_REPORT_CHARS = 50_000
MAX_USER_INPUT_CHARS = 5_000
TTL_SECONDS = 3600
START_TIMEOUT_SECONDS = int(os.environ.get("START_TIMEOUT_SECONDS", os.environ.get("GEMINI_TIMEOUT_SECONDS", "180")))
ITERATE_TIMEOUT_SECONDS = int(os.environ.get("ITERATE_TIMEOUT_SECONDS", os.environ.get("GEMINI_TIMEOUT_SECONDS", "90")))

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
_template_ids: set[str] | None = None


def log(message: str) -> None:
    print(message, file=sys.stdout, flush=True)


def _detail(exc: Exception) -> str:
    return str(exc)[:240] or exc.__class__.__name__


def _load_template_ids() -> set[str]:
    global _template_ids
    if _template_ids is None:
        try:
            with open(TEMPLATES_PATH, encoding="utf-8") as file:
                data = json.load(file)
        except OSError as exc:
            raise RuntimeError(f"templates metadata missing: {TEMPLATES_PATH}") from exc
        templates = data.get("templates")
        if not isinstance(templates, list):
            raise RuntimeError("templates metadata must include a templates list")
        ids = {
            item.get("id")
            for item in templates
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if not ids:
            raise RuntimeError("templates metadata includes no valid template ids")
        _template_ids = ids
    return _template_ids


def _validate_suggested_templates(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    allowed = _load_template_ids()
    result = []
    for item in value:
        if isinstance(item, str) and item in allowed and item not in result:
            result.append(item)
    return result


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def _log_request(
        self,
        status: int,
        elapsed_ms: float,
        sandbox_id: str | None = None,
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        path = urlparse(self.path).path
        suffix = f" sandbox_id={sandbox_id}" if sandbox_id else ""
        log(f"{timestamp} {self.command} {path} {status} {elapsed_ms:.1f}ms{suffix}")

    def _send_json(self, status: int, payload: dict[str, Any]) -> int:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
        self.end_headers()
        self.wfile.write(body)
        return status

    def _send_no_content(self) -> int:
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
        self.end_headers()
        return 204

    def _send_cors_preflight(self) -> int:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
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
            if path == "/api/prototype/health":
                status = self._send_json(
                    200,
                    {"ok": True, "service": "kipina-prototype-api"},
                )
            else:
                status = self._send_json(404, {"error": "not_found"})
        finally:
            self._log_request(status, (time.perf_counter() - start) * 1000)

    def do_POST(self) -> None:  # noqa: N802
        start = time.perf_counter()
        status = 500
        sandbox_id = None
        try:
            path = urlparse(self.path).path
            if path == "/api/prototype/start":
                status, sandbox_id = self._handle_start()
                return
            if path == "/api/prototype/iterate":
                status, sandbox_id = self._handle_iterate()
                return
            if path == "/api/prototype/undo":
                status, sandbox_id = self._handle_undo()
                return
            status = self._send_json(404, {"error": "not_found"})
        finally:
            self._log_request(status, (time.perf_counter() - start) * 1000, sandbox_id)

    def do_DELETE(self) -> None:  # noqa: N802
        start = time.perf_counter()
        status = 500
        sandbox_id = None
        try:
            path = urlparse(self.path).path
            prefix = "/api/prototype/"
            if not path.startswith(prefix) or path == prefix:
                status = self._send_json(404, {"error": "not_found"})
                return
            sandbox_id = unquote(path[len(prefix):].strip("/"))
            if not sandbox_id:
                status = self._send_json(404, {"error": "not_found"})
                return
            sandbox_state.delete_session(sandbox_id)
            status = self._send_no_content()
        finally:
            self._log_request(status, (time.perf_counter() - start) * 1000, sandbox_id)

    def _bad_request(self, error: str, detail: str) -> tuple[int, None]:
        return self._send_json(400, {"error": error, "detail": detail}), None

    def _cleanup_start_sandbox(self, sandbox_id: str | None) -> None:
        if not sandbox_id:
            return
        sandbox_state.delete_session(sandbox_id)

    def _handle_start(self) -> tuple[int, str | None]:
        body = self._read_json_body()
        if body is None:
            return self._bad_request("invalid_body", "Request body must be JSON.")

        concept = body.get("concept")
        report = body.get("report")
        vibe = body.get("vibe")
        tenant_id = body.get("tenant_id")
        session_id = body.get("session_id")
        suggested_templates = _validate_suggested_templates(body.get("suggested_templates"))

        if (concept is None or report is None) and isinstance(vibe, str) and vibe.strip():
            concept = concept if concept is not None else vibe
            report = report if report is not None else vibe

        concept_error = _validate_text(concept, "concept", MAX_REPORT_CHARS)
        if concept_error:
            return self._bad_request("invalid_concept", concept_error)
        report_error = _validate_text(report, "report", MAX_REPORT_CHARS)
        if report_error:
            return self._bad_request("invalid_report", report_error)

        session_text = session_id if isinstance(session_id, str) and session_id else ""
        tenant_text = tenant_id if isinstance(tenant_id, str) and tenant_id else None
        sandbox_id = f"kipina-{uuid.uuid4().hex}"
        try:
            sandbox_state.create_session(
                sandbox_id=sandbox_id,
                session_id=session_text,
                tenant_id=tenant_text,
                concept=concept.strip(),
                report=report.strip(),
                suggested_templates=suggested_templates,
            )
            future = _executor.submit(
                mestari.create_initial_prototype,
                concept.strip(),
                report.strip(),
                "fi",
                sandbox_id,
                suggested_templates,
            )
            data = future.result(timeout=START_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            log("Mestari initial prototype timed out.")
            if "future" in locals():
                future.cancel()
            self._cleanup_start_sandbox(sandbox_id)
            return self._send_json(
                504,
                {"error": "start_timeout", "detail": "Sovelluksen luonti kesti liian kauan. Yritä uudelleen."},
            ), sandbox_id
        except Exception as exc:
            log("Mestari initial prototype failed:")
            traceback.print_exc(file=sys.stdout)
            self._cleanup_start_sandbox(sandbox_id)
            return self._send_json(
                502,
                {"error": "start_failed", "detail": "Sovelluksen luonti epäonnistui. Yritä uudelleen."},
            ), sandbox_id

        html = data["prototype_html"]
        message = data["mestari_message"]
        sandbox_state.add_html_version(sandbox_id, html)
        sandbox_state.add_iteration(sandbox_id, "initial", message)
        return self._send_json(
            200,
            {
                "sandbox_id": sandbox_id,
                "prototype_html": html,
                "mestari_message": message,
                "ttl_seconds": TTL_SECONDS,
            },
        ), sandbox_id

    def _handle_iterate(self) -> tuple[int, str | None]:
        body = self._read_json_body()
        if body is None:
            return self._bad_request("invalid_body", "Request body must be JSON.")
        sandbox_id = body.get("sandbox_id")
        mode = body.get("mode")
        user_input = body.get("user_input")
        language = body.get("language", "fi")

        if not isinstance(sandbox_id, str) or not sandbox_id.strip():
            return self._bad_request("invalid_sandbox_id", "sandbox_id is required.")
        sandbox_id = sandbox_id.strip()
        session = sandbox_state.get_session(sandbox_id)
        if session is None:
            return self._send_json(404, {"error": "sandbox_not_found"}), sandbox_id
        if mode not in (None, "", "iterate", "koodaus", "pohdinta"):
            log(f"Prototype iterate ignoring unknown mode: {mode!r}")
        input_error = _validate_text(user_input, "user_input", MAX_USER_INPUT_CHARS)
        if input_error:
            return self._bad_request("invalid_user_input", input_error)
        if language != "en":
            language = "fi"

        current_html = session["html_history"][-1] if session["html_history"] else ""
        if not current_html:
            return self._send_json(409, {"error": "prototype_missing"}), sandbox_id

        try:
            future = _executor.submit(
                mestari.iterate,
                current_html,
                session["recent_iterations"],
                user_input.strip(),
                session["concept"],
                session["report"],
                language,
                sandbox_id,
                session.get("suggested_templates", []),
            )
            data = future.result(timeout=ITERATE_TIMEOUT_SECONDS)
            prototype_html = data.get("prototype_html")
            changed = isinstance(prototype_html, str) and bool(prototype_html.strip())
            warning = data.get("concept_drift_warning")
            if warning and session.get("concept_drift_warned"):
                warning = None
            elif warning:
                sandbox_state.mark_drift_warned(sandbox_id)
            if changed:
                sandbox_state.add_html_version(sandbox_id, prototype_html)
            iteration_count = sandbox_state.increment_iteration(sandbox_id)
            sandbox_state.add_iteration(sandbox_id, user_input.strip(), data["mestari_message"])
            status = self._send_json(
                200,
                {
                    "prototype_html": prototype_html if changed else None,
                    "mestari_message": data["mestari_message"],
                    "iteration_count": iteration_count,
                    "changed": changed,
                    "concept_drift_warning": warning,
                },
            )
            return status, sandbox_id
        except Exception as exc:
            log("Mestari iteration failed:")
            traceback.print_exc(file=sys.stdout)
            return self._send_json(
                502,
                {"error": "iteration_failed", "detail": _detail(exc)},
            ), sandbox_id

    def _handle_undo(self) -> tuple[int, str | None]:
        body = self._read_json_body()
        if body is None:
            return self._bad_request("invalid_body", "Request body must be JSON.")
        sandbox_id = body.get("sandbox_id")
        if not isinstance(sandbox_id, str) or not sandbox_id.strip():
            return self._bad_request("invalid_sandbox_id", "sandbox_id is required.")
        sandbox_id = sandbox_id.strip()
        if sandbox_state.get_session(sandbox_id) is None:
            return self._send_json(404, {"error": "sandbox_not_found"}), sandbox_id
        html = sandbox_state.pop_last_html_version(sandbox_id)
        if html is None:
            return self._send_json(
                400,
                {
                    "error": "no_undo_available",
                    "message": "Tämä on ensimmäinen versio, ei voi peruuttaa.",
                },
            ), sandbox_id
        iteration_count = sandbox_state.increment_iteration(sandbox_id)
        sandbox_state.add_iteration(sandbox_id, "undo", "Palautin edellisen.")
        sandbox_state.set_last_action(sandbox_id, "undo")
        session = sandbox_state.get_session(sandbox_id)
        undo_available = bool(session and len(session["html_history"]) > 1)
        return self._send_json(
            200,
            {
                "prototype_html": html,
                "mestari_message": "Palautin edellisen.",
                "iteration_count": iteration_count,
                "undo_available": undo_available,
            },
        ), sandbox_id


def _validate_text(value: Any, name: str, max_chars: int) -> str | None:
    if not isinstance(value, str):
        return f"{name} must be a string."
    if not value.strip():
        return f"{name} must not be empty."
    if len(value) > max_chars:
        return f"{name} must be at most {max_chars} characters."
    return None


def main() -> None:
    _load_template_ids()
    log(
        "kipina-prototype-api starting "
        f"model={mestari.GEMINI_MODEL} project={mestari.GCP_PROJECT_ID or '-'} "
        f"location={mestari.GCP_LOCATION} sandbox_id=uuid"
    )
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    log(f"kipina-prototype-api listening on 0.0.0.0:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("shutting down")
    finally:
        server.server_close()
        _executor.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    main()
