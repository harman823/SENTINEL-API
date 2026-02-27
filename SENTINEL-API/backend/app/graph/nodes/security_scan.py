from typing import Dict, Any
from backend.app.services.security_test_generator import SecurityTestGenerator
from backend.app.graph.state import GraphState


def security_scan_node(state: GraphState) -> Dict[str, Any]:
    """
    Graph node: generate OWASP-aware security test cases.
    Safe, spec-aware tests only — not penetration testing.
    """
    try:
        spec_normalized = state.get("spec_normalized")
        if not spec_normalized:
            return {"security_test_cases": [], "security_results": []}

        security_tests = SecurityTestGenerator.generate(spec_normalized)
        security_test_cases = [st.model_dump() for st in security_tests]

        return {
            "security_test_cases": security_test_cases,
            "security_results": [],  # Populated after execution if live
        }
    except Exception as e:
        return {
            "security_test_cases": [],
            "security_results": [],
            "errors": (state.get("errors") or []) + [f"Security scan failed: {str(e)}"],
        }
