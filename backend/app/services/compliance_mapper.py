"""
Compliance Mapper — maps test cases to regulatory framework controls.
Supports SOC 2, ISO 27001, HIPAA, and GDPR.
"""

from typing import Dict, Any, List
from backend.app.schemas.models import ComplianceMapping


# ── Compliance Rule Mappings ──
# Maps test characteristics to compliance framework controls

AUTH_CONTROLS = {
    "SOC2": ["CC6.1", "CC6.2"],       # Logical & Physical Access Controls
    "ISO_27001": ["A.9.4.1"],          # Information Access Restriction
    "HIPAA": ["§164.312(d)"],          # Person or Entity Authentication
    "GDPR": ["Article 32(1)(b)"],      # Security of Processing
}

DATA_PROTECTION_CONTROLS = {
    "SOC2": ["CC6.5", "CC7.2"],        # Data Protection, System Operations
    "ISO_27001": ["A.14.1.2"],         # Securing Application Services
    "HIPAA": ["§164.312(a)(1)"],       # Access Control
    "GDPR": ["Article 25", "Article 32"],
}

DESTRUCTIVE_CONTROLS = {
    "SOC2": ["CC7.2", "CC8.1"],        # System Operations, Change Management
    "ISO_27001": ["A.12.1.2"],         # Change Management
    "HIPAA": ["§164.312(a)(2)(iv)"],   # Encryption & Decryption
    "GDPR": ["Article 32(1)(c)"],      # Availability & Resilience
}

VALIDATION_CONTROLS = {
    "SOC2": ["CC7.1"],                 # System Monitoring
    "ISO_27001": ["A.14.2.8"],         # System Security Testing
    "HIPAA": ["§164.308(a)(8)"],       # Evaluation
    "GDPR": ["Article 32(1)(d)"],      # Testing & Evaluating
}

SECURITY_CONTROLS = {
    "SOC2": ["CC6.1", "CC6.6", "CC7.2"],
    "ISO_27001": ["A.14.2.5"],
    "HIPAA": ["§164.312(e)(1)"],
    "GDPR": ["Article 32"],
}


class ComplianceMapper:
    """
    Maps test cases to compliance framework controls based on
    test type, endpoint risk, and data sensitivity.
    """

    @staticmethod
    def map_tests(
        test_cases: List[Dict[str, Any]],
        risk_details: Dict[str, Any],
    ) -> List[ComplianceMapping]:
        """Map all test cases to compliance controls."""
        mappings: List[ComplianceMapping] = []

        for tc in test_cases:
            tc_id = tc.get("id", "")
            endpoint = tc.get("path", "")
            method = tc.get("method", "").upper()
            is_destructive = tc.get("is_destructive", False)
            risk = tc.get("risk_score") or 0.0

            # Determine which controls apply
            frameworks: Dict[str, List[str]] = {}

            # Auth tests → auth controls
            if "auth" in tc_id.lower() or "token" in tc_id.lower():
                for fw, ctrls in AUTH_CONTROLS.items():
                    frameworks.setdefault(fw, []).extend(ctrls)

            # Destructive operations → change management controls
            if is_destructive:
                for fw, ctrls in DESTRUCTIVE_CONTROLS.items():
                    frameworks.setdefault(fw, []).extend(ctrls)

            # PII-related → data protection
            risk_info = risk_details.get(f"{endpoint}.{method.lower()}", {})
            factors = risk_info.get("factors", []) if isinstance(risk_info, dict) else []
            has_pii = any(
                f.get("name") == "pii_fields" if isinstance(f, dict) else False
                for f in factors
            )
            if has_pii:
                for fw, ctrls in DATA_PROTECTION_CONTROLS.items():
                    frameworks.setdefault(fw, []).extend(ctrls)

            # All tests → validation controls
            for fw, ctrls in VALIDATION_CONTROLS.items():
                frameworks.setdefault(fw, []).extend(ctrls)

            # Deduplicate controls per framework
            for fw in frameworks:
                frameworks[fw] = sorted(set(frameworks[fw]))

            mappings.append(ComplianceMapping(
                test_id=tc_id,
                endpoint=f"{method} {endpoint}",
                frameworks=frameworks,
            ))

        return mappings

    @staticmethod
    def map_security_tests(
        security_results: List[Dict[str, Any]],
    ) -> List[ComplianceMapping]:
        """Map security test results to compliance controls."""
        mappings: List[ComplianceMapping] = []

        for sr in security_results:
            test_id = sr.get("test_id", "")
            endpoint = sr.get("endpoint", "")
            frameworks: Dict[str, List[str]] = {}

            for fw, ctrls in SECURITY_CONTROLS.items():
                frameworks[fw] = list(ctrls)

            mappings.append(ComplianceMapping(
                test_id=test_id,
                endpoint=endpoint,
                frameworks=frameworks,
            ))

        return mappings
