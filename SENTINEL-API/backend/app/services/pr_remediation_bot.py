"""
PR remediation helper for drift auto-fixes.

Builds pull-request payload suggestions from remediation outputs.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "endpoint"


class PRRemediationBot:
    """Generate PR-ready metadata from drift remediation results."""

    @staticmethod
    def build_suggestions(
        remediation_results: List[Dict[str, Any]],
        spec_path: str = "openapi.yaml",
        base_branch: str = "main",
        repo: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        suggestions: List[Dict[str, Any]] = []
        for idx, remediation in enumerate(remediation_results, start=1):
            endpoint = remediation.get("endpoint", "unknown-endpoint")
            status = remediation.get("status", "remediation_pending")
            patch_text = str(remediation.get("patch_proposed", ""))
            branch = f"bot/drift-{_slugify(endpoint)}-{idx}"

            title = f"chore(openapi): remediate contract drift for {endpoint}"
            body_lines = [
                "Automated drift remediation proposal.",
                "",
                f"Endpoint: `{endpoint}`",
                f"Status: `{status}`",
                "",
                "Suggested patch:",
                "```json",
                patch_text[:5000],
                "```",
            ]

            suggestion = {
                "endpoint": endpoint,
                "title": title,
                "branch": branch,
                "base_branch": base_branch,
                "repo": repo,
                "status": status,
                "ready_for_pr": status == "remediated_locally" and bool(patch_text.strip()),
                "files": [
                    {
                        "path": spec_path,
                        "action": "update",
                        "patch_preview": patch_text[:2000],
                    }
                ],
                "body": "\n".join(body_lines),
            }
            suggestions.append(suggestion)

        return suggestions
