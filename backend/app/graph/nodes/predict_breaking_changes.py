from typing import Any, Dict

from backend.app.graph.state import GraphState
from backend.app.services.breaking_change_predictor import BreakingChangePredictor


def predict_breaking_changes_node(state: GraphState) -> Dict[str, Any]:
    """
    Predict likely breaking changes from spec evolution history.
    Uses spec_history[-1] as previous version when provided.
    """
    try:
        current_spec = state.get("spec_raw", {})
        spec_history = state.get("spec_history", []) or []
        prediction = BreakingChangePredictor.predict(spec_history, current_spec)
        return {
            "breaking_change_predictions": prediction.get("predictions", []),
            "errors": [],
        }
    except Exception as e:
        return {
            "breaking_change_predictions": [],
            "errors": (state.get("errors") or []) + [f"Breaking-change prediction failed: {str(e)}"],
        }
