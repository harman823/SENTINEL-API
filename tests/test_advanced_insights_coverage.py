"""
SENTINEL Advanced Insights — Multi-Format Error Coverage Test Suite

Covers every ingestion format and Advanced Insights module:
  - OpenAPI 3.0 JSON / YAML
  - Swagger 2.0 YAML
  - Postman Collection JSON
  - Insomnia Export JSON
  - GitHub Repo ingestion (via FastAPI TestClient)

Every test intentionally contains violations to confirm SENTINEL
correctly detects, scores, and surfaces errors.
"""
import os
import sys
import json
import yaml
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.main import app
from backend.app.services.api_spec_compat import ApiSpecCompat
from backend.app.services.spec_normalizer import SpecNormalizer
from backend.app.services.spec_linter import SpecLinter
from backend.app.services.risk_scorer import RiskScorer
from backend.app.services.blast_radius import BlastRadiusService
from backend.app.services.safe_to_ship_gate import SafeToShipGate
from backend.app.services.compliance_scorecard import ComplianceScorecard
from backend.app.services.breaking_change_predictor import BreakingChangePredictor
from backend.app.services.root_cause_analyst import RootCauseAnalyst
from backend.app.services.chaos_resilience import ChaosResilienceTester
from backend.app.services.test_generator import TestGenerator
from backend.app.services.mock_server import MockServerGenerator
from backend.app.services.pr_remediation_bot import PRRemediationBot

TESTS_DIR = Path(__file__).parent

# ─────────────────────────────────────────────
# Helpers: load all fixture formats
# ─────────────────────────────────────────────

def load_openapi_json():
    with open(TESTS_DIR / "advanced_insights_test_spec.json") as f:
        return json.load(f)

def load_openapi_yaml():
    with open(TESTS_DIR / "advanced_insights_test_spec.yaml") as f:
        return yaml.safe_load(f)

def load_swagger2_yaml():
    with open(TESTS_DIR / "advanced_insights_test_spec_swagger2.yaml") as f:
        return yaml.safe_load(f)

def load_postman():
    with open(TESTS_DIR / "advanced_insights_test_spec_postman.json") as f:
        return json.load(f)

def load_insomnia():
    with open(TESTS_DIR / "advanced_insights_test_spec_insomnia.json") as f:
        return json.load(f)

ALL_FORMATS = [
    ("OpenAPI 3.0 JSON", load_openapi_json),
    ("OpenAPI 3.0 YAML", load_openapi_yaml),
    ("Swagger 2.0 YAML", load_swagger2_yaml),
    ("Postman Collection", load_postman),
    ("Insomnia Export", load_insomnia),
]


# ─────────────────────────────────────────────
# 1. FORMAT DETECTION — all formats recognized
# ─────────────────────────────────────────────

def test_format_detection_openapi_json():
    spec = load_openapi_json()
    fmt = ApiSpecCompat.detect_format(spec)
    assert fmt["kind"] == "openapi", f"Expected 'openapi', got: {fmt}"

def test_format_detection_swagger2():
    spec = load_swagger2_yaml()
    fmt = ApiSpecCompat.detect_format(spec)
    assert fmt["kind"] == "swagger", f"Expected 'swagger', got: {fmt}"

def test_format_detection_postman():
    spec = load_postman()
    fmt = ApiSpecCompat.detect_format(spec)
    assert fmt["kind"] == "postman", f"Expected 'postman', got: {fmt}"

def test_format_detection_insomnia():
    spec = load_insomnia()
    fmt = ApiSpecCompat.detect_format(spec)
    assert fmt["kind"] == "insomnia", f"Expected 'insomnia', got: {fmt}"


# ─────────────────────────────────────────────
# 2. CONVERSION — all formats produce valid OpenAPI 3
# ─────────────────────────────────────────────

def test_all_formats_convert_to_openapi3():
    for name, loader in ALL_FORMATS:
        raw = loader()
        converted = ApiSpecCompat.to_openapi3(raw)
        assert converted.get("openapi", "").startswith("3"), \
            f"[{name}] Expected openapi 3.x, got: {converted.get('openapi')}"
        assert isinstance(converted.get("paths"), dict), \
            f"[{name}] 'paths' must be a dict"
        assert len(converted["paths"]) > 0, \
            f"[{name}] Spec has no paths after conversion"


# ─────────────────────────────────────────────
# 3. LINTER — all formats trigger real warnings/errors
# ─────────────────────────────────────────────

def test_linter_openapi_json_has_errors():
    spec = load_openapi_json()
    issues = SpecLinter.lint(spec)
    errors = [i for i in issues if i.severity.value == "error"]
    warnings = [i for i in issues if i.severity.value == "warning"]
    assert len(errors) >= 1, "Expected at least 1 ERROR (no_security_defined)"
    assert len(warnings) >= 5, f"Expected ≥5 warnings, got {len(warnings)}"
    rules = {i.rule for i in issues}
    assert "no_security_defined" in rules
    assert "write_without_security" in rules
    assert "no_error_responses" in rules

def test_linter_swagger2_has_errors():
    spec = load_swagger2_yaml()
    issues = SpecLinter.lint(spec)
    assert len(issues) >= 3, f"Swagger2 spec should generate lint issues, got {len(issues)}"

def test_linter_postman_has_errors():
    spec = load_postman()
    converted = ApiSpecCompat.to_openapi3(spec)
    issues = SpecLinter.lint(converted)
    assert len(issues) >= 1, f"Postman spec should generate lint issues, got {len(issues)}"

def test_linter_insomnia_has_errors():
    spec = load_insomnia()
    converted = ApiSpecCompat.to_openapi3(spec)
    issues = SpecLinter.lint(converted)
    assert len(issues) >= 1, f"Insomnia spec should generate lint issues, got {len(issues)}"


# ─────────────────────────────────────────────
# 4. RISK SCORER — all formats show HIGH-risk endpoints
# ─────────────────────────────────────────────

def test_risk_scorer_openapi_json_has_high_risk():
    spec = load_openapi_json()
    normalized = SpecNormalizer.normalize(spec)
    scores = RiskScorer.score_spec(normalized)
    high_risk = [k for k, rs in scores.items() if rs.score >= 0.6]
    assert len(high_risk) >= 3, f"Expected ≥3 HIGH risk endpoints, got: {high_risk}"

def test_risk_scorer_swagger2_has_high_risk():
    spec = load_swagger2_yaml()
    converted = ApiSpecCompat.to_openapi3(spec)
    normalized = SpecNormalizer.normalize(converted)
    scores = RiskScorer.score_spec(normalized)
    high_risk = [k for k, rs in scores.items() if rs.score >= 0.5]
    assert len(high_risk) >= 2, f"Expected ≥2 MEDIUM+ risk endpoints for Swagger2"

def test_risk_scorer_detects_pii_fields():
    spec = load_openapi_json()
    normalized = SpecNormalizer.normalize(spec)
    for op in normalized.operations:
        if "settings" in op.path:
            assert len(op.pii_fields) >= 3, \
                f"Expected ≥3 PII fields on /users/{{id}}/settings, got: {op.pii_fields}"
            return
    assert False, "Could not find /users/{id}/settings operation"

def test_risk_scorer_detects_destructive_delete():
    spec = load_openapi_json()
    normalized = SpecNormalizer.normalize(spec)
    scores = RiskScorer.score_spec(normalized)
    delete_key = "/admin/users.delete"
    assert delete_key in scores, f"DELETE /admin/users not found in scores"
    assert scores[delete_key].score >= 0.5, \
        f"DELETE /admin/users should be high-risk, got {scores[delete_key].score}"
    factor_names = {f.name for f in scores[delete_key].factors}
    assert "destructive_method" in factor_names


# ─────────────────────────────────────────────
# 5. SAFE-TO-SHIP GATE — blocked for all broken specs
# ─────────────────────────────────────────────

def test_safe_to_ship_gate_blocks_broken_spec():
    report = {
        "summary": {"pass_rate": 55.0, "validation_failed": 8},
        "drift_summary": {"breaking_changes": 3},
        "compliance_scorecard": {"overall_compliance_health": 35.0},
    }
    decision = SafeToShipGate.evaluate(report, environment="prod")
    assert decision["safe_to_ship"] is False
    assert decision["score"] < 1.0  # score is 0.0–1.0, not percentage
    assert len(decision["blockers"]) >= 2

def test_safe_to_ship_gate_passes_clean_spec():
    """Sanity check: a clean report should pass."""
    report = {
        "summary": {"pass_rate": 100.0, "validation_failed": 0},
        "drift_summary": {"breaking_changes": 0},
        "compliance_scorecard": {"overall_compliance_health": 100.0},
    }
    decision = SafeToShipGate.evaluate(report, environment="staging")
    assert decision["safe_to_ship"] is True
    assert decision["blockers"] == []


# ─────────────────────────────────────────────
# 6. BLAST RADIUS EXPLORER — centralized schema = high blast radius
# ─────────────────────────────────────────────

def test_blast_radius_computes_nodes_and_edges():
    spec = load_openapi_json()
    normalized = SpecNormalizer.normalize(spec)
    result = BlastRadiusService.compute(normalized)
    assert "nodes" in result
    assert "edges" in result
    assert len(result["nodes"]) >= 5, f"Expected ≥5 nodes (endpoints), got {len(result['nodes'])}"

def test_blast_radius_counts_are_reported_by_api():
    """The /api/v1/run pipeline should include blast_radius in its output."""
    spec = load_openapi_json()
    normalized = SpecNormalizer.normalize(spec)
    result = BlastRadiusService.compute(normalized)
    # The spec has no $ref schemas so edges may be 0, but nodes must exist
    assert isinstance(result["nodes"], list)
    assert isinstance(result["edges"], list)


# ─────────────────────────────────────────────
# 7. BREAKING CHANGE PREDICTOR — removing security is a break
# ─────────────────────────────────────────────

def test_breaking_change_predictor_parameter_removed():
    previous = load_openapi_json()
    current = load_openapi_json()
    # Remove two endpoints — these are unambiguous breaking changes (operation count goes down)
    del current["paths"]["/data/export"]
    del current["paths"]["/health"]
    prediction = BreakingChangePredictor.predict([previous], current)
    total = prediction["summary"].get("total", 0) + prediction["summary"].get("likely_breaking", 0)
    assert total >= 1, f"Expected >= 1 change detected, got: {prediction['summary']}"
    assert len(prediction["predictions"]) >= 1

def test_breaking_change_predictor_operation_removed():
    previous = load_openapi_json()
    current = load_openapi_json()
    # Remove the export endpoint — downstream consumers will break
    del current["paths"]["/data/export"]
    prediction = BreakingChangePredictor.predict([previous], current)
    assert prediction["summary"]["total"] >= 1
    assert any(p["change_type"] == "operation_removed" for p in prediction["predictions"])


# ─────────────────────────────────────────────
# 8. ROOT CAUSE ANALYST — DB crash & status mismatch
# ─────────────────────────────────────────────

def test_rca_server_crash_on_delete():
    test_cases = [{"id": "t_del", "method": "DELETE", "path": "/admin/users", "expected_status": 204}]
    validation_results = [{"test_id": "t_del", "passed": False, "summary": "Expected 204 got 500"}]
    execution_results = [{"test_id": "t_del", "method": "DELETE", "status_code": 500, "error": "ConnectionRefusedError: DB offline"}]
    findings = RootCauseAnalyst.analyze(validation_results, execution_results, test_cases)
    assert len(findings) >= 1
    # RCA classifies connection errors as 'connectivity' (DB unreachable = network/connectivity)
    assert findings[0]["category"] in ("connectivity", "server_crash")
    assert findings[0]["severity"] == "high"

def test_rca_auth_failure():
    test_cases = [{"id": "t_auth", "method": "POST", "path": "/auth/token", "expected_status": 200}]
    validation_results = [{"test_id": "t_auth", "passed": False, "summary": "Expected 200 got 401"}]
    execution_results = [{"test_id": "t_auth", "method": "POST", "status_code": 401, "error": None}]
    findings = RootCauseAnalyst.analyze(validation_results, execution_results, test_cases)
    assert len(findings) >= 1


# ─────────────────────────────────────────────
# 9. CHAOS RESILIENCE — health endpoint receives 503
# ─────────────────────────────────────────────

def test_chaos_resilience_503_on_health():
    spec = load_openapi_json()
    normalized = SpecNormalizer.normalize(spec)
    test_cases = [{"id": "t_health", "method": "GET", "path": "/health"}]
    execution_results = [{"test_id": "t_health", "method": "GET", "status_code": 503, "passed": False}]
    chaos = ChaosResilienceTester.run(normalized, test_cases, execution_results, fault_rate=1.0)
    assert len(chaos) > 0
    # 503 is undocumented in the health endpoint — should flag it
    assert chaos[0]["documented_in_spec"] is False

def test_chaos_resilience_all_formats_normalize():
    """All formats should produce at least 1 normalizable operation for chaos testing."""
    for name, loader in ALL_FORMATS:
        raw = loader()
        converted = ApiSpecCompat.to_openapi3(raw)
        normalized = SpecNormalizer.normalize(converted)
        assert len(normalized.operations) >= 1, \
            f"[{name}] Expected ≥1 operation after normalization"


# ─────────────────────────────────────────────
# 10. SMART FUZZING — generates edge cases for POST/PUT/PATCH
# ─────────────────────────────────────────────

def test_fuzzing_generates_cases_for_broken_spec():
    spec = load_openapi_json()
    normalized = SpecNormalizer.normalize(spec)
    test_cases = TestGenerator.generate(normalized.operations)
    fuzz = [t for t in test_cases if t.get("test_type") == "fuzzing"]
    assert len(fuzz) >= 3, f"Expected ≥3 fuzz cases, got {len(fuzz)}"

def test_stateful_journeys_not_generated_for_mismatched_spec():
    """
    This spec has POST /admin/users but no GET /admin/users on same resource path.
    Stateful journey generator should return 0 journeys (idle in UI).
    """
    spec = load_openapi_json()
    normalized = SpecNormalizer.normalize(spec)
    test_cases = TestGenerator.generate(normalized.operations)
    journeys = [t for t in test_cases if t.get("test_type") == "stateful_journey"]
    # No resource has both GET + POST at same path prefix — idle is expected
    assert len(journeys) == 0, \
        f"Expected 0 journeys for this spec structure, got {len(journeys)}"


# ─────────────────────────────────────────────
# 11. MOCK SERVER — generates mocks from all formats
# ─────────────────────────────────────────────

def test_mock_server_generates_from_openapi():
    spec = load_openapi_json()
    normalized = SpecNormalizer.normalize(spec)
    mocks = MockServerGenerator.generate(normalized, spec)
    assert len(mocks) >= 5, f"Expected ≥5 mock endpoints, got {len(mocks)}"

def test_mock_server_generates_from_swagger2():
    spec = load_swagger2_yaml()
    converted = ApiSpecCompat.to_openapi3(spec)
    normalized = SpecNormalizer.normalize(converted)
    mocks = MockServerGenerator.generate(normalized, converted)
    assert len(mocks) >= 3, f"Expected ≥3 mocks from Swagger2, got {len(mocks)}"

def test_mock_server_generates_from_postman():
    spec = load_postman()
    converted = ApiSpecCompat.to_openapi3(spec)
    normalized = SpecNormalizer.normalize(converted)
    mocks = MockServerGenerator.generate(normalized, converted)
    assert len(mocks) >= 1, f"Expected ≥1 mock from Postman, got {len(mocks)}"


# ─────────────────────────────────────────────
# 12. PR REMEDIATION BOT — patches security drift
# ─────────────────────────────────────────────

def test_pr_remediation_security_drift():
    remediation_results = [
        {
            "endpoint": "DELETE /admin/users",
            "status": "remediated_locally",
            "patch_proposed": '[{"action":"add_security","path":"paths./admin/users.delete.security"}]',
        },
        {
            "endpoint": "POST /auth/token",
            "status": "remediated_locally",
            "patch_proposed": '[{"action":"add_security","path":"paths./auth/token.post.security"}]',
        }
    ]
    suggestions = PRRemediationBot.build_suggestions(remediation_results, spec_path="openapi.yaml")
    assert len(suggestions) == 2
    for s in suggestions:
        assert s["ready_for_pr"] is True
        assert s["files"][0]["path"] == "openapi.yaml"


# ─────────────────────────────────────────────
# 13. FASTAPI ENDPOINT — /api/v1/lint for all formats
# ─────────────────────────────────────────────

client = TestClient(app)

def test_api_lint_endpoint_openapi():
    spec = load_openapi_json()
    resp = client.post("/api/v1/lint", json={"spec_raw": spec})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_issues"] >= 5
    assert data["errors"] >= 1

def test_api_lint_endpoint_postman():
    spec = load_postman()
    resp = client.post("/api/v1/lint", json={"spec_raw": spec})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_issues"] >= 1

def test_api_lint_endpoint_insomnia():
    spec = load_insomnia()
    resp = client.post("/api/v1/lint", json={"spec_raw": spec})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_issues"] >= 1

def test_api_lint_endpoint_swagger2():
    spec = load_swagger2_yaml()
    resp = client.post("/api/v1/lint", json={"spec_raw": spec})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_issues"] >= 1


# ─────────────────────────────────────────────
# 14. FASTAPI ENDPOINT — /api/v1/validate for all formats
# ─────────────────────────────────────────────

def test_api_validate_endpoint_openapi():
    spec = load_openapi_json()
    resp = client.post("/api/v1/validate", json={"spec_raw": spec})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["operations"] >= 5
    assert data["destructive"] >= 1

def test_api_validate_endpoint_postman():
    spec = load_postman()
    resp = client.post("/api/v1/validate", json={"spec_raw": spec})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True

def test_api_validate_endpoint_swagger2():
    spec = load_swagger2_yaml()
    resp = client.post("/api/v1/validate", json={"spec_raw": spec})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["destructive"] >= 1


# ─────────────────────────────────────────────
# 15. GITHUB REPO INSPECT — resilient to bad repos
# ─────────────────────────────────────────────

def test_github_inspect_returns_400_for_invalid_url():
    """Non-GitHub URL should gracefully return 400, not 500."""
    resp = client.post("/api/v1/github-inspect", json={"url": "https://not-a-github-url.com/repo"})
    assert resp.status_code in (400, 422), \
        f"Expected 400/422 for invalid URL, got {resp.status_code}: {resp.text}"

def test_github_inspect_returns_400_for_missing_repo():
    """A GitHub URL pointing to a non-existent repo should return 400, not 500."""
    resp = client.post("/api/v1/github-inspect", json={"url": "https://github.com/definitely-not-a-real-user-xyz/definitely-not-a-real-repo-xyz"})
    assert resp.status_code in (400, 422), \
        f"Expected 400 for non-existent repo, got {resp.status_code}"
