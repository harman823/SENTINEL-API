from typing import Any, Dict

from backend.app.graph.state import GraphState
from backend.app.services.iac_validator import IaCValidator


def validate_iac_node(state: GraphState) -> Dict[str, Any]:
    """
    Validate IaC controls against OpenAPI contract requirements.
    Runs as a no-op when no IaC sources are provided.
    """
    try:
        iac_sources = state.get("iac_sources", []) or []
        if not iac_sources:
            return {"iac_validation": {"passed": True, "score": 100.0, "checks": [], "missing_controls": []}}

        result = IaCValidator.validate(
            spec_raw=state.get("spec_raw", {}),
            iac_sources=iac_sources,
        )
        return {"iac_validation": result}
    except Exception as e:
        return {
            "iac_validation": {"passed": False, "score": 0.0, "checks": [], "missing_controls": []},
            "errors": (state.get("errors") or []) + [f"IaC validation failed: {str(e)}"],
        }
