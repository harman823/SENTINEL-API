"""
Contract Drift Detector — compares actual API responses against OpenAPI spec.
Detects when backend behavior no longer matches the documented contract.
"""

from typing import Dict, Any, List, Optional, Set
from backend.app.schemas.models import DriftReport, DriftItem, DriftType
from backend.app.schemas.spec import NormalizedSpec


class DriftDetector:
    """
    Compare API execution results against the OpenAPI spec to detect drifts.
    Only meaningful when running against a live API (not dry-run).
    """

    @staticmethod
    def detect(
        spec: NormalizedSpec,
        test_cases: List[Dict[str, Any]],
        execution_results: List[Dict[str, Any]],
    ) -> List[DriftReport]:
        """Detect all drifts between spec and actual responses."""
        exec_by_id: Dict[str, Dict[str, Any]] = {
            er.get("test_id", ""): er for er in execution_results
        }
        tc_by_id: Dict[str, Dict[str, Any]] = {
            tc.get("id", ""): tc for tc in test_cases
        }

        reports: List[DriftReport] = []

        for tc_id, tc in tc_by_id.items():
            er = exec_by_id.get(tc_id)
            if not er or er.get("dry_run") or er.get("error"):
                continue  # Skip dry-run or failed executions

            drifts = DriftDetector._check_single(spec, tc, er)
            if drifts:
                reports.append(DriftReport(
                    endpoint=f"{tc.get('method', '?')} {tc.get('path', '?')}",
                    test_id=tc_id,
                    drifts=drifts,
                    is_breaking=any(
                        d.drift_type in (DriftType.STATUS_CODE_MISMATCH, DriftType.MISSING_FIELD)
                        for d in drifts
                    ),
                ))

        return reports

    @staticmethod
    def _check_single(
        spec: NormalizedSpec,
        test_case: Dict[str, Any],
        exec_result: Dict[str, Any],
    ) -> List[DriftItem]:
        """Check a single test case execution for spec drifts."""
        drifts: List[DriftItem] = []
        path = test_case.get("path", "")
        method = test_case.get("method", "").lower()

        # Find the matching operation in spec
        op = None
        for spec_op in spec.operations:
            if spec_op.path == path and spec_op.method == method:
                op = spec_op
                break

        if not op:
            return drifts

        # ── Status Code Drift ──
        actual_status = exec_result.get("status_code")
        if actual_status is not None:
            defined_codes = set()
            for code_str in op.responses.keys():
                if code_str.isdigit():
                    defined_codes.add(int(code_str))
                elif code_str == "default":
                    defined_codes.add(actual_status)  # default matches anything

            if defined_codes and actual_status not in defined_codes:
                drifts.append(DriftItem(
                    drift_type=DriftType.STATUS_CODE_MISMATCH,
                    field_path="status_code",
                    expected=f"one of {sorted(defined_codes)}",
                    actual=str(actual_status),
                    message=f"Response status {actual_status} is not documented in spec (expected: {sorted(defined_codes)})",
                ))

        # ── Response Body Drift ──
        body_preview = exec_result.get("response_body_preview", "")
        if body_preview and actual_status:
            status_str = str(actual_status)
            resp_def = op.responses.get(status_str, op.responses.get("default", {}))
            if isinstance(resp_def, dict):
                content = resp_def.get("content", {})
                json_schema = None
                for ct, ct_data in content.items():
                    if "json" in ct and isinstance(ct_data, dict):
                        json_schema = ct_data.get("schema", {})
                        break

                if json_schema:
                    try:
                        import json
                        body = json.loads(body_preview)
                        if isinstance(body, dict):
                            drifts.extend(
                                DriftDetector._check_schema_drift(json_schema, body, "response")
                            )
                    except (json.JSONDecodeError, TypeError):
                        pass  # Can't parse body, skip schema checks

        return drifts

    @staticmethod
    def _check_schema_drift(
        schema: Dict[str, Any],
        actual: Any,
        path_prefix: str,
    ) -> List[DriftItem]:
        """Recursively compare actual response body against schema."""
        drifts: List[DriftItem] = []
        if not isinstance(schema, dict):
            return drifts

        schema_type = schema.get("type", "object")

        if schema_type == "object" and isinstance(actual, dict):
            props = schema.get("properties", {})
            required = set(schema.get("required", []))

            # Check for missing required fields
            for field_name in required:
                if field_name not in actual:
                    drifts.append(DriftItem(
                        drift_type=DriftType.MISSING_FIELD,
                        field_path=f"{path_prefix}.{field_name}",
                        expected=f"required field '{field_name}'",
                        actual="missing",
                        message=f"Required field '{field_name}' is missing from response",
                    ))

            # Check for extra fields not in schema
            if props:
                for field_name in actual.keys():
                    if field_name not in props:
                        drifts.append(DriftItem(
                            drift_type=DriftType.EXTRA_FIELD,
                            field_path=f"{path_prefix}.{field_name}",
                            expected="not defined in schema",
                            actual=f"present with value type {type(actual[field_name]).__name__}",
                            message=f"Field '{field_name}' found in response but not defined in spec schema",
                        ))

            # Check type mismatches for defined fields
            for field_name, field_schema in props.items():
                if field_name in actual:
                    value = actual[field_name]
                    expected_type = field_schema.get("type") if isinstance(field_schema, dict) else None
                    if expected_type and value is not None:
                        type_ok = DriftDetector._type_matches(expected_type, value)
                        if not type_ok:
                            drifts.append(DriftItem(
                                drift_type=DriftType.TYPE_MISMATCH,
                                field_path=f"{path_prefix}.{field_name}",
                                expected=expected_type,
                                actual=type(value).__name__,
                                message=f"Field '{field_name}': expected type '{expected_type}', got '{type(value).__name__}'",
                            ))
                    elif value is None and field_name in required:
                        drifts.append(DriftItem(
                            drift_type=DriftType.NULL_UNEXPECTED,
                            field_path=f"{path_prefix}.{field_name}",
                            expected=expected_type or "non-null",
                            actual="null",
                            message=f"Required field '{field_name}' is null",
                        ))

        return drifts

    @staticmethod
    def _type_matches(expected_type: str, value: Any) -> bool:
        """Check if a Python value matches the expected JSON schema type."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected_python = type_map.get(expected_type)
        if expected_python is None:
            return True  # Unknown type, can't validate
        # Special case: bool is a subclass of int in Python
        if expected_type == "integer" and isinstance(value, bool):
            return False
        return isinstance(value, expected_python)
