from pathlib import Path

import yaml

from backend.app.services.report_generator import ReportGenerator
from backend.app.services.risk_scorer import RiskScorer
from backend.app.services.spec_normalizer import SpecNormalizer


FIXTURE_PATH = Path(__file__).with_name("high_risk_failure_report.yaml")


def _load_fixture():
    return yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_failure_heavy_report_has_non_perfect_pass_rate_errors_and_multiple_high_risk_operations():
    spec = _load_fixture()
    normalized = SpecNormalizer.normalize(spec)
    detailed_scores = RiskScorer.score_spec(normalized)
    risk_scores = {key: value.score for key, value in detailed_scores.items()}
    risk_details = {key: value.model_dump() for key, value in detailed_scores.items()}

    policy_results = [
        {
            "operation_key": "/admin/system/users/{userId}.delete",
            "requires_approval": True,
            "violated_rules": ["destructive_method"],
            "messages": ["Approval required for destructive admin deletion"],
        },
        {
            "operation_key": "/system/secrets/{secretId}.patch",
            "requires_approval": True,
            "violated_rules": ["high_risk_score"],
            "messages": ["Approval required for secret rotation"],
        },
        {
            "operation_key": "/internal/admin/config.put",
            "requires_approval": True,
            "violated_rules": ["destructive_method", "high_risk_score"],
            "messages": ["Approval required for internal config replacement"],
        },
    ]

    test_cases = [
        {
            "id": "delete_user",
            "method": "DELETE",
            "url": "https://demo.test/admin/system/users/42",
            "path": "/admin/system/users/{userId}",
            "expected_status": 204,
            "is_destructive": True,
            "risk_score": risk_scores["/admin/system/users/{userId}.delete"],
        },
        {
            "id": "rotate_secret",
            "method": "PATCH",
            "url": "https://demo.test/system/secrets/core",
            "path": "/system/secrets/{secretId}",
            "expected_status": 200,
            "is_destructive": True,
            "risk_score": risk_scores["/system/secrets/{secretId}.patch"],
        },
        {
            "id": "replace_config",
            "method": "PUT",
            "url": "https://demo.test/internal/admin/config",
            "path": "/internal/admin/config",
            "expected_status": 200,
            "is_destructive": True,
            "risk_score": risk_scores["/internal/admin/config.put"],
        },
        {
            "id": "health_check",
            "method": "GET",
            "url": "https://demo.test/public/health",
            "path": "/public/health",
            "expected_status": 200,
            "is_destructive": False,
            "risk_score": risk_scores["/public/health.get"],
        },
    ]

    execution_results = [
        {
            "test_id": "delete_user",
            "method": "DELETE",
            "url": "https://demo.test/admin/system/users/42",
            "status_code": 403,
            "expected_status": 204,
            "passed": False,
            "response_time_ms": 133.0,
            "response_headers": {},
            "response_body_preview": '{"error":"forbidden"}',
            "error": "approval_required",
            "dry_run": False,
        },
        {
            "test_id": "rotate_secret",
            "method": "PATCH",
            "url": "https://demo.test/system/secrets/core",
            "status_code": 500,
            "expected_status": 200,
            "passed": False,
            "response_time_ms": 91.0,
            "response_headers": {},
            "response_body_preview": '{"error":"unexpected"}',
            "error": "unexpected_failure",
            "dry_run": False,
        },
        {
            "test_id": "replace_config",
            "method": "PUT",
            "url": "https://demo.test/internal/admin/config",
            "status_code": 400,
            "expected_status": 200,
            "passed": False,
            "response_time_ms": 77.0,
            "response_headers": {},
            "response_body_preview": '{"error":"invalid payload"}',
            "error": "bad_request",
            "dry_run": False,
        },
        {
            "test_id": "health_check",
            "method": "GET",
            "url": "https://demo.test/public/health",
            "status_code": 200,
            "expected_status": 200,
            "passed": True,
            "response_time_ms": 11.0,
            "response_headers": {},
            "response_body_preview": '{"ok":true}',
            "error": None,
            "dry_run": False,
        },
    ]

    validation_results = [
        {"test_id": "delete_user", "passed": False, "assertions": [], "summary": "Forbidden"},
        {"test_id": "rotate_secret", "passed": False, "assertions": [], "summary": "Unexpected 500"},
        {"test_id": "replace_config", "passed": False, "assertions": [], "summary": "Unexpected 400"},
        {"test_id": "health_check", "passed": True, "assertions": [], "summary": "Healthy"},
    ]

    errors = [
        "Approval blocked destructive deletion for /admin/system/users/{userId}.delete",
        "Unexpected 500 from /system/secrets/{secretId}.patch",
        "Unexpected 400 from /internal/admin/config.put",
    ]

    report = ReportGenerator.generate(
        spec_normalized=normalized,
        risk_scores=risk_scores,
        risk_details=risk_details,
        policy_results=policy_results,
        approval_required=True,
        approval_status=False,
        test_cases=test_cases,
        execution_results=execution_results,
        validation_results=validation_results,
        errors=errors,
        environment="prod",
    )

    high_risk_operations = report["risk_summary"]["high_risk_operations"]

    assert report["summary"]["pass_rate"] < 100
    assert report["summary"]["errors"] > 0
    assert len(report["errors"]) == len(errors)
    assert len(high_risk_operations) >= 3
    assert sum(1 for item in high_risk_operations if item["risk_score"] >= 0.6) >= 2
    assert report["risk_distribution"]["high"] >= 2
    assert report["fix_prompt"]["id"] == "sentinel-langgraph-remediation"
    assert report["fix_prompt"]["prompt"].count("Error:") >= 3
    assert "Fix:" in report["fix_prompt"]["prompt"]
