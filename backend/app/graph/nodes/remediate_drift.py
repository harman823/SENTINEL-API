import logging
from typing import Any, Dict

from backend.app.graph.state import GraphState
from backend.app.services.pr_remediation_bot import DriftRemediationPatchBuilder, PRRemediationBot

logger = logging.getLogger(__name__)


def remediate_drift_node(state: GraphState) -> Dict[str, Any]:
    """
    Graph node: generate one-click remediation patches for contract drift.
    """
    try:
        drift_results = state.get("drift_results", [])
        if not drift_results:
            return {
                "remediation_results": [],
                "remediation_patch": None,
                "suggested_diff": None,
                "pr_remediation_suggestions": [],
            }

        remediation_results, remediation_patch, suggested_diff = DriftRemediationPatchBuilder.build(
            spec_raw=state.get("spec_raw", {}),
            drift_results=drift_results,
            test_cases=state.get("test_cases", []),
            execution_results=state.get("execution_results", []),
        )

        pr_suggestions = PRRemediationBot.build_suggestions(remediation_results)
        logger.info("Generated %s drift remediation result(s)", len(remediation_results))
        return {
            "remediation_results": remediation_results,
            "remediation_patch": remediation_patch,
            "suggested_diff": suggested_diff,
            "pr_remediation_suggestions": pr_suggestions,
        }

    except Exception as exc:
        logger.error("Remediation failed: %s", str(exc))
        return {
            "remediation_results": [],
            "remediation_patch": None,
            "suggested_diff": None,
            "pr_remediation_suggestions": [],
            "errors": (state.get("errors") or []) + [f"Remediation failed: {str(exc)}"],
        }
