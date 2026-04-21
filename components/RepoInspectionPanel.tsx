"use client";

import { Braces, FolderGit2, GitBranch, Globe2, Layers3, Languages, ShieldAlert } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ApiManifest, RepoInspection } from "@/lib/sentinel-types";

export function RepoInspectionPanel({
  repoInspection,
  apiManifest,
}: {
  repoInspection: RepoInspection;
  apiManifest?: ApiManifest | null;
}) {
  const summary = apiManifest?.api_catalog.summary;

  return (
    <Card className="border-cyan-500/20 bg-zinc-950/80 backdrop-blur-md">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-cyan-300">
          <FolderGit2 className="size-5" />
          Repository Intake
        </CardTitle>
        <CardDescription className="text-zinc-500">
          Repo-level metadata, detected formats, frameworks, and the active API source used for analysis
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-2xl border border-zinc-800 bg-black/40 p-4">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-mono uppercase tracking-[0.28em] text-zinc-500">repo</p>
                <p className="mt-1 text-xl font-semibold text-zinc-100">{repoInspection.full_name}</p>
                <p className="mt-2 text-sm text-zinc-500">{repoInspection.description || "No description provided."}</p>
              </div>
              <a
                href={repoInspection.repo_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 rounded-full border border-zinc-800 px-3 py-1 text-xs text-zinc-300 hover:border-cyan-500/40 hover:text-white"
              >
                <Globe2 className="size-3.5" />
                Open Repo
              </a>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-3">
                <p className="text-xs text-zinc-500">Branch</p>
                <p className="mt-2 flex items-center gap-2 text-sm text-zinc-200">
                  <GitBranch className="size-4 text-emerald-400" />
                  {repoInspection.selected_ref}
                </p>
              </div>
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-3">
                <p className="text-xs text-zinc-500">Files</p>
                <p className="mt-2 text-sm text-zinc-200">{repoInspection.total_files.toLocaleString()}</p>
              </div>
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-3">
                <p className="text-xs text-zinc-500">Selected Source</p>
                <p className="mt-2 text-sm text-zinc-200">{repoInspection.selected_spec?.path ?? "n/a"}</p>
                <p className="mt-1 text-xs uppercase tracking-[0.22em] text-zinc-500">
                  {repoInspection.selected_source_kind === "code" ? "code-derived" : "openapi"}
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-zinc-800 bg-gradient-to-b from-cyan-500/10 to-emerald-500/5 p-4">
            <div className="mb-4 flex items-center gap-2 text-sm font-medium text-zinc-200">
              <ShieldAlert className="size-4 text-amber-400" />
              Approval Check
            </div>
            <p className="text-sm leading-relaxed text-zinc-400">{repoInspection.approval_prompt}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-zinc-800 bg-black/40 p-3">
                <p className="text-xs text-zinc-500">Operations</p>
                <p className="mt-2 text-lg font-semibold text-zinc-100">{summary?.total_operations ?? 0}</p>
              </div>
              <div className="rounded-xl border border-zinc-800 bg-black/40 p-3">
                <p className="text-xs text-zinc-500">High Risk</p>
                <p className="mt-2 text-lg font-semibold text-amber-300">{summary?.high_risk_operations ?? 0}</p>
              </div>
              <div className="rounded-xl border border-zinc-800 bg-black/40 p-3">
                <p className="text-xs text-zinc-500">Destructive</p>
                <p className="mt-2 text-lg font-semibold text-red-300">{summary?.destructive_operations ?? 0}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-zinc-800 bg-black/40 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium text-zinc-200">
              <Languages className="size-4 text-cyan-400" />
              Languages
            </div>
            <div className="flex flex-wrap gap-2">
              {repoInspection.languages.map((item) => (
                <Badge key={item.name} variant="outline" className="border-zinc-700 bg-zinc-900/70 text-zinc-300">
                  {item.name} {item.percent}%
                </Badge>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-zinc-800 bg-black/40 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium text-zinc-200">
              <Layers3 className="size-4 text-emerald-400" />
              File Formats
            </div>
            <div className="flex flex-wrap gap-2">
              {repoInspection.file_formats
                .filter((item) => item.extension !== "[dotfile]")
                .slice(0, 8)
                .map((item) => (
                <Badge key={item.extension} variant="outline" className="border-zinc-700 bg-zinc-900/70 text-zinc-300">
                  {item.extension} x{item.count}
                </Badge>
              ))}
            </div>
          </div>
        </div>

        {repoInspection.detected_frameworks.length > 0 && (
          <div className="rounded-2xl border border-zinc-800 bg-black/40 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium text-zinc-200">
              <Braces className="size-4 text-amber-300" />
              Framework Routes
            </div>
            <div className="flex flex-wrap gap-2">
              {repoInspection.detected_frameworks.map((item) => (
                <Badge key={item.framework} variant="outline" className="border-zinc-700 bg-zinc-900/70 text-zinc-300">
                  {item.framework} {item.route_count} routes
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
