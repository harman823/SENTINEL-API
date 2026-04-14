"""
Compliance scorecard generator.

Builds framework and endpoint-level compliance health metrics from
test-to-control mappings and validation outcomes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _parse_endpoint_key(endpoint: str) -> Tuple[str, str]:
    endpoint = endpoint.strip()
    if " " not in endpoint:
        return "", endpoint
    method, path = endpoint.split(" ", 1)
    return method.upper(), path.strip()


def _risk_for_endpoint(endpoint: str, risk_details: Dict[str, Any]) -> float:
    method, path = _parse_endpoint_key(endpoint)
    if not method:
        return 0.0
    key = f"{path}.{method.lower()}"
    detail = risk_details.get(key, {})
    if isinstance(detail, dict):
        try:
            return float(detail.get("score", 0.0))
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _risk_weight(score: float) -> float:
    if score >= 0.7:
        return 1.5
    if score >= 0.4:
        return 1.2
    return 1.0


class ComplianceScorecard:
    """Compute compliance health percentages with risk-aware weighting."""

    @staticmethod
    def generate(
        compliance_mappings: List[Dict[str, Any]],
        validation_results: List[Dict[str, Any]],
        risk_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        pass_by_test_id = {
            item.get("test_id"): bool(item.get("passed", False))
            for item in validation_results
        }

        framework_acc: Dict[str, Dict[str, float]] = {}
        endpoint_acc: Dict[Tuple[str, str], Dict[str, float]] = {}
        total_weight = 0.0
        passed_weight = 0.0

        for mapping in compliance_mappings:
            test_id = mapping.get("test_id")
            endpoint = mapping.get("endpoint", "")
            passed = pass_by_test_id.get(test_id, False)
            frameworks = mapping.get("frameworks", {}) or {}
            risk = _risk_for_endpoint(endpoint, risk_details)
            weight = _risk_weight(risk)

            if frameworks:
                total_weight += weight
                if passed:
                    passed_weight += weight

            for framework in frameworks.keys():
                acc = framework_acc.setdefault(
                    framework,
                    {"weighted_total": 0.0, "weighted_passed": 0.0, "tests": 0, "passed_tests": 0},
                )
                acc["weighted_total"] += weight
                acc["weighted_passed"] += weight if passed else 0.0
                acc["tests"] += 1
                if passed:
                    acc["passed_tests"] += 1

                ep_key = (endpoint, framework)
                ep_acc = endpoint_acc.setdefault(
                    ep_key,
                    {"weighted_total": 0.0, "weighted_passed": 0.0, "tests": 0, "passed_tests": 0},
                )
                ep_acc["weighted_total"] += weight
                ep_acc["weighted_passed"] += weight if passed else 0.0
                ep_acc["tests"] += 1
                if passed:
                    ep_acc["passed_tests"] += 1

        framework_scores: Dict[str, Dict[str, Any]] = {}
        for framework, acc in framework_acc.items():
            weighted_total = max(acc["weighted_total"], 1.0)
            score = round((acc["weighted_passed"] / weighted_total) * 100, 1)
            framework_scores[framework] = {
                "score": score,
                "total_tests": int(acc["tests"]),
                "passed_tests": int(acc["passed_tests"]),
                "failed_tests": int(acc["tests"] - acc["passed_tests"]),
            }

        endpoint_scores: List[Dict[str, Any]] = []
        for (endpoint, framework), acc in endpoint_acc.items():
            weighted_total = max(acc["weighted_total"], 1.0)
            score = round((acc["weighted_passed"] / weighted_total) * 100, 1)
            endpoint_scores.append(
                {
                    "endpoint": endpoint,
                    "framework": framework,
                    "score": score,
                    "total_tests": int(acc["tests"]),
                    "passed_tests": int(acc["passed_tests"]),
                }
            )

        endpoint_scores.sort(key=lambda item: (item["score"], item["endpoint"], item["framework"]))
        overall = round((passed_weight / max(total_weight, 1.0)) * 100, 1)

        return {
            "overall_compliance_health": overall,
            "framework_scores": framework_scores,
            "endpoint_scores": endpoint_scores,
            "mapped_tests": len(compliance_mappings),
        }
