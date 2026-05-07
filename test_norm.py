import json
from backend.app.services.api_spec_compat import ApiSpecCompat
from backend.app.services.spec_normalizer import SpecNormalizer
from backend.app.services.risk_scorer import RiskScorer

spec_raw = {
    "editor.formatOnSave": True,
    "python.formatting.provider": "black"
}

try:
    compatible_spec = ApiSpecCompat.to_openapi3(spec_raw)
    normalized = SpecNormalizer.normalize(compatible_spec)
    print("Normalized!", len(normalized.operations))
    scores = RiskScorer.score_spec(normalized)
    print("Scores:", scores)
except Exception as e:
    import traceback
    traceback.print_exc()
