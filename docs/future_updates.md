# Future Updates

## Goal

Expand Sentinel so repositories without OpenAPI YAML/JSON files can still be analyzed reliably by extracting APIs directly from source code and feeding that data into the existing risk, report, and approval pipeline.

## Core Direction

Sentinel should support a second ingestion path alongside spec validation:

1. Detect framework or API library usage in source code.
2. Extract routes from code.
3. Normalize extracted routes into one shared internal shape.
4. Optionally synthesize a minimal OpenAPI document so the rest of the existing pipeline can run without major duplication.

Current foundation:

- Core extractor: `backend/app/services/repo_code_api_extractor.py`
- Repo intake: `backend/app/services/github_repo_analyzer.py`

## Phase 1: Solidify Framework Detection

### Objective

Improve framework/library detection so Sentinel correctly recognizes source-code APIs even when no spec file exists.

### Scope

- Detect imports and framework objects for:
  - `FastAPI`
  - `APIRouter`
  - `Flask`
  - `Blueprint`
  - `Django path/re_path`
  - `Express`
  - `Fastify`

### Tasks

- Standardize import detection rules per language.
- Detect router/app instances in addition to imports.
- Track which files contributed to each detected framework.
- Add ranking so high-signal backend files are scanned first.

### Acceptance Criteria

- Sentinel identifies supported framework usage from code-only repos.
- Detected frameworks include file references and route counts.

## Phase 2: Expand Route Extraction

### Objective

Extract route definitions from framework code consistently.

### Scope

- Support patterns such as:
  - `@app.get("/x")`
  - `@app.route("/x", methods=["POST"])`
  - `router.delete("/x")`
  - `urlpatterns = [path(...), re_path(...)]`

### Tasks

- Keep one extractor per ecosystem/framework.
- Ensure every extractor returns the same normalized route shape.
- Merge all extracted routes into a shared `code_analysis` object.
- Deduplicate routes across files/routers.

### Shared Route Shape

Each extracted route should include:

- `framework`
- `method`
- `path`
- `source_file`
- `handler_name`
- optional future fields like auth, params, and inferred status codes

### Acceptance Criteria

- Extracted routes appear consistently across supported frameworks.
- Duplicate definitions do not create duplicate API entries.

## Phase 3: Normalize and Synthesize OpenAPI

### Objective

Allow code-derived APIs to reuse the existing OpenAPI-based pipeline.

### Tasks

- Convert route path syntax into a shared format:
  - Flask `<id>` to `{id}`
  - Express `:id` to `{id}`
- Build a synthetic OpenAPI document from extracted routes.
- If no real OpenAPI exists, call `synthesize_openapi_spec(...)`.
- Mark source provenance with code-derived metadata.

### Acceptance Criteria

- Code-derived repos can still flow through risk scoring, reporting, and approval logic.
- Synthetic specs preserve enough metadata for downstream analysis.

## Phase 4: Add More Framework Support

### Objective

Broaden coverage beyond the initial set of frameworks.

### Candidate Frameworks

- `aiohttp`
- `Bottle`
- `Sanic`
- `NestJS`
- `Koa`
- `Hono`
- `Spring`
- `ASP.NET`

### Tasks

- Add framework-specific extractors one by one.
- Reuse the same normalized route output contract.
- Prioritize lightweight regex/AST extraction first, then deeper parsers only where needed.

### Acceptance Criteria

- New frameworks can be added without changing downstream analysis code.

## Phase 5: Improve Accuracy of Code-Derived APIs

### Objective

Make extracted APIs richer and more useful than just method + path.

### Enhancements

- Read docstrings and nearby comments above handlers.
- Infer request params from function signatures.
- Infer path params from placeholders.
- Detect auth decorators and middleware.
- Detect destructive routes from:
  - HTTP method
  - handler names like `delete`, `remove`, `purge`
- Infer response status codes from common return patterns.

### Acceptance Criteria

- Reports for code-derived APIs include more meaningful metadata and risk context.

## Phase 6: Clean Up OpenAPI Candidate Handling

### Objective

Reduce misleading invalid cards for ordinary JSON/YAML files.

### Problem

- JSON/YAML files may be tested as possible OpenAPI candidates.
- Ordinary config or manifest files fail validation and appear as invalid spec cards.

### Tasks

- Rank/filter candidates more aggressively.
- Hide invalid OpenAPI candidate cards by default when `selected_source_kind === "code"`.
- Show a compact “Possible spec files” collapsible only when useful.
- Continue honoring a user-selected file or explicit GitHub blob URL when present.

### Acceptance Criteria

- Code-derived mode no longer feels broken because of irrelevant invalid spec cards.

## Phase 7: UI Behavior for Code-Derived Mode

### Objective

Make the frontend clearly reflect whether Sentinel is using code extraction or a real OpenAPI spec.

### Recommended UI Rules

When `selected_source_kind === "code"`:

- Show:
  - Detected Frameworks
  - Extracted Routes
  - Source Files
- Hide invalid OpenAPI candidate cards by default.
- Only show possible spec files in a secondary collapsible if needed.

When `selected_source_kind === "openapi"`:

- Show:
  - Selected OpenAPI file
  - Valid candidate specs
  - Repo details

### Acceptance Criteria

- Users can immediately tell whether Sentinel is analyzing source code or a real spec.

## Suggested Architecture Pattern

- Keep one extractor per framework or ecosystem.
- Normalize all extractors to one route schema.
- Merge into `code_analysis`.
- Reuse synthetic OpenAPI generation for downstream compatibility.
- Keep UI source-aware so code-derived mode and spec-derived mode feel intentional.

## Recommended Order of Work

1. Harden current framework detection and candidate filtering.
2. Improve metadata extraction for currently supported frameworks.
3. Clean up code-derived UI behavior.
4. Add additional Python and Node frameworks.
5. Add deeper inference for auth, params, and responses.
6. Add JVM and .NET framework support later.

## Validation Plan

- Add fixtures for code-only repos across supported frameworks.
- Add tests for mixed repos containing both specs and framework code.
- Add tests for invalid JSON/YAML files that should not surface as primary API candidates.
- Verify:
  - extractor output
  - synthetic OpenAPI generation
  - approval/report flow
  - frontend repo intake rendering

## Success Definition

Sentinel should be able to analyze a repository successfully when:

- a valid OpenAPI file exists, or
- no OpenAPI file exists but supported framework routes can be extracted from source code.

The resulting repo experience should feel clear, intentional, and trustworthy in both cases.
