"""
Automated root cause analysis for validation failures.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _find_execution(execution_results: List[Dict[str, Any]], test_id: str) -> Optional[Dict[str, Any]]:
    for item in execution_results:
        if item.get("test_id") == test_id:
            return item
    return None


def _find_test_case(test_cases: List[Dict[str, Any]], test_id: str) -> Optional[Dict[str, Any]]:
    for test_case in test_cases:
        if test_case.get("id") == test_id:
            return test_case
    return None


class RootCauseAnalyst:
    """Derives likely root causes and suggested fixes for failed tests."""

    @staticmethod
    def analyze(
        validation_results: List[Dict[str, Any]],
        execution_results: List[Dict[str, Any]],
        test_cases: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        for validation in validation_results:
            if validation.get("passed", True):
                continue

            test_id = validation.get("test_id", "")
            execution = _find_execution(execution_results, test_id)
            test_case = _find_test_case(test_cases, test_id) or {}

            if execution is None:
                findings.append(
                    {
                        "test_id": test_id,
                        "endpoint": f"{test_case.get('method', '?')} {test_case.get('path', '?')}",
                        "category": "missing_execution_result",
                        "root_cause": "Validation ran without a matching execution result.",
                        "evidence": [validation.get("summary", "No validation summary available.")],
                        "suggested_fix": "Ensure execution and validation IDs stay aligned.",
                        "spec_reference": test_case.get("spec_reference", ""),
                        "severity": "high",
                    }
                )
                continue

            execution_error = str(execution.get("error") or "")
            if execution_error:
                category = "execution_error"
                suggested_fix = "Inspect runtime logs and networking dependencies."
                if "timeout" in execution_error.lower():
                    category = "timeout"
                    suggested_fix = "Review upstream latency, retry policy, and timeout settings."
                elif "connect" in execution_error.lower():
                    category = "connectivity"
                    suggested_fix = "Verify base URL, DNS, and connectivity from the test runner."

                findings.append(
                    {
                        "test_id": test_id,
                        "endpoint": f"{execution.get('method', '?')} {test_case.get('path', '?')}",
                        "category": category,
                        "root_cause": execution_error,
                        "evidence": [validation.get("summary", ""), execution_error],
                        "suggested_fix": suggested_fix,
                        "spec_reference": test_case.get("spec_reference", ""),
                        "severity": "high",
                    }
                )
                continue

            expected_status = test_case.get("expected_status")
            actual_status = execution.get("status_code")
            failed_assertions = [a for a in validation.get("assertions", []) if not a.get("passed", False)]

            if expected_status is not None and actual_status is not None and expected_status != actual_status:
                findings.append(
                    {
                        "test_id": test_id,
                        "endpoint": f"{execution.get('method', '?')} {test_case.get('path', '?')}",
                        "category": "status_code_mismatch",
                        "root_cause": f"Expected status {expected_status}, received {actual_status}.",
                        "evidence": [validation.get("summary", "")],
                        "suggested_fix": "Align API handler response codes or update the OpenAPI contract.",
                        "spec_reference": test_case.get("spec_reference", ""),
                        "severity": "medium",
                    }
                )
                continue

            details = [assertion.get("message", "") for assertion in failed_assertions] or [validation.get("summary", "")]
            findings.append(
                {
                    "test_id": test_id,
                    "endpoint": f"{execution.get('method', '?')} {test_case.get('path', '?')}",
                    "category": "assertion_failure",
                    "root_cause": "One or more assertions failed.",
                    "evidence": details,
                    "suggested_fix": "Review assertion expectations and response payload contracts.",
                    "spec_reference": test_case.get("spec_reference", ""),
                    "severity": "medium",
                }
            )

        return findings
