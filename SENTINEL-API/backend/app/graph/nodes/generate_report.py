from typing import Dict, Any
from backend.app.services.report_generator import ReportGenerator
from backend.app.graph.state import GraphState


def generate_report_node(state: GraphState) -> Dict[str, Any]:
    """
    Graph node: compile all pipeline results into a structured report.
    Now includes lint, risk details, security, drift, and compliance data.
    """
    try:
        report = ReportGenerator.generate(
            spec_normalized=state.get("spec_normalized"),
            risk_scores=state.get("risk_scores", {}),
            risk_details=state.get("risk_details", {}),
            policy_results=state.get("policy_results", []),
            approval_required=state.get("approval_required", False),
            approval_status=state.get("approval_status"),
            test_cases=state.get("test_cases", []),
            execution_results=state.get("execution_results", []),
            validation_results=state.get("validation_results", []),
            errors=state.get("errors", []),
            lint_results=state.get("lint_results", []),
            security_test_cases=state.get("security_test_cases", []),
            security_results=state.get("security_results", []),
            drift_results=state.get("drift_results", []),
            compliance_mappings=state.get("compliance_mappings", []),
        )

        return {
            "report": report,
            "errors": [],
        }

    except Exception as e:
        return {"errors": (state.get("errors") or []) + [f"Report generation failed: {str(e)}"]}
