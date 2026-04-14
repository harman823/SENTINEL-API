"""
Deployment safe-to-ship gate.
"""

from __future__ import annotations

from typing import Any, Dict, List


ENVIRONMENT_RULES = {
    "dev": {"min_pass_rate": 70.0, "max_risk_score": 1.0, "min_compliance": 0.0},
    "staging": {"min_pass_rate": 85.0, "max_risk_score": 0.8, "min_compliance": 70.0},
    "prod": {"min_pass_rate": 95.0, "max_risk_score": 0.6, "min_compliance": 85.0},
}


def _max_risk(report: Dict[str, Any]) -> float:
    risk_details = report.get("risk_details", {}) or {}
    max_score = 0.0
    for detail in risk_details.values():
        if not isinstance(detail, dict):
            continue
        try:
            max_score = max(max_score, float(detail.get("score", 0.0)))
        except (TypeError, ValueError):
            continue
    return max_score


class SafeToShipGate:
    """Evaluates deployment readiness from validation, risk, and compliance signals."""

    @staticmethod
    def evaluate(report: Dict[str, Any], environment: str = "dev") -> Dict[str, Any]:
        env = environment.lower()
        rules = ENVIRONMENT_RULES.get(env, ENVIRONMENT_RULES["dev"])
        summary = report.get("summary", {}) or {}
        drift_summary = report.get("drift_summary", {}) or {}
        compliance = report.get("compliance_scorecard", {}) or {}

        pass_rate = float(summary.get("pass_rate", 0.0))
        validation_failed = int(summary.get("validation_failed", 0))
        max_risk_score = _max_risk(report)
        compliance_health = float(compliance.get("overall_compliance_health", 0.0))
        breaking_drifts = int(drift_summary.get("breaking_changes", 0))

        blockers: List[str] = []
        if pass_rate < rules["min_pass_rate"]:
            blockers.append(
                f"Pass rate {pass_rate}% is below {rules['min_pass_rate']}% for {env}."
            )
        if validation_failed > 0:
            blockers.append(f"{validation_failed} validation test(s) failed.")
        if max_risk_score > rules["max_risk_score"]:
            blockers.append(
                f"Max risk score {max_risk_score:.2f} exceeds {rules['max_risk_score']:.2f}."
            )
        if env in {"staging", "prod"} and breaking_drifts > 0:
            blockers.append(f"{breaking_drifts} breaking drift issue(s) detected.")
        if compliance_health < rules["min_compliance"]:
            blockers.append(
                f"Compliance health {compliance_health}% is below {rules['min_compliance']}%."
            )

        penalty = (100.0 - pass_rate) + (max(0.0, max_risk_score - rules["max_risk_score"]) * 100.0)
        if validation_failed:
            penalty += 20.0
        if breaking_drifts:
            penalty += 15.0
        if compliance_health < rules["min_compliance"]:
            penalty += (rules["min_compliance"] - compliance_health)

        score = max(0.0, round(100.0 - penalty, 1))
        return {
            "environment": env,
            "safe_to_ship": len(blockers) == 0,
            "score": score,
            "blockers": blockers,
            "thresholds": rules,
            "signals": {
                "pass_rate": pass_rate,
                "validation_failed": validation_failed,
                "max_risk_score": round(max_risk_score, 3),
                "breaking_drifts": breaking_drifts,
                "compliance_health": compliance_health,
            },
        }
