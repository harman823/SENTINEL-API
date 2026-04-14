from typing import Any, Dict, List, Optional, TypedDict

from backend.app.schemas.spec import NormalizedSpec


class GraphState(TypedDict):
    # Input
    spec_raw: Dict[str, Any]
    spec_history: List[Dict[str, Any]]
    traffic_samples: List[Dict[str, Any]]
    iac_sources: List[str]
    chaos_enabled: bool
    chaos_fault_rate: float
    max_concurrency: int

    # Derived
    spec_normalized: Optional[NormalizedSpec]
    lint_results: List[Dict[str, Any]]
    breaking_change_predictions: List[Dict[str, Any]]
    iac_validation: Dict[str, Any]

    # Intelligence - Risk
    risk_scores: Dict[str, float]  # path.method -> score
    risk_details: Dict[str, Any]  # path.method -> RiskScore dict

    # Policy
    policy_config: Optional[Dict[str, Any]]
    policy_results: List[Dict[str, Any]]
    approval_required: bool
    approval_status: Optional[bool]

    # Testing
    test_cases: List[Dict[str, Any]]
    security_test_cases: List[Dict[str, Any]]
    security_results: List[Dict[str, Any]]

    # Execution
    execution_results: List[Dict[str, Any]]
    chaos_results: List[Dict[str, Any]]

    # Validation + RCA
    validation_results: List[Dict[str, Any]]
    rca_results: List[Dict[str, Any]]

    # Drift + remediation
    drift_results: List[Dict[str, Any]]
    remediation_results: List[Dict[str, Any]]
    pr_remediation_suggestions: List[Dict[str, Any]]

    # Compliance
    compliance_mappings: List[Dict[str, Any]]

    # Observability
    blast_radius: Optional[Dict[str, Any]]
    execution_history: List[Dict[str, Any]]

    # Environment
    environment: str  # dev | staging | prod
    live: bool

    # Output
    report: Dict[str, Any]
    errors: List[str]
