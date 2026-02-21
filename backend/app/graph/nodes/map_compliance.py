from typing import Dict, Any
from backend.app.services.compliance_mapper import ComplianceMapper
from backend.app.graph.state import GraphState


def map_compliance_node(state: GraphState) -> Dict[str, Any]:
    """
    Graph node: map test cases and security results to compliance frameworks.
    Covers SOC 2, ISO 27001, HIPAA, and GDPR.
    """
    try:
        test_cases = state.get("test_cases", [])
        risk_details = state.get("risk_details", {})
        security_results = state.get("security_results", [])

        mappings = ComplianceMapper.map_tests(test_cases, risk_details)

        if security_results:
            sec_mappings = ComplianceMapper.map_security_tests(security_results)
            mappings.extend(sec_mappings)

        compliance_mappings = [m.model_dump() for m in mappings]

        return {"compliance_mappings": compliance_mappings}
    except Exception as e:
        return {
            "compliance_mappings": [],
            "errors": (state.get("errors") or []) + [f"Compliance mapping failed: {str(e)}"],
        }
