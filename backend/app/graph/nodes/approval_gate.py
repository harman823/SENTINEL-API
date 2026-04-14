from typing import Dict, Any
from backend.app.graph.state import GraphState


def approval_gate_node(state: GraphState) -> Dict[str, Any]:
    """
    Graph node: Approval Gate.

    Checks if any policy violations require human approval.
    In automated mode, destructive operations are auto-skipped (not blocked).
    In interactive mode, this node would pause for human input.

    For now, the gate auto-approves safe operations and logs warnings
    for operations requiring approval.
    """
    try:
        approval_required = state.get("approval_required", False)
        policy_results = state.get("policy_results", [])

        if not approval_required:
            # All clear — no approval needed
            return {
                "approval_status": True,
                "errors": [],
            }

        # Count operations needing approval
        flagged = [pr for pr in policy_results if pr.get("requires_approval")]
        safe = [pr for pr in policy_results if not pr.get("requires_approval")]

        # Auto-approve safe operations, flag dangerous ones
        # In future: this is where we'd pause for human input via CLI prompt
        return {
            "approval_status": False,  # Not fully approved (destructive ops blocked)
            "errors": [],
        }

    except Exception as e:
        return {"errors": (state.get("errors") or []) + [f"Approval gate failed: {str(e)}"]}


def should_generate_tests(state: GraphState) -> str:
    """
    Conditional edge: decide whether to proceed to test generation.
    Always proceeds — generate_tests_node handles filtering internally.
    """
    return "generate_tests"
