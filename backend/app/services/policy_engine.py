"""
Enhanced Policy Engine — supports user-defined YAML policies.
AI translates policy → test requirements and enforces them.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import json
import os
import sqlite3
import yaml

from backend.app.schemas.spec import Operation
from backend.app.schemas.models import PolicyViolation


@dataclass
class PolicyRule:
    """A single policy rule with a name, condition function, and message."""
    name: str
    message: str
    check: Any  # Callable[[Operation, Dict[str, float]], bool]


@dataclass
class PolicyResult:
    """Result of evaluating all policies against one operation."""
    operation_key: str  # path.method
    requires_approval: bool
    violated_rules: List[str] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)
    min_negative_tests: int = 0
    must_fail_without_token: bool = False


# --- Built-in Rules ---

BUILT_IN_RULES: List[PolicyRule] = [
    PolicyRule(
        name="destructive_method",
        message="Operation uses a destructive HTTP method (DELETE/PUT/PATCH) and requires approval.",
        check=lambda op, scores: op.is_destructive,
    ),
    PolicyRule(
        name="high_risk_score",
        message="Operation has a risk score >= 0.6 and requires approval.",
        check=lambda op, scores: (scores.get(f"{op.path}.{op.method}", 0.0) >= 0.6),
    ),
    PolicyRule(
        name="no_operation_id",
        message="Operation has no operationId defined — traceability concern.",
        check=lambda op, scores: op.operationId is None,
    ),
    PolicyRule(
        name="pii_without_auth",
        message="Operation handles PII data but has no security scheme defined.",
        check=lambda op, scores: bool(op.pii_fields) and not bool(op.security_schemes),
    ),
]


class PolicyConfigLoader:
    """Load and parse YAML policy configuration files."""

    @staticmethod
    def load_from_yaml(yaml_content: str) -> Dict[str, Any]:
        """Parse YAML policy content into a dict."""
        try:
            config = yaml.safe_load(yaml_content)
            if not isinstance(config, dict):
                raise ValueError("Policy config must be a YAML mapping")
            return config
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid policy YAML: {e}")

    @staticmethod
    def load_from_file(path: str) -> Dict[str, Any]:
        """Load policy config from a YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            return PolicyConfigLoader.load_from_yaml(f.read())

    @staticmethod
    def to_rules(config: Dict[str, Any]) -> List[PolicyRule]:
        """Convert a policy config dict into PolicyRule objects."""
        rules: List[PolicyRule] = list(BUILT_IN_RULES)
        policies = config.get("policies", {})

        for policy_name, policy_def in policies.items():
            if not isinstance(policy_def, dict):
                continue
            rule_type = policy_def.get("rule_type", policy_name)

            # destructive_endpoints policy
            if policy_name == "destructive_endpoints" or rule_type == "destructive_endpoints":
                if policy_def.get("require_approval", False):
                    # Already covered by built-in, but we can adjust
                    min_neg = policy_def.get("min_negative_tests", 0)
                    rules.append(PolicyRule(
                        name=f"policy:{policy_name}",
                        message=f"Policy requires approval for destructive endpoints (min {min_neg} negative tests)",
                        check=lambda op, scores, _mn=min_neg: op.is_destructive,
                    ))

            # auth_required policy
            elif policy_name == "auth_required" or rule_type == "auth_required":
                if policy_def.get("must_fail_without_token", False):
                    rules.append(PolicyRule(
                        name=f"policy:{policy_name}",
                        message=policy_def.get("message", "Policy requires operations to declare an auth scheme."),
                        check=lambda op, scores: not bool(op.security_schemes),
                    ))

            # high_risk policy with custom threshold
            elif policy_name == "high_risk" or rule_type == "high_risk":
                threshold = policy_def.get("threshold", 0.7)
                if policy_def.get("require_approval", False):
                    rules.append(PolicyRule(
                        name=f"policy:{policy_name}",
                        message=f"Policy requires approval for risk score >= {threshold}",
                        check=lambda op, scores, _t=threshold: (
                            scores.get(f"{op.path}.{op.method}", 0.0) >= _t
                        ),
                    ))

            elif rule_type == "required_header":
                header_name = str(policy_def.get("header", "")).lower()
                if header_name:
                    rules.append(PolicyRule(
                        name=f"policy:{policy_name}",
                        message=policy_def.get("message", f"Operation must define required header '{header_name}'."),
                        check=lambda op, scores, _h=header_name: not any(
                            str(param.get("in", "")).lower() == "header"
                            and str(param.get("name", "")).lower() == _h
                            and bool(param.get("required", False))
                            for param in op.parameters
                        ),
                    ))

            elif rule_type == "naming_convention":
                prefix = str(policy_def.get("operation_id_prefix", ""))
                if prefix:
                    rules.append(PolicyRule(
                        name=f"policy:{policy_name}",
                        message=policy_def.get("message", f"operationId must start with '{prefix}'."),
                        check=lambda op, scores, _p=prefix: not bool(op.operationId and op.operationId.startswith(_p)),
                    ))

            # Custom policy with message
            else:
                msg = policy_def.get("message", f"Custom policy: {policy_name}")
                if policy_def.get("require_approval", False):
                    rules.append(PolicyRule(
                        name=f"policy:{policy_name}",
                        message=msg,
                        check=lambda op, scores: False,
                    ))

        return rules

    @staticmethod
    def merge_configs(*configs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {"policies": {}}
        for config in configs:
            if not config:
                continue
            policies = config.get("policies", {})
            if isinstance(policies, dict):
                merged["policies"].update(policies)
        return merged

    @staticmethod
    def load_from_database() -> Dict[str, Any]:
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "autoapi.db"))
        if not os.path.exists(db_path):
            return {"policies": {}}

        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT name, category, rule_type, severity, description, config_json "
                    "FROM api_policies WHERE enabled = 1"
                ).fetchall()
        except sqlite3.Error:
            return {"policies": {}}

        policies: Dict[str, Any] = {}
        for row in rows:
            try:
                config = json.loads(row["config_json"] or "{}")
            except json.JSONDecodeError:
                config = {}

            policy_name = row["name"]
            rule_type = row["rule_type"]
            policies[policy_name] = {
                **config,
                "category": row["category"],
                "rule_type": rule_type,
                "severity": row["severity"],
                "message": row["description"] or config.get("message") or f"Policy violation: {policy_name}",
            }

        return {"policies": policies}


class PolicyEngine:
    """
    Evaluates operations against a set of policy rules.
    Returns a list of PolicyResult, one per operation.
    Supports both built-in and user-defined policies.
    """

    def __init__(
        self,
        rules: Optional[List[PolicyRule]] = None,
        policy_config: Optional[Dict[str, Any]] = None,
        include_database_policies: bool = True,
    ):
        database_config = (
            PolicyConfigLoader.load_from_database()
            if include_database_policies
            else {"policies": {}}
        )
        merged_policy_config = PolicyConfigLoader.merge_configs(database_config, policy_config)
        if rules is not None:
            self.rules = rules
        elif merged_policy_config.get("policies"):
            self.rules = PolicyConfigLoader.to_rules(merged_policy_config)
        else:
            self.rules = BUILT_IN_RULES

        self.policy_config = merged_policy_config

    def evaluate(
        self,
        operations: List[Operation],
        risk_scores: Dict[str, float],
    ) -> List[PolicyResult]:
        """Evaluate all operations against all policy rules."""
        results: List[PolicyResult] = []

        # Extract policy-level settings
        policies = self.policy_config.get("policies", {})
        dest_policy = policies.get("destructive_endpoints", {})
        auth_policy = policies.get("auth_required", {})

        min_neg_tests = dest_policy.get("min_negative_tests", 0)
        must_fail_no_token = auth_policy.get("must_fail_without_token", False)

        for op in operations:
            key = f"{op.path}.{op.method}"
            violated: List[str] = []
            messages: List[str] = []

            for rule in self.rules:
                try:
                    if rule.check(op, risk_scores):
                        violated.append(rule.name)
                        messages.append(rule.message)
                except Exception:
                    pass  # Skip malformed rules

            results.append(PolicyResult(
                operation_key=key,
                requires_approval=len(violated) > 0,
                violated_rules=violated,
                messages=messages,
                min_negative_tests=min_neg_tests if op.is_destructive else 0,
                must_fail_without_token=(
                    must_fail_no_token and bool(op.security_schemes)
                ),
            ))

        return results

    def get_violations(
        self,
        operations: List[Operation],
        risk_scores: Dict[str, float],
    ) -> List[PolicyViolation]:
        """Get flat list of all policy violations."""
        violations: List[PolicyViolation] = []
        results = self.evaluate(operations, risk_scores)
        for pr in results:
            for rule_name, message in zip(pr.violated_rules, pr.messages):
                violations.append(PolicyViolation(
                    rule_name=rule_name,
                    endpoint=pr.operation_key,
                    message=message,
                    severity="error" if "approval" in message.lower() else "warning",
                ))
        return violations
