from typing import Dict, Any, List
from backend.app.services.policy_engine import PolicyEngine, PolicyResult
from backend.app.graph.state import GraphState


def evaluate_policy_node(state: GraphState) -> Dict[str, Any]:
    """
    Graph node: evaluate policy rules against all operations.
    Sets approval_required=True if any operation violates a rule.
    Supports user-defined policy config from state.
    """
    try:
        spec_normalized = state.get("spec_normalized")
        risk_scores = state.get("risk_scores") or {}
        policy_config = state.get("policy_config")

        if not spec_normalized:
            return {"errors": (state.get("errors") or []) + ["No normalized spec for policy evaluation"]}

        engine = PolicyEngine(policy_config=policy_config)
        results: List[PolicyResult] = engine.evaluate(spec_normalized.operations, risk_scores)

        # Serialize results for state storage
        policy_results = [
            {
                "operation_key": r.operation_key,
                "requires_approval": r.requires_approval,
                "violated_rules": r.violated_rules,
                "messages": r.messages,
                "min_negative_tests": r.min_negative_tests,
                "must_fail_without_token": r.must_fail_without_token,
            }
            for r in results
        ]

        approval_required = any(r.requires_approval for r in results)

        return {
            "policy_results": policy_results,
            "approval_required": approval_required,
            "errors": [],
        }
    except Exception as e:
        return {"errors": (state.get("errors") or []) + [f"Policy evaluation failed: {str(e)}"]}
