from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("ENVIRONMENT", "test")
BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402


PUBLIC_API_PATHS = {
    "/api/auth/google",
    "/api/auth/refresh",
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/health/dependencies",
}


def _schema_name(schema: dict[str, Any] | None) -> str:
    if not schema:
        return "Not declared"
    reference = schema.get("$ref")
    if reference:
        return reference.rsplit("/", 1)[-1]
    if "items" in schema:
        return f"Array[{_schema_name(schema['items'])}]"
    return schema.get("type", "inline schema")


def _request(operation: dict[str, Any]) -> str:
    parameters = []
    for item in operation.get("parameters", []):
        schema = item.get("schema", {})
        details = [
            item["in"],
            _schema_name(schema),
            "required" if item.get("required") else "optional",
        ]
        if "default" in schema:
            details.append(f"default={schema['default']}")
        parameters.append(f"{item['name']} ({', '.join(details)})")
    body = operation.get("requestBody", {}).get("content", {})
    for content_type, content in body.items():
        parameters.append(
            f"{content_type}"
            f"{' (required)' if operation['requestBody'].get('required') else ' (optional)'}"
            f": {_schema_name(content.get('schema'))}"
        )
    return ", ".join(parameters) if parameters else "None"


def _response(operation: dict[str, Any]) -> str:
    for code, response in operation.get("responses", {}).items():
        if code.startswith("2"):
            content = response.get("content", {}).get("application/json", {})
            schema = _schema_name(content.get("schema"))
            return f"{code}: {schema or 'No JSON body'}"
    return "Not declared"


def _errors(operation: dict[str, Any]) -> str:
    codes = sorted(
        code
        for code in operation.get("responses", {})
        if code[:1] in {"4", "5"}
    )
    return ", ".join(codes) if codes else "None documented"


def generate_frontend_reference() -> str:
    schema = app.openapi()
    operations = []
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete", "options"}:
                continue
            auth = (
                "Public"
                if not path.startswith("/api/") or path in PUBLIC_API_PATHS
                else "Bearer access token"
            )
            if path == "/api/metrics/summary":
                auth += " + `X-Admin-Token`"
            operations.append(
                (
                    method.upper(),
                    path,
                    auth,
                    _request(operation),
                    _response(operation),
                    _errors(operation),
                )
            )

    lines = [
        "# Frontend API Reference",
        "",
        "Generated from the registered FastAPI OpenAPI schema by "
        "`backend/scripts/generate_api_inventory.py`.",
        "",
        f"- OpenAPI version: {schema['openapi']}",
        f"- Paths: {len(schema['paths'])}",
        f"- Operations: {len(operations)}",
        "- Success envelope: `{ \"success\": true, \"data\": ... }`.",
        "- Error envelope: `{ \"success\": false, \"error\": "
        "{ \"code\": \"...\", \"message\": \"...\" } }`.",
        "- Authentication is derived from backend middleware; the OpenAPI "
        "schema currently has no `securitySchemes` declaration.",
        "- All `/api/*` operations require a bearer access token except the "
        "listed public authentication and health operations. "
        "`GET /api/metrics/summary` also requires `X-Admin-Token`.",
        "- Browser clients must use an origin included in `ALLOWED_ORIGINS`.",
        "- Follow request/response component names in `/openapi.json` for "
        "field-level schemas. An `Any` response leaves the inner `data` "
        "payload unspecified.",
        "",
        "| Method | Route | Auth | Request body / parameters | Success response | Common error statuses |",
        "|---|---|---|---|---|---|",
    ]
    for method, path, auth, request, response, errors in sorted(operations):
        lines.append(
            f"| {method} | `{path}` | {auth} | {request} | {response} | {errors} |"
        )
    return "\n".join(lines) + "\n"


def generate_inventory() -> str:
    schema = app.openapi()
    lines = [
        "# Backend API Inventory",
        "",
        "Generated from the registered FastAPI OpenAPI schema by `backend/scripts/generate_api_inventory.py`.",
        "",
        f"- Registered paths: {len(schema['paths'])}",
        f"- Registered operations: {sum(1 for item in schema['paths'].values() for method in item if method in {'get', 'post', 'put', 'patch', 'delete', 'options'})}",
        "- Success response format: `{ \"success\": true, \"data\": ... }`.",
        "- Error response format: `{ \"success\": false, \"error\": { \"code\": ..., \"message\": ... } }`.",
        "- All API routes require a bearer access token except public health, Google login, and refresh routes. `GET /api/metrics/summary` also requires `X-Admin-Token`.",
        "- The browser-origin allowlist is configured through comma-separated `ALLOWED_ORIGINS`; credentials are enabled and wildcard origins are rejected.",
        "",
        "| Method | Route | Authentication | Request parameters/body | Success response schema |",
        "|---|---|---|---|---|",
    ]
    operations = []
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete", "options"}:
                continue
            auth = "Public" if not path.startswith("/api/") or path in PUBLIC_API_PATHS else "Bearer access token"
            if path == "/api/metrics/summary":
                auth += " + X-Admin-Token"
            operations.append(
                (
                    method.upper(),
                    path,
                    auth,
                    _request(operation),
                    _response(operation),
                )
            )
    for method, path, auth, request, response in sorted(operations):
        lines.append(f"| {method} | `{path}` | {auth} | {request} | {response} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    outputs = {
        REPOSITORY_ROOT / "docs" / "API_INVENTORY.md": generate_inventory(),
        REPOSITORY_ROOT / "docs" / "FRONTEND_API_REFERENCE.md": generate_frontend_reference(),
    }
    for output, contents in outputs.items():
        output.write_text(contents, encoding="utf-8")
        print(f"Wrote {output.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
