# AI Safety Rules

This document outlines the mandatory safety contract for AI agents operating within this system.

## Forbidden Actions

The following actions are strictly prohibited for any AI agent:

1.  **Approval Decisions**: Agents cannot approve their own work or the work of others. All approvals must come from an authenticated human user.
2.  **Execution Without Approval**: Destructive or high-risk operations cannot be executed without explicit human consent.
3.  **Secret Access**: Agents must never have access to raw credentials, keys, or secrets.
4.  **Spec Inference**: Agents cannot invent or infer endpoints, parameters, or schemas that are not explicitly defined in the OpenAPI specification.

## Agent Behavior

*   **Deterministic**: AI behavior must be reproducible.
*   **Explainable**: All AI decisions and outputs must be accompanied by a clear, human-readable explanation.
*   **Scoped**: AI context is strictly limited to the task at hand and the provided OpenAPI spec.

## Enforcement

*   Violation of these rules will result in immediate termination of the agent process.
*   The system architecture (LangGraph) is designed to physically prevent these actions where possible.
