"""Quick end-to-end pipeline test with rich spec."""
from backend.app.graph.builder import GraphBuilder
import json

spec = {
    "openapi": "3.0.0",
    "info": {"title": "Test API", "version": "1.0.0"},
    "paths": {
        "/users": {
            "get": {
                "operationId": "listUsers",
                "summary": "List all users",
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "email": {"type": "string"},
                                            "name": {"type": "string"},
                                        },
                                    },
                                }
                            }
                        },
                    }
                },
            },
            "post": {
                "operationId": "createUser",
                "summary": "Create user",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "email": {"type": "string"},
                                    "password": {"type": "string"},
                                    "name": {"type": "string"},
                                },
                                "required": ["email", "password"],
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "Created"}},
            },
        },
        "/users/{id}": {
            "delete": {
                "operationId": "deleteUser",
                "summary": "Delete user",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                ],
                "responses": {"204": {"description": "Deleted"}},
            }
        },
    },
}

graph = GraphBuilder.build()
result = graph.invoke(
    {
        "spec_raw": spec,
        "risk_scores": {},
        "risk_details": {},
        "lint_results": [],
        "policy_config": None,
        "test_cases": [],
        "security_test_cases": [],
        "security_results": [],
        "execution_results": [],
        "validation_results": [],
        "drift_results": [],
        "compliance_mappings": [],
        "policy_results": [],
        "approval_required": False,
        "approval_status": True,
        "environment": "dev",
        "errors": [],
    }
)

report = result.get("report", {})
print("=== Pipeline Success ===")
si = report.get("spec_info", {})
sm = report.get("summary", {})
ls = report.get("lint_summary", {})
ss = report.get("security_summary", {})
rd = report.get("risk_distribution", {})
cs = report.get("compliance_summary", {})
ds = report.get("drift_summary", {})
print(f"Total operations: {si.get('total_operations', 0)}")
print(f"Total tests: {sm.get('total_tests', 0)}")
print(f"Lint issues: {ls.get('total_issues', 0)} (err={ls.get('errors',0)}, warn={ls.get('warnings',0)})")
print(f"Security tests: {ss.get('total_security_tests', 0)}")
print(f"Risk levels: {rd}")
print(f"Drift: {ds}")
print(f"Compliance frameworks: {cs.get('frameworks_covered', [])}")
print(f"Compliance mappings: {cs.get('total_mappings', 0)}")
print(f"Errors: {report.get('errors', [])}")
print()
print("--- Risk Details ---")
for endpoint, details in report.get("risk_details", {}).items():
    print(f"  {endpoint}: score={details.get('score')}, level={details.get('level')}")
    for f in details.get("factors", []):
        print(f"    - {f.get('name')}: {f.get('description')}")
print()
print("--- Test Cases ---")
for tr in report.get("test_results", []):
    reason = tr.get("reason", "")[:80]
    ttype = tr.get("test_type", "?")
    print(f"  [{ttype:8s}] {tr.get('test_id')}")
    print(f"            -> {reason}")
print()
print("--- Security Test Cases ---")
for st in report.get("security_test_cases", []):
    print(f"  [{st.get('owasp_category')}] {st.get('id')}")
    print(f"    {st.get('description', '')[:80]}")
