from typing import Dict, Any
from backend.app.services.drift_detector import DriftDetector
from backend.app.graph.state import GraphState


def detect_drift_node(state: GraphState) -> Dict[str, Any]:
    """
    Graph node: detect contract drift between spec and actual API responses.
    Only meaningful for live (non-dry-run) executions.
    """
    try:
        spec_normalized = state.get("spec_normalized")
        test_cases = state.get("test_cases", [])
        execution_results = state.get("execution_results", [])

        if not spec_normalized or not execution_results:
            return {"drift_results": []}

        # Check if any results are from live execution (not dry-run)
        has_live = any(not er.get("dry_run", False) for er in execution_results)
        if not has_live:
            return {"drift_results": []}

        drift_reports = DriftDetector.detect(
            spec_normalized, test_cases, execution_results
        )
        drift_results = [dr.model_dump() for dr in drift_reports]

        return {"drift_results": drift_results}
    except Exception as e:
        return {
            "drift_results": [],
            "errors": (state.get("errors") or []) + [f"Drift detection failed: {str(e)}"],
        }
