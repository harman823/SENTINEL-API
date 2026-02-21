"""
Enhanced Test Generator — generates explainable test cases with
positive, negative, boundary, and policy-driven tests.
Each test case includes reason, spec_reference, and risk_coverage.
"""

from typing import Dict, Any, List, Optional
from backend.app.schemas.spec import Operation


# Sensible defaults for path parameter placeholders
PATH_PARAM_DEFAULTS: Dict[str, Any] = {
    "string": "example-id",
    "integer": 1,
    "number": 1.0,
    "boolean": True,
}


def _resolve_path(path: str, parameters: List[Dict[str, Any]]) -> str:
    """Replace {param} placeholders with sensible defaults."""
    resolved = path
    for param in parameters:
        if param.get("in") == "path":
            name = param["name"]
            schema = param.get("schema", {})
            ptype = schema.get("type", "string")
            default = PATH_PARAM_DEFAULTS.get(ptype, "example")
            resolved = resolved.replace(f"{{{name}}}", str(default))
    return resolved


def _build_query_params(parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build query parameter dict with defaults for required params."""
    query: Dict[str, Any] = {}
    for param in parameters:
        if param.get("in") == "query" and param.get("required", False):
            schema = param.get("schema", {})
            ptype = schema.get("type", "string")
            query[param["name"]] = PATH_PARAM_DEFAULTS.get(ptype, "example")
    return query


def _build_request_body(request_body: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Generate a minimal request body skeleton from the schema."""
    if not request_body:
        return None
    content = request_body.get("content", {})
    json_content = content.get("application/json", {})
    schema = json_content.get("schema", {})
    return _schema_to_example(schema)


def _schema_to_example(schema: Dict[str, Any]) -> Any:
    """Recursively build a minimal example from a JSON schema."""
    if not schema:
        return {}
    stype = schema.get("type", "object")
    if stype == "object":
        result: Dict[str, Any] = {}
        for prop_name, prop_schema in schema.get("properties", {}).items():
            result[prop_name] = _schema_to_example(prop_schema)
        return result
    elif stype == "array":
        items = schema.get("items", {})
        return [_schema_to_example(items)]
    elif stype == "integer":
        return schema.get("example", 1)
    elif stype == "number":
        return schema.get("example", 1.0)
    elif stype == "boolean":
        return schema.get("example", True)
    elif stype == "string":
        return schema.get("example", schema.get("enum", ["example"])[0] if schema.get("enum") else "example")
    return None


class TestGenerator:
    """
    Generates HTTP test cases from normalized OpenAPI operations.
    Each test case is a dict describing the request to make and what to assert.
    Now includes explainability fields and negative tests.
    """

    @staticmethod
    def generate(
        operations: List[Operation],
        base_url: str = "http://localhost",
        policy_results: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate all test cases including positive, negative, and policy-driven tests."""
        test_cases: List[Dict[str, Any]] = []
        policy_by_key: Dict[str, Dict[str, Any]] = {}
        if policy_results:
            for pr in policy_results:
                policy_by_key[pr.get("operation_key", "")] = pr

        for op in operations:
            key = f"{op.path}.{op.method}"
            policy = policy_by_key.get(key, {})

            # Positive test (happy path)
            test_cases.append(TestGenerator._positive_test(op, base_url))

            # Negative tests
            test_cases.extend(TestGenerator._negative_tests(op, base_url, policy))

        return test_cases

    @staticmethod
    def _positive_test(op: Operation, base_url: str) -> Dict[str, Any]:
        """Generate a positive (happy path) test case."""
        resolved_path = _resolve_path(op.path, op.parameters)
        query_params = _build_query_params(op.parameters)
        body = _build_request_body(op.requestBody)

        success_codes = [
            int(code) for code in op.responses.keys()
            if code.isdigit() and 200 <= int(code) < 300
        ]
        expected_status = success_codes[0] if success_codes else 200

        test_case: Dict[str, Any] = {
            "id": f"{op.method.upper()}_{op.path.replace('/', '_').strip('_')}",
            "operation_id": op.operationId,
            "method": op.method.upper(),
            "url": f"{base_url}{resolved_path}",
            "path": op.path,
            "query_params": query_params,
            "headers": {"Content-Type": "application/json", "Accept": "application/json"},
            "body": body,
            "expected_status": expected_status,
            "is_destructive": op.is_destructive,
            "risk_score": op.risk_score,
            "test_type": "positive",
            # Explainability
            "reason": f"Happy path test: verifies {op.method.upper()} {op.path} returns {expected_status} with valid input",
            "spec_reference": f"paths.{op.path}.{op.method}.responses.{expected_status}",
            "risk_coverage": list(op.risk_factors),
            "assertions": [
                {"type": "status_code", "expected": expected_status},
                {"type": "response_time_ms", "max": 5000},
            ],
        }

        # Add content-type assertion for JSON responses
        for code, resp in op.responses.items():
            if code.isdigit() and 200 <= int(code) < 300:
                content = resp.get("content", {}) if isinstance(resp, dict) else {}
                if "application/json" in content:
                    test_case["assertions"].append({"type": "content_type", "expected": "application/json"})
                break

        return test_case

    @staticmethod
    def _negative_tests(
        op: Operation,
        base_url: str,
        policy: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate negative test cases."""
        tests: List[Dict[str, Any]] = []
        resolved_path = _resolve_path(op.path, op.parameters)

        # ── Auth failure test (if endpoint has security) ──
        must_fail_no_token = policy.get("must_fail_without_token", False)
        if op.security_schemes or must_fail_no_token:
            tests.append({
                "id": f"NEG_NO_AUTH_{op.method.upper()}_{op.path.replace('/', '_').strip('_')}",
                "operation_id": op.operationId,
                "method": op.method.upper(),
                "url": f"{base_url}{resolved_path}",
                "path": op.path,
                "query_params": {},
                "headers": {"Content-Type": "application/json"},
                "body": None,
                "expected_status": 401,
                "is_destructive": False,
                "risk_score": op.risk_score,
                "test_type": "negative",
                "reason": "Auth failure test: request without authentication should be rejected",
                "spec_reference": f"paths.{op.path}.{op.method}.security",
                "risk_coverage": ["auth_required"],
                "assertions": [
                    {"type": "status_code", "expected": 401},
                ],
            })

        # ── Invalid method test ──
        if op.method == "get":
            tests.append({
                "id": f"NEG_WRONG_METHOD_{op.path.replace('/', '_').strip('_')}",
                "operation_id": op.operationId,
                "method": "DELETE",
                "url": f"{base_url}{resolved_path}",
                "path": op.path,
                "query_params": {},
                "headers": {"Content-Type": "application/json"},
                "body": None,
                "expected_status": 405,
                "is_destructive": False,
                "risk_score": op.risk_score,
                "test_type": "negative",
                "reason": "Wrong method test: sending DELETE to a GET-only endpoint should fail",
                "spec_reference": f"paths.{op.path}",
                "risk_coverage": ["method_validation"],
                "assertions": [
                    {"type": "status_code", "expected": 405},
                ],
            })

        # ── Schema violation test (if endpoint accepts body) ──
        if op.requestBody and op.method in ("post", "put", "patch"):
            tests.append({
                "id": f"NEG_BAD_BODY_{op.method.upper()}_{op.path.replace('/', '_').strip('_')}",
                "operation_id": op.operationId,
                "method": op.method.upper(),
                "url": f"{base_url}{resolved_path}",
                "path": op.path,
                "query_params": {},
                "headers": {"Content-Type": "application/json"},
                "body": {"__invalid__": True, "random_field": "should_fail"},
                "expected_status": 400,
                "is_destructive": False,
                "risk_score": op.risk_score,
                "test_type": "negative",
                "reason": "Schema violation test: sending an invalid request body should return 400",
                "spec_reference": f"paths.{op.path}.{op.method}.requestBody",
                "risk_coverage": ["schema_validation"],
                "assertions": [
                    {"type": "status_code", "expected": 400},
                ],
            })

            # ── Empty body test ──
            tests.append({
                "id": f"NEG_EMPTY_BODY_{op.method.upper()}_{op.path.replace('/', '_').strip('_')}",
                "operation_id": op.operationId,
                "method": op.method.upper(),
                "url": f"{base_url}{resolved_path}",
                "path": op.path,
                "query_params": {},
                "headers": {"Content-Type": "application/json"},
                "body": {},
                "expected_status": 400,
                "is_destructive": False,
                "risk_score": op.risk_score,
                "test_type": "negative",
                "reason": "Empty body test: sending an empty body to an endpoint expecting data should fail",
                "spec_reference": f"paths.{op.path}.{op.method}.requestBody",
                "risk_coverage": ["input_validation"],
                "assertions": [
                    {"type": "status_code", "expected": 400},
                ],
            })

        return tests
