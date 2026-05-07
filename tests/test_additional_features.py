import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.breaking_change_predictor import BreakingChangePredictor
from backend.app.services.chaos_resilience import ChaosResilienceTester
from backend.app.services.iac_validator import IaCValidator
from backend.app.services.pr_remediation_bot import PRRemediationBot
from backend.app.services.pr_remediation_bot import DriftRemediationPatchBuilder
from backend.app.services.live_contract_linter import LiveContractLinter
from backend.app.services.mock_server import DynamicMockRouteRegistry
from backend.app.services.policy_engine import PolicyEngine
from fastapi.testclient import TestClient
from backend.app.main import app
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


def test_drift_remediation_builder_creates_applyable_openapi_patch():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Users API", "version": "1.0"},
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"id": {"type": "integer"}},
                                    }
                                }
                            },
                        }
                    }
                }
            }
        },
    }
    drift_results = [
        {
            "endpoint": "GET /users",
            "test_id": "t1",
            "drifts": [
                {
                    "drift_type": "extra_field",
                    "field_path": "response.email",
                    "expected": "not defined in schema",
                    "actual": "present with value type str",
                    "message": "extra field",
                }
            ],
            "is_breaking": False,
        }
    ]

    remediations, patch, diff = DriftRemediationPatchBuilder.build(
        spec,
        drift_results,
        test_cases=[{"id": "t1", "expected_status": 200}],
        execution_results=[{"test_id": "t1", "status_code": 200}],
    )

    assert remediations[0]["status"] == "patch_ready"
    assert patch is not None
    assert diff and "+                  email:" in diff
    updated = DriftRemediationPatchBuilder.apply_to_spec(spec, patch)
    properties = updated["paths"]["/users"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["properties"]
    assert properties["email"]["type"] == "string"


def test_live_contract_linter_flags_extra_response_field():
    source = Path(__file__).resolve().parent / "_sentinel_live_lint_test_api.py"
    source.write_text(
        "\n".join(
            [
                "from fastapi import FastAPI",
                "app = FastAPI()",
                "",
                "@app.get('/users')",
                "def users():",
                "    return {'id': 1, 'email': 'a@example.com'}",
            ]
        ),
        encoding="utf-8",
    )
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Users API", "version": "1.0"},
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"id": {"type": "integer"}},
                                    }
                                }
                            },
                        }
                    }
                }
            }
        },
    }

    result = LiveContractLinter.lint_file(str(source), spec)

    assert result["count"] == 1
    diagnostic = result["diagnostics"][0]
    assert diagnostic["code"] == "sentinel.extra_response_field"
    assert diagnostic["field"] == "email"
    assert diagnostic["remediation_patch"]["operations"][0]["path"].endswith("/properties/email")
    source.unlink(missing_ok=True)


def test_dynamic_mock_registry_provisions_breaking_drift_route():
    DynamicMockRouteRegistry.clear()
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Users API", "version": "1.0"},
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "name": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    }
                }
            }
        },
    }
    normalized = SpecNormalizer.normalize(spec)
    drift_results = [
        {
            "endpoint": "GET /users",
            "test_id": "t1",
            "drifts": [
                {
                    "drift_type": "status_code_mismatch",
                    "field_path": "status_code",
                    "expected": "one of [200]",
                    "actual": "500",
                    "message": "broken endpoint",
                }
            ],
            "is_breaking": True,
        }
    ]

    routes, notifications = DynamicMockRouteRegistry.provision_for_drift(normalized, spec, drift_results)

    assert len(routes) == 1
    assert routes[0]["mock_url"] == "/api/v1/dynamic-mock/users"
    assert routes[0]["body"]["name"]
    assert "Traffic is being dynamically mocked" in notifications[0]["message"]
    assert DynamicMockRouteRegistry.resolve("GET", "/users") is not None
    DynamicMockRouteRegistry.clear()


def test_policy_engine_uses_database_style_required_header_rule():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Policy API", "version": "1.0"},
        "paths": {
            "/users": {
                "get": {
                    "operationId": "getUsers",
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }
    normalized = SpecNormalizer.normalize(spec)
    engine = PolicyEngine(
        policy_config={
            "policies": {
                "request_id_required": {
                    "rule_type": "required_header",
                    "header": "x-request-id",
                    "message": "Every endpoint must require x-request-id.",
                }
            }
        },
        include_database_policies=False,
    )

    results = engine.evaluate(normalized.operations, {})

    assert results[0].requires_approval is True
    assert "policy:request_id_required" in results[0].violated_rules


def test_chaos_sandbox_stream_emits_summary():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Sandbox API", "version": "1.0"},
        "paths": {
            "/api/v1/orders": {
                "get": {
                    "operationId": "getOrders",
                    "responses": {
                        "200": {"description": "ok"},
                        "503": {"description": "unavailable"},
                    },
                }
            }
        },
    }
    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/v1/sandbox/stream",
            json={
                "spec_raw": spec,
                "target_method": "GET",
                "target_path": "/api/v1/orders",
                "fault_rate": 1,
                "malformed_payload_types": ["empty_body"],
            },
        ) as response:
            assert response.status_code == 200
            body = "".join(response.iter_text())

    assert "event: replay" in body
    assert "event: chaos" in body
    assert "event: summary" in body


def test_graph_builder_compilation_is_cached():
    first = GraphBuilder.build()
    second = GraphBuilder.build()
    assert first is second
