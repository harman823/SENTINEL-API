"""
Enhanced risk scoring engine for the API Intelligence Platform.
Scores range from 0.0 (safe) to 1.0 (critical) with full factor breakdown.
"""

from typing import Any, Dict, List, Optional

from backend.app.schemas.models import RiskFactor, RiskLevel, RiskScore
from backend.app.schemas.spec import NormalizedSpec, Operation


DESTRUCTIVE_METHODS = {"delete", "put", "patch"}
HIGH_RISK_KEYWORDS = {
    "admin",
    "root",
    "superuser",
    "password",
    "token",
    "secret",
    "key",
    "auth",
    "sudo",
    "internal",
    "config",
    "settings",
    "credentials",
    "private",
    "system",
    "billing",
    "payment",
    "invoice",
    "webhook",
    "role",
    "permission",
    "user",
    "account",
    "delete",
    "export",
    "import",
    "prod",
    "production",
}

PII_BOOST_THRESHOLD = 1
COMPLEXITY_BOOST_THRESHOLD = 5


def _classify_risk_level(score: float) -> RiskLevel:
    """Map a numeric risk score to a stricter categorical level."""
    if score >= 0.75:
        return RiskLevel.CRITICAL
    if score >= 0.5:
        return RiskLevel.HIGH
    if score >= 0.2:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


class RiskScorer:
    """
    Enhanced risk scorer for API operations.
    Produces detailed RiskScore objects with factor breakdown.
    """

    @staticmethod
    def score_operation(
        op: Operation,
        failure_history: Optional[Dict[str, Any]] = None,
    ) -> RiskScore:
        """Score a single operation with full factor breakdown."""
        factors: List[RiskFactor] = []
        score = 0.0

        if op.method == "delete":
            factors.append(
                RiskFactor(
                    name="destructive_method",
                    weight=0.45,
                    description="DELETE method can destroy resources",
                )
            )
            score += 0.45
        elif op.method in ("put", "patch"):
            factors.append(
                RiskFactor(
                    name="mutation_method",
                    weight=0.28,
                    description=f"{op.method.upper()} method mutates resources",
                )
            )
            score += 0.28
        elif op.method == "post":
            factors.append(
                RiskFactor(
                    name="creation_method",
                    weight=0.16,
                    description="POST method can create resources or trigger workflows",
                )
            )
            score += 0.16

        path_lower = op.path.lower()
        matched_keywords = [kw for kw in HIGH_RISK_KEYWORDS if kw in path_lower]
        if matched_keywords:
            weight = min(0.3, 0.12 * len(matched_keywords))
            factors.append(
                RiskFactor(
                    name="sensitive_path",
                    weight=round(weight, 2),
                    description=f"Path contains sensitive keywords: {', '.join(matched_keywords[:8])}",
                )
            )
            score += weight

        text_surface = " ".join(
            value.lower()
            for value in [
                op.summary or "",
                op.description or "",
                op.operationId or "",
                " ".join(op.tags or []),
            ]
            if value
        )
        matched_text_keywords = [
            kw for kw in HIGH_RISK_KEYWORDS if kw in text_surface and kw not in matched_keywords
        ]
        if matched_text_keywords:
            weight = min(0.18, 0.06 * len(matched_text_keywords))
            factors.append(
                RiskFactor(
                    name="sensitive_operation_metadata",
                    weight=round(weight, 2),
                    description=(
                        "Operation metadata mentions sensitive concepts: "
                        f"{', '.join(matched_text_keywords[:5])}"
                    ),
                )
            )
            score += weight

        if op.security_schemes:
            factors.append(
                RiskFactor(
                    name="auth_required",
                    weight=0.06,
                    description=f"Requires authentication: {', '.join(op.security_schemes)}",
                )
            )
            score += 0.06
            if op.method in DESTRUCTIVE_METHODS:
                factors.append(
                    RiskFactor(
                        name="protected_write_surface",
                        weight=0.08,
                        description="Authenticated write operation still changes protected state",
                    )
                )
                score += 0.08
        elif op.method != "get":
            factors.append(
                RiskFactor(
                    name="no_auth_on_write",
                    weight=0.28,
                    description="Write operation has no security scheme defined",
                )
            )
            score += 0.28
        elif any(kw in path_lower for kw in ("admin", "internal", "user", "account", "secret")):
            factors.append(
                RiskFactor(
                    name="no_auth_on_sensitive_read",
                    weight=0.18,
                    description="Sensitive read operation has no security scheme defined",
                )
            )
            score += 0.18

        if op.pii_fields:
            weight = min(0.28, 0.08 * len(op.pii_fields))
            factors.append(
                RiskFactor(
                    name="pii_fields",
                    weight=round(weight, 2),
                    description=f"Handles PII data: {', '.join(op.pii_fields[:5])}",
                )
            )
            score += weight

        if op.schema_complexity > COMPLEXITY_BOOST_THRESHOLD:
            weight = min(0.16, 0.025 * (op.schema_complexity - COMPLEXITY_BOOST_THRESHOLD))
            factors.append(
                RiskFactor(
                    name="complex_schema",
                    weight=round(weight, 2),
                    description=f"Complex schema (complexity={op.schema_complexity})",
                )
            )
            score += weight

        if failure_history:
            key = f"{op.path}.{op.method}"
            ep_history = failure_history.get(key, {})
            failure_count = ep_history.get("total_failures", 0)
            is_flaky = ep_history.get("is_flaky", False)
            if is_flaky:
                factors.append(
                    RiskFactor(
                        name="flaky_endpoint",
                        weight=0.18,
                        description=f"Historically flaky endpoint ({failure_count} failures)",
                    )
                )
                score += 0.18
            elif failure_count > 0:
                weight = min(0.14, 0.04 * failure_count)
                factors.append(
                    RiskFactor(
                        name="historical_failures",
                        weight=round(weight, 2),
                        description=f"Has {failure_count} recorded failure(s)",
                    )
                )
                score += weight

        clamped = round(min(score, 1.0), 2)
        endpoint_key = f"{op.path}.{op.method}"
        level = _classify_risk_level(clamped)

        return RiskScore(
            endpoint=endpoint_key,
            score=clamped,
            level=level,
            factors=factors,
            explanation=f"Risk {clamped:.2f} ({level.value}) based on {len(factors)} factor(s)",
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
        """Legacy compatibility: returns just the float scores."""
        detailed = RiskScorer.score_spec(spec, failure_history)
        return {key: rs.score for key, rs in detailed.items()}
