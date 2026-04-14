import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import httpx


class APIExecutor:
    """
    Executes generated test cases against a live API endpoint.
    Records response status, body, headers, and timing for each test.
    
    Supports a dry-run mode (default) that simulates execution
    without making real HTTP requests.
    """

    def __init__(
        self,
        timeout: float = 3.0,
        dry_run: bool = True,
        max_concurrency: Optional[int] = None,
    ):
        self.timeout = timeout
        self.dry_run = dry_run
        cpu_hint = max((os.cpu_count() or 4), 4)
        self.max_concurrency = max_concurrency or min(32, cpu_hint * 2)

    def execute(self, test_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute all test cases and return results."""
        if not test_cases:
            return []

        if self.dry_run:
            return [self._dry_run_result(tc) for tc in test_cases]

        max_workers = max(1, min(self.max_concurrency, len(test_cases)))
        limits = httpx.Limits(max_connections=max_workers * 2, max_keepalive_connections=max_workers)

        with httpx.Client(timeout=self.timeout, limits=limits, http2=True) as client:
            if max_workers == 1:
                return [self._execute_single(tc, client) for tc in test_cases]

            ordered_results: List[Optional[Dict[str, Any]]] = [None] * len(test_cases)
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                future_to_index = {
                    pool.submit(self._execute_single, tc, client): index
                    for index, tc in enumerate(test_cases)
                }
                for future in as_completed(future_to_index):
                    idx = future_to_index[future]
                    ordered_results[idx] = future.result()

            return [item for item in ordered_results if item is not None]

    def _execute_single(
        self,
        test_case: Dict[str, Any],
        client: Optional[httpx.Client] = None,
    ) -> Dict[str, Any]:
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

        start_time = time.perf_counter()
        own_client = client is None
        active_client = client or httpx.Client(timeout=self.timeout, http2=True)
        try:
            response = active_client.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                params=query_params,
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)

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
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
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
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
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
        finally:
            if own_client:
                active_client.close()

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
