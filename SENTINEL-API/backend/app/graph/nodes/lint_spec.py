from typing import Dict, Any
from backend.app.services.spec_linter import SpecLinter
from backend.app.graph.state import GraphState


def lint_spec_node(state: GraphState) -> Dict[str, Any]:
    """
    Graph node: lint the raw OpenAPI spec for quality issues.
    Runs before parsing — catches problems early.
    """
    try:
        spec_raw = state.get("spec_raw")
        if not spec_raw:
            return {"lint_results": [], "errors": (state.get("errors") or []) + ["No spec to lint"]}

        issues = SpecLinter.lint(spec_raw)
        lint_results = [issue.model_dump() for issue in issues]

        return {"lint_results": lint_results}
    except Exception as e:
        return {
            "lint_results": [],
            "errors": (state.get("errors") or []) + [f"Lint failed: {str(e)}"],
        }
