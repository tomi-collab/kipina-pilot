from __future__ import annotations

import json
import os
import time
from typing import Any


PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
AGENT_ENGINE_ID = os.environ.get("AGENT_ENGINE_ID", "")
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
TTL_SECONDS = 3600
SANDBOX_CREATE_TIMEOUT_SECONDS = 60
SANDBOX_CREATE_POLL_SECONDS = 1.0

_client: Any | None = None


class AgentEngineError(Exception):
    status = 502
    error = "agent_engine_error"


class AgentEngineConfigError(AgentEngineError):
    status = 503
    error = "agent_engine_not_configured"


class AgentEngineQuotaError(AgentEngineError):
    status = 503
    error = "sandbox_quota_exceeded"


class AgentEngineTimeoutError(AgentEngineError):
    status = 504
    error = "sandbox_create_timeout"


def missing_config() -> list[str]:
    missing = []
    if not PROJECT_ID:
        missing.append("GCP_PROJECT_ID")
    if not LOCATION:
        missing.append("GCP_LOCATION")
    if not AGENT_ENGINE_ID:
        missing.append("AGENT_ENGINE_ID")
    if not GOOGLE_APPLICATION_CREDENTIALS:
        missing.append("GOOGLE_APPLICATION_CREDENTIALS")
    elif not os.path.isfile(GOOGLE_APPLICATION_CREDENTIALS):
        missing.append("GOOGLE_APPLICATION_CREDENTIALS file")
    return missing


def _require_config() -> None:
    missing = missing_config()
    if missing:
        raise AgentEngineConfigError("Missing Prototype API config: " + ", ".join(missing))


def _get_client() -> Any:
    global _client
    _require_config()
    if _client is None:
        # Agent Engine Code Execution is currently exposed through the
        # preview Vertex AI client surface. Mestari generates HTML directly
        # with Gemini in B1; this sandbox is created so later B-phases can add
        # actual browser/code validation without changing the public API.
        import vertexai

        _client = vertexai.Client(project=PROJECT_ID, location=LOCATION)
    return _client


def _extract_name(value: Any) -> str:
    if isinstance(value, str):
        return value
    for attr in ("name", "resource_name"):
        name = getattr(value, attr, None)
        if isinstance(name, str) and name:
            return name
    api_resource = getattr(value, "api_resource", None)
    if api_resource is not None:
        name = getattr(api_resource, "name", None)
        if isinstance(name, str) and name:
            return name
    response = getattr(value, "response", None)
    if response is not None:
        return _extract_name(response)
    raise AgentEngineError("Agent Engine response did not include sandbox name")


def _extract_sandbox_name(operation: Any) -> str | None:
    response = getattr(operation, "response", None)
    if response is None:
        return None
    name = getattr(response, "name", None)
    return name if isinstance(name, str) and name else None


def create_sandbox() -> str:
    """Create a Code Execution sandbox and return its resource name."""
    client = _get_client()
    try:
        from vertexai._genai.types import common

        operation = client.agent_engines.sandboxes.create(
            name=AGENT_ENGINE_ID,
            poll_interval_seconds=SANDBOX_CREATE_POLL_SECONDS,
            spec=common.SandboxEnvironmentSpec(
                codeExecutionEnvironment=common.SandboxEnvironmentSpecCodeExecutionEnvironment(
                    codeLanguage=common.Language.LANGUAGE_JAVASCRIPT,
                    machineConfig=common.MachineConfig.MACHINE_CONFIG_VCPU4_RAM4GIB,
                )
            ),
            config=common.CreateAgentEngineSandboxConfig(
                displayName="kipina-prototype-b1",
                ttl=f"{TTL_SECONDS}s",
                waitForCompletion=False,
            ),
        )
        operation_name = _extract_name(operation)
        print(f"operation started: {operation_name}", flush=True)

        deadline = time.monotonic() + SANDBOX_CREATE_TIMEOUT_SECONDS
        while not getattr(operation, "done", False):
            if time.monotonic() >= deadline:
                raise AgentEngineTimeoutError(
                    f"Sandbox create operation did not complete within {SANDBOX_CREATE_TIMEOUT_SECONDS}s"
                )
            time.sleep(SANDBOX_CREATE_POLL_SECONDS)
            operation = client.agent_engines.sandboxes._get_sandbox_operation(
                operation_name=operation_name,
            )

        error = getattr(operation, "error", None)
        if error:
            raise AgentEngineError(f"Sandbox create operation failed: {error}")

        sandbox_name = _extract_sandbox_name(operation)
        if not sandbox_name:
            raise AgentEngineError("Sandbox create operation completed without sandbox name")
        print(f"operation completed: {sandbox_name}", flush=True)
        return sandbox_name
    except Exception as exc:
        if isinstance(exc, AgentEngineError):
            raise
        detail = str(exc).lower()
        if "quota" in detail or "resource exhausted" in detail:
            raise AgentEngineQuotaError(str(exc)[:240]) from exc
        raise AgentEngineError(str(exc)[:240]) from exc


def execute_code(sandbox_id: str, code: str) -> dict[str, Any]:
    """Run code in a sandbox. B1 does not call this yet."""
    client = _get_client()
    try:
        response = client.agent_engines.sandboxes.execute_code(
            name=sandbox_id,
            input_data={"code": code},
        )
    except Exception as exc:
        raise AgentEngineError(str(exc)[:240]) from exc

    outputs = []
    for output in getattr(response, "outputs", []) or []:
        data = getattr(output, "data", b"")
        if isinstance(data, bytes):
            text = data.decode("utf-8", errors="replace")
        else:
            text = str(data)
        try:
            outputs.append(json.loads(text))
        except ValueError:
            outputs.append({"text": text})
    return {"outputs": outputs}


def delete_sandbox(sandbox_id: str) -> None:
    client = _get_client()
    try:
        client.agent_engines.sandboxes.delete(name=sandbox_id)
    except Exception as exc:
        raise AgentEngineError(str(exc)[:240]) from exc
