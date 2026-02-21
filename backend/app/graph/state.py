from typing import TypedDict, List, Dict, Any, Optional
from backend.app.schemas.spec import NormalizedSpec


class GraphState(TypedDict):
    # Input
    spec_raw: Dict[str, Any]

    # Derived
    spec_normalized: Optional[NormalizedSpec]

    # Intelligence — Risk
    risk_scores: Dict[str, float]  # path.method -> score (legacy compat)
    risk_details: Dict[str, Any]  # path.method -> RiskScore dict

    # Intelligence — Linting (pre-testing)
    lint_results: List[Dict[str, Any]]

    # Policy
    policy_config: Optional[Dict[str, Any]]  # user-defined policy YAML
    policy_results: List[Dict[str, Any]]  # one per operation
    approval_required: bool
    approval_status: Optional[bool]

    # Testing
    test_cases: List[Dict[str, Any]]

    # Security Testing
    security_test_cases: List[Dict[str, Any]]
    security_results: List[Dict[str, Any]]

    # Execution
    execution_results: List[Dict[str, Any]]

    # Validation
    validation_results: List[Dict[str, Any]]

    # Drift Detection
    drift_results: List[Dict[str, Any]]

    # Compliance
    compliance_mappings: List[Dict[str, Any]]

    # Environment
    environment: str  # dev | staging | prod

    # Output
    report: Dict[str, Any]

    # Errors
    errors: List[str]
