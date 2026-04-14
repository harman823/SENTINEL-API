from typing import Dict, Any, List


class ResponseValidator:
    """
    Validates API execution results against test case assertions.
    Each assertion is checked and produces a pass/fail with reason.
    """

    @staticmethod
    def validate(test_cases: List[Dict[str, Any]], execution_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Match test cases to execution results by test_id and validate assertions.
        Returns a list of validation results, one per test case.
        """
        # Index execution results by test_id
        exec_by_id: Dict[str, Dict[str, Any]] = {}
        for er in execution_results:
            exec_by_id[er.get("test_id", "")] = er

        validation_results: List[Dict[str, Any]] = []

        for tc in test_cases:
            tc_id = tc.get("id", "unknown")
            er = exec_by_id.get(tc_id)

            if not er:
                validation_results.append({
                    "test_id": tc_id,
                    "passed": False,
                    "assertions": [],
                    "summary": "No execution result found for this test case",
                })
                continue

            if er.get("error"):
                validation_results.append({
                    "test_id": tc_id,
                    "passed": False,
                    "assertions": [],
                    "summary": f"Execution error: {er['error']}",
                })
                continue

            assertion_results = ResponseValidator._check_assertions(tc, er)
            all_passed = all(a["passed"] for a in assertion_results)

            validation_results.append({
                "test_id": tc_id,
                "passed": all_passed,
                "assertions": assertion_results,
                "summary": "All assertions passed" if all_passed else f"{sum(1 for a in assertion_results if not a['passed'])} assertion(s) failed",
            })

        return validation_results

    @staticmethod
    def _check_assertions(test_case: Dict[str, Any], exec_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run each assertion defined in the test case against the execution result."""
        results: List[Dict[str, Any]] = []
        assertions = test_case.get("assertions", [])

        for assertion in assertions:
            atype = assertion.get("type", "")

            if atype == "status_code":
                expected = assertion.get("expected")
                actual = exec_result.get("status_code")
                results.append({
                    "type": "status_code",
                    "expected": expected,
                    "actual": actual,
                    "passed": actual == expected,
                    "message": f"Status code: expected {expected}, got {actual}",
                })

            elif atype == "response_time_ms":
                max_ms = assertion.get("max", 5000)
                actual = exec_result.get("response_time_ms", 0)
                passed = actual <= max_ms
                results.append({
                    "type": "response_time_ms",
                    "expected": f"<= {max_ms}ms",
                    "actual": f"{actual}ms",
                    "passed": passed,
                    "message": f"Response time: {actual}ms (max {max_ms}ms)",
                })

            elif atype == "content_type":
                expected = assertion.get("expected", "")
                headers = exec_result.get("response_headers", {})
                actual = headers.get("content-type", "")
                passed = expected.lower() in actual.lower() if actual else False
                results.append({
                    "type": "content_type",
                    "expected": expected,
                    "actual": actual,
                    "passed": passed,
                    "message": f"Content-Type: expected '{expected}', got '{actual}'",
                })

            else:
                results.append({
                    "type": atype,
                    "expected": assertion,
                    "actual": None,
                    "passed": False,
                    "message": f"Unknown assertion type: {atype}",
                })

        return results
