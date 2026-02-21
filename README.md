# AutoAPI Intelligence

> AI-powered, OpenAPI-first API testing and intelligence platform that automatically generates, executes, validates, and reports API tests using controlled AI agent workflows (LangGraph).

---

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Project](#running-the-project)
  - [Web Dashboard](#1-web-dashboard)
  - [CLI](#2-cli)
- [Sample Specs](#sample-specs)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)

---

## Features

| Capability | Description |
|---|---|
| **Spec Parsing** | Accepts OpenAPI 3.0/3.1 specs in YAML or JSON |
| **Risk Scoring** | Heuristic scoring (0.0–1.0) based on HTTP method, path keywords, and security |
| **Policy Evaluation** | Checks destructive methods, high risk scores, and missing `operationId` |
| **Approval Gate** | Blocks destructive operations (DELETE/PUT/PATCH) until explicitly approved |
| **Test Generation** | Auto-generates positive test cases for every operation |
| **Execution** | Dry-run simulation or live API execution with auth injection |
| **Validation** | Asserts status codes, content-types, and response times |
| **Reporting** | Full JSON reports with pass rates, risk distribution, and flagged operations |

---

## Prerequisites

- **Python 3.11+**
- **pip** (Python package manager)

---

## Installation

```bash
# 1. Clone or navigate to the project directory
cd "path/to/AutoAPI-Intelligence"

# 2. Install all dependencies
pip install -r requirements.txt
```

---

## Running the Project

### 1. Web Dashboard

Start the FastAPI server which serves both the backend API and the frontend UI:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open your browser:

| URL | Description |
|-----|-------------|
| `http://localhost:8000` | Frontend Dashboard |
| `http://localhost:8000/docs` | Swagger UI (interactive API docs) |
| `http://localhost:8000/health` | Health check endpoint |

**Upload a spec via the UI:**
1. Open `http://localhost:8000`
2. Click the upload area and select a YAML/JSON OpenAPI spec file
3. Click **Run Pipeline** to execute the full analysis
4. View risk scores, policy results, test outcomes, and the final report

**Upload a spec via cURL:**

```bash
# Upload and run pipeline
curl -X POST http://localhost:8000/api/v1/upload -F "file=@examples/full_test_api.yaml"

# Upload with auto-approval for destructive operations
curl -X POST "http://localhost:8000/api/v1/upload?approve=true" -F "file=@examples/full_test_api.yaml"

# Validate only (no execution)
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d @examples/bookstore.json
```

---

### 2. CLI

The CLI provides the same pipeline functionality from the terminal with rich, colorful output.

#### Validate a Spec

Quick validation and normalization check — does not run the full pipeline:

```bash
python -m cli.main validate examples/full_test_api.yaml
```

#### Run the Full Pipeline

**Basic run (dry-run, no approval):**
```bash
python -m cli.main run-graph examples/full_test_api.yaml
```
> Destructive operations (DELETE/PUT/PATCH) are **blocked** by the approval gate.

**With auto-approval (unlocks destructive operations):**
```bash
python -m cli.main run-graph examples/full_test_api.yaml --approve
```

**With verbose output (shows assertion-level details):**
```bash
python -m cli.main run-graph examples/full_test_api.yaml --approve --verbose
```

**Export report to JSON file:**
```bash
python -m cli.main run-graph examples/full_test_api.yaml --approve -o report.json
```

**All options combined:**
```bash
python -m cli.main run-graph examples/full_test_api.yaml --approve --verbose -o report.json
```

#### CLI Flags Reference

| Flag | Short | Description |
|------|-------|-------------|
| `--approve` | | Auto-approve destructive operations for testing |
| `--live` | | Execute tests against a live API (default: dry-run) |
| `--verbose` | `-v` | Show assertion-level output for every validation |
| `--output` | `-o` | Export the full JSON report to a file |

#### CLI Help

```bash
python -m cli.main --help
python -m cli.main run-graph --help
python -m cli.main validate --help
```

---

## Sample Specs

Three sample OpenAPI specs are included in the `examples/` directory:

| File | Description |
|------|-------------|
| `examples/petstore.yaml` | Minimal spec (3 operations) — quick smoke test |
| `examples/bookstore.json` | Medium spec in JSON format |
| `examples/full_test_api.yaml` | Comprehensive spec (31 operations) — exercises all pipeline features |

The `full_test_api.yaml` spec is designed to cover:
- All HTTP methods (GET, POST, PUT, PATCH, DELETE)
- High-risk keyword paths (`/admin`, `/auth`, `/secret-keys`, `/password`)
- Missing `operationId` (policy violation)
- Complex nested schemas with `$ref`
- Multiple response codes (200, 201, 204, 400, 401, 403, 404, 409, 500)
- Path, query, and header parameters
- File upload (multipart)
- Bulk operations

---

## Project Structure

```
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI app (API + frontend serving)
│       ├── schemas/                 # Pydantic models (NormalizedSpec, Operation)
│       ├── services/                # Business logic
│       │   ├── openapi_loader.py    # Load YAML/JSON spec files
│       │   ├── spec_validator.py    # Validate OpenAPI structure
│       │   ├── spec_normalizer.py   # Normalize spec into internal model
│       │   ├── risk_scorer.py       # Heuristic risk scoring
│       │   ├── policy_engine.py     # Policy evaluation engine
│       │   ├── test_generator.py    # Test case generation
│       │   └── report_generator.py  # Report generation
│       └── graph/
│           ├── builder.py           # LangGraph pipeline builder
│           ├── state.py             # Graph state definition
│           └── nodes/               # Pipeline nodes
│               ├── parse_spec.py
│               ├── score_risk.py
│               ├── evaluate_policy.py
│               ├── approval_gate.py
│               ├── generate_tests.py
│               ├── execute_api.py
│               ├── validate_responses.py
│               └── generate_report.py
├── cli/
│   └── main.py                      # Typer CLI application
├── frontend/
│   ├── index.html                   # Dashboard UI
│   ├── app.js                       # Frontend logic
│   └── styles.css                   # Styles
├── examples/                        # Sample OpenAPI specs
├── tests/                           # Unit tests
├── requirements.txt                 # Python dependencies
└── pyproject.toml                   # Project metadata
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/run` | Run pipeline with JSON spec body |
| `POST` | `/api/v1/upload` | Upload YAML/JSON file and run pipeline |
| `POST` | `/api/v1/validate` | Validate spec without running pipeline |
| `GET` | `/` | Serve frontend dashboard |

---

## Pipeline Flow

```
Parse Spec → Score Risk → Evaluate Policy → Approval Gate → Generate Tests → Execute API → Validate Responses → Generate Report
```

Each step is a LangGraph node. The pipeline runs end-to-end and produces a structured report with pass/fail results, risk scores, and policy violations.
