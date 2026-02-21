"""
Enhanced Report Generator — compiles all pipeline stage results
including lint findings, risk details, security tests, drift detection,
compliance mappings, and test explainability.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any, List


class ReportGenerator:
    """
    Compiles all pipeline stage results into a structured report.
    Produces both a summary dict and a serializable JSON report.
    """

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
        lint_results: List[Dict[str, Any]] = None,
        security_test_cases: List[Dict[str, Any]] = None,
        security_results: List[Dict[str, Any]] = None,
        drift_results: List[Dict[str, Any]] = None,
        compliance_mappings: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a full pipeline report from all stage outputs."""
        lint_results = lint_results or []
        security_test_cases = security_test_cases or []
        security_results = security_results or []
        drift_results = drift_results or []
        compliance_mappings = compliance_mappings or []

        # ── Summary Stats ──
        total_ops = len(spec_normalized.operations) if spec_normalized else 0
        total_tests = len(test_cases)
        exec_passed = sum(1 for r in execution_results if r.get("passed"))
        exec_failed = total_tests - exec_passed
        val_passed = sum(1 for v in validation_results if v.get("passed"))
        val_failed = len(validation_results) - val_passed
        flagged_ops = sum(1 for p in policy_results if p.get("requires_approval"))

        # ── Risk Distribution ──
        high_risk = sum(1 for s in risk_scores.values() if s >= 0.7)
        medium_risk = sum(1 for s in risk_scores.values() if 0.4 <= s < 0.7)
        low_risk = sum(1 for s in risk_scores.values() if s < 0.4)

        # ── Lint Summary ──
        lint_errors = sum(1 for l in lint_results if l.get("severity") == "error")
        lint_warnings = sum(1 for l in lint_results if l.get("severity") == "warning")
        lint_info = sum(1 for l in lint_results if l.get("severity") == "info")

        # ── Drift Summary ──
        drift_count = sum(len(d.get("drifts", [])) for d in drift_results)
        breaking_drifts = sum(1 for d in drift_results if d.get("is_breaking"))

        # ── Spec Info ──
        spec_info_raw = spec_normalized.info if spec_normalized else {}

        report: Dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "platform_version": "2.0.0",
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
                "pass_rate": round(val_passed / max(len(validation_results), 1) * 100, 1),
                "approval_required": approval_required,
                "approval_status": approval_status,
                "flagged_operations": flagged_ops,
                "errors": len(errors),
            },
            "risk_distribution": {
                "high": high_risk,
                "medium": medium_risk,
                "low": low_risk,
            },
            # ── NEW: Lint Results ──
            "lint_summary": {
                "total_issues": len(lint_results),
                "errors": lint_errors,
                "warnings": lint_warnings,
                "info": lint_info,
            },
            "lint_results": lint_results,
            # ── NEW: Detailed Risk Factors ──
            "risk_details": risk_details,
            # ── Policy ──
            "policy_results": policy_results,
            # ── Test Results with Explainability ──
            "test_results": [
                {
                    "test_id": tc.get("id"),
                    "method": tc.get("method"),
                    "url": tc.get("url"),
                    "path": tc.get("path"),
                    "expected_status": tc.get("expected_status"),
                    "is_destructive": tc.get("is_destructive"),
                    "risk_score": tc.get("risk_score"),
                    "test_type": tc.get("test_type", "positive"),
                    # Explainability
                    "reason": tc.get("reason", ""),
                    "spec_reference": tc.get("spec_reference", ""),
                    "risk_coverage": tc.get("risk_coverage", []),
                    # Results
                    "execution": next(
                        (er for er in execution_results if er.get("test_id") == tc.get("id")),
                        None,
                    ),
                    "validation": next(
                        (vr for vr in validation_results if vr.get("test_id") == tc.get("id")),
                        None,
                    ),
                }
                for tc in test_cases
            ],
            # ── NEW: Security Testing ──
            "security_summary": {
                "total_security_tests": len(security_test_cases),
                "categories_covered": list(set(
                    st.get("owasp_category", "") for st in security_test_cases
                )),
            },
            "security_test_cases": security_test_cases,
            "security_results": security_results,
            # ── NEW: Drift Detection ──
            "drift_summary": {
                "total_drifts": drift_count,
                "breaking_changes": breaking_drifts,
                "endpoints_with_drift": len(drift_results),
            },
            "drift_results": drift_results,
            # ── NEW: Compliance Mapping ──
            "compliance_summary": {
                "total_mappings": len(compliance_mappings),
                "frameworks_covered": list(set(
                    fw
                    for cm in compliance_mappings
                    for fw in cm.get("frameworks", {}).keys()
                )),
            },
            "compliance_mappings": compliance_mappings,
            # ── Errors ──
            "errors": errors,
        }

        return report

    @staticmethod
    def to_json(report: Dict[str, Any], indent: int = 2) -> str:
        """Serialize the report to a JSON string."""
        return json.dumps(report, indent=indent, default=str)
