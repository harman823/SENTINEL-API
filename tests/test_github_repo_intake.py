from pathlib import Path

import yaml

from backend.app.services.github_repo_analyzer import GitHubRepoAnalyzer
from backend.app.services.report_generator import ReportGenerator
from backend.app.services.risk_scorer import RiskScorer
from backend.app.services.spec_normalizer import SpecNormalizer


FIXTURE_PATH = Path(__file__).with_name("highest_risk_apis.yaml")


def _load_fixture():
    return yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_github_repo_analyzer_builds_repo_manifest(monkeypatch):
    spec = _load_fixture()
    fixture_text = FIXTURE_PATH.read_text(encoding="utf-8")

    def fake_fetch_json(url: str):
        if url.endswith("/repos/acme/security-demo"):
            return {
                "name": "security-demo",
                "full_name": "acme/security-demo",
                "html_url": "https://github.com/acme/security-demo",
                "description": "Demo repo for repo-level API intake",
                "default_branch": "main",
                "stargazers_count": 14,
                "watchers_count": 14,
                "forks_count": 3,
                "visibility": "public",
            }
        if url.endswith("/languages"):
            return {"Python": 1800, "TypeScript": 900, "Shell": 120}
        if "git/trees/main" in url:
            return {
                "tree": [
                    {"path": "README.md", "type": "blob", "size": 200},
                    {"path": "api/openapi.yaml", "type": "blob", "size": 1400},
                    {"path": "docs/reference.json", "type": "blob", "size": 120},
                    {"path": "src/index.ts", "type": "blob", "size": 300},
                ]
            }
        raise AssertionError(f"Unexpected JSON URL: {url}")

    def fake_fetch_text(url: str):
        if url.endswith("/api/openapi.yaml"):
            return fixture_text
        if url.endswith("/docs/reference.json"):
            return "{}"
        raise AssertionError(f"Unexpected text URL: {url}")

    monkeypatch.setattr(GitHubRepoAnalyzer, "_fetch_json", staticmethod(fake_fetch_json))
    monkeypatch.setattr(GitHubRepoAnalyzer, "_fetch_text", staticmethod(fake_fetch_text))

    inspection = GitHubRepoAnalyzer.inspect_repo("https://github.com/acme/security-demo")

    repo_inspection = inspection["repo_inspection"]
    api_manifest = inspection["api_manifest"]

    assert repo_inspection["full_name"] == "acme/security-demo"
    assert repo_inspection["selected_spec"]["path"] == "api/openapi.yaml"
    assert repo_inspection["approval_required"] is True
    assert api_manifest["api_catalog"]["summary"]["high_risk_operations"] >= 2
    assert api_manifest["api_catalog"]["operations"][0]["risk_score"] >= 0.6
    assert inspection["selected_spec_raw"]["info"]["title"] == spec["info"]["title"]


def test_report_generator_surfaces_high_risk_operations_and_errors():
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
            "messages": ["Approval required for destructive admin operation"],
        },
        {
            "operation_key": "/system/secrets/{secretId}.patch",
            "requires_approval": True,
            "violated_rules": ["high_risk_score"],
            "messages": ["Approval required for secret rotation"],
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
            "url": "https://demo.test/system/secrets/alpha",
            "path": "/system/secrets/{secretId}",
            "expected_status": 200,
            "is_destructive": True,
            "risk_score": risk_scores["/system/secrets/{secretId}.patch"],
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
            "response_time_ms": 120.0,
            "response_headers": {},
            "response_body_preview": '{"error":"forbidden"}',
            "error": "approval_required",
            "dry_run": False,
        },
        {
            "test_id": "rotate_secret",
            "method": "PATCH",
            "url": "https://demo.test/system/secrets/alpha",
            "status_code": 500,
            "expected_status": 200,
            "passed": False,
            "response_time_ms": 88.0,
            "response_headers": {},
            "response_body_preview": '{"error":"unexpected"}',
            "error": "undocumented_failure",
            "dry_run": False,
        },
    ]
    validation_results = [
        {"test_id": "delete_user", "passed": False, "assertions": [], "summary": "Forbidden"},
        {"test_id": "rotate_secret", "passed": False, "assertions": [], "summary": "Unexpected 500"},
    ]
    errors = [
        "Approval blocked live deletion run for /admin/system/users/{userId}.delete",
        "Unexpected 500 from /system/secrets/{secretId}.patch",
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

    assert len(high_risk_operations) >= 2
    assert high_risk_operations[0]["risk_score"] >= 0.6
    assert high_risk_operations[0]["risk_factors"]
    assert report["error_details"][0]["message"] == errors[0]
    assert report["summary"]["errors"] == len(errors)
