from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure `backend.app.*` imports resolve when launching from either repo root
# (`backend.app.main`) or backend directory (`app.main`).
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


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
    errors: List[str] = Field(default_factory=list)


class GitHubRunRequest(BaseModel):
    url: str
    approve: bool = False
    live: bool = False


class LintRequest(BaseModel):
    spec_raw: Dict[str, Any]


class MockRequest(BaseModel):
    spec_raw: Dict[str, Any]


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


class SafeToShipRequest(BaseModel):
    report: Dict[str, Any]
    environment: str = "dev"


def _initial_state(request: RunPipelineRequest) -> Dict[str, Any]:
    return {
        "spec_raw": request.spec_raw,
        "spec_history": request.spec_history,
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
        "remediation_results": [],
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
    from backend.app.services.openapi_loader import OpenAPILoader

    try:
        spec_raw = OpenAPILoader.load_spec(request.url)
        return await run_pipeline(
            RunPipelineRequest(spec_raw=spec_raw, approve=request.approve, live=request.live)
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/v1/validate")
async def validate_spec(request: RunPipelineRequest):
    try:
        from backend.app.services.spec_normalizer import SpecNormalizer
        from backend.app.services.spec_validator import SpecValidator

        SpecValidator.validate(request.spec_raw)
        normalized = SpecNormalizer.normalize(request.spec_raw)
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


@app.post("/api/v1/safe-to-ship")
async def safe_to_ship(request: SafeToShipRequest):
    try:
        from backend.app.services.safe_to_ship_gate import SafeToShipGate

        return SafeToShipGate.evaluate(request.report, environment=request.environment)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
