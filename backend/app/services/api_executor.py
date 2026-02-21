import time
import httpx
from typing import Dict, Any, List


class APIExecutor:
    """
    Executes generated test cases against a live API endpoint.
    Records response status, body, headers, and timing for each test.
    
    Supports a dry-run mode (default) that simulates execution
    without making real HTTP requests.
    """

    def __init__(self, timeout: float = 30.0, dry_run: bool = True):
        self.timeout = timeout
        self.dry_run = dry_run

    def execute(self, test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute all test cases and return results."""
        results: List[Dict[str, Any]] = []
        for tc in test_cases:
            result = self._execute_single(tc)
            results.append(result)
        return results

    def _execute_single(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test case."""
        tc_id = test_case.get("id", "unknown")
        method = test_case.get("method", "GET")
        url = test_case.get("url", "")
        headers = test_case.get("headers", {})
        body = test_case.get("body")
        query_params = test_case.get("query_params", {})
        expected_status = test_case.get("expected_status", 200)

        if self.dry_run:
            return self._dry_run_result(test_case)

        start_time = time.time()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body,
                    params=query_params,
                )
            elapsed_ms = round((time.time() - start_time) * 1000, 1)

            return {
                "test_id": tc_id,
                "method": method,
                "url": url,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "passed": response.status_code == expected_status,
                "response_time_ms": elapsed_ms,
                "response_headers": dict(response.headers),
                "response_body_preview": response.text[:500],
                "error": None,
            }

        except httpx.TimeoutException:
            elapsed_ms = round((time.time() - start_time) * 1000, 1)
            return {
                "test_id": tc_id,
                "method": method,
                "url": url,
                "status_code": None,
                "expected_status": expected_status,
                "passed": False,
                "response_time_ms": elapsed_ms,
                "response_headers": {},
                "response_body_preview": None,
                "error": f"Request timed out after {self.timeout}s",
            }

        except Exception as e:
            elapsed_ms = round((time.time() - start_time) * 1000, 1)
            return {
                "test_id": tc_id,
                "method": method,
                "url": url,
                "status_code": None,
                "expected_status": expected_status,
                "passed": False,
                "response_time_ms": elapsed_ms,
                "response_headers": {},
                "response_body_preview": None,
                "error": str(e),
            }

    def _dry_run_result(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate execution without making a real HTTP request."""
        expected = test_case.get("expected_status", 200)
        return {
            "test_id": test_case.get("id", "unknown"),
            "method": test_case.get("method", "GET"),
            "url": test_case.get("url", ""),
            "status_code": expected,  # Simulate success
            "expected_status": expected,
            "passed": True,
            "response_time_ms": 0.0,
            "response_headers": {"content-type": "application/json"},
            "response_body_preview": '{"dry_run": true}',
            "error": None,
            "dry_run": True,
        }
