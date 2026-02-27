from typing import Dict, Any
from backend.app.services.risk_scorer import RiskScorer
from backend.app.graph.state import GraphState


def score_risk_node(state: GraphState) -> Dict[str, Any]:
    """
    Graph node: score risk for all operations in the normalized spec.
    Produces both legacy flat scores and detailed RiskScore objects.
    """
    try:
        spec_normalized = state.get("spec_normalized")
        if not spec_normalized:
            return {"errors": (state.get("errors") or []) + ["No normalized spec in state for risk scoring"]}

        # Detailed risk scores with factor breakdown
        detailed_scores = RiskScorer.score_spec(spec_normalized)

        # Flat scores for backward compatibility
        flat_scores: Dict[str, float] = {}
        risk_details: Dict[str, Any] = {}

        for key, risk_score in detailed_scores.items():
            flat_scores[key] = risk_score.score
            risk_details[key] = risk_score.model_dump()

        # Update risk_score on each operation
        for op in spec_normalized.operations:
            key = f"{op.path}.{op.method}"
            op.risk_score = flat_scores.get(key)
            rs = detailed_scores.get(key)
            if rs:
                op.risk_factors = [f.name for f in rs.factors]

        return {
            "risk_scores": flat_scores,
            "risk_details": risk_details,
            "errors": [],
        }
    except Exception as e:
        return {"errors": (state.get("errors") or []) + [f"Risk scoring failed: {str(e)}"]}
