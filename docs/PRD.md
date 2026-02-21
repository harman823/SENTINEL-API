# Product Name

AutoAPI Intelligence (working name)

## 1. Purpose & Vision
### 1.1 Purpose

AutoAPI Intelligence is an AI-powered, OpenAPI-first API testing and intelligence platform that automatically generates, executes, validates, and reports API tests using controlled AI agent workflows.

The system prioritizes:

*   Safety
*   Explainability
*   Reproducibility
*   Human control

### 1.2 Vision

Become the source of truth for API behavior, not just a testing tool.

The product should evolve from static test execution to continuous API intelligence, detecting drift, risk, and regressions across environments.

## 2. Problem Statement
### Current Problems

*   Manual API testing is slow and inconsistent
*   Existing tools do not reason semantically about APIs
*   Negative and edge-case testing is incomplete
*   Destructive endpoints are risky to automate
*   OpenAPI specs and real behavior often drift apart
*   Test cases are not explainable or auditable

## 3. Target Users
### Primary Users

*   Backend Engineers
*   QA Engineers
*   API Platform Teams

### Secondary Users

*   DevOps / SRE
*   Security Engineers
*   Compliance Teams

## 4. Goals & Success Metrics
### Product Goals

| Goal | Metric |
| :--- | :--- |
| Reduce manual API testing | ≥ 70% |
| Increase negative test coverage | ≥ 3× |
| Prevent destructive incidents | 0 unauthorized executions |
| Improve API reliability | Fewer regressions |
| Build trust in AI tests | 100% explainable tests |

### Non-Goals (Explicit)

*   ❌ UI testing
*   ❌ Browser automation
*   ❌ Autonomous production writes
*   ❌ Model fine-tuning (v1)

## 5. Core Functional Requirements
### 5.1 OpenAPI Specification Handling

**Requirements**

*   Support OpenAPI 3.0 and 3.1
*   Accept YAML and JSON
*   Validate schema strictly
*   Reject malformed specs

**Outputs**

*   Normalized internal representation
*   Endpoint metadata
*   Destructive endpoint tagging

### 5.2 AI-Generated Test Cases

**Test Types (Mandatory)**

*   Positive (happy path)
*   Negative (auth, schema, validation)
*   Boundary conditions
*   Required/optional fields
*   Error response validation

**Rules**

*   Every test must map to OpenAPI constraints
*   No fabricated endpoints
*   No uncontrolled randomness

### 5.3 Human-in-the-Loop Approval

**Approval Required For**

*   DELETE
*   PUT
*   PATCH
*   Any endpoint marked destructive

**Approval Modes**

*   CLI prompt
*   Web UI confirmation
*   API approval token

**Blocking Behavior**

*   Execution must halt until approval

### 5.4 API Execution

**Capabilities**

*   Auth injection (Bearer, API key)
*   Rate limit respect
*   Timeout handling
*   Retry logic (non-destructive only)

**Restrictions**

*   No execution without approval
*   No production writes by default

### 5.5 Response Validation

**Validations**

*   HTTP status code
*   Schema conformity
*   Required fields
*   Error message format

**Output**

```json
{
  "test_id": "...",
  "passed": true,
  "failures": []
}
```

### 5.6 Reporting

**Formats**

*   JSON (machine-readable)
*   HTML (human-readable)
*   JUnit XML (CI/CD)

**Report Must Include**

*   Test rationale
*   Expected vs actual
*   Failure explanations
*   Spec references

## 6. Advanced Feature Requirements (V1.5+)
### 6.1 API Risk Scoring

Each endpoint must receive a risk score derived from:

*   HTTP method
*   Auth requirements
*   Data sensitivity
*   Schema complexity

```json
{
  "risk_score": 0.82,
  "risk_level": "HIGH"
}
```

### 6.2 Policy-Driven Testing

Users define policies, not tests.

```yaml
policies:
  destructive:
    require_approval: true
    min_negative_tests: 5
```

AI must:

*   Translate policy → tests
*   Enforce policy
*   Explain violations

### 6.3 Contract Drift Detection (Optional)

*   Compare live responses vs OpenAPI
*   Flag mismatches
*   Block CI if configured

## 7. Interfaces
### 7.1 CLI Interface

**Commands**

*   init
*   validate
*   generate
*   approve
*   run
*   report

**Rules**

*   Non-interactive mode supported
*   CI-safe exit codes

### 7.2 Cloud Platform

**Capabilities**

*   Spec upload
*   Test review
*   Approval UI
*   Execution dashboard
*   Historical reports

## 8. Security Requirements
### Credentials

*   Encrypted at rest
*   Decrypted only at runtime
*   Never logged

### Access Control

*   Role-based (viewer / approver / executor)
*   Audit logs required

## 9. Compliance & Safety
### Mandatory Safeguards

*   Approval gates cannot be bypassed
*   All actions are auditable
*   All AI outputs are explainable

## 10. Constraints
### Technical Constraints

*   OpenAPI-first design
*   LangGraph-based orchestration
*   Python backend

### Organizational Constraints

*   No unsafe automation
*   No black-box decisions

## 11. Assumptions

*   Users provide accurate OpenAPI specs
*   APIs are reachable in test environments
*   Credentials are environment-scoped

## 12. Out of Scope (Explicit)

*   Load testing
*   Performance benchmarking
*   DDoS simulation
*   Penetration testing

## 13. Open Questions (For Future Docs)

*   Spec versioning strategy?
*   Multi-tenant isolation?
*   Plugin marketplace governance?

## 14. Acceptance Criteria

The product is V1 complete when:

*   A user can upload an OpenAPI spec
*   Tests are generated deterministically
*   Destructive tests require approval
*   Tests execute safely
*   Results are validated and reported
*   CLI and cloud both function correctly

## 15. Rules for AI Agents (Hard Constraints)

*   Do not invent endpoints
*   Do not bypass approval
*   Do not mutate state implicitly
*   Every test must reference OpenAPI
*   Every failure must be explainable
