# SENTINEL-API

SENTINEL-API is an OpenAPI-first API testing and governance toolkit. It includes a Next.js dashboard, a FastAPI backend, and a Python CLI named `autoapi` for validating specs, linting contracts, generating mocks, running the full testing pipeline, and applying generated spec fixes.

## Live Links

- Production app: `https://sentinel-api-tau.vercel.app`
- API health check: `https://sentinel-api-tau.vercel.app/api/health`

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer
- npm
- PowerShell on Windows, or any POSIX shell on macOS/Linux

## Quick Start

From the repository root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
npm install
```

Run the frontend and backend together:

```powershell
npm run dev
```

This starts:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`

Run them separately:

```powershell
npm run dev:frontend
npm run dev:backend
```

## CLI Overview

Run the CLI from the repository root. Both forms work:

```powershell
python -m cli.main --help
autoapi --help
```

Use `python -m cli.main ...` if you have not run `pip install -e .`. Use `autoapi ...` after the editable install.

Available commands:

```text
validate        Validate and normalize an OpenAPI spec.
lint            Lint an OpenAPI spec for quality issues.
live-lint       Compare a backend source file against an OpenAPI response contract.
apply-spec-fix  Apply a generated Sentinel remediation patch to an OpenAPI spec.
mock            Generate mock responses or run a local mock server.
run-graph       Run the full Sentinel testing pipeline.
```

## CLI Command Reference

### Validate a Spec

Checks that a YAML or JSON OpenAPI file can be loaded, structurally validated, and normalized into Sentinel's internal operation model.

```powershell
python -m cli.main validate examples\petstore.yaml
autoapi validate examples\petstore.yaml
```

Expected success output includes:

```text
Spec loaded successfully
Spec structure validated
Normalized N operations
```

### Lint a Spec

Runs the standalone OpenAPI quality linter.

```powershell
python -m cli.main lint examples\petstore.yaml
autoapi lint examples\petstore.yaml
```

The linter reports issues such as missing descriptions, undocumented error responses, missing security schemes, and unsecured write operations.

### Run the Full Pipeline

Runs the LangGraph pipeline in dry-run mode by default. This is the main CI-friendly command.

```powershell
python -m cli.main run-graph examples\petstore.yaml --approve --output sentinel-report.json
autoapi run-graph examples\petstore.yaml --approve --output sentinel-report.json
```

Useful options:

```text
--approve          Auto-approve destructive or high-risk generated tests.
--live             Execute against the API server declared in the OpenAPI spec.
--output, -o       Write the full JSON report to a file.
--verbose, -v      Show assertion-level details.
--env, -e          Set environment profile: dev, staging, or prod.
--ci               Print machine-readable JSON and use CI-style exit codes.
```

CI example:

```powershell
python -m cli.main run-graph examples\petstore.yaml --approve --ci --output autoapi-report.json
```

Live API example:

```powershell
python -m cli.main run-graph path\to\openapi.yaml --live --approve --env staging --output live-report.json
```

For live mode, make sure the OpenAPI file has a valid `servers` entry, or the generated test URLs will not point at the intended API.

### Generate Mock Responses

Print generated mock responses:

```powershell
python -m cli.main mock examples\petstore.yaml
```

Export mocks to JSON:

```powershell
python -m cli.main mock examples\petstore.yaml --output mocks.json
```

Start a local intelligent mock server:

```powershell
python -m cli.main mock examples\petstore.yaml --serve --port 8080
```

Then call the mocked endpoints at:

```text
http://localhost:8080/<path-from-spec>
```

### Live Contract Lint a Source File

Checks a backend source file against an OpenAPI response contract. This is useful while editing route handlers.

```powershell
python -m cli.main live-lint backend\app\main.py --spec examples\petstore.yaml
```

Machine-readable mode:

```powershell
python -m cli.main live-lint backend\app\main.py --spec examples\petstore.yaml --ci
```

### Apply a Generated Spec Fix

Applies a Sentinel remediation patch JSON object to an OpenAPI file.

```powershell
python -m cli.main apply-spec-fix --spec openapi.yaml --patch-json '{"operations":[]}'
```

Use this with patch payloads produced by Sentinel's drift remediation flow. Because this command edits the spec file in place, commit your spec before applying large patches.

## Frontend and Backend Commands

```powershell
npm run dev           # Frontend and backend together
npm run dev:frontend  # Next.js only
npm run dev:backend   # FastAPI only
npm run build         # Production frontend build
npm run start         # Start built Next.js app
npm run lint          # ESLint
```

Backend health check when running locally:

```powershell
curl http://localhost:8000/api/health
```

## Example Specs

Use these files for smoke tests:

```text
examples\petstore.yaml
examples\bookstore.json
examples\high_risk_spec.yaml
examples\full_test_api.yaml
```

Recommended first verification:

```powershell
python -m cli.main validate examples\petstore.yaml
python -m cli.main lint examples\petstore.yaml
python -m cli.main run-graph examples\petstore.yaml --approve --ci --output autoapi-report.json
```

## GitHub Actions

The repository includes `.github/workflows/autoapi-test.yml`, which runs the CLI in CI:

```powershell
python -m cli.main lint examples/petstore.yaml
python -m cli.main run-graph examples/petstore.yaml --approve --ci --output autoapi-report.json
```

The workflow publishes artifacts:

```text
autoapi-report.json
junit-results.xml
```

It also publishes JUnit results as a GitHub check when the workflow token has `checks: write`. For forked pull requests, it falls back to annotations because GitHub intentionally makes the default token read-only for those events.

## Troubleshooting

### `python -m cli.main` cannot import dependencies

Activate the virtual environment and reinstall requirements:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

### `autoapi` is not recognized

Install the package in editable mode:

```powershell
pip install -e .
```

Or use the module form:

```powershell
python -m cli.main --help
```

### Windows console shows odd symbols

Use a UTF-8 terminal session:

```powershell
$env:PYTHONUTF8 = "1"
chcp 65001
```

The CLI also configures Python stdout/stderr as UTF-8 at startup.

### Live mode calls the wrong URL

Check the `servers` block in the OpenAPI spec:

```yaml
servers:
  - url: https://api.example.com
```

Dry-run mode does not make real HTTP calls. Live mode does.

### CI fails on GitHub check creation

Make sure the workflow has:

```yaml
permissions:
  contents: read
  checks: write
  pull-requests: read
```

Forked PRs cannot create check runs with the default `GITHUB_TOKEN`; use annotation-only reporting for those runs.

## Repository Layout

```text
app/                  Next.js app routes
components/           Shared frontend components
backend/app/          FastAPI app, graph nodes, services, schemas
backend/cli/          Mock server helpers used by the CLI
cli/main.py           Typer CLI entry point
examples/             Example OpenAPI specs and plugins
docs/                 Product, design, and technical docs
.github/workflows/    CI workflow definitions
```

## Minimal Operator Flow

For day-to-day CLI usage:

```powershell
.\venv\Scripts\Activate.ps1
python -m cli.main validate path\to\openapi.yaml
python -m cli.main lint path\to\openapi.yaml
python -m cli.main run-graph path\to\openapi.yaml --approve --ci --output autoapi-report.json
```
