import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box
import sys
import os
import json

# Add project root to path to allow imports from backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.openapi_loader import OpenAPILoader
from backend.app.services.spec_validator import SpecValidator
from backend.app.services.spec_normalizer import SpecNormalizer

app = typer.Typer(
    name="autoapi",
    no_args_is_help=True,
    help="AutoAPI Intelligence v2.0 — automated API testing powered by LangGraph.",
)
console = Console()

SEVERITY_COLORS = {"error": "red", "warning": "yellow", "info": "cyan"}
RISK_COLORS = {"high": "red", "medium": "yellow", "low": "green"}


def _build_initial_state(spec_raw, approve=False, env="dev", policy_config=None):
    """Build the full GraphState-compatible initial state."""
    return {
        "spec_raw": spec_raw,
        "risk_scores": {},
        "risk_details": {},
        "lint_results": [],
        "policy_config": policy_config,
        "test_cases": [],
        "security_test_cases": [],
        "security_results": [],
        "execution_results": [],
        "validation_results": [],
        "drift_results": [],
        "compliance_mappings": [],
        "policy_results": [],
        "approval_required": False,
        "approval_status": approve,
        "environment": env,
        "errors": [],
    }


# ──────────────────────────────────────────────────
#  validate
# ──────────────────────────────────────────────────
@app.command()
def validate(
    spec_path: str = typer.Argument(..., help="Path to an OpenAPI YAML/JSON spec file."),
):
    """Validate and normalize an OpenAPI specification."""
    console.print(f"[blue]Validating spec at: {spec_path}[/blue]")
    try:
        spec_raw = OpenAPILoader.load_spec(spec_path)
        console.print("[green]✓ Spec loaded successfully[/green]")

        SpecValidator.validate(spec_raw)
        console.print("[green]✓ Spec structure validated[/green]")

        normalized_spec = SpecNormalizer.normalize(spec_raw)
        op_count = len(normalized_spec.operations)
        destructive = sum(1 for op in normalized_spec.operations if op.is_destructive)
        console.print(f"[green]✓ Normalized {op_count} operations ({destructive} destructive).[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


# ──────────────────────────────────────────────────
#  lint  (standalone linting)
# ──────────────────────────────────────────────────
@app.command()
def lint(
    spec_path: str = typer.Argument(..., help="Path to an OpenAPI YAML/JSON spec file."),
):
    """Lint an OpenAPI specification for quality issues."""
    console.print(f"\n[bold blue]AutoAPI Linter[/bold blue]")
    console.print(f"  Spec: {spec_path}\n")
    try:
        from backend.app.services.spec_linter import SpecLinter

        spec_raw = OpenAPILoader.load_spec(spec_path)
        issues = SpecLinter.lint(spec_raw)

        if not issues:
            console.print("[green]✓ No lint issues found — spec quality is excellent![/green]")
            return

        table = Table(title="Lint Results", box=box.ROUNDED, border_style="dim")
        table.add_column("Severity", width=8)
        table.add_column("Rule", style="cyan", width=20)
        table.add_column("Path", style="dim", width=18)
        table.add_column("Message")

        for issue in issues:
            sev = issue.get("severity", "info")
            color = SEVERITY_COLORS.get(sev, "white")
            table.add_row(
                f"[{color}]{sev.upper()}[/{color}]",
                issue.get("rule", ""),
                issue.get("path", ""),
                issue.get("message", ""),
            )

        console.print(table)
        errors = sum(1 for i in issues if i.get("severity") == "error")
        warns = sum(1 for i in issues if i.get("severity") == "warning")
        console.print(f"\n  Total: {len(issues)} issues ({errors} errors, {warns} warnings)")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


# ──────────────────────────────────────────────────
#  mock  (generate mock responses)
# ──────────────────────────────────────────────────
@app.command()
def mock(
    spec_path: str = typer.Argument(..., help="Path to an OpenAPI YAML/JSON spec file."),
    output: str = typer.Option(None, "--output", "-o", help="Export mock data to JSON file."),
    serve: bool = typer.Option(False, "--serve", "-s", help="Start an intelligent, stateful mock server locally."),
    port: int = typer.Option(8080, "--port", "-p", help="Port for the mock server."),
):
    """Generate mock API responses or start an intelligent mock server."""
    console.print(f"\n[bold blue]AutoAPI Mock Generator & Server[/bold blue]")
    console.print(f"  Spec: {spec_path}\n")
    try:
        from backend.app.services.mock_server import MockServerGenerator
        from backend.cli.mock_server import run_intelligent_mock

        if serve:
            run_intelligent_mock(spec_path, port)
            return

        spec_raw = OpenAPILoader.load_spec(spec_path)
        normalized = SpecNormalizer.normalize(spec_raw)
        mocks = MockServerGenerator.generate(normalized, spec_raw)

        for endpoint, data in mocks.items():
            console.print(f"[cyan]{endpoint}[/cyan]")
            console.print(f"  [dim]{json.dumps(data, indent=2, default=str)[:300]}[/dim]")
            console.print()

        console.print(f"[green]✓ Generated static mock responses for {len(mocks)} endpoints[/green]")

        if output:
            with open(output, "w", encoding="utf-8") as f:
                json.dump(mocks, f, indent=2, default=str)
            console.print(f"[green]✓ Mock data exported to {output}[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


# ──────────────────────────────────────────────────
#  run-graph  (main pipeline command)
# ──────────────────────────────────────────────────
@app.command()
def run_graph(
    spec_path: str = typer.Argument(..., help="Path to an OpenAPI YAML/JSON spec file."),
    approve: bool = typer.Option(False, "--approve", help="Auto-approve destructive operations for testing."),
    live: bool = typer.Option(False, "--live", help="Execute tests against a live API (default: dry-run)."),
    output: str = typer.Option(None, "--output", "-o", help="Export full JSON report to a file path."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed assertion-level output."),
    env: str = typer.Option("dev", "--env", "-e", help="Environment profile: dev, staging, prod."),
    ci: bool = typer.Option(False, "--ci", help="CI mode: JSON output, no Rich formatting."),
):
    """Run the full 12-node LangGraph pipeline."""
    if not ci:
        console.print(f"\n[bold blue]⚡ AutoAPI Intelligence v2.0[/bold blue]")
        console.print(f"  Spec:     {spec_path}")
        console.print(f"  Mode:     {'[red]LIVE[/red]' if live else '[dim]dry-run[/dim]'}")
        console.print(f"  Env:      [cyan]{env}[/cyan]")
        console.print(f"  Approve:  {'[green]yes[/green]' if approve else '[yellow]no[/yellow]'}")
        console.print()

    try:
        from backend.app.graph.builder import GraphBuilder

        spec_raw = OpenAPILoader.load_spec(spec_path)
        initial_state = _build_initial_state(spec_raw, approve=approve, env=env)

        graph = GraphBuilder.build()
        result = graph.invoke(initial_state)

        # ── CI Mode: JSON output ──
        if ci:
            _output_ci(result, output)
            return

        # ── Errors ──
        if result.get("errors"):
            for err in result["errors"]:
                console.print(f"[red]✗ {err}[/red]")
            raise typer.Exit(code=1)

        # ── Spec Summary ──
        normalized = result.get("spec_normalized")
        if normalized:
            destructive_count = sum(1 for op in normalized.operations if op.is_destructive)
            pii_count = sum(len(op.pii_fields) for op in normalized.operations)
            console.print(f"[green]✓ Parsed {len(normalized.operations)} operations[/green]", end="")
            extras = []
            if destructive_count:
                extras.append(f"[yellow]{destructive_count} destructive[/yellow]")
            if pii_count:
                extras.append(f"[magenta]{pii_count} PII fields[/magenta]")
            if extras:
                console.print(f"  ({', '.join(extras)})")
            else:
                console.print()

        # ── Lint Results ──
        _display_lint_results(result.get("lint_results", []))

        # ── Risk Scores + Factors ──
        _display_risk_details(result.get("risk_scores", {}), result.get("risk_details", {}), verbose)

        # ── Policy Evaluation ──
        _display_policy_results(result.get("policy_results", []))

        # ── Approval Gate ──
        _display_approval_gate(result)

        # ── Test Cases ──
        _display_test_cases(result.get("test_cases", []), verbose)

        # ── Security Test Cases ──
        _display_security_tests(result.get("security_test_cases", []))

        # ── Execution Results ──
        _display_execution_results(result.get("execution_results", []))

        # ── Validation Results ──
        _display_validation_results(result.get("validation_results", []), verbose)

        # ── Drift Detection ──
        _display_drift_results(result.get("drift_results", []))

        # ── Compliance Mapping ──
        _display_compliance(result.get("compliance_mappings", []))

        # ── Report Summary ──
        _display_report_summary(result.get("report", {}))

        # ── JSON Export ──
        report = result.get("report", {})
        if output and report:
            from backend.app.services.report_generator import ReportGenerator
            report_json = ReportGenerator.to_json(report)
            with open(output, "w", encoding="utf-8") as f:
                f.write(report_json)
            console.print(f"\n[green]✓ Report exported to {output}[/green]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)


# ══════════════════════════════════════════════════
#  Display Helpers
# ══════════════════════════════════════════════════

def _display_lint_results(lint_results):
    if not lint_results:
        return
    errors = sum(1 for i in lint_results if i.get("severity") == "error")
    warns = sum(1 for i in lint_results if i.get("severity") == "warning")
    infos = len(lint_results) - errors - warns
    console.print(f"\n[bold]🔍 Lint: {errors} errors, {warns} warnings, {infos} info[/bold]")
    for issue in lint_results:
        sev = issue.get("severity", "info")
        color = SEVERITY_COLORS.get(sev, "white")
        console.print(f"  [{color}]{sev[0].upper()}[/{color}] {issue.get('rule', '?')} — {issue.get('message', '')}")
        if issue.get("path"):
            console.print(f"    [dim]at {issue['path']}[/dim]")


def _display_risk_details(risk_scores, risk_details, verbose):
    if not risk_scores:
        return
    console.print("\n[bold]🎯 Risk Scores:[/bold]")
    for endpoint, score in sorted(risk_scores.items(), key=lambda x: -x[1]):
        color = "red" if score >= 0.7 else "yellow" if score >= 0.4 else "green"
        console.print(f"  [{color}]{score:.2f}[/{color}]  {endpoint}")
        # Show factors if available
        detail = risk_details.get(endpoint, {})
        factors = detail.get("factors", []) if isinstance(detail, dict) else []
        if factors and verbose:
            for f in factors:
                console.print(f"    [dim]• {f.get('name', '?')}: {f.get('description', '')}[/dim]")


def _display_policy_results(policy_results):
    if not policy_results:
        return
    console.print("\n[bold]🛡️ Policy Evaluation:[/bold]")
    for pr in policy_results:
        if pr.get("requires_approval"):
            console.print(f"  [red]✗ APPROVAL REQUIRED[/red]  {pr['operation_key']}")
            for msg in pr.get("messages", []):
                console.print(f"    [dim]→ {msg}[/dim]")
        else:
            console.print(f"  [green]✓ OK[/green]  {pr['operation_key']}")


def _display_approval_gate(result):
    approval_required = result.get("approval_required", False)
    approval_status = result.get("approval_status")
    if approval_required and not approval_status:
        console.print("\n[bold red]⚠ Approval Gate: BLOCKED[/bold red]")
        console.print("[dim]  Destructive operations skipped. Use --approve to unlock.[/dim]")
    elif approval_required and approval_status:
        console.print("\n[bold green]✓ Approval Gate: APPROVED[/bold green]")
    else:
        console.print("\n[bold green]✓ Approval Gate: PASSED — no approval needed.[/bold green]")


def _display_test_cases(test_cases, verbose):
    if not test_cases:
        return
    positive = sum(1 for tc in test_cases if tc.get("test_type") != "negative")
    negative = len(test_cases) - positive
    console.print(f"\n[bold]🧪 Generated {len(test_cases)} Test Case(s)[/bold]  ({positive} positive, {negative} negative)")
    for tc in test_cases:
        risk = tc.get("risk_score") or 0.0
        color = "red" if risk >= 0.7 else "yellow" if risk >= 0.4 else "green"
        ttype = tc.get("test_type", "positive")
        icon = "●" if ttype == "positive" else "◆"
        console.print(f"  [{color}]{icon}[/{color}] [{tc['method']}] {tc['url']}  (expect {tc['expected_status']})")
        if verbose and tc.get("reason"):
            console.print(f"    [dim]Reason: {tc['reason']}[/dim]")


def _display_security_tests(security_tests):
    if not security_tests:
        return
    categories = {}
    for st in security_tests:
        cat = st.get("owasp_category", "unknown")
        categories.setdefault(cat, []).append(st)
    console.print(f"\n[bold]🔒 Security Tests: {len(security_tests)} generated[/bold]")
    for cat, tests in categories.items():
        console.print(f"  [magenta]{cat}[/magenta] ({len(tests)} tests)")
        for t in tests:
            console.print(f"    • {t.get('description', t.get('id', '?'))[:80]}")


def _display_execution_results(exec_results):
    if not exec_results:
        return
    passed = sum(1 for r in exec_results if r.get("passed"))
    failed = len(exec_results) - passed
    console.print(f"\n[bold]⚡ Execution: {passed} passed, {failed} failed[/bold]")
    for er in exec_results:
        icon = "✓" if er["passed"] else "✗"
        color = "green" if er["passed"] else "red"
        dry = " [dim](dry-run)[/dim]" if er.get("dry_run") else ""
        console.print(f"  [{color}]{icon}[/{color}] [{er['method']}] {er['url']}  → {er['status_code']}{dry}")
        if er.get("error"):
            console.print(f"    [red]Error: {er['error']}[/red]")


def _display_validation_results(val_results, verbose):
    if not val_results:
        return
    v_passed = sum(1 for v in val_results if v.get("passed"))
    v_failed = len(val_results) - v_passed
    console.print(f"\n[bold]✅ Validation: {v_passed} passed, {v_failed} failed[/bold]")
    for vr in val_results:
        icon = "✓" if vr["passed"] else "✗"
        color = "green" if vr["passed"] else "red"
        console.print(f"  [{color}]{icon}[/{color}] {vr['test_id']}  — {vr['summary']}")
        if not vr["passed"] or verbose:
            for a in vr.get("assertions", []):
                a_icon = "✓" if a["passed"] else "✗"
                a_color = "green" if a["passed"] else "red"
                console.print(f"    [{a_color}]{a_icon} {a['message']}[/{a_color}]")


def _display_drift_results(drift_results):
    if not drift_results:
        return
    console.print(f"\n[bold]📡 Drift Detection: {len(drift_results)} issue(s)[/bold]")
    for dr in drift_results:
        dtype = dr.get("drift_type", "unknown")
        console.print(f"  [yellow]⚠[/yellow] [{dtype}] {dr.get('endpoint', '?')}")
        console.print(f"    [dim]Expected: {dr.get('expected', '?')}  Actual: {dr.get('actual', '?')}[/dim]")
        if dr.get("field"):
            console.print(f"    [dim]Field: {dr['field']}[/dim]")


def _display_compliance(compliance_mappings):
    if not compliance_mappings:
        return
    frameworks = set()
    for cm in compliance_mappings:
        for fw in cm.get("frameworks", []):
            frameworks.add(fw.get("framework", fw) if isinstance(fw, dict) else fw)
    console.print(f"\n[bold]📋 Compliance: {len(compliance_mappings)} mappings across {len(frameworks)} frameworks[/bold]")
    console.print(f"  Frameworks: {', '.join(sorted(frameworks))}")


def _display_report_summary(report):
    if not report:
        return
    summary = report.get("summary", {})
    risk_dist = report.get("risk_distribution", {})
    spec_info = report.get("spec_info", {})
    lint_sum = report.get("lint_summary", {})
    sec_sum = report.get("security_summary", {})
    rate = summary.get("pass_rate", 0)
    rate_color = "green" if rate == 100 else "yellow" if rate >= 80 else "red"

    console.print(f"\n{'═' * 55}")
    console.print(f"[bold]📋 Report: {spec_info.get('title', 'API')} v{spec_info.get('version', '?')}[/bold]")
    console.print(f"  Pass Rate:    [{rate_color}]{rate}%[/{rate_color}]")
    console.print(f"  Tests:        {summary.get('total_tests', 0)}  |  Passed: {summary.get('validation_passed', 0)}  |  Failed: {summary.get('validation_failed', 0)}")
    console.print(f"  Risk:         🔴 {risk_dist.get('high', 0)} high  🟡 {risk_dist.get('medium', 0)} med  🟢 {risk_dist.get('low', 0)} low")
    console.print(f"  Lint:         {lint_sum.get('total_issues', 0)} issues ({lint_sum.get('errors', 0)} errors)")
    console.print(f"  Security:     {sec_sum.get('total_security_tests', 0)} tests generated")
    if summary.get("flagged_operations"):
        console.print(f"  Flagged:      {summary['flagged_operations']} operation(s) require approval")
    console.print(f"  Generated:    {report.get('generated_at', 'N/A')}")
    console.print(f"{'═' * 55}")


def _output_ci(result, output_path):
    """CI mode: output machine-readable JSON, set exit code."""
    report = result.get("report", {})
    ci_output = {
        "success": not result.get("errors"),
        "errors": result.get("errors", []),
        "summary": report.get("summary", {}),
        "risk_distribution": report.get("risk_distribution", {}),
        "lint_summary": report.get("lint_summary", {}),
        "security_summary": report.get("security_summary", {}),
        "drift_summary": report.get("drift_summary", {}),
        "compliance_summary": report.get("compliance_summary", {}),
        "test_results": report.get("test_results", []),
    }
    json_str = json.dumps(ci_output, indent=2)
    print(json_str)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(report, indent=2))

    if result.get("errors"):
        raise SystemExit(1)
    total = report.get("summary", {}).get("total_tests", 0)
    failed = report.get("summary", {}).get("validation_failed", 0)
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    app()
