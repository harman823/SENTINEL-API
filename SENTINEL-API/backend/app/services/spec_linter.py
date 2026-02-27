"""
OpenAPI Quality Linter — pre-testing spec analysis.
Detects common spec issues before the pipeline runs.
"""

from typing import Dict, Any, List, Set
from backend.app.schemas.models import LintIssue, LintSeverity


# HTTP methods that should have response definitions
METHODS_NEEDING_RESPONSES = {"get", "post", "put", "patch", "delete"}

# Standard error codes every API should document
RECOMMENDED_ERROR_CODES = {"400", "401", "404", "500"}


class SpecLinter:
    """
    Analyze an OpenAPI spec for quality issues.
    Does not modify the spec — only reports findings.
    """

    @staticmethod
    def lint(spec: Dict[str, Any]) -> List[LintIssue]:
        """Run all lint rules and return issues."""
        issues: List[LintIssue] = []
        issues.extend(SpecLinter._check_info(spec))
        issues.extend(SpecLinter._check_paths(spec))
        issues.extend(SpecLinter._check_security(spec))
        issues.extend(SpecLinter._check_components(spec))
        issues.extend(SpecLinter._check_naming_consistency(spec))
        return issues

    @staticmethod
    def _check_info(spec: Dict[str, Any]) -> List[LintIssue]:
        """Check info section for completeness."""
        issues: List[LintIssue] = []
        info = spec.get("info", {})
        if not info.get("description"):
            issues.append(LintIssue(
                rule="missing_api_description",
                path="/info",
                message="API has no description defined",
                severity=LintSeverity.WARNING,
                suggestion="Add a 'description' field to the info section",
            ))
        if not info.get("contact"):
            issues.append(LintIssue(
                rule="missing_contact",
                path="/info",
                message="No contact information provided",
                severity=LintSeverity.INFO,
                suggestion="Add contact info for API maintainers",
            ))
        return issues

    @staticmethod
    def _check_paths(spec: Dict[str, Any]) -> List[LintIssue]:
        """Check all paths and operations for quality issues."""
        issues: List[LintIssue] = []
        paths = spec.get("paths", {})

        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue

            for method, op_data in methods.items():
                if method.lower() not in METHODS_NEEDING_RESPONSES:
                    continue
                if not isinstance(op_data, dict):
                    continue

                op_path = f"{method.upper()} {path}"

                # Missing operationId
                if not op_data.get("operationId"):
                    issues.append(LintIssue(
                        rule="missing_operation_id",
                        path=op_path,
                        message="No operationId defined — reduces traceability",
                        severity=LintSeverity.WARNING,
                        suggestion="Add a unique operationId for every operation",
                    ))

                # Missing description
                if not op_data.get("description") and not op_data.get("summary"):
                    issues.append(LintIssue(
                        rule="missing_description",
                        path=op_path,
                        message="No description or summary for this operation",
                        severity=LintSeverity.WARNING,
                        suggestion="Add a description or summary to document behavior",
                    ))

                # Check responses
                responses = op_data.get("responses", {})
                if not responses:
                    issues.append(LintIssue(
                        rule="no_responses_defined",
                        path=op_path,
                        message="No response codes defined",
                        severity=LintSeverity.ERROR,
                        suggestion="Define at least a success response (2xx)",
                    ))
                else:
                    # No success response
                    has_success = any(
                        k.startswith("2") for k in responses.keys() if k.isdigit()
                    )
                    if not has_success and "default" not in responses:
                        issues.append(LintIssue(
                            rule="no_success_response",
                            path=op_path,
                            message="No 2xx success response defined",
                            severity=LintSeverity.ERROR,
                            suggestion="Define at least one 2xx response",
                        ))

                    # No error responses
                    has_error = any(
                        k.startswith(("4", "5")) for k in responses.keys() if k.isdigit()
                    )
                    if not has_error:
                        issues.append(LintIssue(
                            rule="no_error_responses",
                            path=op_path,
                            message="No error responses (4xx/5xx) documented",
                            severity=LintSeverity.WARNING,
                            suggestion="Document expected error responses (400, 401, 404, 500)",
                        ))

                    # Check response schemas
                    for code, resp in responses.items():
                        if isinstance(resp, dict):
                            content = resp.get("content", {})
                            if content:
                                for ct, ct_data in content.items():
                                    if isinstance(ct_data, dict) and not ct_data.get("schema"):
                                        issues.append(LintIssue(
                                            rule="missing_response_schema",
                                            path=f"{op_path} → {code}",
                                            message=f"Response {code} has content-type '{ct}' but no schema",
                                            severity=LintSeverity.WARNING,
                                            suggestion="Define a schema for the response body",
                                        ))

                # Check request body schema
                req_body = op_data.get("requestBody", {})
                if isinstance(req_body, dict) and req_body:
                    content = req_body.get("content", {})
                    for ct, ct_data in content.items():
                        if isinstance(ct_data, dict) and not ct_data.get("schema"):
                            issues.append(LintIssue(
                                rule="missing_request_schema",
                                path=op_path,
                                message=f"Request body has content-type '{ct}' but no schema",
                                severity=LintSeverity.ERROR,
                                suggestion="Define a schema for the request body",
                            ))

        return issues

    @staticmethod
    def _check_security(spec: Dict[str, Any]) -> List[LintIssue]:
        """Check security definitions."""
        issues: List[LintIssue] = []
        components = spec.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        global_security = spec.get("security", [])

        if not security_schemes and not global_security:
            issues.append(LintIssue(
                rule="no_security_defined",
                path="/",
                message="No security schemes or global security defined",
                severity=LintSeverity.ERROR,
                suggestion="Define securitySchemes in components and apply them globally or per-operation",
            ))

        # Check for operations without security on sensitive methods
        paths = spec.get("paths", {})
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, op_data in methods.items():
                if method.lower() in ("post", "put", "patch", "delete"):
                    if not isinstance(op_data, dict):
                        continue
                    op_security = op_data.get("security")
                    if op_security is None and not global_security:
                        issues.append(LintIssue(
                            rule="write_without_security",
                            path=f"{method.upper()} {path}",
                            message="Write operation has no security scheme applied",
                            severity=LintSeverity.WARNING,
                            suggestion="Apply a security scheme to protect this endpoint",
                        ))

        return issues

    @staticmethod
    def _check_components(spec: Dict[str, Any]) -> List[LintIssue]:
        """Check for unused or poorly defined components."""
        issues: List[LintIssue] = []
        components = spec.get("components", {})
        schemas = components.get("schemas", {})

        for schema_name, schema_def in schemas.items():
            if not isinstance(schema_def, dict):
                continue

            # Schema without type
            if not schema_def.get("type") and not schema_def.get("$ref") and not schema_def.get("allOf"):
                issues.append(LintIssue(
                    rule="schema_missing_type",
                    path=f"/components/schemas/{schema_name}",
                    message=f"Schema '{schema_name}' has no 'type' defined",
                    severity=LintSeverity.WARNING,
                    suggestion="Add 'type: object' or the appropriate type",
                ))

            # Object without properties
            if schema_def.get("type") == "object" and not schema_def.get("properties"):
                issues.append(LintIssue(
                    rule="empty_object_schema",
                    path=f"/components/schemas/{schema_name}",
                    message=f"Schema '{schema_name}' is type object but has no properties",
                    severity=LintSeverity.WARNING,
                    suggestion="Define properties for this object schema",
                ))

        return issues

    @staticmethod
    def _check_naming_consistency(spec: Dict[str, Any]) -> List[LintIssue]:
        """Check for inconsistent naming conventions."""
        issues: List[LintIssue] = []
        paths = spec.get("paths", {})

        # Collect all operationIds and check for pattern consistency
        operation_ids: List[str] = []
        for _path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for _method, op_data in methods.items():
                if isinstance(op_data, dict) and op_data.get("operationId"):
                    operation_ids.append(op_data["operationId"])

        if len(operation_ids) >= 3:
            camel = sum(1 for oid in operation_ids if oid[0].islower() and "_" not in oid)
            snake = sum(1 for oid in operation_ids if "_" in oid)
            if camel > 0 and snake > 0:
                issues.append(LintIssue(
                    rule="inconsistent_naming",
                    path="/paths",
                    message=f"Mixed naming conventions in operationIds: {camel} camelCase, {snake} snake_case",
                    severity=LintSeverity.INFO,
                    suggestion="Use a consistent naming convention for all operationIds",
                ))

        return issues
