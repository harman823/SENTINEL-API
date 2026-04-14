"""
Security Test Generator — OWASP API Security Top 10 aware testing.
Generates safe, spec-aware security test cases.
NOT penetration testing — only verifies expected security behaviors.
"""

from typing import Dict, Any, List
import json
import logging
from backend.app.schemas.spec import NormalizedSpec, Operation
from backend.app.schemas.models import SecurityTestCase, OWASPCategory
from backend.app.core.llm import get_llm_text

logger = logging.getLogger(__name__)


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

        # Feature 2: Batch BOLA analysis in ONE LLM call (instead of N calls)
        tests.extend(SecurityTestGenerator._batch_bola_tests(spec.operations))
        return tests

    @staticmethod
    def _broken_auth_tests(op: Operation) -> List[SecurityTestCase]:
        """API1:2023 — Broken Object Level Authorization."""
        tests: List[SecurityTestCase] = []

        if op.security_schemes:
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
        if op.method == "get" and op.pii_fields:
            tests.append(SecurityTestCase(
                id=f"SEC_DATA_EXPOSURE_{op.method.upper()}_{op.path.replace('/', '_').strip('_')}",
                endpoint=op.path,
                method=op.method.upper(),
                owasp_category=OWASPCategory.EXCESSIVE_DATA,
                description=f"Response should not expose undocumented PII fields: {', '.join(op.pii_fields)}",
                request={"method": op.method.upper(), "path": op.path},
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
                    "extra_fields": {"isAdmin": True, "role": "admin", "_internal_id": "injected"},
                },
                expected_behavior="Extra fields should be ignored or rejected with 400 Bad Request",
            ))
        return tests

    @staticmethod
    def _missing_rate_limit_tests(op: Operation) -> List[SecurityTestCase]:
        """API4:2023 — Unrestricted Resource Consumption."""
        tests: List[SecurityTestCase] = []
        if not op.security_schemes or op.method in ("post", "put"):
            tests.append(SecurityTestCase(
                id=f"SEC_RATE_LIMIT_{op.method.upper()}_{op.path.replace('/', '_').strip('_')}",
                endpoint=op.path,
                method=op.method.upper(),
                owasp_category=OWASPCategory.UNRESTRICTED_RESOURCE,
                description=f"Rapid sequential requests should be rate-limited",
                request={"method": op.method.upper(), "path": op.path, "rapid_count": 10},
                expected_behavior="Should eventually return 429 Too Many Requests",
            ))
        return tests

    @staticmethod
    def _batch_bola_tests(operations: list) -> List[SecurityTestCase]:
        """
        Feature 2: Batched BOLA/IDOR analysis.
        Uses heuristic detection (instant) with optional LLM enrichment.
        """
        tests: List[SecurityTestCase] = []

        # Filter to endpoints with ID path params AND security schemes
        eligible = []
        for op in operations:
            has_id_param = any(
                p.get("in") == "path" and "id" in p.get("name", "").lower()
                for p in op.parameters
            )
            if has_id_param and op.security_schemes:
                eligible.append(op)

        if not eligible:
            return tests

        # ── Heuristic fallback (instant): any endpoint with /{id} + auth is BOLA-eligible ──
        llm = get_llm_text(temperature=0.0)
        if llm is None:
            for op in eligible:
                # Infer resource type from path: /users/{id} → "user"
                segments = [s for s in op.path.strip("/").split("/") if not s.startswith("{")]
                resource = segments[-1] if segments else "resource"
                if resource.endswith("s"):
                    resource = resource[:-1]  # "users" → "user"
                tests.append(SecurityTestCase(
                    id=f"SEC_BOLA_{op.method.upper()}_{op.path.replace('/', '_').strip('_')}",
                    endpoint=op.path,
                    method=op.method.upper(),
                    owasp_category=OWASPCategory.BROKEN_OBJECT_AUTH,
                    description=f"BOLA/IDOR test: Auth Context A attempting to access {resource} of Context B",
                    request={
                        "method": op.method.upper(),
                        "path": op.path,
                        "use_alt_auth_context": True,
                        "headers": {"Content-Type": "application/json"},
                    },
                    expected_behavior="Should return 401/403/404",
                ))
            return tests

        # ── LLM-enriched path (if Ollama is available) ──
        try:
            endpoints_list = [
                {"method": op.method.upper(), "path": op.path}
                for op in eligible
            ]
            prompt = (
                f"Analyze these API endpoints and determine which ones access user-scoped resources "
                f"(resources belonging to a specific user, like profiles, orders, invoices).\n"
                f"Endpoints: {json.dumps(endpoints_list)}\n"
                f"Return a JSON array where each element has 'method', 'path', 'is_user_scoped' (bool), "
                f"and 'resource_type' (string, e.g. 'invoice'). Only include user-scoped ones."
            )

            response = llm.invoke([{"role": "user", "content": prompt}])
            response_text = response.content
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1

            if start_idx != -1 and end_idx > 0:
                results = json.loads(response_text[start_idx:end_idx])
                for item in results:
                    if item.get("is_user_scoped"):
                        resource = item.get("resource_type", "resource")
                        method = item.get("method", "GET")
                        path = item.get("path", "")
                        tests.append(SecurityTestCase(
                            id=f"SEC_BOLA_{method}_{path.replace('/', '_').strip('_')}",
                            endpoint=path,
                            method=method,
                            owasp_category=OWASPCategory.BROKEN_OBJECT_AUTH,
                            description=f"Semantic BOLA/IDOR test: Auth Context A attempting to access {resource} of Context B",
                            request={
                                "method": method,
                                "path": path,
                                "use_alt_auth_context": True,
                                "headers": {"Content-Type": "application/json"},
                            },
                            expected_behavior="Should return 401/403/404",
                        ))
        except Exception as e:
            logger.warning(f"Batch BOLA generation failed: {e}")

        return tests
