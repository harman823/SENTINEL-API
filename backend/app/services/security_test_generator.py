"""
Security Test Generator — OWASP API Security Top 10 aware testing.
Generates safe, spec-aware security test cases.
NOT penetration testing — only verifies expected security behaviors.
"""

from typing import Dict, Any, List
from backend.app.schemas.spec import NormalizedSpec, Operation
from backend.app.schemas.models import SecurityTestCase, OWASPCategory


class SecurityTestGenerator:
    """
    Generate security-focused test cases based on the OpenAPI spec.
    All tests are safe and non-destructive — they verify that security
    controls are in place, not attempt to bypass them.
    """

    @staticmethod
    def generate(spec: NormalizedSpec) -> List[SecurityTestCase]:
        """Generate all security test cases for the spec."""
        tests: List[SecurityTestCase] = []
        for op in spec.operations:
            tests.extend(SecurityTestGenerator._broken_auth_tests(op))
            tests.extend(SecurityTestGenerator._excessive_data_tests(op))
            tests.extend(SecurityTestGenerator._mass_assignment_tests(op))
            tests.extend(SecurityTestGenerator._missing_rate_limit_tests(op))
        return tests

    @staticmethod
    def _broken_auth_tests(op: Operation) -> List[SecurityTestCase]:
        """API1:2023 — Broken Object Level Authorization."""
        tests: List[SecurityTestCase] = []

        if op.security_schemes:
            # Test: request WITHOUT auth token should fail
            tests.append(SecurityTestCase(
                id=f"SEC_NO_AUTH_{op.method.upper()}_{op.path.replace('/', '_').strip('_')}",
                endpoint=op.path,
                method=op.method.upper(),
                owasp_category=OWASPCategory.BROKEN_AUTH,
                description=f"Request to {op.method.upper()} {op.path} without authentication should be rejected",
                request={
                    "method": op.method.upper(),
                    "path": op.path,
                    "headers": {"Content-Type": "application/json"},
                    "omit_auth": True,
                },
                expected_behavior="Should return 401 Unauthorized or 403 Forbidden",
            ))

            # Test: request with invalid auth token should fail
            tests.append(SecurityTestCase(
                id=f"SEC_BAD_AUTH_{op.method.upper()}_{op.path.replace('/', '_').strip('_')}",
                endpoint=op.path,
                method=op.method.upper(),
                owasp_category=OWASPCategory.BROKEN_AUTH,
                description=f"Request with invalid auth token should be rejected",
                request={
                    "method": op.method.upper(),
                    "path": op.path,
                    "headers": {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer invalid_token_12345",
                    },
                },
                expected_behavior="Should return 401 Unauthorized",
            ))

        return tests

    @staticmethod
    def _excessive_data_tests(op: Operation) -> List[SecurityTestCase]:
        """API3:2023 — Excessive Data Exposure."""
        tests: List[SecurityTestCase] = []

        # If response has defined schema, check response doesn't leak extra fields
        if op.method == "get" and op.pii_fields:
            tests.append(SecurityTestCase(
                id=f"SEC_DATA_EXPOSURE_{op.method.upper()}_{op.path.replace('/', '_').strip('_')}",
                endpoint=op.path,
                method=op.method.upper(),
                owasp_category=OWASPCategory.EXCESSIVE_DATA,
                description=f"Response should not expose undocumented PII fields: {', '.join(op.pii_fields)}",
                request={
                    "method": op.method.upper(),
                    "path": op.path,
                },
                expected_behavior="Response should only contain fields documented in the schema",
            ))

        return tests

    @staticmethod
    def _mass_assignment_tests(op: Operation) -> List[SecurityTestCase]:
        """API6:2023 — Mass Assignment."""
        tests: List[SecurityTestCase] = []

        if op.method in ("post", "put", "patch") and op.requestBody:
            tests.append(SecurityTestCase(
                id=f"SEC_MASS_ASSIGN_{op.method.upper()}_{op.path.replace('/', '_').strip('_')}",
                endpoint=op.path,
                method=op.method.upper(),
                owasp_category=OWASPCategory.MASS_ASSIGNMENT,
                description=f"Sending undocumented fields (isAdmin, role) should not modify protected properties",
                request={
                    "method": op.method.upper(),
                    "path": op.path,
                    "extra_fields": {
                        "isAdmin": True,
                        "role": "admin",
                        "_internal_id": "injected",
                    },
                },
                expected_behavior="Extra fields should be ignored or rejected with 400 Bad Request",
            ))

        return tests

    @staticmethod
    def _missing_rate_limit_tests(op: Operation) -> List[SecurityTestCase]:
        """API4:2023 — Unrestricted Resource Consumption."""
        tests: List[SecurityTestCase] = []

        # Only test rate limiting on public-facing or high-risk endpoints
        if not op.security_schemes or op.method in ("post", "put"):
            tests.append(SecurityTestCase(
                id=f"SEC_RATE_LIMIT_{op.method.upper()}_{op.path.replace('/', '_').strip('_')}",
                endpoint=op.path,
                method=op.method.upper(),
                owasp_category=OWASPCategory.UNRESTRICTED_RESOURCE,
                description=f"Rapid sequential requests should be rate-limited",
                request={
                    "method": op.method.upper(),
                    "path": op.path,
                    "rapid_count": 10,
                },
                expected_behavior="Should eventually return 429 Too Many Requests",
            ))

        return tests
