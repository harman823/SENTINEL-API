"use client";

import { useState } from "react";
import { ChevronDown, Download, FileJson, FileText, FileType2, FileType } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { downloadReportExport, type ReportExportFormat } from "@/lib/report-export";
import type { ApiManifest, RepoInspection, Report } from "@/lib/sentinel-types";

const FORMATS: Array<{
  format: ReportExportFormat;
  label: string;
  description: string;
  icon: typeof FileJson;
}> = [
  { format: "json", label: "JSON", description: "Structured export", icon: FileJson },
  { format: "yaml", label: "YAML", description: "Readable manifest", icon: FileType2 },
  { format: "txt", label: "TXT", description: "Terminal plain text", icon: FileText },
  { format: "md", label: "Markdown", description: "Terminal-styled markdown", icon: FileType },
  { format: "docx", label: "DOCX", description: "Shareable document", icon: FileText },
];

export function ReportDownloadMenu({
  report,
  repoInspection,
  apiManifest,
}: {
  report: Report;
  repoInspection?: RepoInspection | null;
  apiManifest?: ApiManifest | null;
}) {
  const [isBusy, setIsBusy] = useState(false);

  const handleDownload = async (format: ReportExportFormat) => {
    setIsBusy(true);
    try {
      await downloadReportExport(format, report, repoInspection, apiManifest);
    } finally {
      setIsBusy(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          disabled={isBusy}
          className="gap-2 border-zinc-700 bg-zinc-950/70 text-zinc-300 hover:border-emerald-500/50 hover:text-white"
        >
          <Download className="size-4" />
          {isBusy ? "Preparing Export..." : "Download Report"}
          <ChevronDown className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64 border-zinc-800 bg-zinc-950 text-zinc-200">
        <DropdownMenuLabel className="font-mono text-xs uppercase tracking-[0.28em] text-zinc-500">
          Export Formats
        </DropdownMenuLabel>
        <DropdownMenuSeparator className="bg-zinc-800" />
        {FORMATS.map((item) => {
          const Icon = item.icon;
          return (
            <DropdownMenuItem
              key={item.format}
              className="flex items-start gap-3 rounded-lg px-3 py-3 focus:bg-zinc-900"
              onSelect={() => void handleDownload(item.format)}
            >
              <span className="mt-0.5 rounded-md border border-zinc-800 bg-zinc-900 p-1.5">
                <Icon className="size-4 text-emerald-400" />
              </span>
              <span className="flex flex-col">
                <span className="text-sm font-medium text-zinc-100">{item.label}</span>
                <span className="text-xs text-zinc-500">{item.description}</span>
              </span>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
