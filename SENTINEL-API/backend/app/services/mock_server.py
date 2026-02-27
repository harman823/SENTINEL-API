"""
Mock Server Generator — Generate mock API responses from OpenAPI spec schemas.

Creates realistic, type-aware fake data for each endpoint based on the
schema definitions in the OpenAPI specification.
"""

from typing import Any, Dict, List, Optional
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
