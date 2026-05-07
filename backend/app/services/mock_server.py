"""
Mock Server Generator — Generate mock API responses from OpenAPI spec schemas.

Creates realistic, type-aware fake data for each endpoint based on the
schema definitions in the OpenAPI specification.
"""

from typing import Any, Dict, List, Optional, Tuple
import random
import string
import uuid
from datetime import datetime, timedelta


# ── Data generators by field name (smart matching) ──
_FIELD_GENERATORS = {
    "email": lambda: f"user{random.randint(1,999)}@example.com",
    "name": lambda: random.choice(["Alice Johnson", "Bob Smith", "Charlie Davis", "Diana Miller", "Eve Wilson"]),
    "first_name": lambda: random.choice(["Alice", "Bob", "Charlie", "Diana", "Eve"]),
    "last_name": lambda: random.choice(["Johnson", "Smith", "Davis", "Miller", "Wilson"]),
    "username": lambda: f"user_{random.randint(1000,9999)}",
    "password": lambda: "********",
    "phone": lambda: f"+1-555-{random.randint(100,999)}-{random.randint(1000,9999)}",
    "address": lambda: f"{random.randint(1,999)} {random.choice(['Main', 'Oak', 'Pine', 'Elm'])} St",
    "city": lambda: random.choice(["New York", "San Francisco", "London", "Tokyo", "Sydney"]),
    "country": lambda: random.choice(["US", "UK", "JP", "AU", "DE"]),
    "zip": lambda: f"{random.randint(10000,99999)}",
    "zipcode": lambda: f"{random.randint(10000,99999)}",
    "url": lambda: f"https://example.com/{uuid.uuid4().hex[:8]}",
    "website": lambda: f"https://{random.choice(['acme', 'globex', 'initech', 'umbrella'])}.com",
    "avatar": lambda: f"https://api.dicebear.com/7.x/avataaars/svg?seed={random.randint(1,100)}",
    "description": lambda: random.choice([
        "A detailed description of this resource.",
        "Mock data generated from the OpenAPI specification.",
        "This is a sample value for testing purposes.",
    ]),
    "title": lambda: random.choice(["Project Alpha", "Task Beta", "Report Gamma", "Item Delta"]),
    "status": lambda: random.choice(["active", "inactive", "pending", "completed"]),
    "role": lambda: random.choice(["admin", "user", "editor", "viewer"]),
    "created_at": lambda: (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat() + "Z",
    "updated_at": lambda: (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat() + "Z",
    "id": lambda: str(uuid.uuid4()),
    "uuid": lambda: str(uuid.uuid4()),
}

# ── Type-based fallback generators ──
_TYPE_GENERATORS = {
    "string": lambda: f"mock_{uuid.uuid4().hex[:6]}",
    "integer": lambda: random.randint(1, 1000),
    "number": lambda: round(random.uniform(0.1, 999.9), 2),
    "boolean": lambda: random.choice([True, False]),
    "array": lambda: [],
    "object": lambda: {},
}

_FORMAT_GENERATORS = {
    "date-time": lambda: datetime.now().isoformat() + "Z",
    "date": lambda: datetime.now().strftime("%Y-%m-%d"),
    "time": lambda: datetime.now().strftime("%H:%M:%S"),
    "email": lambda: f"mock{random.randint(1,99)}@example.com",
    "uri": lambda: f"https://example.com/{uuid.uuid4().hex[:8]}",
    "url": lambda: f"https://example.com/{uuid.uuid4().hex[:8]}",
    "uuid": lambda: str(uuid.uuid4()),
    "ipv4": lambda: f"{random.randint(1,254)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
    "ipv6": lambda: "::1",
    "hostname": lambda: f"host-{random.randint(1,99)}.example.com",
    "binary": lambda: "<binary data>",
    "byte": lambda: "dGVzdA==",
    "password": lambda: "********",
    "int32": lambda: random.randint(-2147483648, 2147483647),
    "int64": lambda: random.randint(1, 9999999999),
    "float": lambda: round(random.uniform(0, 100), 4),
    "double": lambda: round(random.uniform(0, 1000), 6),
}


class MockServerGenerator:
    """Generate mock responses from an OpenAPI specification."""

    @staticmethod
    def generate(spec_normalized, spec_raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate mock responses for all endpoints in the spec.

        Returns:
            Dict mapping "METHOD /path" to mock response data
        """
        mocks = {}

        for op in spec_normalized.operations:
            key = f"{op.method.upper()} {op.path}"

            # Try to find response schema from raw spec
            response_schema = MockServerGenerator._find_response_schema(
                spec_raw, op.path, op.method
            )

            if response_schema:
                mock_data = MockServerGenerator._generate_from_schema(response_schema)
            else:
                # Fallback: generate a basic success response
                mock_data = {"message": "Success", "id": str(uuid.uuid4())}

            mocks[key] = {
                "status_code": MockServerGenerator._primary_success_code(spec_raw, op.path, op.method),
                "headers": {
                    "Content-Type": "application/json",
                    "X-Mock-Response": "true",
                },
                "body": mock_data,
            }

        return mocks

    @staticmethod
    def _find_response_schema(spec_raw: Dict, path: str, method: str) -> Optional[Dict]:
        """Extract the response schema for a specific operation from the raw spec."""
        paths = spec_raw.get("paths", {})
        path_item = paths.get(path, {})
        operation = path_item.get(method.lower(), {})
        responses = operation.get("responses", {})

        # Try 200, 201, 2xx in priority order
        for code in ["200", "201", "202", "204"]:
            resp = responses.get(code, {})
            content = resp.get("content", {})
            json_content = content.get("application/json", {})
            schema = json_content.get("schema")
            if schema:
                return MockServerGenerator._resolve_schema(schema, spec_raw)

        return None

    @staticmethod
    def _resolve_schema(schema: Dict, spec_raw: Dict) -> Dict:
        """Resolve $ref references in schema."""
        if "$ref" in schema:
            ref_path = schema["$ref"]
            parts = ref_path.replace("#/", "").split("/")
            resolved = spec_raw
            for part in parts:
                resolved = resolved.get(part, {})
            return resolved
        return schema

    @staticmethod
    def _primary_success_code(spec_raw: Dict, path: str, method: str) -> int:
        """Determine the primary success status code for an operation."""
        responses = spec_raw.get("paths", {}).get(path, {}).get(method.lower(), {}).get("responses", {})
        for code in ["200", "201", "202", "204"]:
            if code in responses:
                return int(code)
        return 200

    @staticmethod
    def _generate_from_schema(schema: Dict[str, Any], depth: int = 0) -> Any:
        """Recursively generate mock data from a JSON schema."""
        if not isinstance(schema, dict) or depth > 8:
            return None

        schema_type = schema.get("type", "object")

        # Handle enums
        if "enum" in schema:
            return random.choice(schema["enum"])

        # Handle examples
        if "example" in schema:
            return schema["example"]

        if schema_type == "object":
            result = {}
            properties = schema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                result[prop_name] = MockServerGenerator._generate_field(
                    prop_name, prop_schema, depth + 1
                )
            return result

        elif schema_type == "array":
            items = schema.get("items", {})
            count = random.randint(1, 3)
            return [
                MockServerGenerator._generate_from_schema(items, depth + 1)
                for _ in range(count)
            ]

        else:
            return MockServerGenerator._generate_value(schema_type, schema.get("format"))

    @staticmethod
    def _generate_field(name: str, schema: Dict[str, Any], depth: int = 0) -> Any:
        """Generate a value for a named field, using smart name-based matching first."""
        # Check for enum
        if "enum" in schema:
            return random.choice(schema["enum"])

        # Check for example
        if "example" in schema:
            return schema["example"]

        # Smart name matching
        name_lower = name.lower().replace("-", "_")
        if name_lower in _FIELD_GENERATORS:
            return _FIELD_GENERATORS[name_lower]()

        # Nested object/array
        schema_type = schema.get("type", "string")
        if schema_type in ("object", "array"):
            return MockServerGenerator._generate_from_schema(schema, depth)

        # Format-based
        fmt = schema.get("format")
        if fmt and fmt in _FORMAT_GENERATORS:
            return _FORMAT_GENERATORS[fmt]()

        # Type-based fallback
        return MockServerGenerator._generate_value(schema_type, fmt)

    @staticmethod
    def _generate_value(schema_type: str, fmt: Optional[str] = None) -> Any:
        """Generate a single value based on type and optional format."""
        if fmt and fmt in _FORMAT_GENERATORS:
            return _FORMAT_GENERATORS[fmt]()
        return _TYPE_GENERATORS.get(schema_type, lambda: "mock_value")()


class DynamicMockRouteRegistry:
    """
    In-memory registry for temporary mock routes created during drift detection.
    The FastAPI app exposes these routes under /api/v1/dynamic-mock/{path}.
    """

    _routes: Dict[str, Dict[str, Any]] = {}
    _notifications: List[Dict[str, Any]] = []

    @classmethod
    def provision_for_drift(
        cls,
        spec_normalized: Any,
        spec_raw: Dict[str, Any],
        drift_results: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        mocks = MockServerGenerator.generate(spec_normalized, spec_raw)
        created: List[Dict[str, Any]] = []
        notifications: List[Dict[str, Any]] = []

        for drift in drift_results:
            endpoint = drift.get("endpoint")
            if not endpoint or not cls._should_mock(drift):
                continue
            mock_response = mocks.get(endpoint)
            if not mock_response:
                continue

            method, route_path = cls._parse_endpoint(endpoint)
            route = cls.register(
                method=method,
                path=route_path,
                mock_response=mock_response,
                reason="contract_drift",
                source=drift,
            )
            notification = cls._notification(route)
            created.append(route)
            notifications.append(notification)

        return created, notifications

    @classmethod
    def provision_endpoint(
        cls,
        spec_normalized: Any,
        spec_raw: Dict[str, Any],
        method: str,
        path: str,
        reason: str = "manual",
    ) -> Dict[str, Any]:
        mocks = MockServerGenerator.generate(spec_normalized, spec_raw)
        endpoint = f"{method.upper()} {path}"
        mock_response = mocks.get(endpoint)
        if not mock_response:
            raise ValueError(f"No mock response could be generated for {endpoint}")
        return cls.register(method=method, path=path, mock_response=mock_response, reason=reason)

    @classmethod
    def register(
        cls,
        method: str,
        path: str,
        mock_response: Dict[str, Any],
        reason: str,
        source: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        method = method.upper()
        path = cls._normalize_route_path(path)
        key = cls._key(method, path)
        route = {
            "id": key,
            "method": method,
            "path": path,
            "mock_url": f"/api/v1/dynamic-mock{path}",
            "status_code": int(mock_response.get("status_code", 200)),
            "headers": mock_response.get("headers", {}),
            "body": mock_response.get("body", {}),
            "reason": reason,
            "source": source or {},
            "active": True,
        }
        cls._routes[key] = route
        notification = cls._notification(route)
        cls._notifications.append(notification)
        return route

    @classmethod
    def resolve(cls, method: str, path: str) -> Optional[Dict[str, Any]]:
        return cls._routes.get(cls._key(method.upper(), cls._normalize_route_path(path)))

    @classmethod
    def list_routes(cls) -> List[Dict[str, Any]]:
        return list(cls._routes.values())

    @classmethod
    def list_notifications(cls) -> List[Dict[str, Any]]:
        return list(cls._notifications)

    @classmethod
    def clear(cls) -> None:
        cls._routes.clear()
        cls._notifications.clear()

    @staticmethod
    def _should_mock(drift: Dict[str, Any]) -> bool:
        if drift.get("is_breaking"):
            return True
        drift_types = {item.get("drift_type") for item in drift.get("drifts", [])}
        return bool(drift_types & {"status_code_mismatch", "missing_field", "null_unexpected"})

    @staticmethod
    def _parse_endpoint(endpoint: str) -> Tuple[str, str]:
        parts = endpoint.split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"Invalid endpoint format: {endpoint}")
        return parts[0].upper(), parts[1]

    @staticmethod
    def _key(method: str, path: str) -> str:
        return f"{method.upper()} {path}"

    @staticmethod
    def _normalize_route_path(path: str) -> str:
        normalized = path.strip() or "/"
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        return normalized

    @staticmethod
    def _notification(route: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "type": "dynamic_mock_started",
            "severity": "warning",
            "endpoint": f"{route['method']} {route['path']}",
            "mock_url": route["mock_url"],
            "message": (
                f"Traffic is being dynamically mocked for {route['method']} {route['path']} "
                "until the backend is fixed."
            ),
        }
