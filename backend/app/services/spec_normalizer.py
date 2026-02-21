from typing import Dict, Any, List, Set
from backend.app.schemas.spec import NormalizedSpec, Operation


# Common PII field names for auto-detection
PII_FIELD_NAMES: Set[str] = {
    "email", "phone", "ssn", "social_security", "address", "zip_code",
    "postal_code", "date_of_birth", "dob", "first_name", "last_name",
    "full_name", "credit_card", "card_number", "cvv", "bank_account",
    "password", "secret", "token", "api_key", "ip_address", "location",
    "latitude", "longitude", "passport", "driver_license", "national_id",
}


def _detect_pii_fields(schema: Dict[str, Any], _depth: int = 0) -> List[str]:
    """Recursively detect PII field names in a JSON schema."""
    found: List[str] = []
    if not isinstance(schema, dict) or _depth > 10:
        return found
    for prop_name, prop_schema in schema.get("properties", {}).items():
        if prop_name.lower().replace("-", "_") in PII_FIELD_NAMES:
            found.append(prop_name)
        if isinstance(prop_schema, dict) and prop_schema.get("properties"):
            found.extend(_detect_pii_fields(prop_schema, _depth + 1))
    items = schema.get("items")
    if isinstance(items, dict) and items:
        found.extend(_detect_pii_fields(items, _depth + 1))
    return found


def _calculate_schema_complexity(schema: Dict[str, Any], depth: int = 0) -> int:
    """Calculate schema complexity score based on depth, field count, nesting."""
    if not isinstance(schema, dict) or depth > 10:
        return 0
    score = 0
    props = schema.get("properties", {})
    score += len(props)  # +1 per field
    for _name, prop_schema in props.items():
        if isinstance(prop_schema, dict):
            ptype = prop_schema.get("type", "")
            if ptype == "object" and prop_schema.get("properties"):
                score += 2 + _calculate_schema_complexity(prop_schema, depth + 1)
            elif ptype == "array":
                items = prop_schema.get("items")
                if isinstance(items, dict) and items:
                    score += 1 + _calculate_schema_complexity(items, depth + 1)
    return score


def _extract_pii_from_operation(op_data: Dict[str, Any]) -> List[str]:
    """Extract PII fields from request body and responses of an operation."""
    pii: List[str] = []
    # Check request body
    req_body = op_data.get("requestBody", {})
    if isinstance(req_body, dict):
        content = req_body.get("content", {})
        for _ct, ct_data in content.items():
            if isinstance(ct_data, dict):
                pii.extend(_detect_pii_fields(ct_data.get("schema", {})))
    # Check responses
    for _code, resp in op_data.get("responses", {}).items():
        if isinstance(resp, dict):
            content = resp.get("content", {})
            for _ct, ct_data in content.items():
                if isinstance(ct_data, dict):
                    pii.extend(_detect_pii_fields(ct_data.get("schema", {})))
    return list(set(pii))


def _get_schema_complexity(op_data: Dict[str, Any]) -> int:
    """Get overall schema complexity for an operation."""
    total = 0
    req_body = op_data.get("requestBody", {})
    if isinstance(req_body, dict):
        content = req_body.get("content", {})
        for _ct, ct_data in content.items():
            if isinstance(ct_data, dict):
                total += _calculate_schema_complexity(ct_data.get("schema", {}))
    for _code, resp in op_data.get("responses", {}).items():
        if isinstance(resp, dict):
            content = resp.get("content", {})
            for _ct, ct_data in content.items():
                if isinstance(ct_data, dict):
                    total += _calculate_schema_complexity(ct_data.get("schema", {}))
    return total


def _extract_security_schemes(
    op_data: Dict[str, Any], global_security: List[Dict[str, Any]]
) -> List[str]:
    """Extract security scheme names applied to an operation."""
    security = op_data.get("security", global_security)
    schemes: List[str] = []
    if isinstance(security, list):
        for sec_req in security:
            if isinstance(sec_req, dict):
                schemes.extend(sec_req.keys())
    return schemes


class SpecNormalizer:
    @staticmethod
    def normalize(spec: Dict[str, Any]) -> NormalizedSpec:
        """
        Convert raw dict spec into a NormalizedSpec object.
        Now enriched with PII detection, schema complexity, and security schemes.
        """
        openapi_version = spec.get("openapi", "3.0.0")
        info = spec.get("info", {})
        paths = spec.get("paths", {})
        components = spec.get("components", {})
        global_security = spec.get("security", [])

        # Extract top-level security scheme definitions
        security_schemes = components.get("securitySchemes", {})

        operations: List[Operation] = []
        normalized_paths: Dict[str, Dict[str, Operation]] = {}

        for path, methods in paths.items():
            normalized_paths[path] = {}
            for method, operation_data in methods.items():
                if method.lower() not in [
                    "get", "post", "put", "delete", "patch",
                    "options", "head", "trace",
                ]:
                    continue

                if not isinstance(operation_data, dict):
                    continue

                is_destructive = method.lower() in ["delete", "put", "patch"]
                pii_fields = _extract_pii_from_operation(operation_data)
                schema_complexity = _get_schema_complexity(operation_data)
                op_security = _extract_security_schemes(
                    operation_data, global_security
                )
                tags = operation_data.get("tags", [])

                op = Operation(
                    method=method.lower(),
                    path=path,
                    summary=operation_data.get("summary"),
                    description=operation_data.get("description"),
                    operationId=operation_data.get("operationId"),
                    parameters=operation_data.get("parameters", []),
                    requestBody=operation_data.get("requestBody"),
                    responses=operation_data.get("responses", {}),
                    is_destructive=is_destructive,
                    risk_score=None,
                    security_schemes=op_security,
                    pii_fields=pii_fields,
                    schema_complexity=schema_complexity,
                    tags=tags if isinstance(tags, list) else [],
                )

                operations.append(op)
                normalized_paths[path][method.lower()] = op

        return NormalizedSpec(
            openapi=openapi_version,
            info=info,
            paths=normalized_paths,
            components=components,
            security_schemes=security_schemes,
            operations=operations,
        )
