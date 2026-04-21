"use client";

import { AlertTriangle, ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ApiManifest, HighRiskOperation, Report } from "@/lib/sentinel-types";

function formatScore(score: number) {
  return `${(score * 10).toFixed(1)}/10`;
}

function scoreTone(score: number) {
  if (score >= 0.8) return "text-red-300 border-red-500/30 bg-red-500/10";
  if (score >= 0.6) return "text-amber-300 border-amber-500/30 bg-amber-500/10";
  return "text-emerald-300 border-emerald-500/30 bg-emerald-500/10";
}

function resolveHighRisk(report: Report, apiManifest?: ApiManifest | null) {
  const fromReport = report.risk_summary?.high_risk_operations ?? [];
  if (fromReport.length > 0) {
    return fromReport;
  }
  return (apiManifest?.api_catalog.operations ?? []).filter((item) => item.risk_score >= 0.6);
}

export function HighRiskOperationsPanel({
  report,
  apiManifest,
}: {
  report: Report;
  apiManifest?: ApiManifest | null;
}) {
  const highRisk = resolveHighRisk(report, apiManifest).slice(0, 8) as HighRiskOperation[];
  const errors = report.error_details?.map((item) => item.message) ?? report.errors ?? [];

  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <Card className="border-red-500/20 bg-zinc-900/60 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-red-300">
            <ShieldAlert className="size-5" />
            High-Risk APIs
          </CardTitle>
          <CardDescription className="text-zinc-500">
            Risk hotspots surfaced from the report and repo manifest
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {highRisk.length === 0 && (
            <div className="rounded-xl border border-zinc-800 bg-black/40 p-4 text-sm text-zinc-500">
              No high-risk APIs were detected in this run.
            </div>
          )}
          {highRisk.map((item) => (
            <div key={item.operation_key} className="rounded-xl border border-zinc-800 bg-black/40 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className="border-zinc-700 text-zinc-200">
                  {item.method ?? "API"}
                </Badge>
                <Badge variant="outline" className={scoreTone(item.risk_score)}>
                  Risk {formatScore(item.risk_score)}
                </Badge>
                {item.is_destructive && (
                  <Badge variant="outline" className="border-red-500/30 bg-red-500/10 text-red-300">
                    Destructive
                  </Badge>
                )}
                {item.requires_approval && (
                  <Badge variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-300">
                    Approval Required
                  </Badge>
                )}
              </div>
              <p className="mt-3 font-mono text-sm text-zinc-100">{item.path ?? item.operation_key}</p>
              {item.summary && <p className="mt-2 text-sm text-zinc-400">{item.summary}</p>}
              {item.risk_explanation && (
                <p className="mt-2 text-sm leading-relaxed text-zinc-500">{item.risk_explanation}</p>
              )}
              {item.risk_factors && item.risk_factors.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {item.risk_factors.slice(0, 4).map((factor, index) => (
                    <Badge
                      key={`${item.operation_key}-${factor.name ?? index}`}
                      variant="outline"
                      className="border-zinc-700 bg-zinc-900/70 text-zinc-400"
                    >
                      {factor.name ?? "factor"}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="border-amber-500/20 bg-zinc-900/60 backdrop-blur-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-amber-300">
            <AlertTriangle className="size-5" />
            Error Terminal
          </CardTitle>
          <CardDescription className="text-zinc-500">
            Pipeline errors are kept explicit so exported reports stay actionable
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-2xl border border-zinc-800 bg-black/70 p-4 font-mono text-sm text-zinc-300">
            <div className="mb-3 text-xs uppercase tracking-[0.28em] text-zinc-500">stderr</div>
            {errors.length === 0 ? (
              <p className="text-emerald-300">[ok] no pipeline errors detected</p>
            ) : (
              <div className="space-y-2">
                {errors.map((item, index) => (
                  <p key={`${item}-${index}`} className="leading-relaxed text-red-300">
                    [err] {item}
                  </p>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
