"""
Enhanced risk scoring engine for the API Intelligence Platform.
Scores range from 0.0 (safe) to 1.0 (critical) with full factor breakdown.
"""

from typing import Dict, Any, List, Optional
from backend.app.schemas.spec import NormalizedSpec, Operation
from backend.app.schemas.models import RiskFactor, RiskScore, RiskLevel


DESTRUCTIVE_METHODS = {"delete", "put", "patch"}
HIGH_RISK_KEYWORDS = {
    "admin", "root", "superuser", "password", "token",
    "secret", "key", "auth", "sudo", "internal", "config",
    "settings", "credentials", "private", "system",
}

PII_BOOST_THRESHOLD = 1  # Any PII fields found adds risk
COMPLEXITY_BOOST_THRESHOLD = 5  # Schema complexity above this adds risk


def _classify_risk_level(score: float) -> RiskLevel:
    """Map a numeric risk score to a categorical level."""
    if score >= 0.8:
        return RiskLevel.CRITICAL
    elif score >= 0.6:
        return RiskLevel.HIGH
    elif score >= 0.3:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


class RiskScorer:
    """
    Enhanced risk scorer for OpenAPI operations.
    Produces detailed RiskScore objects with factor breakdown.
    Scores range from 0.0 (safe) to 1.0 (critical).
    """

    @staticmethod
    def score_operation(
        op: Operation,
        failure_history: Optional[Dict[str, Any]] = None,
    ) -> RiskScore:
        """Score a single operation with full factor breakdown."""
        factors: List[RiskFactor] = []
        score = 0.0

        # ── HTTP Method Risk ──
        if op.method == "delete":
            factors.append(RiskFactor(
                name="destructive_method",
                weight=0.35,
                description=f"DELETE method — destroys resources",
            ))
            score += 0.35
        elif op.method in ("put", "patch"):
            factors.append(RiskFactor(
                name="mutation_method",
                weight=0.2,
                description=f"{op.method.upper()} method — mutates resources",
            ))
            score += 0.2
        elif op.method == "post":
            factors.append(RiskFactor(
                name="creation_method",
                weight=0.1,
                description="POST method — creates resources",
            ))
            score += 0.1

        # ── Path Keyword Risk ──
        path_lower = op.path.lower()
        matched_keywords = [kw for kw in HIGH_RISK_KEYWORDS if kw in path_lower]
        if matched_keywords:
            weight = min(0.2, 0.1 * len(matched_keywords))
            factors.append(RiskFactor(
                name="sensitive_path",
                weight=weight,
                description=f"Path contains sensitive keywords: {', '.join(matched_keywords)}",
            ))
            score += weight

        # ── Auth Requirements ──
        if op.security_schemes:
            factors.append(RiskFactor(
                name="auth_required",
                weight=0.1,
                description=f"Requires authentication: {', '.join(op.security_schemes)}",
            ))
            score += 0.1
        elif op.method != "get":
            # Non-GET with no auth is riskier
            factors.append(RiskFactor(
                name="no_auth_on_write",
                weight=0.15,
                description="Write operation has no security scheme defined",
            ))
            score += 0.15

        # ── PII Data Sensitivity ──
        if op.pii_fields:
            weight = min(0.2, 0.05 * len(op.pii_fields))
            factors.append(RiskFactor(
                name="pii_fields",
                weight=weight,
                description=f"Handles PII data: {', '.join(op.pii_fields[:5])}",
            ))
            score += weight

        # ── Schema Complexity ──
        if op.schema_complexity > COMPLEXITY_BOOST_THRESHOLD:
            weight = min(0.1, 0.02 * (op.schema_complexity - COMPLEXITY_BOOST_THRESHOLD))
            factors.append(RiskFactor(
                name="complex_schema",
                weight=round(weight, 2),
                description=f"Complex schema (complexity={op.schema_complexity})",
            ))
            score += weight

        # ── Historical Failures ──
        if failure_history:
            key = f"{op.path}.{op.method}"
            ep_history = failure_history.get(key, {})
            failure_count = ep_history.get("total_failures", 0)
            is_flaky = ep_history.get("is_flaky", False)
            if is_flaky:
                factors.append(RiskFactor(
                    name="flaky_endpoint",
                    weight=0.15,
                    description=f"Historically flaky endpoint ({failure_count} failures)",
                ))
                score += 0.15
            elif failure_count > 0:
                weight = min(0.1, 0.03 * failure_count)
                factors.append(RiskFactor(
                    name="historical_failures",
                    weight=round(weight, 2),
                    description=f"Has {failure_count} recorded failure(s)",
                ))
                score += weight

        # Clamp to [0.0, 1.0]
        clamped = round(min(score, 1.0), 2)
        endpoint_key = f"{op.path}.{op.method}"

        return RiskScore(
            endpoint=endpoint_key,
            score=clamped,
            level=_classify_risk_level(clamped),
            factors=factors,
            explanation=f"Risk {clamped:.2f} ({_classify_risk_level(clamped).value}) "
                        f"based on {len(factors)} factor(s)",
        )

    @staticmethod
    def score_spec(
        spec: NormalizedSpec,
        failure_history: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, RiskScore]:
        """Score all operations, returning detailed RiskScore per endpoint."""
        scores: Dict[str, RiskScore] = {}
        for op in spec.operations:
            key = f"{op.path}.{op.method}"
            scores[key] = RiskScorer.score_operation(op, failure_history)
        return scores

    @staticmethod
    def score_spec_flat(
        spec: NormalizedSpec,
        failure_history: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """Legacy compatibility — returns just the float scores."""
        detailed = RiskScorer.score_spec(spec, failure_history)
        return {key: rs.score for key, rs in detailed.items()}
