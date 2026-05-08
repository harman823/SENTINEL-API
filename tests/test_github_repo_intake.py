from pathlib import Path
import asyncio

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

    async def fake_fetch_json(url: str):
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

    async def fake_fetch_text(url: str):
        if url.endswith("/api/openapi.yaml"):
            return fixture_text
        if url.endswith("/docs/reference.json"):
            return "{}"
        raise AssertionError(f"Unexpected text URL: {url}")

    monkeypatch.setattr(GitHubRepoAnalyzer, "_fetch_json", staticmethod(fake_fetch_json))
    monkeypatch.setattr(GitHubRepoAnalyzer, "_fetch_text", staticmethod(fake_fetch_text))

    inspection = asyncio.run(GitHubRepoAnalyzer.inspect_repo("https://github.com/acme/security-demo"))

    repo_inspection = inspection["repo_inspection"]
    api_manifest = inspection["api_manifest"]

    assert repo_inspection["full_name"] == "acme/security-demo"
    assert repo_inspection["selected_spec"]["path"] == "api/openapi.yaml"
    assert repo_inspection["approval_required"] is True
    assert [item["path"] for item in repo_inspection["candidate_specs"]] == ["api/openapi.yaml", "docs/reference.json"]
    assert api_manifest["api_catalog"]["summary"]["high_risk_operations"] >= 2
    assert api_manifest["api_catalog"]["operations"][0]["risk_score"] >= 0.6
    assert inspection["selected_spec_raw"]["info"]["title"] == spec["info"]["title"]
    assert repo_inspection["detected_frameworks"] == []
    assert repo_inspection["scanned_source_files"] == 0


def test_github_repo_analyzer_extracts_routes_from_framework_code(monkeypatch):
    fastapi_source = """
from fastapi import FastAPI, APIRouter

app = FastAPI()
router = APIRouter(prefix="/admin/system")

@app.get("/health")
async def health():
    return {"ok": True}

@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    return {"deleted": user_id}
"""
    flask_source = """
from flask import Flask

app = Flask(__name__)

@app.route("/system/secrets/<secret_id>", methods=["PATCH"])
def rotate_secret(secret_id):
    return {"secret": secret_id}
"""

    async def fake_fetch_json(url: str):
        if url.endswith("/repos/acme/framework-demo"):
            return {
                "name": "framework-demo",
                "full_name": "acme/framework-demo",
                "html_url": "https://github.com/acme/framework-demo",
                "description": "Repo without OpenAPI docs but with API frameworks",
                "default_branch": "main",
                "stargazers_count": 2,
                "watchers_count": 2,
                "forks_count": 0,
                "visibility": "public",
            }
        if url.endswith("/languages"):
            return {"Python": 2500}
        if "git/trees/main" in url:
            return {
                "tree": [
                    {"path": "backend/app.py", "type": "blob", "size": 350},
                    {"path": "backend/admin.py", "type": "blob", "size": 280},
                    {"path": "README.md", "type": "blob", "size": 200},
                ]
            }
        raise AssertionError(f"Unexpected JSON URL: {url}")

    async def fake_fetch_text(url: str):
        if url.endswith("/backend/app.py"):
            return fastapi_source
        if url.endswith("/backend/admin.py"):
            return flask_source
        raise AssertionError(f"Unexpected text URL: {url}")

    monkeypatch.setattr(GitHubRepoAnalyzer, "_fetch_json", staticmethod(fake_fetch_json))
    monkeypatch.setattr(GitHubRepoAnalyzer, "_fetch_text", staticmethod(fake_fetch_text))

    inspection = asyncio.run(GitHubRepoAnalyzer.inspect_repo("https://github.com/acme/framework-demo"))

    repo_inspection = inspection["repo_inspection"]
    api_manifest = inspection["api_manifest"]

    assert repo_inspection["selected_source_kind"] == "code"
    assert repo_inspection["selected_spec"]["path"] == "[source-code]"
    assert repo_inspection["code_route_count"] == 3
    assert {item["framework"] for item in repo_inspection["detected_frameworks"]} == {"FastAPI", "Flask"}
    assert api_manifest["api_catalog"]["source_kind"] == "code"
    assert api_manifest["api_catalog"]["code_analysis"]["summary"]["route_count"] == 3
    assert "/admin/system/users/{user_id}" in inspection["selected_spec_raw"]["paths"]
    assert inspection["selected_spec_raw"]["paths"]["/admin/system/users/{user_id}"]["delete"]["x-sentinel-source"]["type"] == "code"


def test_github_repo_analyzer_scans_docs_and_code_when_spec_exists(monkeypatch):
    openapi_doc = {
        "openapi": "3.0.0",
        "info": {"title": "Documented API", "version": "1.0"},
        "paths": {
            "/documented": {
                "get": {"responses": {"200": {"description": "ok"}}}
            }
        },
    }
    fastapi_source = """
from fastapi import FastAPI

app = FastAPI()

@app.delete("/admin/accounts/{account_id}")
async def delete_account(account_id: str):
    return {"deleted": account_id}
"""

    async def fake_fetch_json(url: str):
        if url.endswith("/repos/acme/hybrid-demo"):
            return {
                "name": "hybrid-demo",
                "full_name": "acme/hybrid-demo",
                "html_url": "https://github.com/acme/hybrid-demo",
                "description": "Repo with API docs and source routes",
                "default_branch": "main",
                "stargazers_count": 1,
                "watchers_count": 1,
                "forks_count": 0,
                "visibility": "public",
            }
        if url.endswith("/languages"):
            return {"Python": 1200, "YAML": 200}
        if "git/trees/main" in url:
            return {
                "tree": [
                    {"path": "openapi.yaml", "type": "blob", "size": 500},
                    {"path": "backend/app.py", "type": "blob", "size": 300},
                ]
            }
        raise AssertionError(f"Unexpected JSON URL: {url}")

    async def fake_fetch_text(url: str):
        if url.endswith("/openapi.yaml"):
            return yaml.safe_dump(openapi_doc)
        if url.endswith("/backend/app.py"):
            return fastapi_source
        raise AssertionError(f"Unexpected text URL: {url}")

    monkeypatch.setattr(GitHubRepoAnalyzer, "_fetch_json", staticmethod(fake_fetch_json))
    monkeypatch.setattr(GitHubRepoAnalyzer, "_fetch_text", staticmethod(fake_fetch_text))

    inspection = asyncio.run(GitHubRepoAnalyzer.inspect_repo("https://github.com/acme/hybrid-demo"))

    repo_inspection = inspection["repo_inspection"]
    api_manifest = inspection["api_manifest"]

    assert repo_inspection["selected_source_kind"] == "hybrid"
    assert repo_inspection["code_route_count"] == 1
    assert repo_inspection["candidate_specs"][0]["document_kind"] == "openapi"
    assert api_manifest["api_catalog"]["code_analysis"]["summary"]["route_count"] == 1
    assert api_manifest["api_catalog"]["summary"]["total_operations"] == 2


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
    assert report["fix_prompt"]["generated_by"] == "langgraph.generate_report"
    assert report["fix_prompt"]["issue_count"] >= 4
    assert len(report["fix_prompts"]) == 1
    assert "Specific findings and fixes:" in report["fix_prompt"]["prompt"]
    assert "Approval blocked live deletion" in report["fix_prompt"]["prompt"]
