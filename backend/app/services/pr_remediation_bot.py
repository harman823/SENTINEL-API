"""
PR remediation helper for drift auto-fixes.

Builds pull-request payload suggestions from remediation outputs.
"""

from __future__ import annotations

import copy
import difflib
import json
import re
from typing import Any, Dict, List, Optional, Tuple

import yaml


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "endpoint"


class PRRemediationBot:
    """Generate PR-ready metadata from drift remediation results."""

    @staticmethod
    def build_suggestions(
        remediation_results: List[Dict[str, Any]],
        spec_path: str = "openapi.yaml",
        base_branch: str = "main",
        repo: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        suggestions: List[Dict[str, Any]] = []
        for idx, remediation in enumerate(remediation_results, start=1):
            endpoint = remediation.get("endpoint", "unknown-endpoint")
            status = remediation.get("status", "remediation_pending")
            patch_text = str(remediation.get("patch_proposed", ""))
            branch = f"bot/drift-{_slugify(endpoint)}-{idx}"

            title = f"chore(openapi): remediate contract drift for {endpoint}"
            body_lines = [
                "Automated drift remediation proposal.",
                "",
                f"Endpoint: `{endpoint}`",
                f"Status: `{status}`",
                "",
                "Suggested patch:",
                "```json",
                patch_text[:5000],
                "```",
            ]

            suggestion = {
                "endpoint": endpoint,
                "title": title,
                "branch": branch,
                "base_branch": base_branch,
                "repo": repo,
                "status": status,
                "ready_for_pr": status in {"remediated_locally", "patch_ready"} and bool(patch_text.strip()),
                "files": [
                    {
                        "path": spec_path,
                        "action": "update",
                        "patch_preview": patch_text[:2000],
                    }
                ],
                "body": "\n".join(body_lines),
            }
            suggestions.append(suggestion)

        return suggestions


class DriftRemediationPatchBuilder:
    """Build and apply deterministic OpenAPI remediation patches for drift reports."""

    @staticmethod
    def build(
        spec_raw: Dict[str, Any],
        drift_results: List[Dict[str, Any]],
        test_cases: Optional[List[Dict[str, Any]]] = None,
        execution_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
        remediation_results: List[Dict[str, Any]] = []
        all_operations: List[Dict[str, Any]] = []
        test_cases = test_cases or []
        execution_results = execution_results or []

        for drift_report in drift_results:
            endpoint = str(drift_report.get("endpoint", "unknown-endpoint"))
            test_id = str(drift_report.get("test_id", ""))
            method, path = DriftRemediationPatchBuilder._parse_endpoint(endpoint)
            if not method or not path:
                remediation_results.append(
                    DriftRemediationPatchBuilder._pending_result(
                        endpoint,
                        test_id,
                        "Could not parse endpoint from drift report.",
                    )
                )
                continue

            status_code = DriftRemediationPatchBuilder._actual_status(test_id, execution_results)
            if status_code is None:
                status_code = DriftRemediationPatchBuilder._expected_status(test_id, test_cases)
            operations: List[Dict[str, Any]] = []
            code_hints: List[Dict[str, str]] = []
            notes: List[str] = []

            for drift in drift_report.get("drifts", []):
                drift_type = str(drift.get("drift_type", ""))
                if drift_type == "status_code_mismatch":
                    op = DriftRemediationPatchBuilder._status_code_patch(spec_raw, path, method, drift)
                    if op:
                        operations.append(op)
                    else:
                        notes.append(f"No OpenAPI response container found for {endpoint}.")
                    continue

                if drift_type == "extra_field":
                    op = DriftRemediationPatchBuilder._extra_field_patch(
                        spec_raw,
                        path,
                        method,
                        status_code,
                        drift,
                    )
                    if op:
                        operations.append(op)
                    else:
                        notes.append(f"No JSON response schema found for {endpoint}; cannot add extra field.")
                    continue

                if drift_type == "type_mismatch":
                    op = DriftRemediationPatchBuilder._type_mismatch_patch(
                        spec_raw,
                        path,
                        method,
                        status_code,
                        drift,
                    )
                    if op:
                        operations.append(op)
                    else:
                        notes.append(f"No schema property found for {endpoint}; cannot replace field type.")
                    continue

                if drift_type in {"missing_field", "null_unexpected"}:
                    field_name = DriftRemediationPatchBuilder._field_name(drift.get("field_path"))
                    code_hints.append(
                        {
                            "field": field_name,
                            "target": "python",
                            "suggestion": (
                                f"Update the {endpoint} handler to always return non-null field "
                                f"'{field_name}' because it is required by the OpenAPI contract."
                            ),
                            "code_snippet": (
                                "# Ensure the response payload includes the required contract field.\n"
                                f"payload['{field_name}'] = payload.get('{field_name}') or <computed_{field_name}_value>"
                            ),
                        }
                    )

            patch = {
                "endpoint": endpoint,
                "test_id": test_id,
                "target": "openapi",
                "format": "json_patch",
                "operations": operations,
                "code_hints": code_hints,
                "notes": notes,
            }
            status = "patch_ready" if operations else "code_fix_required" if code_hints else "remediation_pending"
            remediation_results.append(
                {
                    "endpoint": endpoint,
                    "test_id": test_id,
                    "status": status,
                    "patch_proposed": json.dumps(operations, indent=2),
                    "remediation_patch": patch,
                    "message": DriftRemediationPatchBuilder._message(status, operations, code_hints),
                }
            )
            all_operations.extend(operations)

        remediation_patch: Optional[Dict[str, Any]] = None
        suggested_diff: Optional[str] = None
        if all_operations:
            remediation_patch = {
                "target": "openapi",
                "format": "json_patch",
                "operations": all_operations,
            }
            suggested_diff = DriftRemediationPatchBuilder.diff_for_patch(spec_raw, remediation_patch)

        return remediation_results, remediation_patch, suggested_diff

    @staticmethod
    def diff_for_patch(spec_raw: Dict[str, Any], remediation_patch: Dict[str, Any]) -> str:
        updated = DriftRemediationPatchBuilder.apply_to_spec(spec_raw, remediation_patch)
        before = yaml.safe_dump(spec_raw, sort_keys=False).splitlines(keepends=True)
        after = yaml.safe_dump(updated, sort_keys=False).splitlines(keepends=True)
        return "".join(
            difflib.unified_diff(before, after, fromfile="openapi.before.yaml", tofile="openapi.after.yaml")
        )

    @staticmethod
    def apply_to_spec(spec_raw: Dict[str, Any], remediation_patch: Dict[str, Any]) -> Dict[str, Any]:
        updated = copy.deepcopy(spec_raw)
        for operation in remediation_patch.get("operations", []):
            DriftRemediationPatchBuilder._apply_operation(updated, operation)
        return updated

    @staticmethod
    def _parse_endpoint(endpoint: str) -> Tuple[Optional[str], Optional[str]]:
        parts = endpoint.strip().split(maxsplit=1)
        if len(parts) != 2:
            return None, None
        return parts[0].lower(), parts[1]

    @staticmethod
    def _actual_status(test_id: str, execution_results: List[Dict[str, Any]]) -> Optional[str]:
        for result in execution_results:
            if result.get("test_id") == test_id and result.get("status_code") is not None:
                return str(result["status_code"])
        return None

    @staticmethod
    def _expected_status(test_id: str, test_cases: List[Dict[str, Any]]) -> Optional[str]:
        for test_case in test_cases:
            if test_case.get("id") == test_id and test_case.get("expected_status") is not None:
                return str(test_case["expected_status"])
        return None

    @staticmethod
    def _status_code_patch(
        spec_raw: Dict[str, Any],
        path: str,
        method: str,
        drift: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        actual_code = DriftRemediationPatchBuilder._first_int(str(drift.get("actual", "")))
        if actual_code is None:
            return None
        responses = spec_raw.get("paths", {}).get(path, {}).get(method, {}).get("responses")
        if not isinstance(responses, dict):
            return None
        source_response = responses.get("default") or responses.get("200") or next(iter(responses.values()), {})
        value = copy.deepcopy(source_response) if isinstance(source_response, dict) else {}
        value.setdefault("description", f"Documented response observed during drift detection ({actual_code}).")
        return {
            "op": "add" if str(actual_code) not in responses else "replace",
            "path": DriftRemediationPatchBuilder._pointer(["paths", path, method, "responses", str(actual_code)]),
            "value": value,
        }

    @staticmethod
    def _extra_field_patch(
        spec_raw: Dict[str, Any],
        path: str,
        method: str,
        status_code: Optional[str],
        drift: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        schema_path = DriftRemediationPatchBuilder._schema_path(spec_raw, path, method, status_code)
        if not schema_path:
            return None
        field_name = DriftRemediationPatchBuilder._field_name(drift.get("field_path"))
        value_type = DriftRemediationPatchBuilder._json_schema_type(str(drift.get("actual", "")))
        return {
            "op": "add",
            "path": DriftRemediationPatchBuilder._pointer(schema_path + ["properties", field_name]),
            "value": {"type": value_type},
        }

    @staticmethod
    def _type_mismatch_patch(
        spec_raw: Dict[str, Any],
        path: str,
        method: str,
        status_code: Optional[str],
        drift: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        schema_path = DriftRemediationPatchBuilder._schema_path(spec_raw, path, method, status_code)
        if not schema_path:
            return None
        field_name = DriftRemediationPatchBuilder._field_name(drift.get("field_path"))
        actual_type = DriftRemediationPatchBuilder._json_schema_type(str(drift.get("actual", "")))
        return {
            "op": "replace",
            "path": DriftRemediationPatchBuilder._pointer(schema_path + ["properties", field_name, "type"]),
            "value": actual_type,
        }

    @staticmethod
    def _schema_path(
        spec_raw: Dict[str, Any],
        path: str,
        method: str,
        status_code: Optional[str],
    ) -> Optional[List[str]]:
        responses = spec_raw.get("paths", {}).get(path, {}).get(method, {}).get("responses", {})
        if not isinstance(responses, dict) or not responses:
            return None
        response_code = status_code if status_code in responses else "200" if "200" in responses else next(iter(responses))
        content = responses.get(response_code, {}).get("content", {})
        if not isinstance(content, dict):
            return None
        for content_type, media in content.items():
            if "json" in content_type and isinstance(media, dict) and isinstance(media.get("schema"), dict):
                return ["paths", path, method, "responses", response_code, "content", content_type, "schema"]
        return None

    @staticmethod
    def _field_name(field_path: Any) -> str:
        value = str(field_path or "").strip(".")
        return value.split(".")[-1] if value else "field"

    @staticmethod
    def _json_schema_type(value: str) -> str:
        lowered = value.lower()
        if "bool" in lowered:
            return "boolean"
        if "int" in lowered:
            return "integer"
        if "float" in lowered or "number" in lowered:
            return "number"
        if "list" in lowered or "array" in lowered:
            return "array"
        if "dict" in lowered or "object" in lowered:
            return "object"
        return "string"

    @staticmethod
    def _first_int(value: str) -> Optional[int]:
        match = re.search(r"\d{3}", value)
        return int(match.group(0)) if match else None

    @staticmethod
    def _pointer(parts: List[str]) -> str:
        escaped = [part.replace("~", "~0").replace("/", "~1") for part in parts]
        return "/" + "/".join(escaped)

    @staticmethod
    def _apply_operation(document: Dict[str, Any], operation: Dict[str, Any]) -> None:
        op = operation.get("op")
        path = str(operation.get("path", ""))
        if op not in {"add", "replace"} or not path.startswith("/"):
            raise ValueError(f"Unsupported remediation operation: {operation}")
        parts = [part.replace("~1", "/").replace("~0", "~") for part in path.lstrip("/").split("/")]
        target: Any = document
        for part in parts[:-1]:
            if not isinstance(target, dict):
                raise ValueError(f"Cannot traverse non-object at '{part}' for patch path '{path}'")
            target = target.setdefault(part, {})
        if not isinstance(target, dict):
            raise ValueError(f"Cannot apply patch at non-object path '{path}'")
        key = parts[-1]
        if op == "replace" and key not in target:
            raise ValueError(f"Cannot replace missing path '{path}'")
        target[key] = copy.deepcopy(operation.get("value"))

    @staticmethod
    def _pending_result(endpoint: str, test_id: str, message: str) -> Dict[str, Any]:
        return {
            "endpoint": endpoint,
            "test_id": test_id,
            "status": "remediation_pending",
            "patch_proposed": "[]",
            "remediation_patch": {
                "endpoint": endpoint,
                "test_id": test_id,
                "target": "openapi",
                "format": "json_patch",
                "operations": [],
                "code_hints": [],
                "notes": [message],
            },
            "message": message,
        }

    @staticmethod
    def _message(
        status: str,
        operations: List[Dict[str, Any]],
        code_hints: List[Dict[str, str]],
    ) -> str:
        if status == "patch_ready":
            return f"Generated {len(operations)} OpenAPI patch operation(s)."
        if status == "code_fix_required":
            return f"Generated {len(code_hints)} backend code fix hint(s)."
        return "No deterministic remediation patch could be generated."
