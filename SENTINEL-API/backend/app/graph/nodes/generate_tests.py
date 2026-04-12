from typing import Dict, Any
from backend.app.services.test_generator import TestGenerator
from backend.app.services.semantic_traffic_replay import SemanticTrafficReplay
from backend.app.graph.state import GraphState


def generate_tests_node(state: GraphState) -> Dict[str, Any]:
    """
    Graph node: generate test cases from normalized operations.
    Skips destructive operations if approval has not been granted.
    Passes policy results for policy-driven test generation.
    """
    try:
        spec_normalized = state.get("spec_normalized")
        approval_required = state.get("approval_required", False)
        approval_status = state.get("approval_status")
        policy_results = state.get("policy_results", [])

        if not spec_normalized:
            return {"errors": (state.get("errors") or []) + ["No normalized spec for test generation"]}

        # Filter operations based on approval state
        operations = spec_normalized.operations
        if approval_required and approval_status is not True:
            operations = [op for op in operations if not op.is_destructive]

        test_cases = TestGenerator.generate(
            operations,
            policy_results=policy_results,
        )

        traffic_samples = state.get("traffic_samples", []) or []
        if traffic_samples:
            replay_cases = SemanticTrafficReplay.to_test_cases(
                spec=spec_normalized,
                records=traffic_samples,
            )
            test_cases.extend(replay_cases)

        return {
            "test_cases": test_cases,
            "errors": [],
        }
    except Exception as e:
        return {"errors": (state.get("errors") or []) + [f"Test generation failed: {str(e)}"]}
