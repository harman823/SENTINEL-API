"""
LangGraph pipeline builder for the API intelligence workflow.
"""

from functools import lru_cache

from langgraph.graph import END, StateGraph

from backend.app.graph.nodes.analyze_rca import analyze_rca_node
from backend.app.graph.nodes.approval_gate import approval_gate_node
from backend.app.graph.nodes.detect_drift import detect_drift_node
from backend.app.graph.nodes.evaluate_policy import evaluate_policy_node
from backend.app.graph.nodes.execute_api import execute_api_node
from backend.app.graph.nodes.generate_report import generate_report_node
from backend.app.graph.nodes.generate_tests import generate_tests_node
from backend.app.graph.nodes.lint_spec import lint_spec_node
from backend.app.graph.nodes.map_compliance import map_compliance_node
from backend.app.graph.nodes.parse_spec import parse_spec_node
from backend.app.graph.nodes.predict_breaking_changes import predict_breaking_changes_node
from backend.app.graph.nodes.remediate_drift import remediate_drift_node
from backend.app.graph.nodes.score_risk import score_risk_node
from backend.app.graph.nodes.security_scan import security_scan_node
from backend.app.graph.nodes.validate_iac import validate_iac_node
from backend.app.graph.nodes.validate_responses import validate_responses_node
from backend.app.graph.state import GraphState


def merge_post_gen(_state: GraphState) -> dict:
    """Sync point after parallel generate_tests + security_scan."""
    return {}


def merge_post_validate(_state: GraphState) -> dict:
    """Sync point after parallel detect_drift + map_compliance + analyze_rca."""
    return {}


class GraphBuilder:
    """
    Workflow topology:

    lint_spec -> parse_spec -> predict_breaking_changes -> validate_iac
    -> score_risk -> evaluate_policy -> approval_gate
    -> [generate_tests || security_scan] -> merge_post_gen
    -> execute_api -> validate_responses
    -> [detect_drift || map_compliance || analyze_rca] -> merge_post_validate
    -> remediate_drift -> generate_report -> END
    """

    @staticmethod
    def build():
        return _build_compiled_graph()


@lru_cache(maxsize=1)
def _build_compiled_graph():
    """
    Compile once and reuse across requests.
    Graph compilation is expensive relative to execution for small specs.
    """
    workflow = StateGraph(GraphState)

    workflow.add_node("lint_spec", lint_spec_node)
    workflow.add_node("parse_spec", parse_spec_node)
    workflow.add_node("predict_breaking_changes", predict_breaking_changes_node)
    workflow.add_node("validate_iac", validate_iac_node)
    workflow.add_node("score_risk", score_risk_node)
    workflow.add_node("evaluate_policy", evaluate_policy_node)
    workflow.add_node("approval_gate", approval_gate_node)
    workflow.add_node("generate_tests", generate_tests_node)
    workflow.add_node("security_scan", security_scan_node)
    workflow.add_node("merge_post_gen", merge_post_gen)
    workflow.add_node("execute_api", execute_api_node)
    workflow.add_node("validate_responses", validate_responses_node)
    workflow.add_node("detect_drift", detect_drift_node)
    workflow.add_node("map_compliance", map_compliance_node)
    workflow.add_node("analyze_rca", analyze_rca_node)
    workflow.add_node("merge_post_validate", merge_post_validate)
    workflow.add_node("remediate_drift", remediate_drift_node)
    workflow.add_node("generate_report", generate_report_node)

    workflow.set_entry_point("lint_spec")
    workflow.add_edge("lint_spec", "parse_spec")
    workflow.add_edge("parse_spec", "predict_breaking_changes")
    workflow.add_edge("predict_breaking_changes", "validate_iac")
    workflow.add_edge("validate_iac", "score_risk")
    workflow.add_edge("score_risk", "evaluate_policy")
    workflow.add_edge("evaluate_policy", "approval_gate")

    workflow.add_edge("approval_gate", "generate_tests")
    workflow.add_edge("approval_gate", "security_scan")
    workflow.add_edge("generate_tests", "merge_post_gen")
    workflow.add_edge("security_scan", "merge_post_gen")

    workflow.add_edge("merge_post_gen", "execute_api")
    workflow.add_edge("execute_api", "validate_responses")

    workflow.add_edge("validate_responses", "detect_drift")
    workflow.add_edge("validate_responses", "map_compliance")
    workflow.add_edge("validate_responses", "analyze_rca")
    workflow.add_edge("detect_drift", "merge_post_validate")
    workflow.add_edge("map_compliance", "merge_post_validate")
    workflow.add_edge("analyze_rca", "merge_post_validate")

    workflow.add_edge("merge_post_validate", "remediate_drift")
    workflow.add_edge("remediate_drift", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow.compile()
