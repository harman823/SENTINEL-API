import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.breaking_change_predictor import BreakingChangePredictor
from backend.app.services.chaos_resilience import ChaosResilienceTester
from backend.app.services.iac_validator import IaCValidator
from backend.app.services.pr_remediation_bot import PRRemediationBot
from backend.app.services.root_cause_analyst import RootCauseAnalyst
from backend.app.services.safe_to_ship_gate import SafeToShipGate
from backend.app.services.semantic_traffic_replay import SemanticTrafficReplay
from backend.app.services.spec_normalizer import SpecNormalizer
from backend.app.graph.builder import GraphBuilder


def test_semantic_replay_sanitizes_sensitive_headers():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Replay API", "version": "1.0"},
        "paths": {
            "/users/{id}": {
                "get": {
                    "responses": {"200": {"description": "ok"}}
                }
            }
        },
    }
    normalized = SpecNormalizer.normalize(spec)
    records = [
        {
            "method": "GET",
            "path": "/users/123",
            "headers": {"Authorization": "Bearer secret"},
            "status_code": 200,
        }
    ]

    replay_cases = SemanticTrafficReplay.to_test_cases(normalized, records)
    assert len(replay_cases) == 1
    assert replay_cases[0]["headers"]["Authorization"] == "***redacted***"
    assert replay_cases[0]["spec_reference"] == "paths./users/{id}.get"


def test_iac_validator_flags_missing_required_controls():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "IaC API", "version": "1.0"},
        "paths": {"/secure": {"get": {"responses": {"200": {"description": "ok"}}}}},
        "components": {
            "securitySchemes": {
                "oauth2_auth": {
                    "type": "oauth2",
                    "flows": {"clientCredentials": {"tokenUrl": "https://example/token", "scopes": {}}},
                }
            }
        },
        "security": [{"oauth2_auth": []}],
    }

    result = IaCValidator.validate(spec, ['resource "aws_api_gateway_rest_api" "api" {}'])
    assert result["passed"] is False
    assert "oauth2_policy" in result["missing_controls"]


def test_breaking_change_predictor_detects_removed_operation():
    previous = {
        "openapi": "3.0.0",
        "info": {"title": "Prev", "version": "1.0"},
        "paths": {"/users": {"get": {"responses": {"200": {"description": "ok"}}}}},
    }
    current = {
        "openapi": "3.0.0",
        "info": {"title": "Curr", "version": "2.0"},
        "paths": {},
    }

    prediction = BreakingChangePredictor.predict([previous], current)
    assert prediction["summary"]["total"] >= 1
    assert any(item["change_type"] == "operation_removed" for item in prediction["predictions"])


def test_chaos_tester_matches_documented_negative_response():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Chaos API", "version": "1.0"},
        "paths": {
            "/health": {
                "get": {
                    "responses": {
                        "200": {"description": "ok"},
                        "503": {"description": "down"},
                    }
                }
            }
        },
    }
    normalized = SpecNormalizer.normalize(spec)

    test_cases = [
        {"id": "t1", "method": "GET", "path": "/health"},
        {"id": "t2", "method": "GET", "path": "/health"},
        {"id": "t3", "method": "GET", "path": "/health"},
    ]
    execution_results = [
        {"test_id": "t1", "method": "GET", "status_code": 200, "passed": True},
        {"test_id": "t2", "method": "GET", "status_code": 200, "passed": True},
        {"test_id": "t3", "method": "GET", "status_code": 200, "passed": True},
    ]

    chaos = ChaosResilienceTester.run(
        spec=normalized,
        test_cases=test_cases,
        execution_results=execution_results,
        fault_rate=1.0,
        max_cases=3,
        seed=7,
    )
    service_unavailable = [item for item in chaos if item["chaos_type"] == "service_unavailable"]
    assert service_unavailable
    assert service_unavailable[0]["documented_in_spec"] is True


def test_root_cause_analyst_and_safe_to_ship_gate():
    validation_results = [{"test_id": "bad_status", "passed": False, "assertions": [], "summary": "status mismatch"}]
    execution_results = [{"test_id": "bad_status", "method": "GET", "status_code": 500, "error": None}]
    test_cases = [{"id": "bad_status", "method": "GET", "path": "/users", "expected_status": 200, "spec_reference": "paths./users.get.responses.200"}]

    findings = RootCauseAnalyst.analyze(validation_results, execution_results, test_cases)
    assert findings
    assert findings[0]["category"] == "status_code_mismatch"

    report = {
        "summary": {"pass_rate": 90.0, "validation_failed": 1},
        "risk_details": {"/users.get": {"score": 0.9}},
        "drift_summary": {"breaking_changes": 1},
        "compliance_scorecard": {"overall_compliance_health": 60.0},
    }
    decision = SafeToShipGate.evaluate(report, environment="prod")
    assert decision["safe_to_ship"] is False
    assert decision["blockers"]


def test_pr_remediation_bot_builds_pr_payload():
    remediation_results = [
        {
            "endpoint": "GET /users",
            "status": "remediated_locally",
            "patch_proposed": '[{"action":"add_field","path":"paths./users.get.responses.200"}]',
        }
    ]

    suggestions = PRRemediationBot.build_suggestions(remediation_results, spec_path="openapi.yaml")
    assert len(suggestions) == 1
    assert suggestions[0]["ready_for_pr"] is True
    assert suggestions[0]["files"][0]["path"] == "openapi.yaml"


def test_graph_builder_compilation_is_cached():
    first = GraphBuilder.build()
    second = GraphBuilder.build()
    assert first is second
