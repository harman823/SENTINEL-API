"""
Infrastructure-as-Contract validator.

Compares OpenAPI requirements against IaC source snippets to detect
missing security and reliability controls.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple


def _flatten_text(iac_sources: Iterable[str]) -> str:
    return "\n".join(str(source) for source in iac_sources if source).lower()


def _has_oauth(spec_raw: Dict[str, Any]) -> bool:
    schemes = (
        spec_raw.get("components", {})
        .get("securitySchemes", {})
    )
    for details in schemes.values():
        if not isinstance(details, dict):
            continue
        if details.get("type") in {"oauth2", "openIdConnect"}:
            return True
    return False


def _has_api_key(spec_raw: Dict[str, Any]) -> bool:
    schemes = (
        spec_raw.get("components", {})
        .get("securitySchemes", {})
    )
    for details in schemes.values():
        if isinstance(details, dict) and details.get("type") == "apiKey":
            return True
    return False


def _has_rate_limit_requirement(spec_raw: Dict[str, Any]) -> bool:
    if "x-rate-limit" in spec_raw or "x-ratelimit" in spec_raw:
        return True
    for methods in spec_raw.get("paths", {}).values():
        if not isinstance(methods, dict):
            continue
        for op in methods.values():
            if isinstance(op, dict) and (
                "x-rate-limit" in op or "x-ratelimit" in op
            ):
                return True
    return False


def _is_https_expected(spec_raw: Dict[str, Any]) -> bool:
    servers = spec_raw.get("servers", [])
    if not servers:
        return True
    for server in servers:
        if isinstance(server, dict) and str(server.get("url", "")).lower().startswith("https://"):
            return True
    return False


class IaCValidator:
    """Validate whether IaC contains controls implied by the OpenAPI contract."""

    CONTROL_PATTERNS: Dict[str, Tuple[str, ...]] = {
        "oauth2_policy": ("oauth", "jwt", "authorizer", "cognito", "openid"),
        "api_key_policy": ("api_key", "x-api-key", "apikeyrequired", "usage_plan_key"),
        "rate_limiting": ("rate_limit", "throttle", "burst_limit", "quota", "usage_plan"),
        "tls_enforcement": ("tls", "ssl_policy", "acm_certificate", "https_listener"),
    }

    @staticmethod
    def validate(spec_raw: Dict[str, Any], iac_sources: List[str]) -> Dict[str, Any]:
        merged = _flatten_text(iac_sources)
        required_controls = {
            "oauth2_policy": _has_oauth(spec_raw),
            "api_key_policy": _has_api_key(spec_raw),
            "rate_limiting": _has_rate_limit_requirement(spec_raw),
            "tls_enforcement": _is_https_expected(spec_raw),
        }

        checks: List[Dict[str, Any]] = []
        for control, required in required_controls.items():
            patterns = IaCValidator.CONTROL_PATTERNS[control]
            evidence = [pattern for pattern in patterns if pattern in merged]
            checks.append(
                {
                    "control": control,
                    "required": required,
                    "detected": bool(evidence),
                    "evidence": evidence,
                    "passed": (not required) or bool(evidence),
                }
            )

        missing = [check["control"] for check in checks if check["required"] and not check["detected"]]
        passed = len(missing) == 0
        score = round(((len(checks) - len(missing)) / max(len(checks), 1)) * 100, 1)

        return {
            "passed": passed,
            "score": score,
            "checks": checks,
            "missing_controls": missing,
            "required_controls": [name for name, required in required_controls.items() if required],
        }
