"""
Chaos resilience testing helpers.

Simulates common fault modes during execution analysis and checks whether
the spec documents matching negative responses.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.schemas.spec import NormalizedSpec


SUPPORTED_FAULTS = ("latency_spike", "timeout", "service_unavailable")


def _index_negative_statuses(spec: Optional[NormalizedSpec]) -> Dict[Tuple[str, str], Set[int]]:
    index: Dict[Tuple[str, str], Set[int]] = {}
    if not spec:
        return index

    for op in spec.operations:
        negatives: Set[int] = set()
        for code in op.responses.keys():
            if code.isdigit() and 400 <= int(code) < 600:
                negatives.add(int(code))
        index[(op.path, op.method.upper())] = negatives
    return index


def _find_test_case(test_cases: List[Dict[str, Any]], test_id: str) -> Optional[Dict[str, Any]]:
    for tc in test_cases:
        if tc.get("id") == test_id:
            return tc
    return None


class ChaosResilienceTester:
    """Injects synthetic faults and validates resilience documentation coverage."""

    @staticmethod
    def run(
        spec: Optional[NormalizedSpec],
        test_cases: List[Dict[str, Any]],
        execution_results: List[Dict[str, Any]],
        fault_rate: float = 0.25,
        latency_ms: int = 8_000,
        seed: int = 42,
        max_cases: int = 20,
    ) -> List[Dict[str, Any]]:
        if not execution_results:
            return []

        negative_index = _index_negative_statuses(spec)
        rng = random.Random(seed)
        findings: List[Dict[str, Any]] = []

        eligible = [er for er in execution_results if er.get("test_id")]
        if not eligible:
            return findings

        faults = list(SUPPORTED_FAULTS)
        selected: List[Dict[str, Any]] = []
        for er in eligible:
            if len(selected) >= max_cases:
                break
            if rng.random() <= fault_rate:
                selected.append(er)

        for idx, baseline in enumerate(selected):
            test_id = baseline.get("test_id", "")
            tc = _find_test_case(test_cases, test_id) or {}
            path = tc.get("path", "")
            method = tc.get("method", baseline.get("method", "GET")).upper()
            negatives = sorted(negative_index.get((path, method), set()))
            chaos_type = faults[idx % len(faults)]

            injected_status: Optional[int]
            injected_error: Optional[str]
            if chaos_type == "latency_spike":
                injected_status = baseline.get("status_code")
                injected_error = None
            elif chaos_type == "timeout":
                injected_status = None
                injected_error = "Injected timeout fault"
            else:
                injected_status = 503
                injected_error = None

            if chaos_type == "timeout":
                documented = any(code in (408, 504) for code in negatives)
            elif injected_status is not None:
                documented = injected_status in negatives
            else:
                documented = False

            pass_if_documented = documented
            findings.append(
                {
                    "chaos_test_id": f"{test_id}__CHAOS__{chaos_type.upper()}",
                    "baseline_test_id": test_id,
                    "endpoint": f"{method} {path}",
                    "chaos_type": chaos_type,
                    "injected_status_code": injected_status,
                    "injected_error": injected_error,
                    "injected_latency_ms": latency_ms if chaos_type == "latency_spike" else None,
                    "documented_negative_statuses": negatives,
                    "documented_in_spec": documented,
                    "passed": pass_if_documented,
                    "message": (
                        "Chaos behavior is documented in OpenAPI negative responses."
                        if pass_if_documented
                        else "OpenAPI negative responses do not document this failure mode."
                    ),
                }
            )

        return findings
