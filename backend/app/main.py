import os
import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from pathlib import Path
import yaml
import json
import tempfile

app = FastAPI(
    title="AutoAPI Intelligence",
    description="Automated API testing powered by LangGraph",
    version="2.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ──

class RunPipelineRequest(BaseModel):
    spec_raw: Dict[str, Any]
    approve: bool = False
    live: bool = False
    environment: str = "dev"  # dev | staging | prod
    policy_config: Optional[Dict[str, Any]] = None  # user-defined YAML policy


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
    # Intelligence metrics
    lint_issues: int = 0
    security_tests: int = 0
    drift_count: int = 0
    compliance_frameworks: List[str] = []


class PipelineResponse(BaseModel):
    success: bool
    summary: Optional[PipelineSummary] = None
    report: Optional[Dict[str, Any]] = None
    errors: List[str] = []


# ── Endpoints ──

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "autoapi-intelligence"}



@app.post("/api/v1/run", response_model=PipelineResponse)
async def run_pipeline(request: RunPipelineRequest):
    """Run the full LangGraph pipeline on a provided OpenAPI spec."""
    try:
        from backend.app.graph.builder import GraphBuilder

        initial_state = {
            "spec_raw": request.spec_raw,
            "risk_scores": {},
            "risk_details": {},
            "lint_results": [],
            "policy_config": request.policy_config,
            "test_cases": [],
            "security_test_cases": [],
            "security_results": [],
            "execution_results": [],
            "validation_results": [],
            "drift_results": [],
            "compliance_mappings": [],
            "policy_results": [],
            "approval_required": False,
            "approval_status": request.approve,
            "environment": request.environment,
            "live": request.live,
            "errors": [],
        }

        graph = GraphBuilder.build()
        result = graph.invoke(initial_state)

        errors = result.get("errors", [])
        if errors:
            return PipelineResponse(success=False, errors=errors)

        report = result.get("report", {})
        report_summary = report.get("summary", {})
        risk_dist = report.get("risk_distribution", {})

        lint_summary = report.get("lint_summary", {})
        sec_summary = report.get("security_summary", {})
        drift_summary = report.get("drift_summary", {})
        comp_summary = report.get("compliance_summary", {})

        summary = PipelineSummary(
            total_operations=report.get("spec_info", {}).get("total_operations", 0),
            total_tests=report_summary.get("total_tests", 0),
            pass_rate=report_summary.get("pass_rate", 0),
            execution_passed=report_summary.get("execution_passed", 0),
            execution_failed=report_summary.get("execution_failed", 0),
            validation_passed=report_summary.get("validation_passed", 0),
            validation_failed=report_summary.get("validation_failed", 0),
            approval_required=report_summary.get("approval_required", False),
            risk_distribution=risk_dist,
            lint_issues=lint_summary.get("total_issues", 0),
            security_tests=sec_summary.get("total_security_tests", 0),
            drift_count=drift_summary.get("total_drifts", 0),
            compliance_frameworks=comp_summary.get("frameworks_covered", []),
        )

        return PipelineResponse(success=True, summary=summary, report=report)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/upload", response_model=PipelineResponse)
async def upload_spec(
    file: UploadFile = File(...),
    approve: bool = False,
    live: bool = False
):
    """Upload an OpenAPI YAML/JSON file and run the pipeline."""
    try:
        content = await file.read()
        filename = file.filename or "spec.yaml"

        if filename.endswith((".yaml", ".yml")):
            spec_raw = yaml.safe_load(content)
        elif filename.endswith(".json"):
            spec_raw = json.loads(content)
        else:
            raise HTTPException(status_code=400, detail="File must be .yaml, .yml, or .json")

        request = RunPipelineRequest(spec_raw=spec_raw, approve=approve, live=live)
        return await run_pipeline(request)

    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")


class GitHubRunRequest(BaseModel):
    url: str
    approve: bool = False
    live: bool = False

@app.post("/api/v1/github-run", response_model=PipelineResponse)
async def github_run(request: GitHubRunRequest):
    """Fetch an OpenAPI spec from a GitHub URL and run the pipeline."""
    from backend.app.services.openapi_loader import OpenAPILoader
    try:
        spec_raw = OpenAPILoader.load_spec(request.url)
        run_request = RunPipelineRequest(spec_raw=spec_raw, approve=request.approve, live=request.live)
        return await run_pipeline(run_request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/validate")
async def validate_spec(request: RunPipelineRequest):
    """Validate an OpenAPI spec without running the full pipeline."""
    try:
        from backend.app.services.spec_validator import SpecValidator
        from backend.app.services.spec_normalizer import SpecNormalizer

        SpecValidator.validate(request.spec_raw)
        normalized = SpecNormalizer.normalize(request.spec_raw)

        return {
            "valid": True,
            "operations": len(normalized.operations),
            "destructive": sum(1 for op in normalized.operations if op.is_destructive),
        }

    except ValueError as e:
        return {"valid": False, "error": str(e)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class LintRequest(BaseModel):
    spec_raw: Dict[str, Any]


@app.post("/api/v1/lint")
async def lint_spec(request: LintRequest):
    """Lint an OpenAPI spec for quality issues without running the full pipeline."""
    try:
        from backend.app.services.spec_linter import SpecLinter

        issues = SpecLinter.lint(request.spec_raw)
        # Convert pydantic models to dicts
        issues_dicts = [i.model_dump() if hasattr(i, 'model_dump') else (i.dict() if hasattr(i, 'dict') else i) for i in issues]
        errors = sum(1 for i in issues_dicts if i.get("severity") == "error")
        warnings = sum(1 for i in issues_dicts if i.get("severity") == "warning")

        return {
            "total_issues": len(issues_dicts),
            "errors": errors,
            "warnings": warnings,
            "issues": issues_dicts,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class MockRequest(BaseModel):
    spec_raw: Dict[str, Any]


@app.post("/api/v1/mock")
async def generate_mocks(request: MockRequest):
    """Generate mock API responses from an OpenAPI specification."""
    try:
        from backend.app.services.spec_normalizer import SpecNormalizer
        from backend.app.services.mock_server import MockServerGenerator

        normalized = SpecNormalizer.normalize(request.spec_raw)
        mocks = MockServerGenerator.generate(normalized, request.spec_raw)

        return {
            "endpoints": len(mocks),
            "mocks": mocks,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


