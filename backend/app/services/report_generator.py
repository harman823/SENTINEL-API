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
        compliance_mappings: Optional[List[Dict[str, Any]]] = None,
        remediation_results: Optional[List[Dict[str, Any]]] = None,
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

        high_risk = sum(1 for score in risk_scores.values() if score >= 0.7)
        medium_risk = sum(1 for score in risk_scores.values() if 0.4 <= score < 0.7)
        low_risk = sum(1 for score in risk_scores.values() if score < 0.4)

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
            "remediation_summary": {
                "total_remediations": len(remediation_results),
                "total_pr_suggestions": len(pr_remediation_suggestions),
            },
            "remediation_results": remediation_results,
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
        }

        report["safe_to_ship"] = SafeToShipGate.evaluate(report, environment=environment)
        return report

    @staticmethod
    def to_json(report: Dict[str, Any], indent: int = 2) -> str:
        return json.dumps(report, indent=indent, default=str)
