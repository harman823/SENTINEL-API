from typing import Dict, Any
from backend.app.services.response_validator import ResponseValidator
from backend.app.graph.state import GraphState


def validate_responses_node(state: GraphState) -> Dict[str, Any]:
    """
    Graph node: validate execution results against test case assertions.
    Stores validation_results in state for the report generation node.
    """
    try:
        test_cases = state.get("test_cases", [])
        execution_results = state.get("execution_results", [])

        if not execution_results:
            return {
                "validation_results": [],
                "errors": (state.get("errors") or []) + ["No execution results to validate"],
            }

        validation_results = ResponseValidator.validate(test_cases, execution_results)

        return {
            "validation_results": validation_results,
            "errors": [],
        }

    except Exception as e:
        return {"errors": (state.get("errors") or []) + [f"Response validation failed: {str(e)}"]}
