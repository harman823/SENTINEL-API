from __future__ import annotations

import datetime
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Ensure `backend.app.*` imports resolve when launching from either repo root
# (`backend.app.main`) or backend directory (`app.main`).
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.app.core.database import get_db
from backend.app.schemas.policy import ApiPolicyCreate, ApiPolicyUpdate


app = FastAPI(
    title="AutoAPI Intelligence",
    description="Automated API testing powered by LangGraph",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    from backend.app.core.database import init_db

    await init_db()


class RunPipelineRequest(BaseModel):
    spec_raw: Dict[str, Any]
    approve: bool = False
    live: bool = False
    environment: str = "dev"  # dev | staging | prod
    policy_config: Optional[Dict[str, Any]] = None
    spec_history: List[Dict[str, Any]] = Field(default_factory=list)
    traffic_samples: List[Dict[str, Any]] = Field(default_factory=list)
    iac_sources: List[str] = Field(default_factory=list)
    chaos_enabled: bool = False
    chaos_fault_rate: float = 0.25
    max_concurrency: int = 16


class PipelineSummary(BaseModel):
    total_operations: int
    total_tests: int
    pass_rate: float
    execution_passed: int
    execution_failed: int
    validation_passed: int
    validation_failed: int
    approval_required: bool
    risk_distribution: Dict[str, int]
    lint_issues: int = 0
    security_tests: int = 0
    drift_count: int = 0
    compliance_frameworks: List[str] = Field(default_factory=list)
    safe_to_ship: bool = False
    safe_to_ship_score: float = 0.0


class PipelineResponse(BaseModel):
    success: bool
    summary: Optional[PipelineSummary] = None
    report: Optional[Dict[str, Any]] = None
    execution_history: List[Dict[str, Any]] = Field(default_factory=list)
    blast_radius: Optional[Dict[str, Any]] = None
    dynamic_mock_routes: List[Dict[str, Any]] = Field(default_factory=list)
    mock_notifications: List[Dict[str, Any]] = Field(default_factory=list)
    repo_inspection: Optional[Dict[str, Any]] = None
    api_manifest: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)


class GitHubInspectRequest(BaseModel):
    url: str
    selected_path: Optional[str] = None


class GitHubInspectResponse(BaseModel):
    success: bool
    repo_inspection: Optional[Dict[str, Any]] = None
    api_manifest: Optional[Dict[str, Any]] = None
    approval_required: bool = False
    approval_prompt: str = ""
    errors: List[str] = Field(default_factory=list)


class GitHubRunRequest(BaseModel):
    url: str
    selected_path: Optional[str] = None
    approve: bool = False
    live: bool = False


class LintRequest(BaseModel):
    spec_raw: Dict[str, Any]


class MockRequest(BaseModel):
    spec_raw: Dict[str, Any]


class DynamicMockRequest(BaseModel):
    spec_raw: Dict[str, Any]
    method: str
    path: str
    reason: str = "manual"


class IaCValidationRequest(BaseModel):
    spec_raw: Dict[str, Any]
    iac_sources: List[str] = Field(default_factory=list)


class BreakingChangeRequest(BaseModel):
    current_spec: Dict[str, Any]
    spec_history: List[Dict[str, Any]] = Field(default_factory=list)


class TrafficReplayRequest(BaseModel):
    spec_raw: Dict[str, Any]
    traffic_samples: List[Dict[str, Any]] = Field(default_factory=list)
    base_url: str = "http://localhost"


class ChaosSandboxRequest(BaseModel):
    spec_raw: Dict[str, Any]
    target_method: str = "GET"
    target_path: str
    base_url: str = "http://localhost"
    fault_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    latency_ms: int = Field(default=8000, ge=1)
    malformed_payload_types: List[str] = Field(default_factory=list)
    traffic_samples: List[Dict[str, Any]] = Field(default_factory=list)
    max_cases: int = Field(default=12, ge=1, le=50)


class SafeToShipRequest(BaseModel):
    report: Dict[str, Any]
    environment: str = "dev"


class RemediationRequest(BaseModel):
    spec_raw: Dict[str, Any]
    drift_results: List[Dict[str, Any]] = Field(default_factory=list)
    test_cases: List[Dict[str, Any]] = Field(default_factory=list)
    execution_results: List[Dict[str, Any]] = Field(default_factory=list)
    apply_patch: bool = False


class RemediationResponse(BaseModel):
    success: bool
    remediation_results: List[Dict[str, Any]] = Field(default_factory=list)
    remediation_patch: Optional[Dict[str, Any]] = None
    suggested_diff: Optional[str] = None
    updated_spec: Optional[Dict[str, Any]] = None
    pr_remediation_suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class LiveLintRequest(BaseModel):
    source_path: str
    spec_raw: Dict[str, Any]


class LiveLintResponse(BaseModel):
    diagnostics: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0
    errors: List[str] = Field(default_factory=list)


def _policy_to_response(policy: Any) -> Dict[str, Any]:
    return {
        "id": policy.id,
        "name": policy.name,
        "category": policy.category,
        "rule_type": policy.rule_type,
        "severity": policy.severity,
        "description": policy.description,
        "config": json.loads(policy.config_json or "{}"),
        "enabled": policy.enabled,
        "created_at": policy.created_at,
        "updated_at": policy.updated_at,
    }


def _initial_state(request: RunPipelineRequest) -> Dict[str, Any]:
    from backend.app.services.api_spec_compat import ApiSpecCompat

    spec_raw = ApiSpecCompat.to_openapi3(request.spec_raw)
    spec_history = [ApiSpecCompat.to_openapi3(spec) for spec in request.spec_history]
    return {
        "spec_raw": spec_raw,
        "spec_history": spec_history,
        "traffic_samples": request.traffic_samples,
        "iac_sources": request.iac_sources,
        "chaos_enabled": request.chaos_enabled,
        "chaos_fault_rate": request.chaos_fault_rate,
        "max_concurrency": request.max_concurrency,
        "risk_scores": {},
        "risk_details": {},
        "lint_results": [],
        "breaking_change_predictions": [],
        "iac_validation": {},
        "policy_config": request.policy_config,
        "test_cases": [],
        "security_test_cases": [],
        "security_results": [],
        "execution_results": [],
        "chaos_results": [],
        "validation_results": [],
        "rca_results": [],
        "drift_results": [],
        "dynamic_mock_routes": [],
        "mock_notifications": [],
        "remediation_results": [],
        "remediation_patch": None,
        "suggested_diff": None,
        "pr_remediation_suggestions": [],
        "compliance_mappings": [],
        "policy_results": [],
        "approval_required": False,
        "approval_status": request.approve,
        "environment": request.environment,
        "live": request.live,
        "errors": [],
    }


@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "autoapi-intelligence"}


@app.post("/api/v1/run", response_model=PipelineResponse)
async def run_pipeline(request: RunPipelineRequest):
    try:
        from backend.app.graph.builder import GraphBuilder
        from backend.app.services.blast_radius import BlastRadiusService

        graph = GraphBuilder.build()
        result = await graph.ainvoke(_initial_state(request))

        errors = result.get("errors", [])
        if errors:
            return PipelineResponse(success=False, errors=errors)

        report = result.get("report", {})
        report_summary = report.get("summary", {})
        lint_summary = report.get("lint_summary", {})
        security_summary = report.get("security_summary", {})
        drift_summary = report.get("drift_summary", {})
        compliance_summary = report.get("compliance_summary", {})
        safe_to_ship = report.get("safe_to_ship", {})

        summary = PipelineSummary(
            total_operations=report.get("spec_info", {}).get("total_operations", 0),
            total_tests=report_summary.get("total_tests", 0),
            pass_rate=report_summary.get("pass_rate", 0),
            execution_passed=report_summary.get("execution_passed", 0),
            execution_failed=report_summary.get("execution_failed", 0),
            validation_passed=report_summary.get("validation_passed", 0),
            validation_failed=report_summary.get("validation_failed", 0),
            approval_required=report_summary.get("approval_required", False),
            risk_distribution=report.get("risk_distribution", {}),
            lint_issues=lint_summary.get("total_issues", 0),
            security_tests=security_summary.get("total_security_tests", 0),
            drift_count=drift_summary.get("total_drifts", 0),
            compliance_frameworks=compliance_summary.get("frameworks_covered", []),
            safe_to_ship=bool(safe_to_ship.get("safe_to_ship", False)),
            safe_to_ship_score=float(safe_to_ship.get("score", 0.0)),
        )

        blast_radius = None
        if result.get("spec_normalized"):
            blast_radius = BlastRadiusService.compute(result["spec_normalized"])

        now = datetime.datetime.utcnow().isoformat()
        execution_history = [
            {"step": 1, "action": "Linted OpenAPI", "timestamp": now, "details": f"Found {summary.lint_issues} issue(s)."},
            {"step": 2, "action": "Predicted Breaking Changes", "timestamp": now, "details": f"Predictions: {len(report.get('breaking_change_predictions', []))}"},
            {"step": 3, "action": "Validated IaC Contracts", "timestamp": now, "details": f"IaC score: {report.get('iac_validation', {}).get('score', 0)}"},
            {"step": 4, "action": "Parsed and Scored Risk", "timestamp": now, "details": f"Operations: {summary.total_operations}"},
            {"step": 5, "action": "Generated Tests", "timestamp": now, "details": f"Total tests: {summary.total_tests}"},
            {"step": 6, "action": "Executed and Validated", "timestamp": now, "details": f"Pass rate: {summary.pass_rate}%"},
            {"step": 7, "action": "Analyzed Failures", "timestamp": now, "details": f"RCA findings: {report.get('rca_summary', {}).get('total_findings', 0)}"},
            {"step": 8, "action": "Generated Report", "timestamp": now, "details": f"Safe to ship: {summary.safe_to_ship}"},
        ]

        return PipelineResponse(
            success=True,
            summary=summary,
            report=report,
            execution_history=execution_history,
            blast_radius=blast_radius,
            dynamic_mock_routes=result.get("dynamic_mock_routes", []),
            mock_notifications=result.get("mock_notifications", []),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/v1/upload", response_model=PipelineResponse)
async def upload_spec(file: UploadFile = File(...), approve: bool = False, live: bool = False):
    try:
        content = await file.read()
        filename = file.filename or "spec.yaml"

        if filename.endswith((".yaml", ".yml")):
            spec_raw = yaml.safe_load(content)
        elif filename.endswith(".json"):
            spec_raw = json.loads(content)
        else:
            raise HTTPException(status_code=400, detail="File must be .yaml, .yml, or .json")

        return await run_pipeline(RunPipelineRequest(spec_raw=spec_raw, approve=approve, live=live))
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(exc)}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(exc)}")


@app.post("/api/v1/github-run", response_model=PipelineResponse)
async def github_run(request: GitHubRunRequest):
    from backend.app.services.github_repo_analyzer import GitHubRepoAnalyzer

    try:
        inspection = GitHubRepoAnalyzer.inspect_repo(request.url, selected_path=request.selected_path)
        spec_raw = inspection["selected_spec_raw"]
        response = await run_pipeline(
            RunPipelineRequest(spec_raw=spec_raw, approve=request.approve, live=request.live)
        )
        response.repo_inspection = inspection["repo_inspection"]
        response.api_manifest = inspection["api_manifest"]
        return response
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/v1/github-inspect", response_model=GitHubInspectResponse)
async def github_inspect(request: GitHubInspectRequest):
    from backend.app.services.github_repo_analyzer import GitHubRepoAnalyzer

    try:
        inspection = GitHubRepoAnalyzer.inspect_repo(request.url, selected_path=request.selected_path)
        repo_inspection = inspection["repo_inspection"]
        return GitHubInspectResponse(
            success=True,
            repo_inspection=repo_inspection,
            api_manifest=inspection["api_manifest"],
            approval_required=bool(repo_inspection.get("approval_required", False)),
            approval_prompt=repo_inspection.get("approval_prompt", ""),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/v1/validate")
async def validate_spec(request: RunPipelineRequest):
    try:
        from backend.app.services.spec_normalizer import SpecNormalizer
        from backend.app.services.spec_validator import SpecValidator
        from backend.app.services.api_spec_compat import ApiSpecCompat

        spec_raw = ApiSpecCompat.to_openapi3(request.spec_raw)
        SpecValidator.validate(spec_raw)
        normalized = SpecNormalizer.normalize(spec_raw)
        return {
            "valid": True,
            "operations": len(normalized.operations),
            "destructive": sum(1 for op in normalized.operations if op.is_destructive),
        }
    except ValueError as exc:
        return {"valid": False, "error": str(exc)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/v1/lint")
async def lint_spec(request: LintRequest):
    try:
        from backend.app.services.spec_linter import SpecLinter

        issues = SpecLinter.lint(request.spec_raw)
        issue_dicts = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in issues
        ]
        errors = sum(1 for item in issue_dicts if item.get("severity") == "error")
        warnings = sum(1 for item in issue_dicts if item.get("severity") == "warning")
        return {
            "total_issues": len(issue_dicts),
            "errors": errors,
            "warnings": warnings,
            "issues": issue_dicts,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/v1/mock")
async def generate_mocks(request: MockRequest):
    try:
        from backend.app.services.mock_server import MockServerGenerator
        from backend.app.services.spec_normalizer import SpecNormalizer

        normalized = SpecNormalizer.normalize(request.spec_raw)
        mocks = MockServerGenerator.generate(normalized, request.spec_raw)
        return {"endpoints": len(mocks), "mocks": mocks}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/v1/dynamic-mocks")
async def create_dynamic_mock(request: DynamicMockRequest):
    try:
        from backend.app.services.api_spec_compat import ApiSpecCompat
        from backend.app.services.mock_server import DynamicMockRouteRegistry
        from backend.app.services.spec_normalizer import SpecNormalizer

        spec_raw = ApiSpecCompat.to_openapi3(request.spec_raw)
        normalized = SpecNormalizer.normalize(spec_raw)
        route = DynamicMockRouteRegistry.provision_endpoint(
            normalized,
            spec_raw,
            method=request.method,
            path=request.path,
            reason=request.reason,
        )
        return {
            "success": True,
            "route": route,
            "notification": DynamicMockRouteRegistry._notification(route),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/v1/dynamic-mocks")
async def list_dynamic_mocks():
    from backend.app.services.mock_server import DynamicMockRouteRegistry

    return {
        "routes": DynamicMockRouteRegistry.list_routes(),
        "notifications": DynamicMockRouteRegistry.list_notifications(),
    }


@app.api_route("/api/v1/dynamic-mock/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def serve_dynamic_mock(request: Request, path: str):
    from backend.app.services.mock_server import DynamicMockRouteRegistry

    route_path = f"/{path}"
    route = DynamicMockRouteRegistry.resolve(request.method, route_path)
    if not route:
        raise HTTPException(status_code=404, detail=f"No dynamic mock registered for {request.method} {route_path}")
    headers = {
        "X-Sentinel-Dynamic-Mock": "true",
        "X-Sentinel-Mocked-Endpoint": f"{route['method']} {route['path']}",
    }
    return Response(
        content=json.dumps(route.get("body", {}), default=str),
        status_code=int(route.get("status_code", 200)),
        media_type="application/json",
        headers=headers,
    )


@app.post("/api/v1/remediate-drift", response_model=RemediationResponse)
@app.post("/api/v1/one-click-fixes", response_model=RemediationResponse)
async def remediate_drift(request: RemediationRequest):
    try:
        from backend.app.services.api_spec_compat import ApiSpecCompat
        from backend.app.services.pr_remediation_bot import DriftRemediationPatchBuilder, PRRemediationBot

        spec_raw = ApiSpecCompat.to_openapi3(request.spec_raw)
        remediation_results, remediation_patch, suggested_diff = DriftRemediationPatchBuilder.build(
            spec_raw=spec_raw,
            drift_results=request.drift_results,
            test_cases=request.test_cases,
            execution_results=request.execution_results,
        )
        updated_spec = None
        if request.apply_patch and remediation_patch:
            updated_spec = DriftRemediationPatchBuilder.apply_to_spec(spec_raw, remediation_patch)

        return RemediationResponse(
            success=True,
            remediation_results=remediation_results,
            remediation_patch=remediation_patch,
            suggested_diff=suggested_diff,
            updated_spec=updated_spec,
            pr_remediation_suggestions=PRRemediationBot.build_suggestions(remediation_results),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/v1/live-lint", response_model=LiveLintResponse)
async def live_lint(request: LiveLintRequest):
    try:
        from backend.app.services.api_spec_compat import ApiSpecCompat
        from backend.app.services.live_contract_linter import LiveContractLinter

        spec_raw = ApiSpecCompat.to_openapi3(request.spec_raw)
        return LiveLintResponse(**LiveContractLinter.lint_file(request.source_path, spec_raw))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/v1/policies")
async def list_policies(db: AsyncSession = Depends(get_db)):
    from backend.app.models.policy import ApiPolicy

    result = await db.execute(select(ApiPolicy).order_by(ApiPolicy.created_at.desc()))
    return {"policies": [_policy_to_response(policy) for policy in result.scalars().all()]}


@app.post("/api/v1/policies")
async def create_policy(
    request: ApiPolicyCreate,
    db: AsyncSession = Depends(get_db),
):
    from backend.app.models.policy import ApiPolicy

    result = await db.execute(select(ApiPolicy).where(ApiPolicy.name == request.name))
    if result.scalars().first():
        raise HTTPException(status_code=409, detail="A policy with this name already exists.")

    policy = ApiPolicy(
        name=request.name,
        category=request.category,
        rule_type=request.rule_type,
        severity=request.severity,
        description=request.description,
        config_json=json.dumps(request.config),
        enabled=request.enabled,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return _policy_to_response(policy)


@app.put("/api/v1/policies/{policy_id}")
async def update_policy(
    policy_id: int,
    request: ApiPolicyUpdate,
    db: AsyncSession = Depends(get_db),
):
    from backend.app.models.policy import ApiPolicy

    result = await db.execute(select(ApiPolicy).where(ApiPolicy.id == policy_id))
    policy = result.scalars().first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")

    updates = request.model_dump(exclude_unset=True)
    if "name" in updates:
        policy.name = updates["name"]
    if "category" in updates:
        policy.category = updates["category"]
    if "rule_type" in updates:
        policy.rule_type = updates["rule_type"]
    if "severity" in updates:
        policy.severity = updates["severity"]
    if "description" in updates:
        policy.description = updates["description"]
    if "config" in updates:
        policy.config_json = json.dumps(updates["config"])
    if "enabled" in updates:
        policy.enabled = updates["enabled"]
    policy.updated_at = datetime.datetime.utcnow()

    await db.commit()
    await db.refresh(policy)
    return _policy_to_response(policy)


@app.delete("/api/v1/policies/{policy_id}")
async def delete_policy(
    policy_id: int,
    db: AsyncSession = Depends(get_db),
):
    from backend.app.models.policy import ApiPolicy

    result = await db.execute(select(ApiPolicy).where(ApiPolicy.id == policy_id))
    policy = result.scalars().first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")
    await db.delete(policy)
    await db.commit()
    return {"success": True}


@app.post("/api/v1/validate-iac")
async def validate_iac(request: IaCValidationRequest):
    try:
        from backend.app.services.iac_validator import IaCValidator

        return IaCValidator.validate(request.spec_raw, request.iac_sources)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/v1/predict-breaking-changes")
async def predict_breaking_changes(request: BreakingChangeRequest):
    try:
        from backend.app.services.breaking_change_predictor import BreakingChangePredictor

        return BreakingChangePredictor.predict(
            spec_history=request.spec_history,
            current_spec=request.current_spec,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/v1/traffic-replay")
async def traffic_replay(request: TrafficReplayRequest):
    try:
        from backend.app.services.semantic_traffic_replay import SemanticTrafficReplay
        from backend.app.services.spec_normalizer import SpecNormalizer

        normalized = SpecNormalizer.normalize(request.spec_raw)
        replay_tests = SemanticTrafficReplay.to_test_cases(
            spec=normalized,
            records=request.traffic_samples,
            base_url=request.base_url,
        )
        return {"replay_tests": replay_tests, "count": len(replay_tests)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def _sse_event(event: str, payload: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"


@app.post("/api/v1/sandbox/stream")
async def chaos_sandbox_stream(request: ChaosSandboxRequest):
    async def event_stream():
        try:
            from backend.app.services.api_spec_compat import ApiSpecCompat
            from backend.app.services.chaos_resilience import ChaosResilienceTester
            from backend.app.services.semantic_traffic_replay import SemanticTrafficReplay
            from backend.app.services.spec_normalizer import SpecNormalizer

            spec_raw = ApiSpecCompat.to_openapi3(request.spec_raw)
            normalized = SpecNormalizer.normalize(spec_raw)
            endpoint = f"{request.target_method.upper()} {request.target_path}"
            yield _sse_event("status", {"stage": "setup", "message": f"Sandbox armed for {endpoint}"})
            await asyncio.sleep(0)

            traffic_samples = request.traffic_samples or [
                {
                    "method": request.target_method.upper(),
                    "path": request.target_path,
                    "headers": {"x-sentinel-sandbox": "true"},
                    "status_code": 200,
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                }
            ]
            replay_tests = SemanticTrafficReplay.to_test_cases(
                spec=normalized,
                records=traffic_samples,
                base_url=request.base_url.rstrip("/"),
            )
            replay_tests = [
                item
                for item in replay_tests
                if item.get("method", "").upper() == request.target_method.upper()
                and item.get("path") == request.target_path
            ] or replay_tests[:1]

            for test_case in replay_tests:
                yield _sse_event("replay", {"message": f"Replay generated for {test_case['method']} {test_case['path']}", "test_case": test_case})
                await asyncio.sleep(0)

            execution_results = [
                {
                    "test_id": test_case["id"],
                    "method": test_case["method"],
                    "status_code": test_case.get("expected_status", 200),
                    "passed": True,
                    "response_time_ms": 120,
                }
                for test_case in replay_tests
            ]
            chaos_results = ChaosResilienceTester.run(
                spec=normalized,
                test_cases=replay_tests,
                execution_results=execution_results,
                fault_rate=request.fault_rate,
                latency_ms=request.latency_ms,
                max_cases=request.max_cases,
            )

            for result in chaos_results:
                yield _sse_event("chaos", {"message": result.get("message", ""), "result": result})
                await asyncio.sleep(0)

            for malformed_type in request.malformed_payload_types:
                probe = {
                    "endpoint": endpoint,
                    "payload_type": malformed_type,
                    "expected_behavior": "OpenAPI should document a matching 4xx response.",
                    "passed": any(
                        str(code).startswith("4")
                        for op in normalized.operations
                        if op.method.upper() == request.target_method.upper() and op.path == request.target_path
                        for code in op.responses.keys()
                    ),
                }
                probe["message"] = (
                    f"Malformed payload '{malformed_type}' is covered by a 4xx response."
                    if probe["passed"]
                    else f"Malformed payload '{malformed_type}' lacks documented 4xx coverage."
                )
                yield _sse_event("malformed", probe)
                await asyncio.sleep(0)

            total_events = len(replay_tests) + len(chaos_results) + len(request.malformed_payload_types)
            passed = sum(1 for item in chaos_results if item.get("passed"))
            failed = len(chaos_results) - passed
            yield _sse_event(
                "summary",
                {
                    "endpoint": endpoint,
                    "total_events": total_events,
                    "replay_cases": len(replay_tests),
                    "chaos_findings": len(chaos_results),
                    "passed": passed,
                    "failed": failed,
                    "message": f"Sandbox completed for {endpoint}: {passed} documented, {failed} undocumented chaos findings.",
                },
            )
        except Exception as exc:
            yield _sse_event("error", {"message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/v1/safe-to-ship")
async def safe_to_ship(request: SafeToShipRequest):
    try:
        from backend.app.services.safe_to_ship_gate import SafeToShipGate

        return SafeToShipGate.evaluate(request.report, environment=request.environment)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
