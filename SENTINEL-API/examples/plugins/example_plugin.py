"""
Example AutoAPI Plugin — Custom Risk Rule + Custom Lint Rule

Place this file in `.autoapi/plugins/` to load automatically.
Each plugin must define a `register(hooks)` function.
"""


def register(hooks):
    """Register plugin hooks with AutoAPI."""

    # ── Custom Risk Rule: flag deprecated endpoints ──
    def deprecated_risk_boost(context):
        """Boost risk score for deprecated endpoints."""
        spec = context.get("spec_raw", {})
        extra_factors = []

        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if method in ("get", "post", "put", "delete", "patch"):
                    if details.get("deprecated", False):
                        extra_factors.append({
                            "endpoint": f"{method.upper()} {path}",
                            "factor": "deprecated",
                            "weight": 0.15,
                            "description": "Endpoint is marked as deprecated",
                        })

        return {"plugin_risk_factors": extra_factors}

    hooks.register("custom_risk_rule", deprecated_risk_boost)

    # ── Custom Lint Rule: check for versioned paths ──
    def check_path_versioning(context):
        """Warn if API paths don't include version prefix."""
        spec = context.get("spec_raw", {})
        issues = []

        for path in spec.get("paths", {}).keys():
            if not path.startswith("/v") and not path.startswith("/api/v"):
                issues.append({
                    "rule": "plugin-path-versioning",
                    "severity": "info",
                    "path": path,
                    "message": f"Path '{path}' does not include a version prefix (e.g., /v1/...)",
                })

        return {"plugin_lint_issues": issues}

    hooks.register("custom_lint_rule", check_path_versioning)

    # ── After Report: add custom metadata ──
    def add_plugin_metadata(context):
        """Add plugin metadata to the report."""
        return {"plugin_metadata": {"name": "example_plugin", "version": "1.0.0"}}

    hooks.register("after_report", add_plugin_metadata)
