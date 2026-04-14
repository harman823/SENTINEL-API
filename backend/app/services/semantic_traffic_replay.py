"""
Semantic traffic replay utilities.

Converts sanitized production-like traffic records into executable tests
and maps each replay request back to the closest OpenAPI operation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from backend.app.schemas.spec import NormalizedSpec, Operation


SENSITIVE_KEYS = {
    "password",
    "passcode",
    "token",
    "secret",
    "authorization",
    "cookie",
    "set-cookie",
    "api_key",
    "apikey",
    "client_secret",
    "ssn",
    "credit_card",
}

SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key", "proxy-authorization"}


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: Dict[str, Any] = {}
        for key, nested_value in value.items():
            if key.lower() in SENSITIVE_KEYS:
                sanitized[key] = "***redacted***"
            else:
                sanitized[key] = _sanitize_value(nested_value)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value


def _sanitize_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in (headers or {}).items():
        if key.lower() in SENSITIVE_HEADERS:
            sanitized[key] = "***redacted***"
        else:
            sanitized[key] = value
    return sanitized


def _path_segments(path: str) -> List[str]:
    return [segment for segment in (path or "").strip("/").split("/") if segment]


def _match_operation(spec: NormalizedSpec, method: str, request_path: str) -> Tuple[Optional[Operation], Dict[str, str]]:
    request_segments = _path_segments(request_path)
    exact = next(
        (op for op in spec.operations if op.method.lower() == method.lower() and op.path == request_path),
        None,
    )
    if exact:
        return exact, {}

    for op in spec.operations:
        if op.method.lower() != method.lower():
            continue
        template_segments = _path_segments(op.path)
        if len(template_segments) != len(request_segments):
            continue

        params: Dict[str, str] = {}
        matched = True
        for template, actual in zip(template_segments, request_segments):
            if template.startswith("{") and template.endswith("}"):
                params[template.strip("{}")] = actual
                continue
            if template != actual:
                matched = False
                break
        if matched:
            return op, params

    return None, {}


class SemanticTrafficReplay:
    """Build replay tests from real-world traffic samples."""

    @staticmethod
    def sanitize(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sanitized_records: List[Dict[str, Any]] = []
        for record in records or []:
            sanitized_records.append(
                {
                    "method": str(record.get("method", "GET")).upper(),
                    "path": record.get("path", "/"),
                    "query_params": _sanitize_value(record.get("query_params", {})),
                    "headers": _sanitize_headers(record.get("headers", {})),
                    "body": _sanitize_value(record.get("body")),
                    "status_code": record.get("status_code"),
                    "timestamp": record.get("timestamp"),
                }
            )
        return sanitized_records

    @staticmethod
    def to_test_cases(
        spec: NormalizedSpec,
        records: List[Dict[str, Any]],
        base_url: str = "http://localhost",
    ) -> List[Dict[str, Any]]:
        test_cases: List[Dict[str, Any]] = []
        for idx, record in enumerate(SemanticTrafficReplay.sanitize(records), start=1):
            method = record.get("method", "GET").upper()
            path = record.get("path", "/")
            status_code = record.get("status_code")

            op, matched_params = _match_operation(spec, method, path)
            expected_status = status_code
            if expected_status is None and op:
                success_codes = [
                    int(code)
                    for code in op.responses.keys()
                    if code.isdigit() and 200 <= int(code) < 300
                ]
                expected_status = success_codes[0] if success_codes else 200
            if expected_status is None:
                expected_status = 200

            tc_id = f"REPLAY_{idx}_{method}_{path.replace('/', '_').strip('_') or 'root'}"
            test_cases.append(
                {
                    "id": tc_id,
                    "operation_id": op.operationId if op else f"replay_{idx}",
                    "method": method,
                    "url": f"{base_url}{path}",
                    "path": op.path if op else path,
                    "query_params": record.get("query_params", {}),
                    "headers": record.get("headers", {}),
                    "body": record.get("body"),
                    "expected_status": expected_status,
                    "is_destructive": op.is_destructive if op else method in {"PUT", "PATCH", "DELETE"},
                    "risk_score": op.risk_score if op else None,
                    "test_type": "semantic_replay",
                    "reason": f"Replay from sanitized gateway traffic ({method} {path})",
                    "spec_reference": f"paths.{op.path}.{op.method}" if op else "paths.unknown",
                    "risk_coverage": ["real_world_traffic", "edge_case_reproduction"],
                    "assertions": [
                        {"type": "status_code", "expected": expected_status},
                        {"type": "response_time_ms", "max": 8000},
                    ],
                    "replay_metadata": {
                        "matched_operation": f"{op.method.upper()} {op.path}" if op else None,
                        "path_params": matched_params,
                        "source_timestamp": record.get("timestamp"),
                    },
                }
            )

        return test_cases
