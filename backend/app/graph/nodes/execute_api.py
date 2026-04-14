from typing import Dict, Any, List
from backend.app.services.api_executor import APIExecutor
from backend.app.services.chaos_resilience import ChaosResilienceTester
from backend.app.graph.state import GraphState


def execute_api_node(state: GraphState) -> Dict[str, Any]:
    """
    Graph node: execute generated test cases against the target API.
    Uses dry-run mode by default (no real HTTP calls).
    Stores execution_results in state for the response validation node.
    """
    try:
        test_cases = state.get("test_cases", [])

        if not test_cases:
            return {
                "execution_results": [],
                "errors": (state.get("errors") or []) + ["No test cases to execute"],
            }

        # Default to dry-run; live mode would be toggled via config/CLI flag
        live = state.get("live", False)
        max_concurrency = int(state.get("max_concurrency", 16) or 16)
        executor = APIExecutor(dry_run=not live, max_concurrency=max_concurrency)
        results = executor.execute(test_cases)

        chaos_results: List[Dict[str, Any]] = []
        if state.get("chaos_enabled", False):
            chaos_results = ChaosResilienceTester.run(
                spec=state.get("spec_normalized"),
                test_cases=test_cases,
                execution_results=results,
                fault_rate=float(state.get("chaos_fault_rate", 0.25) or 0.25),
            )

        return {
            "execution_results": results,
            "chaos_results": chaos_results,
            "errors": [],
        }

    except Exception as e:
        return {"errors": (state.get("errors") or []) + [f"API execution failed: {str(e)}"]}
