"""
Enhanced Test Generator — generates explainable test cases with
positive, negative, boundary, and policy-driven tests.
Each test case includes reason, spec_reference, and risk_coverage.
"""

from typing import Dict, Any, List, Optional
import json
import logging
from backend.app.schemas.spec import Operation
from backend.app.core.llm import get_llm, get_llm_text

logger = logging.getLogger(__name__)


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

        fuzzable_ops = []
        for op in operations:
            key = f"{op.path}.{op.method}"
            policy = policy_by_key.get(key, {})

            # Positive test (happy path)
            test_cases.append(TestGenerator._positive_test(op, base_url))

            # Negative tests
            test_cases.extend(TestGenerator._negative_tests(op, base_url, policy))

            # Collect fuzzable operations for batch call
            if op.requestBody and op.method in ("post", "put", "patch"):
                content = op.requestBody.get("content", {})
                schema = content.get("application/json", {}).get("schema", {})
                if schema:
                    fuzzable_ops.append((op, schema))

        # Feature 5: Batch AI-Driven Contextual Edge-Case Fuzzing (1 LLM call)
        if fuzzable_ops:
            fuzz_tests = TestGenerator._batch_contextual_fuzz(fuzzable_ops, base_url)
            test_cases.extend(fuzz_tests)

        # Feature 1: Stateful "API Journey" Generation (heuristic-first, LLM fallback)
        journeys = TestGenerator._generate_stateful_journeys(operations, base_url)
        test_cases.extend(journeys)

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
            "reason": f"Happy path test: verifies {op.method.upper()} {op.path} returns {expected_status} with valid input",
            "spec_reference": f"paths.{op.path}.{op.method}.responses.{expected_status}",
            "risk_coverage": list(op.risk_factors),
            "assertions": [
                {"type": "status_code", "expected": expected_status},
                {"type": "response_time_ms", "max": 5000},
            ],
        }

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
                "assertions": [{"type": "status_code", "expected": 401}],
            })

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
                "assertions": [{"type": "status_code", "expected": 405}],
            })

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
                "assertions": [{"type": "status_code", "expected": 400}],
            })

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
                "assertions": [{"type": "status_code", "expected": 400}],
            })

        return tests

    @staticmethod
    def _batch_contextual_fuzz(fuzzable_ops: list, base_url: str) -> List[Dict[str, Any]]:
        """
        Feature 5: Batched AI-Driven Contextual Edge-Case Fuzzing.
        Falls back to heuristic fuzzing (instant) when LLM is unavailable.
        """
        tests = []
        llm = get_llm_text(temperature=0.7)

        # ── Heuristic fuzzing (instant): generate deterministic edge-case payloads ──
        if llm is None:
            FUZZ_VALUES = {
                "string": ["", " ", "a" * 10000, "'; DROP TABLE users;--", "<script>alert(1)</script>",
                           "null", "undefined", "true", "\u0000", "🔥💀👻"],
                "integer": [0, -1, 2147483647, -2147483648],
                "number": [0.0, -0.001, 1e308, float("inf")],
                "boolean": ["yes", 0, ""],
                "email": ["notanemail", "@@@", "a" * 255 + "@x.com"],
            }

            for i, (op, schema) in enumerate(fuzzable_ops):
                payload = {}
                props = schema.get("properties", {})
                for field_name, field_schema in props.items():
                    ftype = field_schema.get("type", "string")
                    # Pick a contextual fuzz value
                    if "email" in field_name.lower():
                        payload[field_name] = FUZZ_VALUES["email"][0]
                    elif ftype in FUZZ_VALUES:
                        payload[field_name] = FUZZ_VALUES[ftype][i % len(FUZZ_VALUES[ftype])]
                    else:
                        payload[field_name] = FUZZ_VALUES["string"][i % len(FUZZ_VALUES["string"])]

                resolved_path = _resolve_path(op.path, op.parameters)
                tests.append({
                    "id": f"FUZZ_{i}_{op.method.upper()}_{op.path.replace('/', '_').strip('_')}",
                    "operation_id": f"fuzz_{i}",
                    "method": op.method.upper(),
                    "url": f"{base_url}{resolved_path}",
                    "path": op.path,
                    "query_params": {},
                    "headers": {"Content-Type": "application/json"},
                    "body": payload,
                    "expected_status": 400,
                    "is_destructive": op.is_destructive,
                    "risk_score": op.risk_score,
                    "test_type": "fuzzing",
                    "reason": f"Heuristic Edge-Case Fuzzing for {op.method.upper()} {op.path}",
                    "spec_reference": f"paths.{op.path}.{op.method}.requestBody",
                    "risk_coverage": ["edge_cases", "business_logic"],
                    "assertions": [{"type": "status_code", "expected": 400}],
                })
            return tests

        # ── LLM-enriched fuzzing (if Ollama is available) ──
        try:
            schemas_summary = []
            for op, schema in fuzzable_ops:
                schemas_summary.append({
                    "path": op.path,
                    "method": op.method.upper(),
                    "schema": schema,
                })

            prompt = (
                f"For each of these API endpoints, generate 1 edge-case JSON payload "
                f"tailored to the semantic meaning of the fields. "
                f"For example: if 'email', use emojis or long strings. If 'date', use leap year dates.\n"
                f"Endpoints: {json.dumps(schemas_summary)}\n"
                f"Return a JSON array where each element has 'path', 'method', and 'payload' (the fuzz body)."
            )

            response = llm.invoke([{"role": "user", "content": prompt}])
            response_text = response.content
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1

            if start_idx != -1 and end_idx > 0:
                json_data = json.loads(response_text[start_idx:end_idx])
                for i, item in enumerate(json_data):
                    path = item.get("path", "")
                    method = item.get("method", "POST")
                    payload = item.get("payload", {})

                    matched_op = next((op for op, _ in fuzzable_ops if op.path == path), None)
                    resolved_path = path
                    if matched_op:
                        resolved_path = _resolve_path(matched_op.path, matched_op.parameters)

                    tests.append({
                        "id": f"FUZZ_{i}_{method}_{path.replace('/', '_').strip('_')}",
                        "operation_id": f"fuzz_{i}",
                        "method": method,
                        "url": f"{base_url}{resolved_path}",
                        "path": path,
                        "query_params": {},
                        "headers": {"Content-Type": "application/json"},
                        "body": payload,
                        "expected_status": 400,
                        "is_destructive": matched_op.is_destructive if matched_op else False,
                        "risk_score": matched_op.risk_score if matched_op else 0.5,
                        "test_type": "fuzzing",
                        "reason": f"AI Contextual Fuzzing for {method} {path}",
                        "spec_reference": f"paths.{path}.{method.lower()}.requestBody",
                        "risk_coverage": ["edge_cases", "business_logic"],
                        "assertions": [{"type": "status_code", "expected": 400}],
                    })
        except Exception as e:
            logger.warning(f"Batch fuzzing generation failed: {e}")

        return tests

    @staticmethod
    def _generate_stateful_journeys(operations: List[Operation], base_url: str) -> List[Dict[str, Any]]:
        """
        Feature 1: Stateful 'API Journey' Generation.
        Uses fast heuristic matching first; only calls LLM if heuristic finds CRUD groups.
        """
        if not operations:
            return []

        journeys = []

        # ── Fast heuristic: group operations by resource path prefix ──
        resource_groups: Dict[str, Dict[str, Operation]] = {}
        for op in operations:
            # Extract resource name from path segments
            segments = [s for s in op.path.strip("/").split("/") if not s.startswith("{")]
            resource = segments[0] if segments else None
            if resource:
                resource_groups.setdefault(resource, {})[op.method.lower()] = op

        # Find resources with at least POST + GET (a minimal lifecycle)
        for resource, methods in resource_groups.items():
            if "post" not in methods or "get" not in methods:
                continue

            steps = []
            # Step 1: Create
            post_op = methods["post"]
            body = _build_request_body(post_op.requestBody)
            steps.append({
                "method": "POST",
                "path": post_op.path,
                "body": body,
                "extracts": {"id": "response.body.id"},
            })

            # Step 2: Fetch
            get_op = methods["get"]
            steps.append({
                "method": "GET",
                "path": get_op.path,
                "body": None,
                "extracts": {},
            })

            # Step 3: Update (if available)
            if "put" in methods or "patch" in methods:
                update_op = methods.get("put") or methods.get("patch")
                steps.append({
                    "method": update_op.method.upper(),
                    "path": update_op.path,
                    "body": body,
                    "extracts": {},
                })

            # Step 4: Delete (if available)
            if "delete" in methods:
                steps.append({
                    "method": "DELETE",
                    "path": methods["delete"].path,
                    "body": None,
                    "extracts": {},
                })

            journeys.append({
                "id": f"STATEFUL_JOURNEY_{resource.upper()}",
                "test_type": "stateful_journey",
                "is_destructive": True,
                "reason": f"Stateful lifecycle journey for '{resource}': {' → '.join(s['method'] for s in steps)}",
                "risk_coverage": ["state_machine", "workflow"],
                "journey_steps": steps,
            })

        return journeys

