# TECH STACK & RULES DOCUMENT

**Product:** AI-Powered OpenAPI-First API Testing Platform
**Status:** Canonical / Enforced

## 1. Global Technology Principles

*   Explicit over implicit
*   Deterministic over probabilistic
*   Security over convenience
*   Auditability over performance
*   Safety over coverage

These principles override all local decisions.

## 2. Programming Languages & Runtimes
### 2.1 Backend Language

| Item | Requirement |
| :--- | :--- |
| Language | Python 3.11+ |
| Runtime | CPython |
| Async | Mandatory |

**Rules**

*   No Python < 3.11
*   No blocking I/O
*   No global mutable state

### 2.2 Frontend Language

| Item | Requirement |
| :--- | :--- |
| Language | TypeScript (strict) |
| JS Target | ES2022 |
| Runtime | Browser |

**Rules**

*   strict: true
*   No any
*   No business logic in UI

### 2.3 CLI Language

| Item | Requirement |
| :--- | :--- |
| Language | Python |
| Packaging | pipx compatible |

**Rules**

*   CLI must work without backend (local mode)
*   CLI must be scriptable

## 3. Backend Stack (Mandatory)
### 3.1 API Framework

| Component | Technology |
| :--- | :--- |
| Web Framework | FastAPI |
| ASGI Server | Uvicorn |
| Schema | OpenAPI auto-generated |

**Rules**

*   No Flask / Django
*   FastAPI models must use Pydantic v2
*   OpenAPI auto-docs must be enabled

### 3.2 Orchestration

| Component | Technology |
| :--- | :--- |
| Workflow Engine | LangGraph |
| Agent Model | Multi-agent DAG |
| Memory | Explicit state only |

**Rules**

*   No LangChain agents without LangGraph
*   No autonomous loops
*   No agent self-reflection nodes

### 3.3 HTTP Client

| Component | Technology |
| :--- | :--- |
| HTTP Client | httpx |
| Mode | Async |

**Rules**

*   No requests
*   Timeouts required
*   Retries explicitly configured

### 3.4 Validation & Schema

| Component | Technology |
| :--- | :--- |
| Data Models | Pydantic v2 |
| JSON Schema | OpenAPI schema |
| Validation | Strict |

**Rules**

*   extra=forbid
*   No silent coercion
*   Fail on mismatch

## 4. CLI Stack
### 4.1 CLI Framework

| Component | Technology |
| :--- | :--- |
| CLI Framework | Typer |
| Output Styling | Rich |
| Config | YAML |

**Rules**

*   Must support --json output
*   Must support non-interactive mode
*   Exit codes must reflect success/failure

### 4.2 CLI Commands (Required)

| Command | Purpose |
| :--- | :--- |
| init | Initialize project |
| validate | Validate OpenAPI |
| generate | Generate tests |
| approve | Approve destructive tests |
| run | Execute tests |
| report | Export reports |

## 5. Frontend Stack
### 5.1 Core Framework

| Component | Technology |
| :--- | :--- |
| Framework | React |
| State | React Query |
| Routing | React Router |

### 5.2 UI Rules

*   UI is read-only intelligence
*   No API execution from browser
*   No credential storage
*   All writes go through backend

## 6. Storage & Persistence
### 6.1 Primary Database

| Component | Technology |
| :--- | :--- |
| DB | PostgreSQL |
| ORM | SQLAlchemy (async) |

**Stored Data**

*   Specs
*   Test metadata
*   Reports
*   Approval records

### 6.2 Ephemeral Storage

| Component | Technology |
| :--- | :--- |
| Cache | Redis |

**Rules**

*   No secrets
*   No reports
*   TTL required

## 7. Security Stack
### 7.1 Secrets & Credentials

| Component | Technology |
| :--- | :--- |
| Encryption | Fernet (AES-256) |
| Secret Source | Env / Vault |
| Decryption | Runtime only |

**Rules**

*   Never store plaintext
*   Never log secrets
*   Never send secrets to AI

### 7.2 Authentication & Authorization

| Area | Technology |
| :--- | :--- |
| Auth | JWT / OAuth2 |
| RBAC | Role-based |
| Audit Logs | Mandatory |

## 8. AI Model Usage Rules
### 8.1 Allowed AI Usage

*   Test generation
*   Explanation generation
*   Policy interpretation
*   Risk reasoning

### 8.2 Forbidden AI Usage

*   Approval decisions
*   HTTP execution
*   Credential handling
*   State mutation

## 9. Versioning Rules

| Item | Rule |
| :--- | :--- |
| Specs | Versioned |
| Test Runs | Immutable |
| Reports | Immutable |

## 10. CI/CD Integration
### Required Integrations

*   GitHub Actions
*   GitLab CI
*   Jenkins (optional)

**Rules**

*   Non-zero exit on failures
*   Machine-readable outputs
*   Approval gates respected

## 11. Logging & Observability
### Logging

*   Structured logs (JSON)
*   No secrets
*   Correlation IDs

### Metrics

*   Test pass/fail rate
*   Approval latency
*   Drift detection count

## 12. Plugin & Extension Rules
### Allowed

*   Custom validators
*   Custom reporters
*   Policy modules

### Forbidden

*   Execution overrides
*   Approval bypass
*   Secret access

## 13. Definition of “Tech-Stack Compliant”

A component is tech-stack compliant only if:

*   It uses approved libraries
*   It follows async rules
*   It respects AI boundaries
*   It enforces security rules
*   It logs appropriately

## 14. Hard Stop Conditions

If any of the following occur, halt development:

*   Secrets logged
*   Approval bypassed
*   Agent runs autonomously
*   Spec ignored
*   State mutated implicitly
