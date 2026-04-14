from typing import Any, Dict

from backend.app.graph.state import GraphState
from backend.app.services.root_cause_analyst import RootCauseAnalyst


def analyze_rca_node(state: GraphState) -> Dict[str, Any]:
    """
    Analyze failed validation results and produce root-cause findings.
    """
    try:
        validation_results = state.get("validation_results", []) or []
        execution_results = state.get("execution_results", []) or []
        test_cases = state.get("test_cases", []) or []

        findings = RootCauseAnalyst.analyze(
            validation_results=validation_results,
            execution_results=execution_results,
            test_cases=test_cases,
        )
        return {"rca_results": findings}
    except Exception as e:
        return {
            "rca_results": [],
            "errors": (state.get("errors") or []) + [f"RCA analysis failed: {str(e)}"],
        }
