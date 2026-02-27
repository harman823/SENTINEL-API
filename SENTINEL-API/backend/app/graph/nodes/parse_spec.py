from typing import Dict, Any
from backend.app.services.spec_normalizer import SpecNormalizer
from backend.app.graph.state import GraphState

def parse_spec_node(state: GraphState) -> Dict[str, Any]:
    """
    Node to parse and normalize the OpenAPI spec.
    """
    try:
        spec_raw = state.get("spec_raw")
        if not spec_raw:
            return {"errors": ["No raw spec provided in state"]}
            
        normalized = SpecNormalizer.normalize(spec_raw)
        return {"spec_normalized": normalized, "errors": []}
    except Exception as e:
        return {"errors": [f"Spec normalization failed: {str(e)}"]}
