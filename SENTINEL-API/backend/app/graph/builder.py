"""
LangGraph Pipeline Builder — the expanded API Intelligence Pipeline.
Supports 12 nodes with conditional routing for security scan and drift detection.
"""

from langgraph.graph import StateGraph, END
from backend.app.graph.state import GraphState
from backend.app.graph.nodes.lint_spec import lint_spec_node
from backend.app.graph.nodes.parse_spec import parse_spec_node
from backend.app.graph.nodes.score_risk import score_risk_node
from backend.app.graph.nodes.evaluate_policy import evaluate_policy_node
from backend.app.graph.nodes.approval_gate import approval_gate_node
from backend.app.graph.nodes.generate_tests import generate_tests_node
from backend.app.graph.nodes.security_scan import security_scan_node
from backend.app.graph.nodes.execute_api import execute_api_node
from backend.app.graph.nodes.validate_responses import validate_responses_node
from backend.app.graph.nodes.detect_drift import detect_drift_node
from backend.app.graph.nodes.remediate_drift import remediate_drift_node
from backend.app.graph.nodes.map_compliance import map_compliance_node
from backend.app.graph.nodes.generate_report import generate_report_node


class GraphBuilder:
    """
    Builds the expanded API Intelligence pipeline:

    lint_spec → parse_spec → score_risk → evaluate_policy → approval_gate
      → generate_tests → security_scan → execute_api → validate_responses
      → detect_drift → remediate_drift → map_compliance → generate_report → END
    """

    @staticmethod
    def build():
        workflow = StateGraph(GraphState)

        # Add all nodes
        workflow.add_node("lint_spec", lint_spec_node)
        workflow.add_node("parse_spec", parse_spec_node)
        workflow.add_node("score_risk", score_risk_node)
        workflow.add_node("evaluate_policy", evaluate_policy_node)
        workflow.add_node("approval_gate", approval_gate_node)
        workflow.add_node("generate_tests", generate_tests_node)
        workflow.add_node("security_scan", security_scan_node)
        workflow.add_node("execute_api", execute_api_node)
        workflow.add_node("validate_responses", validate_responses_node)
        workflow.add_node("detect_drift", detect_drift_node)
        workflow.add_node("remediate_drift", remediate_drift_node)
        workflow.add_node("map_compliance", map_compliance_node)
        workflow.add_node("generate_report", generate_report_node)

        # Define edges — expanded linear pipeline
        workflow.set_entry_point("lint_spec")
        workflow.add_edge("lint_spec", "parse_spec")
        workflow.add_edge("parse_spec", "score_risk")
        workflow.add_edge("score_risk", "evaluate_policy")
        workflow.add_edge("evaluate_policy", "approval_gate")
        workflow.add_edge("approval_gate", "generate_tests")
        workflow.add_edge("generate_tests", "security_scan")
        workflow.add_edge("security_scan", "execute_api")
        workflow.add_edge("execute_api", "validate_responses")
        workflow.add_edge("validate_responses", "detect_drift")
        workflow.add_edge("detect_drift", "remediate_drift")
        workflow.add_edge("remediate_drift", "map_compliance")
        workflow.add_edge("map_compliance", "generate_report")
        workflow.add_edge("generate_report", END)

        return workflow.compile()
