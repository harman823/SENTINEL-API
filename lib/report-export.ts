import type { ApiManifest, HighRiskOperation, RepoInspection, Report } from "@/lib/sentinel-types";

export type ReportExportFormat = "json" | "yaml" | "txt" | "md" | "docx";

type ExportContext = {
  report: Report;
  repoInspection?: RepoInspection | null;
  apiManifest?: ApiManifest | null;
};

function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48) || "sentinel-report";
}

function fileNameBase(report: Report, repoInspection?: RepoInspection | null) {
  const base = repoInspection?.name || report.spec_info.title || "sentinel-report";
  return `${slugify(base)}-${new Date().toISOString().slice(0, 10)}`;
}

function topHighRiskOperations(report: Report, apiManifest?: ApiManifest | null) {
  const fromReport = report.risk_summary?.high_risk_operations ?? [];
  if (fromReport.length > 0) {
    return fromReport.slice(0, 8);
  }
  return (apiManifest?.api_catalog.operations ?? [])
    .filter((item) => item.risk_score >= 0.6)
    .slice(0, 8);
}

function formatRiskItem(item: HighRiskOperation | ApiManifest["api_catalog"]["operations"][number]) {
  return `${item.method ?? "API"} ${item.path ?? item.operation_key} | risk ${(item.risk_score * 10).toFixed(1)}/10 | ${item.risk_level ?? "unknown"}`;
}

function buildTerminalText({ report, repoInspection, apiManifest }: ExportContext) {
  const repoName = repoInspection?.full_name ?? report.spec_info.title;
  const highRisk = topHighRiskOperations(report, apiManifest);
  const errors = report.error_details?.map((item) => item.message) ?? report.errors ?? [];

  const lines = [
    "┌──────────────────────────────────────────────────────────────┐",
    "│ SENTINEL REPORT :: TERMINAL EXPORT                          │",
    "└──────────────────────────────────────────────────────────────┘",
    "",
    `$ repo          : ${repoName}`,
    `$ generated_at  : ${report.generated_at}`,
    `$ spec_title    : ${report.spec_info.title}`,
    `$ spec_version  : ${report.spec_info.version}`,
    `$ operations    : ${report.spec_info.total_operations}`,
    `$ tests         : ${report.summary.total_tests}`,
    `$ pass_rate     : ${report.summary.pass_rate}%`,
    `$ errors        : ${report.summary.errors}`,
    `$ approval_gate : ${report.summary.approval_required ? "REQUIRED" : "CLEAR"}`,
    "",
    "== REPOSITORY ==",
    `name            : ${repoInspection?.full_name ?? "manual upload"}`,
    `source_kind     : ${repoInspection?.selected_source_kind ?? "upload"}`,
    `languages       : ${(repoInspection?.languages ?? []).map((item) => `${item.name} ${item.percent}%`).join(", ") || "n/a"}`,
    `file_formats    : ${(repoInspection?.file_formats ?? []).map((item) => `${item.extension} x${item.count}`).join(", ") || "n/a"}`,
    `frameworks      : ${(repoInspection?.detected_frameworks ?? []).map((item) => `${item.framework} ${item.route_count}`).join(", ") || "n/a"}`,
    "",
    "== RISK HOTSPOTS ==",
    ...(highRisk.length > 0 ? highRisk.map((item) => `- ${formatRiskItem(item)}`) : ["- none"]),
    "",
    "== ERRORS ==",
    ...(errors.length > 0 ? errors.map((item) => `- ${item}`) : ["- none"]),
    "",
    "== TEST SNAPSHOT ==",
    ...report.test_results.slice(0, 12).map((item) => {
      const status = item.execution?.passed && item.validation?.passed ? "PASS" : "FAIL";
      return `- [${status}] ${item.method} ${item.url} (${item.execution?.response_time_ms?.toFixed?.(1) ?? "n/a"}ms)`;
    }),
  ];

  return `${lines.join("\n")}\n`;
}

function buildTerminalMarkdown({ report, repoInspection, apiManifest }: ExportContext) {
  const highRisk = topHighRiskOperations(report, apiManifest);
  const errors = report.error_details?.map((item) => item.message) ?? report.errors ?? [];

  return [
    "# SENTINEL // REPORT EXPORT",
    "",
    "```text",
    `$ repo          : ${repoInspection?.full_name ?? report.spec_info.title}`,
    `$ generated_at  : ${report.generated_at}`,
    `$ pass_rate     : ${report.summary.pass_rate}%`,
    `$ tests         : ${report.summary.total_tests}`,
    `$ errors        : ${report.summary.errors}`,
    "```",
    "",
    "## Repository",
    "",
    "```text",
    `languages    : ${(repoInspection?.languages ?? []).map((item) => `${item.name} ${item.percent}%`).join(", ") || "n/a"}`,
    `file_formats : ${(repoInspection?.file_formats ?? []).map((item) => `${item.extension} x${item.count}`).join(", ") || "n/a"}`,
    `source_kind  : ${repoInspection?.selected_source_kind ?? "upload"}`,
    `selected_api : ${repoInspection?.selected_spec?.path ?? "n/a"}`,
    `frameworks   : ${(repoInspection?.detected_frameworks ?? []).map((item) => `${item.framework} ${item.route_count}`).join(", ") || "n/a"}`,
    "```",
    "",
    "## High-Risk APIs",
    "",
    "```text",
    ...(highRisk.length > 0 ? highRisk.map((item) => formatRiskItem(item)) : ["none"]),
    "```",
    "",
    "## Pipeline Errors",
    "",
    "```text",
    ...(errors.length > 0 ? errors : ["none"]),
    "```",
    "",
    "## Test Snapshot",
    "",
    "```text",
    ...report.test_results.slice(0, 12).map((item) => {
      const status = item.execution?.passed && item.validation?.passed ? "PASS" : "FAIL";
      return `[${status}] ${item.method} ${item.url} :: risk ${(item.risk_score * 10).toFixed(1)}/10`;
    }),
    "```",
    "",
  ].join("\n");
}

async function buildDocxBlob(context: ExportContext) {
  const [{ Document, Packer, Paragraph, TextRun, HeadingLevel, ShadingType, BorderStyle }, yaml] =
    await Promise.all([import("docx"), import("js-yaml")]);

  const highRisk = topHighRiskOperations(context.report, context.apiManifest);
  const errors = context.report.error_details?.map((item) => item.message) ?? context.report.errors ?? [];
  const yamlPreview = yaml.dump(
    {
      repo: context.repoInspection?.full_name ?? context.report.spec_info.title,
      source_kind: context.repoInspection?.selected_source_kind ?? null,
      selected_spec: context.repoInspection?.selected_spec?.path ?? null,
      frameworks: context.repoInspection?.detected_frameworks ?? [],
      top_high_risk: highRisk.slice(0, 3),
    },
    { lineWidth: 80, noRefs: true }
  );

  const mono = "Consolas";
  const makeLine = (text: string, size = 20) =>
    new Paragraph({
      spacing: { after: 80 },
      children: [new TextRun({ text, font: mono, size, color: "E5E7EB" })],
    });

  const doc = new Document({
    sections: [
      {
        properties: {},
        children: [
          new Paragraph({
            heading: HeadingLevel.TITLE,
            shading: { type: ShadingType.CLEAR, color: "auto", fill: "07130E" },
            border: { bottom: { color: "00D084", style: BorderStyle.SINGLE, size: 6 } },
            spacing: { after: 240 },
            children: [
              new TextRun({
                text: "SENTINEL // REPORT EXPORT",
                font: mono,
                size: 30,
                bold: true,
                color: "00D084",
              }),
            ],
          }),
          makeLine(`repo         : ${context.repoInspection?.full_name ?? context.report.spec_info.title}`),
          makeLine(`generated_at : ${context.report.generated_at}`),
          makeLine(`source_kind  : ${context.repoInspection?.selected_source_kind ?? "upload"}`),
          makeLine(`pass_rate    : ${context.report.summary.pass_rate}%`),
          makeLine(`tests        : ${context.report.summary.total_tests}`),
          makeLine(`errors       : ${context.report.summary.errors}`),
          new Paragraph({
            spacing: { before: 180, after: 120 },
            children: [new TextRun({ text: "RISK HOTSPOTS", font: mono, size: 24, bold: true, color: "F59E0B" })],
          }),
          ...(highRisk.length > 0 ? highRisk : [{ operation_key: "none", risk_score: 0, is_destructive: false }]).map((item) =>
            makeLine(
              item.operation_key === "none"
                ? "- none"
                : `- ${formatRiskItem(item)}`,
              18
            )
          ),
          new Paragraph({
            spacing: { before: 180, after: 120 },
            children: [new TextRun({ text: "PIPELINE ERRORS", font: mono, size: 24, bold: true, color: "F87171" })],
          }),
          ...(errors.length > 0 ? errors : ["none"]).map((item) => makeLine(`- ${item}`, 18)),
          new Paragraph({
            spacing: { before: 180, after: 120 },
            children: [new TextRun({ text: "YAML PREVIEW", font: mono, size: 24, bold: true, color: "60A5FA" })],
          }),
          ...yamlPreview.split("\n").map((line) => makeLine(line || " ", 16)),
        ],
      },
    ],
  });

  return Packer.toBlob(doc);
}

function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function downloadReportExport(
  format: ReportExportFormat,
  report: Report,
  repoInspection?: RepoInspection | null,
  apiManifest?: ApiManifest | null
) {
  const context = { report, repoInspection, apiManifest };
  const base = fileNameBase(report, repoInspection);
  const payload = {
    report,
    repo_inspection: repoInspection ?? null,
    api_manifest: apiManifest ?? null,
  };

  if (format === "json") {
    downloadBlob(
      new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }),
      `${base}.json`
    );
    return;
  }

  if (format === "yaml") {
    const yaml = await import("js-yaml");
    downloadBlob(
      new Blob([yaml.dump(payload, { noRefs: true, lineWidth: 120 })], { type: "application/yaml" }),
      `${base}.yaml`
    );
    return;
  }

  if (format === "txt") {
    downloadBlob(new Blob([buildTerminalText(context)], { type: "text/plain;charset=utf-8" }), `${base}.txt`);
    return;
  }

  if (format === "md") {
    downloadBlob(new Blob([buildTerminalMarkdown(context)], { type: "text/markdown;charset=utf-8" }), `${base}.md`);
    return;
  }

  const docxBlob = await buildDocxBlob(context);
  downloadBlob(
    docxBlob,
    `${base}.docx`
  );
}
