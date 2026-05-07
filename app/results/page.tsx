"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import SentinelLoader from "@/components/SentinelLoader";
import {
    ArrowLeft,
    CheckCircle2,
    XCircle,
    AlertTriangle,
    Shield,
    Clock,
    FileJson,
    ChevronDown,
    ChevronUp,
    BarChart3,
    Activity,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TimeTravelDebugger } from "@/components/TimeTravelDebugger";
import { BlastRadiusGraph } from "@/components/BlastRadiusGraph";
import { ReportDownloadMenu } from "@/components/ReportDownloadMenu";
import { RepoInspectionPanel } from "@/components/RepoInspectionPanel";
import { HighRiskOperationsPanel } from "@/components/HighRiskOperationsPanel";
import type { ApiManifest, RepoInspection } from "@/lib/sentinel-types";

interface ExecutionHistoryStep {
    step: number;
    action: string;
    timestamp: string;
    details: string;
}

interface BlastRadiusData {
    blast_radius_by_schema?: Record<string, string[]>;
    nodes?: Array<{ id: string; label: string; type: string }>;
    edges?: Array<{ source: string; target: string; type: string }>;
}

interface StoredPipelineResponse {
    execution_history?: ExecutionHistoryStep[];
    blast_radius?: BlastRadiusData | null;
    repo_inspection?: RepoInspection | null;
    api_manifest?: ApiManifest | null;
}

/* ─── Types matching report.json ─── */
interface Assertion {
    type: string;
    expected: string | number;
    actual: string | number;
    passed: boolean;
    message: string;
}

interface Execution {
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

interface Validation {
    test_id: string;
    passed: boolean;
    assertions: Assertion[];
    summary: string;
}

interface TestResult {
    test_id: string;
    method: string;
    url: string;
    expected_status: number;
    is_destructive: boolean;
    risk_score: number;
    test_type?: string;
    execution: Execution;
    validation: Validation;
}

interface PolicyResult {
    operation_key: string;
    requires_approval: boolean;
    violated_rules: string[];
    messages: string[];
}

interface Report {
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
        high_risk_operations: Array<{
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
        }>;
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

/* ─── Demo data (used when no report passed via state) ─── */
const DEMO_REPORT: Report = {
    generated_at: new Date().toISOString(),
    spec_info: { title: "Failure Heavy Risk API", version: "1.2.0", total_operations: 4 },
    summary: {
        total_tests: 4,
        execution_passed: 1,
        execution_failed: 3,
        validation_passed: 1,
        validation_failed: 3,
        pass_rate: 25,
        approval_required: true,
        approval_status: false,
        flagged_operations: 3,
        errors: 3,
    },
    risk_distribution: { high: 3, medium: 1, low: 0 },
    risk_summary: {
        highest_risk_score: 0.92,
        high_risk_operations: [
            {
                operation_key: "/admin/system/users/{userId}.delete",
                method: "DELETE",
                path: "/admin/system/users/{userId}",
                summary: "Delete privileged user",
                is_destructive: true,
                risk_score: 0.92,
                risk_level: "high",
                risk_explanation: "Privileged destructive admin action with direct account impact.",
                risk_factors: [
                    { name: "destructive_method", weight: 0.35, description: "DELETE operation" },
                    { name: "admin_scope", weight: 0.3, description: "Administrative path segment" },
                    { name: "identity_target", weight: 0.27, description: "Operates on privileged users" },
                ],
                requires_approval: true,
                violated_rules: ["destructive_method"],
            },
            {
                operation_key: "/system/secrets/{secretId}.patch",
                method: "PATCH",
                path: "/system/secrets/{secretId}",
                summary: "Rotate production secret",
                is_destructive: true,
                risk_score: 0.86,
                risk_level: "high",
                risk_explanation: "Mutates highly sensitive credentials and secret material.",
                risk_factors: [
                    { name: "sensitive_fields", weight: 0.38, description: "password, token, api_key, secret, cvv" },
                    { name: "credential_rotation", weight: 0.26, description: "Directly updates secrets" },
                    { name: "destructive_method", weight: 0.22, description: "PATCH mutates production state" },
                ],
                requires_approval: true,
                violated_rules: ["high_risk_score"],
            },
            {
                operation_key: "/internal/admin/config.put",
                method: "PUT",
                path: "/internal/admin/config",
                summary: "Replace internal config",
                is_destructive: true,
                risk_score: 0.78,
                risk_level: "high",
                risk_explanation: "Full internal config replacement touching sensitive settings.",
                risk_factors: [
                    { name: "internal_surface", weight: 0.28, description: "Internal administrative route" },
                    { name: "sensitive_fields", weight: 0.31, description: "password, secret, token, api_key" },
                    { name: "config_replacement", weight: 0.19, description: "PUT overwrites service config" },
                ],
                requires_approval: true,
                violated_rules: ["destructive_method", "high_risk_score"],
            },
        ],
    },
    policy_results: [
        {
            operation_key: "/admin/system/users/{userId}.delete",
            requires_approval: true,
            violated_rules: ["destructive_method"],
            messages: ["Approval required for destructive admin deletion"],
        },
        {
            operation_key: "/system/secrets/{secretId}.patch",
            requires_approval: true,
            violated_rules: ["high_risk_score"],
            messages: ["Approval required for secret rotation"],
        },
        {
            operation_key: "/internal/admin/config.put",
            requires_approval: true,
            violated_rules: ["destructive_method", "high_risk_score"],
            messages: ["Approval required for internal config replacement"],
        },
        {
            operation_key: "/public/health.get",
            requires_approval: false,
            violated_rules: [],
            messages: [],
        },
    ],
    test_results: [
        {
            test_id: "delete_user",
            method: "DELETE",
            url: "https://demo.test/admin/system/users/42",
            expected_status: 204,
            is_destructive: true,
            risk_score: 0.92,
            execution: {
                test_id: "delete_user",
                method: "DELETE",
                url: "https://demo.test/admin/system/users/42",
                status_code: 403,
                expected_status: 204,
                passed: false,
                response_time_ms: 133,
                response_headers: { "content-type": "application/json" },
                response_body_preview: '{"error":"forbidden"}',
                error: "approval_required",
                dry_run: false,
            },
            validation: {
                test_id: "delete_user",
                passed: false,
                assertions: [
                    { type: "status_code", expected: 204, actual: 403, passed: false, message: "Status code: expected 204, got 403" },
                    { type: "approval", expected: "approved", actual: "blocked", passed: false, message: "Approval gate blocked destructive admin deletion" },
                ],
                summary: "Forbidden",
            },
        },
        {
            test_id: "rotate_secret",
            method: "PATCH",
            url: "https://demo.test/system/secrets/core",
            expected_status: 200,
            is_destructive: true,
            risk_score: 0.86,
            execution: {
                test_id: "rotate_secret",
                method: "PATCH",
                url: "https://demo.test/system/secrets/core",
                status_code: 500,
                expected_status: 200,
                passed: false,
                response_time_ms: 91,
                response_headers: { "content-type": "application/json" },
                response_body_preview: '{"error":"unexpected"}',
                error: "unexpected_failure",
                dry_run: false,
            },
            validation: {
                test_id: "rotate_secret",
                passed: false,
                assertions: [
                    { type: "status_code", expected: 200, actual: 500, passed: false, message: "Status code: expected 200, got 500" },
                    { type: "response_body", expected: "rotated secret payload", actual: "unexpected server error", passed: false, message: "Unexpected 500 during secret rotation" },
                ],
                summary: "Unexpected 500",
            },
        },
        {
            test_id: "replace_config",
            method: "PUT",
            url: "https://demo.test/internal/admin/config",
            expected_status: 200,
            is_destructive: true,
            risk_score: 0.78,
            execution: {
                test_id: "replace_config",
                method: "PUT",
                url: "https://demo.test/internal/admin/config",
                status_code: 400,
                expected_status: 200,
                passed: false,
                response_time_ms: 77,
                response_headers: { "content-type": "application/json" },
                response_body_preview: '{"error":"invalid payload"}',
                error: "bad_request",
                dry_run: false,
            },
            validation: {
                test_id: "replace_config",
                passed: false,
                assertions: [
                    { type: "status_code", expected: 200, actual: 400, passed: false, message: "Status code: expected 200, got 400" },
                    { type: "request_schema", expected: "valid config payload", actual: "payload rejected", passed: false, message: "Invalid payload rejected by internal config service" },
                ],
                summary: "Unexpected 400",
            },
        },
        {
            test_id: "health_check",
            method: "GET",
            url: "https://demo.test/public/health",
            expected_status: 200,
            is_destructive: false,
            risk_score: 0.12,
            execution: {
                test_id: "health_check",
                method: "GET",
                url: "https://demo.test/public/health",
                status_code: 200,
                expected_status: 200,
                passed: true,
                response_time_ms: 11,
                response_headers: { "content-type": "application/json" },
                response_body_preview: '{"ok":true}',
                error: null,
                dry_run: false,
            },
            validation: {
                test_id: "health_check",
                passed: true,
                assertions: [
                    { type: "status_code", expected: 200, actual: 200, passed: true, message: "Status code: expected 200, got 200" },
                    { type: "response_body", expected: '{"ok":true}', actual: '{"ok":true}', passed: true, message: "Health probe responded with expected payload" },
                ],
                summary: "Healthy",
            },
        },
    ],
    errors: [
        "Approval blocked destructive deletion for /admin/system/users/{userId}.delete",
        "Unexpected 500 from /system/secrets/{secretId}.patch",
        "Unexpected 400 from /internal/admin/config.put",
    ],
    error_details: [
        {
            message: "Approval blocked destructive deletion for /admin/system/users/{userId}.delete",
            severity: "high",
        },
        {
            message: "Unexpected 500 from /system/secrets/{secretId}.patch",
            severity: "high",
        },
        {
            message: "Unexpected 400 from /internal/admin/config.put",
            severity: "medium",
        },
    ],
};

/* ─── Helpers ─── */
const methodColor: Record<string, string> = {
    GET: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    POST: "bg-green-500/20 text-green-400 border-green-500/30",
    PUT: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    PATCH: "bg-orange-500/20 text-orange-400 border-orange-500/30",
    DELETE: "bg-red-500/20 text-red-400 border-red-500/30",
};

function riskColor(score: number) {
    if (score >= 0.7) return "text-red-400";
    if (score >= 0.3) return "text-amber-400";
    return "text-emerald-400";
}

function insightStatusTone(status: "active" | "partial" | "idle") {
    if (status === "active") return "text-emerald-400 border-emerald-500/30 bg-emerald-500/10";
    if (status === "partial") return "text-amber-400 border-amber-500/30 bg-amber-500/10";
    return "text-zinc-400 border-zinc-700 bg-zinc-800/40";
}

function insightStatusLabel(status: "active" | "partial" | "idle") {
    if (status === "active") return "Active";
    if (status === "partial") return "Needs Attention";
    return "Idle";
}

/* ─── Component ─── */
export default function ResultsPage() {
    const [report, setReport] = useState<Report | null>(null);
    const [repoInspection, setRepoInspection] = useState<RepoInspection | null>(null);
    const [apiManifest, setApiManifest] = useState<ApiManifest | null>(null);
    const [executionHistory, setExecutionHistory] = useState<ExecutionHistoryStep[]>([]);
    const [blastRadius, setBlastRadius] = useState<BlastRadiusData | null>(null);
    const [expandedTests, setExpandedTests] = useState<Set<string>>(new Set());

    useEffect(() => {
        // Try to load report from sessionStorage (set by /drop)
        const stored = sessionStorage.getItem("autoapi_report");
        const storedResponse = sessionStorage.getItem("autoapi_response");
        const storedRepoInspection = sessionStorage.getItem("autoapi_repo_inspection");
        const storedApiManifest = sessionStorage.getItem("autoapi_api_manifest");

        if (storedResponse) {
            try {
                const resp = JSON.parse(storedResponse) as StoredPipelineResponse;
                queueMicrotask(() => {
                    setExecutionHistory(resp.execution_history || []);
                    setBlastRadius(resp.blast_radius || null);
                    setRepoInspection(resp.repo_inspection || null);
                    setApiManifest(resp.api_manifest || null);
                });
            } catch {
                console.error("Failed to parse stored response");
            }
        }

        if (storedRepoInspection) {
            try {
                const parsedRepoInspection = JSON.parse(storedRepoInspection) as RepoInspection;
                queueMicrotask(() => setRepoInspection(parsedRepoInspection));
            } catch {
                queueMicrotask(() => setRepoInspection(null));
            }
        }

        if (storedApiManifest) {
            try {
                const parsedApiManifest = JSON.parse(storedApiManifest) as ApiManifest;
                queueMicrotask(() => setApiManifest(parsedApiManifest));
            } catch {
                queueMicrotask(() => setApiManifest(null));
            }
        }

        if (stored) {
            try {
                const parsedReport = JSON.parse(stored) as Report;
                queueMicrotask(() => setReport(parsedReport));
            } catch {
                queueMicrotask(() => setReport(DEMO_REPORT));
            }
        } else {
            queueMicrotask(() => setReport(DEMO_REPORT));
        }
    }, []);

    const toggleTest = (id: string) => {
        setExpandedTests((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    if (!report) {
        return (
            <div className="min-h-screen bg-black flex items-center justify-center">
                <div className="size-8 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    const { summary, risk_distribution, test_results, spec_info } = report;
    const passRate = summary.pass_rate;
    const semanticReplayCount = test_results.filter((t) => t.test_type === "semantic_replay").length;
    const journeyCount = test_results.filter((t) => t.test_type === "stateful_journey").length;
    const fuzzCount = test_results.filter((t) => t.test_type === "fuzzing").length;
    const chaosTotal = report.chaos_summary?.total_injected ?? 0;
    const chaosUndocumented = report.chaos_summary?.undocumented_failures ?? 0;
    const iacChecks = report.iac_validation?.checks?.length ?? 0;
    const iacMissing = report.iac_validation?.missing_controls?.length ?? 0;
    const iacScore = report.iac_validation?.score ?? 0;
    const safeToShip = report.safe_to_ship?.safe_to_ship;
    const safeToShipScore = report.safe_to_ship?.score ?? 0;
    const safeToShipBlockers = report.safe_to_ship?.blockers?.length ?? 0;
    const totalRemediations = report.remediation_summary?.total_remediations ?? 0;
    const prSuggestions = report.remediation_summary?.total_pr_suggestions ?? 0;
    const blastNodes = blastRadius?.nodes?.length ?? 0;
    const blastEdges = blastRadius?.edges?.length ?? 0;
    const rcaFindings = report.rca_summary?.total_findings ?? 0;
    const complianceHealth = report.compliance_scorecard?.overall_compliance_health ?? 0;
    const breakingPredictions = report.breaking_change_summary?.total_predictions ?? 0;
    const likelyBreaking = report.breaking_change_summary?.likely_breaking ?? 0;

    const advancedInsights = [
        {
            name: "Semantic Traffic Replay",
            status: semanticReplayCount > 0 ? "active" as const : "idle" as const,
            detail:
                semanticReplayCount > 0
                    ? `${semanticReplayCount} replay test(s) generated from sanitized traffic`
                    : "No replay samples loaded in this run",
        },
        {
            name: "Stateful User Journey Generator",
            status: journeyCount > 0 ? "active" as const : "idle" as const,
            detail:
                journeyCount > 0
                    ? `${journeyCount} lifecycle journey test(s) chained from endpoint metadata`
                    : "No multi-step resource journey inferred",
        },
        {
            name: "Smart Fuzzing Agent",
            status: fuzzCount > 0 ? "active" as const : "idle" as const,
            detail:
                fuzzCount > 0
                    ? `${fuzzCount} intelligent fuzz test(s) generated from schema`
                    : "No fuzzable request-body operations in this run",
        },
        {
            name: "Chaos Resilience Tester",
            status:
                chaosTotal > 0
                    ? (chaosUndocumented > 0 ? ("partial" as const) : ("active" as const))
                    : ("idle" as const),
            detail:
                chaosTotal > 0
                    ? `${chaosTotal} fault injection(s), ${chaosUndocumented} undocumented failure mode(s)`
                    : "Chaos simulation disabled for this run",
        },
    ];

    const devopsInsights = [
        {
            name: "Infrastructure-as-Contract (IaC) Validator",
            status:
                iacChecks === 0
                    ? ("idle" as const)
                    : report.iac_validation?.passed
                        ? ("active" as const)
                        : ("partial" as const),
            detail:
                iacChecks === 0
                    ? "No IaC sources provided"
                    : `Score ${iacScore.toFixed(1)} with ${iacMissing} missing control(s)`,
        },
        {
            name: "Automatic Mock Server Factory",
            status: spec_info.total_operations > 0 ? ("active" as const) : ("idle" as const),
            detail: `Ready to mock ${spec_info.total_operations} operation(s) from normalized spec`,
        },
        {
            name: "Deployment Safe-to-Ship Gate",
            status:
                safeToShip === undefined
                    ? ("idle" as const)
                    : safeToShip
                        ? ("active" as const)
                        : ("partial" as const),
            detail:
                safeToShip === undefined
                    ? "No deployment gate result in report"
                    : `Gate score ${safeToShipScore.toFixed(1)} with ${safeToShipBlockers} blocker(s)`,
        },
        {
            name: "PR Remediation Bot",
            status:
                prSuggestions > 0
                    ? ("active" as const)
                    : totalRemediations > 0
                        ? ("partial" as const)
                        : ("idle" as const),
            detail:
                prSuggestions > 0
                    ? `${prSuggestions} remediation PR suggestion(s) prepared`
                    : totalRemediations > 0
                        ? `${totalRemediations} remediation(s) generated without PR payload`
                        : "No drift remediation required",
        },
    ];

    const governanceInsights = [
        {
            name: "API Blast Radius Explorer",
            status: blastNodes > 0 ? ("active" as const) : ("idle" as const),
            detail:
                blastNodes > 0
                    ? `${blastNodes} graph node(s), ${blastEdges} dependency edge(s) mapped`
                    : "Blast radius graph unavailable in this run",
        },
        {
            name: "Automated Root Cause Analyst (RCA)",
            status: rcaFindings > 0 ? ("active" as const) : ("idle" as const),
            detail:
                rcaFindings > 0
                    ? `${rcaFindings} failure root-cause finding(s) generated`
                    : "No failed validations requiring RCA",
        },
        {
            name: "Compliance Scorecard",
            status:
                complianceHealth >= 80
                    ? ("active" as const)
                    : complianceHealth > 0
                        ? ("partial" as const)
                        : ("idle" as const),
            detail:
                complianceHealth > 0
                    ? `Compliance health ${complianceHealth.toFixed(1)}%`
                    : "No compliance score available",
        },
        {
            name: "Breaking Change Predictor",
            status:
                breakingPredictions > 0
                    ? (likelyBreaking > 0 ? ("partial" as const) : ("active" as const))
                    : ("idle" as const),
            detail:
                breakingPredictions > 0
                    ? `${breakingPredictions} predicted change(s), ${likelyBreaking} likely breaking`
                    : "No spec-history prediction data in this run",
        },
    ];

    return (
        <div className="min-h-screen bg-black text-white">
            {/* Top bar */}
            <nav className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
                <Link
                    href="/drop"
                    className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors"
                >
                    <ArrowLeft className="size-4" />
                    Back
                </Link>
                <span className="text-xl font-bold tracking-tight inline-flex items-center gap-3">
                    <SentinelLoader size={24} />
                    <span><span className="text-emerald-400">SENTINEL</span>-API</span>
                </span>
                <ReportDownloadMenu
                    report={report}
                    repoInspection={repoInspection}
                    apiManifest={apiManifest}
                />
            </nav>

            <main className="max-w-7xl mx-auto px-6 pb-20">
                {/* Header */}
                <div className="mb-10 animate-fadeIn">
                    <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-3">
                        Analysis{" "}
                        <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                            Results
                        </span>
                    </h1>
                    <p className="text-zinc-400 text-lg">
                        {spec_info.title} v{spec_info.version} ·{" "}
                        {spec_info.total_operations} operations analyzed
                    </p>
                </div>

                {repoInspection && (
                    <div className="mb-8 animate-fadeIn">
                        <RepoInspectionPanel repoInspection={repoInspection} apiManifest={apiManifest} />
                    </div>
                )}

                {/* ─── Summary Cards ─── */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8 animate-fadeIn">
                    {/* Pass Rate */}
                    <Card className="border-zinc-800 bg-zinc-900/60 backdrop-blur-md">
                        <CardContent className="pt-6">
                            <div className="flex items-center gap-3 mb-2">
                                <div className="size-10 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                                    <Activity className="size-5 text-emerald-400" />
                                </div>
                                <p className="text-sm text-zinc-400">Pass Rate</p>
                            </div>
                            <p
                                className={`text-3xl font-bold ${passRate >= 80
                                    ? "text-emerald-400"
                                    : passRate >= 50
                                        ? "text-amber-400"
                                        : "text-red-400"
                                    }`}
                            >
                                {passRate.toFixed(1)}%
                            </p>
                            {/* Mini bar */}
                            <div className="mt-2 h-1.5 w-full rounded-full bg-zinc-800">
                                <div
                                    className={`h-full rounded-full transition-all ${passRate >= 80
                                        ? "bg-emerald-400"
                                        : passRate >= 50
                                            ? "bg-amber-400"
                                            : "bg-red-400"
                                        }`}
                                    style={{ width: `${passRate}%` }}
                                />
                            </div>
                        </CardContent>
                    </Card>

                    {/* Total Tests */}
                    <Card className="border-zinc-800 bg-zinc-900/60 backdrop-blur-md">
                        <CardContent className="pt-6">
                            <div className="flex items-center gap-3 mb-2">
                                <div className="size-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
                                    <BarChart3 className="size-5 text-blue-400" />
                                </div>
                                <p className="text-sm text-zinc-400">Tests</p>
                            </div>
                            <p className="text-3xl font-bold">{summary.total_tests}</p>
                            <p className="text-xs text-zinc-500 mt-1">
                                <span className="text-emerald-400">{summary.execution_passed} passed</span>
                                {summary.execution_failed > 0 && (
                                    <span className="text-red-400"> · {summary.execution_failed} failed</span>
                                )}
                            </p>
                        </CardContent>
                    </Card>

                    {/* Risk Distribution */}
                    <Card className="border-zinc-800 bg-zinc-900/60 backdrop-blur-md">
                        <CardContent className="pt-6">
                            <div className="flex items-center gap-3 mb-2">
                                <div className="size-10 rounded-xl bg-amber-500/10 flex items-center justify-center">
                                    <Shield className="size-5 text-amber-400" />
                                </div>
                                <p className="text-sm text-zinc-400">Risk</p>
                            </div>
                            <div className="flex gap-3 text-sm">
                                <span className="text-red-400 font-semibold">{risk_distribution.high}H</span>
                                <span className="text-amber-400 font-semibold">{risk_distribution.medium}M</span>
                                <span className="text-emerald-400 font-semibold">{risk_distribution.low}L</span>
                            </div>
                            {/* Stacked bar */}
                            <div className="mt-2 h-1.5 w-full rounded-full bg-zinc-800 flex overflow-hidden">
                                {risk_distribution.high > 0 && (
                                    <div
                                        className="h-full bg-red-400"
                                        style={{
                                            width: `${(risk_distribution.high / summary.total_tests) * 100}%`,
                                        }}
                                    />
                                )}
                                {risk_distribution.medium > 0 && (
                                    <div
                                        className="h-full bg-amber-400"
                                        style={{
                                            width: `${(risk_distribution.medium / summary.total_tests) * 100}%`,
                                        }}
                                    />
                                )}
                                {risk_distribution.low > 0 && (
                                    <div
                                        className="h-full bg-emerald-400"
                                        style={{
                                            width: `${(risk_distribution.low / summary.total_tests) * 100}%`,
                                        }}
                                    />
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Errors */}
                    <Card className="border-zinc-800 bg-zinc-900/60 backdrop-blur-md">
                        <CardContent className="pt-6">
                            <div className="flex items-center gap-3 mb-2">
                                <div
                                    className={`size-10 rounded-xl flex items-center justify-center ${summary.errors > 0 ? "bg-red-500/10" : "bg-emerald-500/10"
                                        }`}
                                >
                                    {summary.errors > 0 ? (
                                        <AlertTriangle className="size-5 text-red-400" />
                                    ) : (
                                        <CheckCircle2 className="size-5 text-emerald-400" />
                                    )}
                                </div>
                                <p className="text-sm text-zinc-400">Errors</p>
                            </div>
                            <p
                                className={`text-3xl font-bold ${summary.errors > 0 ? "text-red-400" : "text-emerald-400"
                                    }`}
                            >
                                {summary.errors}
                            </p>
                            <p className="text-xs text-zinc-500 mt-1">
                                {summary.errors === 0 ? "No errors detected" : "Issues found"}
                            </p>
                        </CardContent>
                    </Card>
                </div>

                {/* ─── Visual Analysis Features (F4 & F6) ─── */}
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8 animate-fadeIn">
                    <TimeTravelDebugger history={executionHistory} />
                    <BlastRadiusGraph data={blastRadius} />
                </div>

                <div className="mb-8 animate-fadeIn">
                    <HighRiskOperationsPanel report={report} apiManifest={apiManifest} />
                </div>

                {/* Detailed Insights */}
                <Card className="border-zinc-800 bg-zinc-900/60 backdrop-blur-md mb-8 animate-fadeIn">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Shield className="size-5 text-cyan-400" />
                            Detailed Insights
                        </CardTitle>
                        <CardDescription className="text-zinc-500">
                            Advanced testing, DevOps automation, and governance intelligence coverage
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                        <div className="space-y-3">
                            <h3 className="text-sm font-semibold text-zinc-300 tracking-wide">
                                Advanced Testing & Simulation
                            </h3>
                            {advancedInsights.map((item) => (
                                <div
                                    key={item.name}
                                    className="rounded-lg border border-zinc-800 bg-zinc-800/30 p-3 space-y-2"
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <p className="text-sm font-medium text-zinc-200 leading-tight">
                                            {item.name}
                                        </p>
                                        <Badge
                                            variant="outline"
                                            className={`text-[10px] ${insightStatusTone(item.status)}`}
                                        >
                                            {insightStatusLabel(item.status)}
                                        </Badge>
                                    </div>
                                    <p className="text-xs text-zinc-500 leading-relaxed">{item.detail}</p>
                                </div>
                            ))}
                        </div>

                        <div className="space-y-3">
                            <h3 className="text-sm font-semibold text-zinc-300 tracking-wide">
                                DevOps & Infrastructure
                            </h3>
                            {devopsInsights.map((item) => (
                                <div
                                    key={item.name}
                                    className="rounded-lg border border-zinc-800 bg-zinc-800/30 p-3 space-y-2"
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <p className="text-sm font-medium text-zinc-200 leading-tight">
                                            {item.name}
                                        </p>
                                        <Badge
                                            variant="outline"
                                            className={`text-[10px] ${insightStatusTone(item.status)}`}
                                        >
                                            {insightStatusLabel(item.status)}
                                        </Badge>
                                    </div>
                                    <p className="text-xs text-zinc-500 leading-relaxed">{item.detail}</p>
                                </div>
                            ))}
                        </div>

                        <div className="space-y-3">
                            <h3 className="text-sm font-semibold text-zinc-300 tracking-wide">
                                Intelligence & Governance
                            </h3>
                            {governanceInsights.map((item) => (
                                <div
                                    key={item.name}
                                    className="rounded-lg border border-zinc-800 bg-zinc-800/30 p-3 space-y-2"
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <p className="text-sm font-medium text-zinc-200 leading-tight">
                                            {item.name}
                                        </p>
                                        <Badge
                                            variant="outline"
                                            className={`text-[10px] ${insightStatusTone(item.status)}`}
                                        >
                                            {insightStatusLabel(item.status)}
                                        </Badge>
                                    </div>
                                    <p className="text-xs text-zinc-500 leading-relaxed">{item.detail}</p>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>

                {/* ─── Test Results Table ─── */}
                <Card className="border-zinc-800 bg-zinc-900/60 backdrop-blur-md animate-fadeIn">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <FileJson className="size-5 text-emerald-400" />
                            Test Results
                        </CardTitle>
                        <CardDescription className="text-zinc-500">
                            Detailed results for each endpoint test
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        {test_results.map((t) => {
                            const expanded = expandedTests.has(t.test_id);
                            return (
                                <div
                                    key={t.test_id}
                                    className="rounded-xl border border-zinc-800 bg-zinc-800/30 overflow-hidden"
                                >
                                    {/* Row header */}
                                    <button
                                        onClick={() => toggleTest(t.test_id)}
                                        className="w-full flex items-center gap-3 px-5 py-4 hover:bg-zinc-800/50 transition-colors text-left"
                                    >
                                        {/* Status icon */}
                                        {t.execution.passed && t.validation.passed ? (
                                            <CheckCircle2 className="size-5 text-emerald-400 shrink-0" />
                                        ) : (
                                            <XCircle className="size-5 text-red-400 shrink-0" />
                                        )}


                                        {/* Method badge */}
                                        <Badge
                                            variant="outline"
                                            className={`font-mono text-xs px-2 ${methodColor[t.method] ?? ""
                                                }`}
                                        >
                                            {t.method}
                                        </Badge>

                                        {/* URL */}
                                        <span className="flex-1 font-mono text-sm truncate text-zinc-300">
                                            {t.url}
                                        </span>

                                        {/* Risk */}
                                        <span className={`text-xs font-medium ${riskColor(t.risk_score)}`}>
                                            Risk {(t.risk_score * 10).toFixed(0)}/10
                                        </span>

                                        {/* Response time */}
                                        <span className="text-xs text-zinc-500 flex items-center gap-1">
                                            <Clock className="size-3" />
                                            {t.execution.response_time_ms.toFixed(1)}ms
                                        </span>

                                        {expanded ? (
                                            <ChevronUp className="size-4 text-zinc-500" />
                                        ) : (
                                            <ChevronDown className="size-4 text-zinc-500" />
                                        )}
                                    </button>

                                    {/* Expanded detail */}
                                    {expanded && (
                                        <div className="px-5 pb-5 border-t border-zinc-700/50 pt-4 space-y-4">
                                            {/* Assertions */}
                                            <div>
                                                <p className="text-xs text-zinc-500 font-semibold uppercase tracking-wider mb-2">
                                                    Assertions
                                                </p>
                                                <div className="space-y-1.5">
                                                    {t.validation.assertions.map((a, i) => (
                                                        <div
                                                            key={i}
                                                            className="flex items-center gap-2 text-sm"
                                                        >
                                                            {a.passed ? (
                                                                <CheckCircle2 className="size-3.5 text-emerald-400 shrink-0" />
                                                            ) : (
                                                                <XCircle className="size-3.5 text-red-400 shrink-0" />
                                                            )}
                                                            <span className="text-zinc-400">
                                                                {a.message}
                                                            </span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>

                                            {/* Response preview */}
                                            <div>
                                                <p className="text-xs text-zinc-500 font-semibold uppercase tracking-wider mb-2">
                                                    Response Preview
                                                </p>
                                                <pre className="text-xs bg-black/60 rounded-lg p-3 overflow-x-auto text-zinc-400 font-mono">
                                                    {t.execution.response_body_preview}
                                                </pre>
                                            </div>

                                            {/* Execution info */}
                                            <div className="flex flex-wrap gap-4 text-xs text-zinc-500">
                                                <span>
                                                    Status:{" "}
                                                    <span
                                                        className={
                                                            t.execution.passed
                                                                ? "text-emerald-400"
                                                                : "text-red-400"
                                                        }
                                                    >
                                                        {t.execution.status_code}
                                                    </span>{" "}
                                                    (expected {t.expected_status})
                                                </span>
                                                {t.execution.dry_run && (
                                                    <Badge
                                                        variant="outline"
                                                        className="text-xs border-zinc-700 text-zinc-500"
                                                    >
                                                        Dry Run
                                                    </Badge>
                                                )}
                                                {t.is_destructive && (
                                                    <Badge
                                                        variant="outline"
                                                        className="text-xs border-red-500/30 text-red-400"
                                                    >
                                                        Destructive
                                                    </Badge>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </CardContent>
                </Card>

                {/* ─── Policy Results ─── */}
                {report.policy_results.length > 0 && (
                    <Card className="border-zinc-800 bg-zinc-900/60 backdrop-blur-md mt-6 animate-fadeIn">
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Shield className="size-5 text-amber-400" />
                                Policy Results
                            </CardTitle>
                            <CardDescription className="text-zinc-500">
                                Governance policy checks per operation
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                                {report.policy_results.map((p) => (
                                    <div
                                        key={p.operation_key}
                                        className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-800/30 px-4 py-3"
                                    >
                                        {p.requires_approval ? (
                                            <AlertTriangle className="size-4 text-amber-400 shrink-0" />
                                        ) : (
                                            <CheckCircle2 className="size-4 text-emerald-400 shrink-0" />
                                        )}
                                        <div className="min-w-0">
                                            <p className="text-sm font-mono truncate">
                                                {p.operation_key}
                                            </p>
                                            <p className="text-xs text-zinc-500">
                                                {p.violated_rules.length > 0
                                                    ? `${p.violated_rules.length} violation(s)`
                                                    : "No violations"}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* ─── Download CTA ─── */}
                <div className="flex justify-center mt-10 gap-4">
                    <ReportDownloadMenu
                        report={report}
                        repoInspection={repoInspection}
                        apiManifest={apiManifest}
                    />
                    <Link href="/drop">
                        <Button
                            variant="outline"
                            className="h-12 px-10 rounded-xl border-zinc-700 text-zinc-300 hover:border-emerald-500/50 hover:text-white font-semibold text-base"
                        >
                            Analyze Another File
                        </Button>
                    </Link>
                </div>
            </main>
        </div>
    );
}
