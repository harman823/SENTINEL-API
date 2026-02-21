"""
Extended Pydantic models for the API Intelligence Platform.
Covers risk scoring, policy config, drift detection, compliance,
security testing, linting, environment profiles, and explainability.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


# ─── Risk Scoring ───────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskFactor(BaseModel):
    """A single contributing factor to an endpoint's risk score."""
    name: str
    weight: float = Field(ge=0.0, le=1.0)
    description: str


class RiskScore(BaseModel):
    """Full risk assessment for an endpoint."""
    endpoint: str  # path.method key
    score: float = Field(ge=0.0, le=1.0)
    level: RiskLevel
    factors: List[RiskFactor] = Field(default_factory=list)
    explanation: str = ""


# ─── Policy Configuration ──────────────────────────────────────

class PolicyRuleConfig(BaseModel):
    """A single policy rule from YAML config."""
    require_approval: bool = False
    min_negative_tests: int = 0
    must_fail_without_token: bool = False
    max_risk_score: Optional[float] = None
    custom_message: Optional[str] = None


class PolicyConfig(BaseModel):
    """User-defined policy configuration loaded from YAML."""
    policies: Dict[str, PolicyRuleConfig] = Field(default_factory=dict)


class PolicyViolation(BaseModel):
    """A policy violation with explanation."""
    rule_name: str
    endpoint: str
    message: str
    severity: str = "error"  # error | warning | info


# ─── Test Explainability ───────────────────────────────────────

class TestExplanation(BaseModel):
    """Why a test case exists and what it covers."""
    reason: str
    spec_reference: str = ""
    risk_coverage: List[str] = Field(default_factory=list)
    compliance_refs: List[str] = Field(default_factory=list)


# ─── OpenAPI Linting ───────────────────────────────────────────

class LintSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class LintIssue(BaseModel):
    """A quality issue found in the OpenAPI spec."""
    rule: str
    path: str  # JSON pointer or endpoint path
    message: str
    severity: LintSeverity = LintSeverity.WARNING
    suggestion: str = ""


# ─── Contract Drift Detection ──────────────────────────────────

class DriftType(str, Enum):
    STATUS_CODE_MISMATCH = "status_code_mismatch"
    EXTRA_FIELD = "extra_field"
    MISSING_FIELD = "missing_field"
    TYPE_MISMATCH = "type_mismatch"
    NULL_UNEXPECTED = "null_unexpected"


class DriftItem(BaseModel):
    """A single spec-vs-reality mismatch."""
    drift_type: DriftType
    field_path: str
    expected: str
    actual: str
    message: str


class DriftReport(BaseModel):
    """Drift report for a single endpoint."""
    endpoint: str
    test_id: str
    drifts: List[DriftItem] = Field(default_factory=list)
    is_breaking: bool = False


# ─── Security Testing ──────────────────────────────────────────

class OWASPCategory(str, Enum):
    BROKEN_AUTH = "API1:2023"
    BROKEN_OBJECT_AUTH = "API2:2023"
    EXCESSIVE_DATA = "API3:2023"
    UNRESTRICTED_RESOURCE = "API4:2023"
    BROKEN_FUNCTION_AUTH = "API5:2023"
    MASS_ASSIGNMENT = "API6:2023"
    SECURITY_MISCONFIGURATION = "API7:2023"
    INJECTION = "API8:2023"
    IMPROPER_ASSET_MGMT = "API9:2023"
    UNSAFE_CONSUMPTION = "API10:2023"


class SecurityTestCase(BaseModel):
    """A security-focused test case."""
    id: str
    endpoint: str
    method: str
    owasp_category: OWASPCategory
    description: str
    request: Dict[str, Any] = Field(default_factory=dict)
    expected_behavior: str
    is_safe: bool = True  # Always true — we don't do pentesting


class SecurityTestResult(BaseModel):
    """Result of a security test."""
    test_id: str
    endpoint: str
    owasp_category: OWASPCategory
    passed: bool
    finding: str = ""
    severity: str = "info"  # info | low | medium | high | critical
    recommendation: str = ""


# ─── Compliance Mapping ────────────────────────────────────────

class ComplianceFramework(str, Enum):
    SOC2 = "SOC2"
    ISO_27001 = "ISO_27001"
    HIPAA = "HIPAA"
    GDPR = "GDPR"


class ComplianceMapping(BaseModel):
    """Maps a test case to compliance framework controls."""
    test_id: str
    endpoint: str
    frameworks: Dict[str, List[str]] = Field(default_factory=dict)
    # e.g. {"SOC2": ["CC7.2", "CC6.1"], "HIPAA": ["§164.312"]}


# ─── Environment Profiles ──────────────────────────────────────

class EnvironmentProfile(BaseModel):
    """Per-environment configuration."""
    name: str = "dev"
    destructive_tests: bool = True
    max_risk_score: float = 1.0
    test_intensity: str = "normal"  # minimal | normal | thorough
    security_scanning: bool = True
    drift_detection: bool = False


class EnvironmentConfig(BaseModel):
    """All environment profiles."""
    environments: Dict[str, EnvironmentProfile] = Field(default_factory=dict)
    active: str = "dev"


# ─── Failure Memory ────────────────────────────────────────────

class EndpointHistory(BaseModel):
    """Historical data for a single endpoint."""
    endpoint: str
    total_runs: int = 0
    total_failures: int = 0
    consecutive_failures: int = 0
    last_failure_reason: Optional[str] = None
    is_flaky: bool = False
    false_positive_count: int = 0


class FailureMemory(BaseModel):
    """Aggregated failure history across endpoints."""
    endpoints: Dict[str, EndpointHistory] = Field(default_factory=dict)
    last_updated: str = ""
