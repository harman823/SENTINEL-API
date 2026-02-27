"""
CI/CD Integration — Output formatters for CI pipelines.

Provides JUnit XML, GitHub Actions annotations, and JSON summary output
for integration with continuous integration and deployment pipelines.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import xml.etree.ElementTree as ET


class CICDFormatter:
    """Format pipeline results for CI/CD consumption."""

    @staticmethod
    def to_junit_xml(report: Dict[str, Any]) -> str:
        """
        Convert pipeline report to JUnit XML format.

        Standard format consumed by Jenkins, GitHub Actions, GitLab CI,
        CircleCI, and most CI platforms.
        """
        test_results = report.get("test_results", [])
        summary = report.get("summary", {})
        spec_info = report.get("spec_info", {})

        # JUnit root
        testsuites = ET.Element("testsuites")
        testsuites.set("name", f"AutoAPI - {spec_info.get('title', 'API')}")
        testsuites.set("tests", str(summary.get("total_tests", 0)))
        testsuites.set("failures", str(summary.get("validation_failed", 0)))
        testsuites.set("errors", str(len(report.get("errors", []))))
        testsuites.set("time", "0")
        testsuites.set("timestamp", report.get("generated_at", datetime.now().isoformat()))

        # Functional test suite
        func_suite = ET.SubElement(testsuites, "testsuite")
        func_suite.set("name", "Functional Tests")
        func_suite.set("tests", str(len(test_results)))

        func_failures = 0
        for tr in test_results:
            testcase = ET.SubElement(func_suite, "testcase")
            testcase.set("name", tr.get("test_id", "unknown"))
            testcase.set("classname", f"{tr.get('method', 'GET')} {tr.get('url', '/')}")

            # Execution time
            exec_data = tr.get("execution", {})
            if exec_data.get("response_time_ms"):
                testcase.set("time", str(exec_data["response_time_ms"] / 1000))

            # Check validation
            val = tr.get("validation", {})
            if val and not val.get("passed", True):
                func_failures += 1
                failure = ET.SubElement(testcase, "failure")
                failure.set("message", val.get("summary", "Validation failed"))
                failure.set("type", "AssertionError")
                assertions = val.get("assertions", [])
                failure.text = "\n".join(
                    f"{'PASS' if a.get('passed') else 'FAIL'}: {a.get('message', '')}"
                    for a in assertions
                )

            # Check for execution errors
            if exec_data.get("error"):
                error = ET.SubElement(testcase, "error")
                error.set("message", exec_data["error"])
                error.set("type", "ExecutionError")

        func_suite.set("failures", str(func_failures))

        # Security test suite
        security_tests = report.get("security_test_cases", [])
        if security_tests:
            sec_suite = ET.SubElement(testsuites, "testsuite")
            sec_suite.set("name", "Security Tests (OWASP)")
            sec_suite.set("tests", str(len(security_tests)))
            sec_suite.set("failures", "0")

            for st in security_tests:
                testcase = ET.SubElement(sec_suite, "testcase")
                testcase.set("name", st.get("id", "unknown"))
                testcase.set("classname", st.get("owasp_category", "security"))
                desc = st.get("description", "")
                if desc:
                    system_out = ET.SubElement(testcase, "system-out")
                    system_out.text = desc

        # Lint suite
        lint_results = report.get("lint_results", [])
        if lint_results:
            lint_suite = ET.SubElement(testsuites, "testsuite")
            lint_suite.set("name", "Lint Checks")
            lint_suite.set("tests", str(len(lint_results)))
            lint_errors = sum(1 for i in lint_results if i.get("severity") == "error")
            lint_suite.set("failures", str(lint_errors))

            for issue in lint_results:
                testcase = ET.SubElement(lint_suite, "testcase")
                testcase.set("name", issue.get("rule", "lint"))
                testcase.set("classname", f"lint.{issue.get('severity', 'info')}")
                if issue.get("severity") == "error":
                    failure = ET.SubElement(testcase, "failure")
                    failure.set("message", issue.get("message", ""))
                    failure.set("type", "LintError")

        # Serialize
        return ET.tostring(testsuites, encoding="unicode", xml_declaration=True)

    @staticmethod
    def to_github_annotations(report: Dict[str, Any]) -> str:
        """
        Format results as GitHub Actions workflow commands.

        Uses ::error:: and ::warning:: annotations that GitHub renders
        inline in PR diffs and summary pages.
        """
        lines = []

        # Lint issues
        for issue in report.get("lint_results", []):
            sev = issue.get("severity", "info")
            msg = issue.get("message", "")
            rule = issue.get("rule", "")
            if sev == "error":
                lines.append(f"::error title=Lint: {rule}::{msg}")
            elif sev == "warning":
                lines.append(f"::warning title=Lint: {rule}::{msg}")
            else:
                lines.append(f"::notice title=Lint: {rule}::{msg}")

        # Test failures
        for tr in report.get("test_results", []):
            val = tr.get("validation", {})
            if val and not val.get("passed", True):
                test_id = tr.get("test_id", "unknown")
                summary = val.get("summary", "Test failed")
                lines.append(f"::error title=Test Failed: {test_id}::{summary}")

        # Drift issues
        for dr in report.get("drift_results", []):
            endpoint = dr.get("endpoint", "?")
            dtype = dr.get("drift_type", "unknown")
            lines.append(f"::warning title=Drift: {endpoint}::{dtype}: expected={dr.get('expected')}, actual={dr.get('actual')}")

        # Policy violations
        for pr in report.get("policy_results", []):
            if pr.get("requires_approval"):
                op = pr.get("operation_key", "?")
                msgs = "; ".join(pr.get("messages", []))
                lines.append(f"::warning title=Policy: {op}::{msgs}")

        # Overall summary
        summary = report.get("summary", {})
        rate = summary.get("pass_rate", 0)
        lines.append(f"::notice title=AutoAPI Summary::Pass rate: {rate}%, Tests: {summary.get('total_tests', 0)}")

        return "\n".join(lines)

    @staticmethod
    def to_json_summary(report: Dict[str, Any]) -> str:
        """Machine-readable JSON summary for pipeline scripts."""
        summary = report.get("summary", {})
        return json.dumps({
            "pass_rate": summary.get("pass_rate", 0),
            "total_tests": summary.get("total_tests", 0),
            "validation_passed": summary.get("validation_passed", 0),
            "validation_failed": summary.get("validation_failed", 0),
            "lint_issues": report.get("lint_summary", {}).get("total_issues", 0),
            "security_tests": report.get("security_summary", {}).get("total_security_tests", 0),
            "drift_count": report.get("drift_summary", {}).get("total_drifts", 0),
            "compliance_frameworks": report.get("compliance_summary", {}).get("frameworks_covered", []),
            "risk_distribution": report.get("risk_distribution", {}),
            "errors": report.get("errors", []),
            "generated_at": report.get("generated_at", ""),
        }, indent=2)

    @staticmethod
    def get_exit_code(report: Dict[str, Any], max_risk_score: float = 1.0) -> int:
        """
        Determine CI exit code based on results.

        Returns:
            0 = all passed
            1 = test failures
            2 = policy violations
        """
        if report.get("errors"):
            return 1

        summary = report.get("summary", {})
        if summary.get("validation_failed", 0) > 0:
            return 1

        # Check for unresolved policy violations
        for pr in report.get("policy_results", []):
            if pr.get("requires_approval"):
                return 2

        return 0
