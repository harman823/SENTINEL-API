"""
Report generator for the API intelligence pipeline.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.services.compliance_scorecard import ComplianceScorecard
from backend.app.services.safe_to_ship_gate import SafeToShipGate


class ReportGenerator:
    """Compile all pipeline stage outputs into a single report object."""

    @staticmethod
    def _build_fix_prompts(
        spec_normalized: Any,
        high_risk_operations: List[Dict[str, Any]],
        lint_results: List[Dict[str, Any]],
        validation_results: List[Dict[str, Any]],
        execution_results: List[Dict[str, Any]],
        rca_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        operations = getattr(spec_normalized, "operations", []) if spec_normalized else []
        source_title = "Unknown API"
        if spec_normalized and isinstance(getattr(spec_normalized, "info", None), dict):
            source_title = spec_normalized.info.get("title", source_title)

        failed_test_ids = {
            item.get("test_id")
            for item in validation_results
            if item.get("test_id") and not item.get("passed")
        }
        execution_by_test = {
            item.get("test_id"): item
            for item in execution_results
            if item.get("test_id")
        }

        prompts: List[Dict[str, Any]] = []
        for index, item in enumerate(high_risk_operations[:5], start=1):
            endpoint = f"{item.get('method') or 'API'} {item.get('path') or item.get('operation_key')}"
            factors = ", ".join(
                factor.get("name", "risk")
                for factor in item.get("risk_factors", [])[:5]
                if isinstance(factor, dict)
            ) or "risk factors"
            prompt = "\n".join(
                [
                    "You are working in my local IDE on this API repository.",
                    f"API surface: {source_title}",
                    f"Problem endpoint: {endpoint}",
                    f"Risk score: {float(item.get('risk_score', 0.0)):.2f}",
                    f"Risk factors: {factors}",
                    "",
                    "Task:",
                    "1. Find the handler, route, schema, and tests for this endpoint.",
                    "2. Add or tighten authentication/authorization where the route mutates or exposes sensitive data.",
                    "3. Validate request and response schemas, including PII or credential fields.",
                    "4. Add regression tests covering success, unauthorized, invalid payload, and documented error responses.",
                    "5. Update API documentation so the contract matches the implementation.",
                    "",
                    "Return a concise patch summary and list the files changed.",
                ]
            )
            prompts.append(
                {
                    "id": f"risk-{index}",
                    "title": f"Fix high-risk endpoint {endpoint}",
                    "category": "risk",
                    "endpoint": endpoint,
                    "prompt": prompt,
                }
            )

        if lint_results:
            top_lint = lint_results[:8]
            prompt = "\n".join(
                [
                    "You are working in my local IDE on this API repository.",
                    f"API surface: {source_title}",
                    "Problem: Sentinel found API documentation quality issues.",
                    "",
                    "Top findings:",
                    *[
                        f"- {item.get('severity', 'issue')}: {item.get('message') or item.get('rule') or item}"
                        for item in top_lint
                    ],
                    "",
                    "Task: update the API documentation and related tests so every operation has security, documented 4xx/5xx responses, request/response schemas, and accurate operation metadata.",
                ]
            )
            prompts.append(
                {
                    "id": "lint-contract",
                    "title": "Fix API contract quality issues",
                    "category": "contract",
                    "endpoint": None,
                    "prompt": prompt,
                }
            )

        if failed_test_ids or rca_results:
            failures = []
            for test_id in sorted(failed_test_ids):
                execution = execution_by_test.get(test_id, {})
                failures.append(
                    f"- {test_id}: status={execution.get('status_code', 'n/a')} error={execution.get('error') or 'n/a'}"
                )
            prompt = "\n".join(
                [
                    "You are working in my local IDE on this API repository.",
                    f"API surface: {source_title}",
                    "Problem: Sentinel found failing API validation or execution results.",
                    "",
                    "Failures:",
                    *(failures[:10] or ["- See the Sentinel report RCA section for failure details."]),
                    "",
                    "Task: reproduce the failing API tests locally, fix the implementation or contract mismatch, add regression coverage, and keep the documented response codes aligned with real behavior.",
                ]
            )
            prompts.append(
                {
                    "id": "failed-validations",
                    "title": "Fix failing API validations",
                    "category": "validation",
                    "endpoint": None,
                    "prompt": prompt,
                }
            )

        if not prompts and operations:
            prompt = "\n".join(
                [
                    "You are working in my local IDE on this API repository.",
                    f"API surface: {source_title}",
                    f"Sentinel scanned {len(operations)} operation(s) and did not find blockers.",
                    "Task: add regression tests for the highest-value routes, verify authentication coverage, and keep API docs synchronized with handlers.",
                ]
            )
            prompts.append(
                {
                    "id": "hardening-pass",
                    "title": "Add API hardening coverage",
                    "category": "hardening",
                    "endpoint": None,
                    "prompt": prompt,
                }
            )
        return prompts

    @staticmethod
    def generate(
        spec_normalized: Any,
        risk_scores: Dict[str, float],
        risk_details: Dict[str, Any],
        policy_results: List[Dict[str, Any]],
        approval_required: bool,
        approval_status: Any,
        test_cases: List[Dict[str, Any]],
        execution_results: List[Dict[str, Any]],
        validation_results: List[Dict[str, Any]],
        errors: List[str],
        lint_results: Optional[List[Dict[str, Any]]] = None,
        security_test_cases: Optional[List[Dict[str, Any]]] = None,
        security_results: Optional[List[Dict[str, Any]]] = None,
        drift_results: Optional[List[Dict[str, Any]]] = None,
        dynamic_mock_routes: Optional[List[Dict[str, Any]]] = None,
        mock_notifications: Optional[List[Dict[str, Any]]] = None,
        compliance_mappings: Optional[List[Dict[str, Any]]] = None,
        remediation_results: Optional[List[Dict[str, Any]]] = None,
        remediation_patch: Optional[Dict[str, Any]] = None,
        suggested_diff: Optional[str] = None,
        pr_remediation_suggestions: Optional[List[Dict[str, Any]]] = None,
        chaos_results: Optional[List[Dict[str, Any]]] = None,
        rca_results: Optional[List[Dict[str, Any]]] = None,
        breaking_change_predictions: Optional[List[Dict[str, Any]]] = None,
        iac_validation: Optional[Dict[str, Any]] = None,
        environment: str = "dev",
    ) -> Dict[str, Any]:
        lint_results = lint_results or []
        security_test_cases = security_test_cases or []
        security_results = security_results or []
        drift_results = drift_results or []
        dynamic_mock_routes = dynamic_mock_routes or []
        mock_notifications = mock_notifications or []
        compliance_mappings = compliance_mappings or []
        remediation_results = remediation_results or []
        pr_remediation_suggestions = pr_remediation_suggestions or []
        chaos_results = chaos_results or []
        rca_results = rca_results or []
        breaking_change_predictions = breaking_change_predictions or []
        iac_validation = iac_validation or {}

        total_ops = len(spec_normalized.operations) if spec_normalized else 0
        total_tests = len(test_cases)
        exec_passed = sum(1 for result in execution_results if result.get("passed"))
        exec_failed = total_tests - exec_passed
        val_passed = sum(1 for result in validation_results if result.get("passed"))
        val_failed = len(validation_results) - val_passed
        flagged_ops = sum(1 for result in policy_results if result.get("requires_approval"))

        high_risk = sum(1 for score in risk_scores.values() if score >= 0.5)
        medium_risk = sum(1 for score in risk_scores.values() if 0.2 <= score < 0.5)
        low_risk = sum(1 for score in risk_scores.values() if score < 0.2)

        lint_errors = sum(1 for item in lint_results if item.get("severity") == "error")
        lint_warnings = sum(1 for item in lint_results if item.get("severity") == "warning")
        lint_info = sum(1 for item in lint_results if item.get("severity") == "info")

        drift_count = sum(len(item.get("drifts", [])) for item in drift_results)
        breaking_drifts = sum(1 for item in drift_results if item.get("is_breaking"))

        spec_info_raw = spec_normalized.info if spec_normalized else {}
        pass_rate = round((val_passed / max(len(validation_results), 1)) * 100, 1)

        execution_index = {
            item.get("test_id"): item
            for item in execution_results
            if item.get("test_id")
        }
        validation_index = {
            item.get("test_id"): item
            for item in validation_results
            if item.get("test_id")
        }
        operation_index = {
            f"{op.path}.{op.method}": op
            for op in (spec_normalized.operations if spec_normalized else [])
        }
        policy_index = {
            item.get("operation_key"): item
            for item in policy_results
            if item.get("operation_key")
        }

        test_results = []
        for test_case in test_cases:
            test_id = test_case.get("id")
            test_results.append(
                {
                    "test_id": test_id,
                    "method": test_case.get("method"),
                    "url": test_case.get("url"),
                    "path": test_case.get("path"),
                    "expected_status": test_case.get("expected_status"),
                    "is_destructive": test_case.get("is_destructive"),
                    "risk_score": test_case.get("risk_score"),
                    "test_type": test_case.get("test_type", "positive"),
                    "reason": test_case.get("reason", ""),
                    "spec_reference": test_case.get("spec_reference", ""),
                    "risk_coverage": test_case.get("risk_coverage", []),
                    "execution": execution_index.get(test_id),
                    "validation": validation_index.get(test_id),
                }
            )

        compliance_scorecard = ComplianceScorecard.generate(
            compliance_mappings=compliance_mappings,
            validation_results=validation_results,
            risk_details=risk_details,
        )

        high_risk_operations = []
        for operation_key, detail in sorted(
            risk_details.items(),
            key=lambda item: item[1].get("score", 0),
            reverse=True,
        ):
            score = detail.get("score", 0)
            if score < 0.5:
                continue
            op = operation_index.get(operation_key)
            policy = policy_index.get(operation_key, {})
            high_risk_operations.append(
                {
                    "operation_key": operation_key,
                    "method": op.method.upper() if op else None,
                    "path": op.path if op else None,
                    "summary": op.summary if op else None,
                    "is_destructive": op.is_destructive if op else False,
                    "risk_score": score,
                    "risk_level": detail.get("level"),
                    "risk_explanation": detail.get("explanation"),
                    "risk_factors": detail.get("factors", []),
                    "requires_approval": policy.get("requires_approval", False),
                    "violated_rules": policy.get("violated_rules", []),
                }
            )

        fix_prompts = ReportGenerator._build_fix_prompts(
            spec_normalized=spec_normalized,
            high_risk_operations=high_risk_operations,
            lint_results=lint_results,
            validation_results=validation_results,
            execution_results=execution_results,
            rca_results=rca_results,
        )

        report: Dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "platform_version": "2.1.0",
            "environment": environment,
            "spec_info": {
                "title": spec_info_raw.get("title", "Unknown") if isinstance(spec_info_raw, dict) else "Unknown",
                "version": spec_info_raw.get("version", "Unknown") if isinstance(spec_info_raw, dict) else "Unknown",
                "total_operations": total_ops,
            },
            "summary": {
                "total_tests": total_tests,
                "execution_passed": exec_passed,
                "execution_failed": exec_failed,
                "validation_passed": val_passed,
                "validation_failed": val_failed,
                "pass_rate": pass_rate,
                "approval_required": approval_required,
                "approval_status": approval_status,
                "flagged_operations": flagged_ops,
                "errors": len(errors),
            },
            "risk_distribution": {"high": high_risk, "medium": medium_risk, "low": low_risk},
            "risk_details": risk_details,
            "risk_summary": {
                "high_risk_operations": high_risk_operations,
                "highest_risk_score": max(
                    (detail.get("score", 0) for detail in risk_details.values()),
                    default=0,
                ),
            },
            "lint_summary": {
                "total_issues": len(lint_results),
                "errors": lint_errors,
                "warnings": lint_warnings,
                "info": lint_info,
            },
            "lint_results": lint_results,
            "policy_results": policy_results,
            "test_results": test_results,
            "security_summary": {
                "total_security_tests": len(security_test_cases),
                "categories_covered": sorted(
                    {
                        item.get("owasp_category", "")
                        for item in security_test_cases
                        if item.get("owasp_category")
                    }
                ),
            },
            "security_test_cases": security_test_cases,
            "security_results": security_results,
            "drift_summary": {
                "total_drifts": drift_count,
                "breaking_changes": breaking_drifts,
                "endpoints_with_drift": len(drift_results),
            },
            "drift_results": drift_results,
            "dynamic_mock_summary": {
                "active_routes": len(dynamic_mock_routes),
                "notifications": len(mock_notifications),
            },
            "dynamic_mock_routes": dynamic_mock_routes,
            "mock_notifications": mock_notifications,
            "remediation_summary": {
                "total_remediations": len(remediation_results),
                "total_pr_suggestions": len(pr_remediation_suggestions),
            },
            "remediation_results": remediation_results,
            "remediation_patch": remediation_patch,
            "suggested_diff": suggested_diff,
            "pr_remediation_suggestions": pr_remediation_suggestions,
            "compliance_summary": {
                "total_mappings": len(compliance_mappings),
                "frameworks_covered": sorted(
                    {
                        framework
                        for mapping in compliance_mappings
                        for framework in (mapping.get("frameworks", {}) or {}).keys()
                    }
                ),
            },
            "compliance_mappings": compliance_mappings,
            "compliance_scorecard": compliance_scorecard,
            "chaos_summary": {
                "enabled": bool(chaos_results),
                "total_injected": len(chaos_results),
                "documented_failures": sum(1 for item in chaos_results if item.get("passed")),
                "undocumented_failures": sum(1 for item in chaos_results if not item.get("passed")),
            },
            "chaos_results": chaos_results,
            "rca_summary": {"total_findings": len(rca_results)},
            "rca_results": rca_results,
            "breaking_change_summary": {
                "total_predictions": len(breaking_change_predictions),
                "likely_breaking": sum(1 for item in breaking_change_predictions if item.get("is_breaking")),
            },
            "breaking_change_predictions": breaking_change_predictions,
            "iac_validation": iac_validation,
            "errors": errors,
            "error_details": [{"message": message, "severity": "error"} for message in errors],
            "fix_prompts": fix_prompts,
        }

        report["safe_to_ship"] = SafeToShipGate.evaluate(report, environment=environment)
        return report

    @staticmethod
    def to_json(report: Dict[str, Any], indent: int = 2) -> str:
        return json.dumps(report, indent=indent, default=str)
