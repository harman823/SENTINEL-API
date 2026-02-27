"""
Failure Memory — stores and retrieves historical test failure data.
Enables continuous learning without fine-tuning.
"""

import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from backend.app.schemas.models import EndpointHistory, FailureMemory


DEFAULT_HISTORY_PATH = Path(".autoapi/history.json")
FLAKY_THRESHOLD = 3  # consecutive failures to mark as flaky


class FailureMemoryService:
    """
    Persistent memory of test failures across runs.
    Stores data in a local JSON file.
    """

    def __init__(self, path: Optional[Path] = None):
        self.path = path or DEFAULT_HISTORY_PATH

    def load(self) -> FailureMemory:
        """Load failure history from disk."""
        if not self.path.exists():
            return FailureMemory()
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return FailureMemory(**data)
        except (json.JSONDecodeError, TypeError, KeyError):
            return FailureMemory()

    def save(self, memory: FailureMemory) -> None:
        """Save failure history to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(memory.model_dump(), f, indent=2)

    def update_from_results(
        self,
        execution_results: List[Dict[str, Any]],
        validation_results: List[Dict[str, Any]],
    ) -> FailureMemory:
        """
        Update failure memory based on latest test run results.
        Returns updated memory.
        """
        memory = self.load()

        # Build validation lookup
        val_by_id: Dict[str, Dict[str, Any]] = {
            vr.get("test_id", ""): vr for vr in validation_results
        }

        for er in execution_results:
            test_id = er.get("test_id", "")
            endpoint_key = f"{er.get('url', '')}_{er.get('method', '')}"

            # Use a more stable key based on test_id
            key = test_id or endpoint_key

            if key not in memory.endpoints:
                memory.endpoints[key] = EndpointHistory(endpoint=key)

            ep = memory.endpoints[key]
            ep.total_runs += 1

            # Check if this run failed
            exec_passed = er.get("passed", False)
            val_result = val_by_id.get(test_id, {})
            val_passed = val_result.get("passed", True)

            if not exec_passed or not val_passed:
                ep.total_failures += 1
                ep.consecutive_failures += 1
                ep.last_failure_reason = (
                    er.get("error") or val_result.get("summary", "Unknown")
                )
                if ep.consecutive_failures >= FLAKY_THRESHOLD:
                    ep.is_flaky = True
            else:
                ep.consecutive_failures = 0
                if ep.is_flaky and ep.consecutive_failures == 0:
                    # Had been flaky but last N runs passed — still mark flaky
                    # until explicitly cleared
                    pass

        memory.last_updated = datetime.utcnow().isoformat()
        self.save(memory)
        return memory

    def get_failure_history_dict(self) -> Dict[str, Any]:
        """Get failure history as a plain dict for risk scoring."""
        memory = self.load()
        return {
            key: ep.model_dump() for key, ep in memory.endpoints.items()
        }

    def clear(self) -> None:
        """Clear all failure history."""
        if self.path.exists():
            os.remove(self.path)
