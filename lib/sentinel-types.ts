export interface Assertion {
  type: string;
  expected: string | number;
  actual: string | number;
  passed: boolean;
  message: string;
}

export interface Execution {
  test_id: string;
  method: string;
  url: string;
  status_code: number;
  expected_status: number;
  passed: boolean;
  response_time_ms: number;
  response_headers: Record<string, string>;
  response_body_preview: string;
  error: string | null;
  dry_run: boolean;
}

export interface Validation {
  test_id: string;
  passed: boolean;
  assertions: Assertion[];
  summary: string;
}

export interface TestResult {
  test_id: string;
  method: string;
  url: string;
  path?: string;
  expected_status: number;
  is_destructive: boolean;
  risk_score: number;
  test_type?: string;
  execution: Execution;
  validation: Validation;
}

export interface PolicyResult {
  operation_key: string;
  requires_approval: boolean;
  violated_rules: string[];
  messages: string[];
}

export interface HighRiskOperation {
  operation_key: string;
  method?: string | null;
  path?: string | null;
  summary?: string | null;
  is_destructive: boolean;
  risk_score: number;
  risk_level?: string | null;
  risk_explanation?: string | null;
  risk_factors?: Array<{ name?: string; weight?: number; description?: string }>;
  requires_approval?: boolean;
  violated_rules?: string[];
}

export interface Report {
  generated_at: string;
  spec_info: { title: string; version: string; total_operations: number };
  summary: {
    total_tests: number;
    execution_passed: number;
    execution_failed: number;
    validation_passed: number;
    validation_failed: number;
    pass_rate: number;
    approval_required: boolean;
    approval_status: boolean;
    flagged_operations: number;
    errors: number;
  };
  risk_distribution: { high: number; medium: number; low: number };
  risk_summary?: {
    highest_risk_score: number;
    high_risk_operations: HighRiskOperation[];
  };
  policy_results: PolicyResult[];
  test_results: TestResult[];
  chaos_summary?: {
    enabled: boolean;
    total_injected: number;
    documented_failures: number;
    undocumented_failures: number;
  };
  iac_validation?: {
    passed: boolean;
    score: number;
    checks: Array<{ control: string; required: boolean; detected: boolean; passed: boolean }>;
    missing_controls: string[];
  };
  safe_to_ship?: {
    safe_to_ship: boolean;
    score: number;
    blockers: string[];
  };
  remediation_summary?: {
    total_remediations: number;
    total_pr_suggestions: number;
  };
  rca_summary?: { total_findings: number };
  compliance_scorecard?: { overall_compliance_health: number };
  breaking_change_summary?: { total_predictions: number; likely_breaking: number };
  errors: string[];
  error_details?: Array<{ message: string; severity: string }>;
}

export interface RepoLanguage {
  name: string;
  bytes: number;
  percent: number;
}

export interface RepoFileFormat {
  extension: string;
  count: number;
}

export interface RepoSpecCandidate {
  path: string;
  raw_url?: string;
  parseable: boolean;
  title?: string | null;
  version?: string | null;
  total_operations: number;
  openapi_version?: string | null;
  errors?: string[];
  candidate_score?: number;
  source_kind?: "openapi" | "code";
}

export interface RepoFrameworkDetection {
  framework: string;
  files: string[];
  route_count: number;
}

export interface RepoInspection {
  source_url: string;
  repo_url: string;
  name: string;
  full_name: string;
  description?: string | null;
  owner: string;
  default_branch: string;
  selected_ref: string;
  stars: number;
  watchers: number;
  forks: number;
  visibility: string;
  languages: RepoLanguage[];
  file_formats: RepoFileFormat[];
  total_files: number;
  detected_frameworks: RepoFrameworkDetection[];
  code_route_count: number;
  selected_source_kind: "openapi" | "code";
  candidate_specs: RepoSpecCandidate[];
  selected_spec?: RepoSpecCandidate;
  approval_required: boolean;
  approval_prompt: string;
}

export interface ApiCatalogOperation {
  operation_key: string;
  method: string;
  path: string;
  summary?: string | null;
  description?: string | null;
  operation_id?: string | null;
  tags: string[];
  is_destructive: boolean;
  security_schemes: string[];
  pii_fields: string[];
  schema_complexity: number;
  risk_score: number;
  risk_level: string;
  risk_factors: Array<{ name?: string; weight?: number; description?: string }>;
  risk_explanation?: string | null;
}

export interface CodeExtractedRoute {
  framework: string;
  method: string;
  path: string;
  source_file: string;
  handler_name?: string | null;
}

export interface ApiManifest {
  manifest_version: string;
  generated_at: string;
  source: {
    type: string;
    url: string;
    owner: string;
    repo: string;
    ref: string;
  };
  repository: {
    name: string;
    full_name: string;
    description?: string | null;
    repo_url: string;
    default_branch: string;
    visibility: string;
  };
  tech_stack: {
    languages: RepoLanguage[];
    file_formats: RepoFileFormat[];
    total_files: number;
  };
  api_catalog: {
    source_kind: "openapi" | "code";
    selected_spec?: RepoSpecCandidate;
    candidate_specs: RepoSpecCandidate[];
    spec_info: {
      title: string;
      version: string;
      openapi_version: string;
      total_operations: number;
    };
    summary: {
      total_operations: number;
      destructive_operations: number;
      high_risk_operations: number;
    };
    code_analysis?: {
      frameworks: RepoFrameworkDetection[];
      routes: CodeExtractedRoute[];
      summary: {
        framework_count: number;
        route_count: number;
      };
    };
    operations: ApiCatalogOperation[];
  };
}
