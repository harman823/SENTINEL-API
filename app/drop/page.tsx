"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  BarChart3,
  Brain,
  Bug,
  CheckCircle2,
  FileCheck,
  FileJson,
  FileSearch,
  FlaskConical,
  Github,
  GitCompare,
  Loader2,
  Network,
  Shield,
  Sparkles,
  UploadCloud,
  X,
  Zap,
} from "lucide-react";

import SentinelLoader from "@/components/SentinelLoader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { ApiManifest, RepoInspection } from "@/lib/sentinel-types";

type PipelineResponsePayload = {
  report?: unknown;
  repo_inspection?: RepoInspection;
  api_manifest?: ApiManifest;
  errors?: string[];
};

function messageFromError(err: unknown, fallback: string) {
  return err instanceof Error ? err.message : fallback;
}

interface UploadedFile {
  id: string;
  file: File;
  status: "ready" | "uploading" | "done" | "error";
}

const ACCEPT = ".yaml,.yml,.json";

const PIPELINE_STEPS = [
  { id: "parse", label: "Parsing OpenAPI Spec", icon: FileSearch, duration: 600 },
  { id: "lint", label: "Linting Specification", icon: FileCheck, duration: 500 },
  { id: "normalize", label: "Normalizing Operations", icon: Zap, duration: 400 },
  { id: "risk", label: "Scoring Risk Levels", icon: BarChart3, duration: 500 },
  { id: "policy", label: "Evaluating Policies", icon: Shield, duration: 400 },
  { id: "tests", label: "Generating Test Cases", icon: FlaskConical, duration: 800 },
  { id: "security", label: "Running Security Scan", icon: Bug, duration: 700 },
  { id: "execute", label: "Executing Tests", icon: Sparkles, duration: 600 },
  { id: "validate", label: "Validating Responses", icon: FileCheck, duration: 400 },
  { id: "drift", label: "Detecting Contract Drift", icon: GitCompare, duration: 500 },
  { id: "blast", label: "Mapping Blast Radius", icon: Network, duration: 400 },
  { id: "report", label: "Compiling Report", icon: Brain, duration: 500 },
];

function PipelineProgress({ onComplete }: { onComplete?: () => void }) {
  const [activeStep, setActiveStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [thinkingDots, setThinkingDots] = useState("");

  useEffect(() => {
    const iv = setInterval(() => {
      setThinkingDots((d) => (d.length >= 3 ? "" : `${d}.`));
    }, 400);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    if (activeStep >= PIPELINE_STEPS.length) {
      onComplete?.();
      return;
    }

    const timer = setTimeout(() => {
      setCompletedSteps((prev) => new Set([...prev, activeStep]));
      setTimeout(() => {
        setActiveStep((step) => step + 1);
      }, 200);
    }, PIPELINE_STEPS[activeStep].duration);

    return () => clearTimeout(timer);
  }, [activeStep, onComplete]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-xl">
      <div className="mx-auto w-full max-w-lg px-6">
        <div className="mb-8 text-center">
          <div className="mb-4 flex justify-center">
            <SentinelLoader size={40} />
          </div>
          <div className="mb-3 inline-flex items-center gap-2">
            <span className="text-sm font-semibold uppercase tracking-widest text-emerald-400">
              SENTINEL-API Pipeline
            </span>
          </div>
          <h2 className="mb-1 text-2xl font-bold text-white">Thinking{thinkingDots}</h2>
          <p className="text-sm text-zinc-500">
            {completedSteps.size} of {PIPELINE_STEPS.length} processes completed
          </p>
        </div>

        <div className="mb-8 h-1 overflow-hidden rounded-full bg-zinc-800">
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-400 transition-all duration-500 ease-out"
            style={{ width: `${(completedSteps.size / PIPELINE_STEPS.length) * 100}%` }}
          />
        </div>

        <div className="custom-scrollbar max-h-[50vh] space-y-1.5 overflow-y-auto pr-2">
          {PIPELINE_STEPS.map((step, index) => {
            const isCompleted = completedSteps.has(index);
            const isActive = activeStep === index && !isCompleted;
            const isPending = index > activeStep;
            const Icon = step.icon;

            return (
              <div
                key={step.id}
                className={`flex items-center gap-3 rounded-lg px-4 py-2.5 transition-all duration-500 ${
                  isActive ? "scale-[1.02] border border-emerald-500/30 bg-emerald-500/10" : ""
                } ${isPending ? "opacity-30" : "opacity-100"}`}
                style={{
                  animationDelay: `${index * 80}ms`,
                  animation: isPending ? "none" : "fadeSlideIn 0.3s ease-out forwards",
                }}
              >
                <div className="flex size-7 shrink-0 items-center justify-center rounded-lg">
                  {isCompleted ? (
                    <CheckCircle2 className="animate-scaleIn size-5 text-emerald-400" />
                  ) : isActive ? (
                    <Loader2 className="size-5 animate-spin text-emerald-400" />
                  ) : (
                    <div className="size-2 rounded-full bg-zinc-700" />
                  )}
                </div>

                <div
                  className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-colors duration-300 ${
                    isCompleted
                      ? "bg-emerald-500/20 text-emerald-400"
                      : isActive
                        ? "bg-emerald-500/15 text-emerald-400"
                        : "bg-zinc-800/50 text-zinc-600"
                  }`}
                >
                  <Icon className="size-4" />
                </div>

                <span
                  className={`text-sm font-medium transition-colors duration-300 ${
                    isCompleted ? "text-zinc-300" : isActive ? "text-white" : "text-zinc-600"
                  }`}
                >
                  {step.label}
                </span>

                {isCompleted && <span className="ml-auto font-mono text-[10px] text-emerald-500/70">done</span>}
                {isActive && <span className="ml-auto animate-pulse font-mono text-[10px] text-emerald-400">running</span>}
              </div>
            );
          })}
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeSlideIn {
          from {
            opacity: 0;
            transform: translateY(8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        @keyframes scaleIn {
          from {
            transform: scale(0);
          }
          to {
            transform: scale(1);
          }
        }
        .animate-scaleIn {
          animation: scaleIn 0.3s ease-out;
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #27272a;
          border-radius: 2px;
        }
      `}</style>
    </div>
  );
}

export default function DropPage() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [githubUrl, setGithubUrl] = useState("");
  const [repoInspection, setRepoInspection] = useState<RepoInspection | null>(null);
  const [apiManifest, setApiManifest] = useState<ApiManifest | null>(null);
  const [selectedSpecPath, setSelectedSpecPath] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const [isInspecting, setIsInspecting] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [showProgress, setShowProgress] = useState(false);
  const [animationDone, setAnimationDone] = useState(false);
  const [apiDone, setApiDone] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (animationDone && apiDone) {
      router.push("/results");
    }
  }, [animationDone, apiDone, router]);

  const addFiles = useCallback((incoming: FileList | null) => {
    if (!incoming) return;
    const newFiles: UploadedFile[] = Array.from(incoming)
      .filter((file) => /\.(ya?ml|json)$/i.test(file.name))
      .map((file) => ({
        id: crypto.randomUUID(),
        file,
        status: "ready" as const,
      }));
    setFiles((prev) => [...prev, ...newFiles]);
  }, []);

  const removeFile = useCallback((id: string) => {
    setFiles((prev) => prev.filter((file) => file.id !== id));
  }, []);

  const resetRepoInspection = useCallback(() => {
    setRepoInspection(null);
    setApiManifest(null);
    setSelectedSpecPath("");
  }, []);

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      setIsDragOver(false);
      addFiles(event.dataTransfer.files);
    },
    [addFiles]
  );

  const handleGitHubUrlChange = (value: string) => {
    setGithubUrl(value);
    resetRepoInspection();
  };

  const handleInspectRepo = async () => {
    if (!githubUrl.startsWith("http")) {
      setError("Please enter a valid GitHub repository URL starting with http:// or https://");
      return;
    }

    setIsInspecting(true);
    setError("");

    try {
      const res = await fetch("/api/v1/github-inspect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: githubUrl }),
      });

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `Repository inspection failed (${res.status}).`);
      }

      const data = await res.json();
      setRepoInspection(data.repo_inspection || null);
      setApiManifest(data.api_manifest || null);
      setSelectedSpecPath(data.repo_inspection?.selected_spec?.path || "");
    } catch (err: unknown) {
      setError(messageFromError(err, "Repository inspection failed."));
    } finally {
      setIsInspecting(false);
    }
  };

  const persistResult = (data: PipelineResponsePayload) => {
    sessionStorage.setItem("autoapi_report", JSON.stringify(data.report));
    sessionStorage.setItem("autoapi_response", JSON.stringify(data));

    if (data.repo_inspection) {
      sessionStorage.setItem("autoapi_repo_inspection", JSON.stringify(data.repo_inspection));
    } else {
      sessionStorage.removeItem("autoapi_repo_inspection");
    }

    if (data.api_manifest) {
      sessionStorage.setItem("autoapi_api_manifest", JSON.stringify(data.api_manifest));
    } else {
      sessionStorage.removeItem("autoapi_api_manifest");
    }
  };

  const beginPipeline = () => {
    setIsAnalyzing(true);
    setShowProgress(true);
    setAnimationDone(false);
    setApiDone(false);
    setError("");
  };

  const finishPipelineWithError = (message: string) => {
    setError(message);
    setIsAnalyzing(false);
    setShowProgress(false);
  };

  const handleAnalyze = async () => {
    beginPipeline();

    try {
      let res: Response;

      if (githubUrl.trim()) {
        if (!repoInspection) {
          throw new Error("Inspect the GitHub repository first so you can review the repo details before approval.");
        }

        res = await fetch("/api/v1/github-run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: githubUrl,
            selected_path: selectedSpecPath || repoInspection.selected_spec?.path,
            approve: true,
            live: false,
          }),
        });
      } else if (files.length > 0) {
        const formData = new FormData();
        formData.append("file", files[0].file);
        formData.append("approve", "true");
        formData.append("live", "false");

        res = await fetch("/api/v1/upload", {
          method: "POST",
          body: formData,
        });
      } else {
        throw new Error("Upload a spec file or inspect a GitHub repo first.");
      }

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(
          errBody.detail || `Analysis failed (${res.status}). Check that the input is a valid OpenAPI spec.`
        );
      }

      const data = await res.json();
      if (data.errors && data.errors.length > 0) {
        throw new Error(`Pipeline errors: ${data.errors.join(", ")}`);
      }

      persistResult(data);
      setApiDone(true);
    } catch (err: unknown) {
      finishPipelineWithError(messageFromError(err, "An error occurred during analysis."));
    }
  };

  const handleProgressComplete = useCallback(() => {
    setAnimationDone(true);
  }, []);

  const readyCount = files.filter((file) => file.status === "ready").length;
  const repoOperations = apiManifest?.api_catalog.operations ?? [];
  const isCodeDerivedRepo = repoInspection?.selected_source_kind === "code";
  const operationCount = Math.max(
    apiManifest?.api_catalog.summary.total_operations ?? 0,
    repoInspection?.code_route_count ?? 0,
  );
  const openApiCandidates =
    repoInspection?.candidate_specs.filter(
      (candidate) =>
        candidate.parseable || (!isCodeDerivedRepo && (candidate.candidate_score ?? 0) >= 20)
    ) ?? [];
  const extractedRoutes = apiManifest?.api_catalog.code_analysis?.routes ?? [];

  return (
    <div className="min-h-screen bg-black text-white">
      {showProgress && <PipelineProgress onComplete={handleProgressComplete} />}

      <nav className="mx-auto flex max-w-6xl items-center justify-between px-8 py-6">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-zinc-400 transition-colors hover:text-white"
        >
          <ArrowLeft className="size-4" />
          Back
        </Link>
        <span className="inline-flex items-center gap-3 text-xl font-bold tracking-tight">
          <SentinelLoader size={24} />
          <span>
            <span className="text-emerald-400">SENTINEL</span>-API
          </span>
        </span>
        <div className="w-16" />
      </nav>

      <main className="mx-auto max-w-6xl px-6 pb-20">
        <div className="mb-10 text-center animate-fadeIn">
          <h1 className="mb-4 text-4xl font-bold tracking-tight sm:text-5xl">
            Intake Your{" "}
            <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
              API Surface
            </span>
          </h1>
          <p className="mx-auto max-w-3xl text-lg text-zinc-400">
            Upload a spec directly or inspect a GitHub repository. Repo intake now reads the whole project,
            builds an API manifest, detects framework routes from code, shows languages and file formats, and waits for approval before report generation.
          </p>
        </div>

        <div className="grid gap-8 xl:grid-cols-[0.92fr_1.08fr]">
          <div className="space-y-8">
            <Card className="border-zinc-800 bg-zinc-900/60 backdrop-blur-md">
              <CardContent className="p-0">
                <div
                  onDragOver={(event) => {
                    event.preventDefault();
                    setIsDragOver(true);
                  }}
                  onDragLeave={() => setIsDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => inputRef.current?.click()}
                  className={`relative m-6 flex cursor-pointer flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed px-6 py-20 transition-all duration-300 ${
                    isDragOver
                      ? "scale-[1.01] border-emerald-400 bg-emerald-500/10"
                      : "border-zinc-700 hover:border-zinc-500 hover:bg-zinc-800/40"
                  }`}
                >
                  <div
                    className={`flex size-16 items-center justify-center rounded-2xl transition-colors ${
                      isDragOver ? "bg-emerald-500/20 text-emerald-400" : "bg-zinc-800 text-zinc-400"
                    }`}
                  >
                    <UploadCloud className="size-8" />
                  </div>
                  <div className="text-center">
                    <p className="mb-1 text-lg font-medium">
                      {isDragOver ? "Drop it here!" : "Drag and drop your OpenAPI file"}
                    </p>
                    <p className="text-sm text-zinc-500">Click to browse. Accepted: YAML, YML, JSON.</p>
                  </div>
                  <input
                    ref={inputRef}
                    type="file"
                    accept={ACCEPT}
                    multiple
                    className="hidden"
                    onChange={(event) => {
                      addFiles(event.target.files);
                      event.target.value = "";
                    }}
                  />
                </div>
              </CardContent>
            </Card>

            {files.length > 0 && (
              <Card className="animate-fadeIn border-zinc-800 bg-zinc-900/60 backdrop-blur-md">
                <CardHeader>
                  <CardTitle className="text-base">Uploaded Files</CardTitle>
                  <CardDescription className="text-zinc-500">
                    {files.length} file{files.length > 1 ? "s" : ""} selected
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {files.map((file) => (
                    <div
                      key={file.id}
                      className="group flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-800/40 px-4 py-3"
                    >
                      <FileJson className="size-5 shrink-0 text-emerald-400" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{file.file.name}</p>
                        <p className="text-xs text-zinc-500">{(file.file.size / 1024).toFixed(1)} KB</p>
                      </div>
                      <Badge variant="outline" className="border-zinc-700 text-zinc-400">
                        {file.status}
                      </Badge>
                      <button
                        onClick={(event) => {
                          event.stopPropagation();
                          removeFile(file.id);
                        }}
                        className="text-zinc-500 opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
                      >
                        <X className="size-4" />
                      </button>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {readyCount > 0 && !githubUrl.trim() && (
              <div className="flex justify-center animate-fadeIn">
                <Button
                  onClick={handleAnalyze}
                  disabled={isAnalyzing}
                  className="h-12 rounded-xl bg-emerald-500 px-10 text-base font-semibold text-black shadow-lg shadow-emerald-500/25 transition-all hover:scale-105 hover:bg-emerald-400 disabled:scale-100 disabled:opacity-60"
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="size-5 animate-spin" /> Analyzing...
                    </>
                  ) : (
                    <>Analyze {readyCount} File{readyCount > 1 ? "s" : ""} -&gt;</>
                  )}
                </Button>
              </div>
            )}
          </div>

          <div className="space-y-8">
            <Card className="border-cyan-500/20 bg-zinc-900/60 backdrop-blur-md">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Github className="size-5 text-cyan-400" />
                  GitHub Repo Intake
                </CardTitle>
                <CardDescription className="text-zinc-500">
                  Paste a repository URL. We&apos;ll inspect the whole repo, detect framework code like FastAPI or Flask, build an API manifest, and wait for approval before generating the report.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <Input
                  type="url"
                  value={githubUrl}
                  onChange={(event) => handleGitHubUrlChange(event.target.value)}
                  placeholder="https://github.com/user/repo"
                  className="border-zinc-700 bg-zinc-800/50 text-white placeholder:text-zinc-600 focus:border-emerald-500 focus:ring-emerald-500"
                />

                <div className="flex flex-wrap gap-3">
                  <Button
                    onClick={handleInspectRepo}
                    disabled={isInspecting || githubUrl.trim().length < 10}
                    variant="outline"
                    className="border-cyan-500/30 bg-cyan-500/10 text-cyan-200 hover:bg-cyan-500/20 hover:text-white"
                  >
                    {isInspecting ? (
                      <>
                        <Loader2 className="size-4 animate-spin" /> Inspecting Repo...
                      </>
                    ) : (
                      <>
                        <Github className="size-4" /> Inspect Repository
                      </>
                    )}
                  </Button>

                  <Button
                    onClick={handleAnalyze}
                    disabled={isAnalyzing || !repoInspection}
                    className="bg-emerald-500 text-black hover:bg-emerald-400"
                  >
                    {isAnalyzing ? (
                      <>
                        <Loader2 className="size-4 animate-spin" /> Generating...
                      </>
                    ) : (
                      <>
                        <Brain className="size-4" /> Approve & Generate Report
                      </>
                    )}
                  </Button>
                </div>

                {repoInspection && (
                  <div className="space-y-5 rounded-2xl border border-zinc-800 bg-black/40 p-5">
                    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(320px,360px)]">
                      <div>
                        <p className="text-xs font-mono uppercase tracking-[0.28em] text-zinc-500">repo summary</p>
                        <h3 className="mt-2 text-2xl font-semibold text-zinc-100">{repoInspection.full_name}</h3>
                        <p className="mt-2 text-sm text-zinc-500">{repoInspection.description || "No description provided."}</p>
                        <div className="mt-4 flex flex-wrap gap-2">
                          {repoInspection.languages.map((item) => (
                            <Badge key={item.name} variant="outline" className="border-zinc-700 bg-zinc-900/70 text-zinc-300">
                              {item.name} {item.percent}%
                            </Badge>
                          ))}
                        </div>
                      </div>

                      <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-4">
                        <p className="flex items-center gap-2 text-sm font-medium text-zinc-200">
                          <Shield className="size-4 text-amber-400" />
                          Approval Prompt
                        </p>
                        <p className="mt-3 text-sm leading-relaxed text-zinc-400">{repoInspection.approval_prompt}</p>
                        <div className="mt-4 grid grid-cols-3 gap-3">
                          <div className="rounded-lg border border-zinc-800 bg-black/40 p-3">
                            <p className="text-xs text-zinc-500">Ops</p>
                            <p className="mt-2 text-lg font-semibold text-zinc-100">
                              {operationCount}
                            </p>
                          </div>
                          <div className="rounded-lg border border-zinc-800 bg-black/40 p-3">
                            <p className="text-xs text-zinc-500">High Risk</p>
                            <p className="mt-2 text-lg font-semibold text-amber-300">
                              {apiManifest?.api_catalog.summary.high_risk_operations ?? 0}
                            </p>
                          </div>
                          <div className="rounded-lg border border-zinc-800 bg-black/40 p-3">
                            <p className="text-xs text-zinc-500">Formats</p>
                            <p className="mt-2 text-lg font-semibold text-cyan-300">{repoInspection.file_formats.length}</p>
                          </div>
                        </div>
                        <div className="mt-4 flex flex-wrap gap-2">
                          <Badge variant="outline" className="border-zinc-700 bg-zinc-900/70 text-zinc-300">
                            Source {repoInspection.selected_source_kind === "code" ? "Code-Derived" : repoInspection.selected_source_kind === "hybrid" ? "Hybrid Docs + Code" : "API Docs + Code Scan"}
                          </Badge>
                          {repoInspection.detected_frameworks.map((item) => (
                            <Badge key={item.framework} variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-200">
                              {item.framework} {item.route_count} routes
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="grid gap-5 lg:grid-cols-2">
                      <div>
                        <p className="mb-3 text-xs font-mono uppercase tracking-[0.28em] text-zinc-500">
                          {isCodeDerivedRepo ? "detected framework files" : "openapi candidates"}
                        </p>
                        <div className="space-y-2">
                          {!isCodeDerivedRepo && openApiCandidates.length === 0 && (
                            <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 px-4 py-4 text-sm text-zinc-500">
                              No strong OpenAPI candidate was found. Sentinel will keep using framework code extraction if you continue with this repo.
                            </div>
                          )}
                          {isCodeDerivedRepo &&
                            repoInspection.detected_frameworks.map((framework) => (
                              <div
                                key={framework.framework}
                                className="rounded-xl border border-zinc-800 bg-zinc-950/70 px-4 py-3"
                              >
                                <div className="flex items-center justify-between gap-3">
                                  <p className="truncate font-mono text-sm text-zinc-200">{framework.framework}</p>
                                  <Badge
                                    variant="outline"
                                    className="border-amber-500/30 bg-amber-500/10 text-amber-200"
                                  >
                                    {framework.route_count} routes
                                  </Badge>
                                </div>
                                <p className="mt-2 text-xs text-zinc-500">
                                  {framework.files.slice(0, 2).join(", ")}
                                  {framework.files.length > 2 ? ` +${framework.files.length - 2} more` : ""}
                                </p>
                              </div>
                            ))}
                          {!isCodeDerivedRepo && openApiCandidates.map((candidate) => {
                            const active = selectedSpecPath === candidate.path;
                            return (
                              <button
                                key={candidate.path}
                                type="button"
                                onClick={() => candidate.parseable && setSelectedSpecPath(candidate.path)}
                                className={`w-full rounded-xl border px-4 py-3 text-left transition-colors ${
                                  active
                                    ? "border-emerald-500/40 bg-emerald-500/10"
                                    : "border-zinc-800 bg-zinc-950/70 hover:border-zinc-700"
                                } ${candidate.parseable ? "" : "opacity-60"}`}
                              >
                                <div className="flex items-center justify-between gap-3">
                                  <p className="truncate font-mono text-sm text-zinc-200">{candidate.path}</p>
                                  <Badge
                                    variant="outline"
                                    className={
                                      candidate.parseable
                                        ? "border-emerald-500/30 text-emerald-300"
                                        : "border-red-500/30 text-red-300"
                                    }
                                  >
                                    {candidate.parseable
                                      ? candidate.total_operations > 0
                                        ? `${candidate.total_operations} ops`
                                        : "parsed"
                                      : "invalid"}
                                  </Badge>
                                </div>
                                <p className="mt-2 text-xs text-zinc-500">
                                  {candidate.parseable
                                    ? `${candidate.title || "Unknown"} v${candidate.version || "?"}`
                                    : candidate.errors?.[0] || "Not parseable as supported API docs"}
                                </p>
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      <div>
                        <p className="mb-3 text-xs font-mono uppercase tracking-[0.28em] text-zinc-500">manifest preview</p>
                        <div className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-4">
                          <div className="mb-4 flex flex-wrap gap-2">
                            {repoInspection.file_formats
                              .filter((item) => item.extension !== "[dotfile]")
                              .slice(0, 8)
                              .map((item) => (
                              <Badge key={item.extension} variant="outline" className="border-zinc-700 bg-zinc-900/70 text-zinc-300">
                                {item.extension} x{item.count}
                              </Badge>
                            ))}
                          </div>
                          {apiManifest?.api_catalog.code_analysis && apiManifest.api_catalog.code_analysis.routes.length > 0 && (
                            <div className="mb-4 rounded-xl border border-zinc-800 bg-black/40 p-3">
                              <p className="mb-2 text-xs font-mono uppercase tracking-[0.22em] text-zinc-500">code extraction</p>
                              <div className="flex flex-wrap gap-2">
                                {apiManifest.api_catalog.code_analysis.frameworks.map((item) => (
                                  <Badge key={item.framework} variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-200">
                                    {item.framework} {item.route_count} routes
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          )}
                          {isCodeDerivedRepo && extractedRoutes.length > 0 && (
                            <div className="mb-4 rounded-xl border border-zinc-800 bg-black/40 p-3">
                              <p className="mb-2 text-xs font-mono uppercase tracking-[0.22em] text-zinc-500">sample extracted routes</p>
                              <div className="space-y-2">
                                {extractedRoutes.slice(0, 3).map((route) => (
                                  <div
                                    key={`${route.framework}-${route.method}-${route.path}`}
                                    className="rounded-lg border border-zinc-800 bg-zinc-950/70 px-3 py-2"
                                  >
                                    <div className="flex flex-wrap items-center gap-2">
                                      <Badge variant="outline" className="border-zinc-700 text-zinc-200">
                                        {route.method}
                                      </Badge>
                                      <Badge variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-200">
                                        {route.framework}
                                      </Badge>
                                    </div>
                                    <p className="mt-2 font-mono text-sm text-zinc-100">{route.path}</p>
                                    <p className="mt-1 text-xs text-zinc-500">{route.source_file}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                          <div className="space-y-3">
                            {repoOperations.slice(0, 5).map((operation) => (
                              <div key={operation.operation_key} className="rounded-xl border border-zinc-800 bg-black/40 p-3">
                                <div className="flex flex-wrap items-center gap-2">
                                  <Badge variant="outline" className="border-zinc-700 text-zinc-200">
                                    {operation.method}
                                  </Badge>
                                  <Badge
                                    variant="outline"
                                    className={
                                      operation.risk_score >= 0.8
                                        ? "border-red-500/30 text-red-300"
                                        : operation.risk_score >= 0.6
                                          ? "border-amber-500/30 text-amber-300"
                                          : "border-emerald-500/30 text-emerald-300"
                                    }
                                  >
                                    Risk {(operation.risk_score * 10).toFixed(1)}/10
                                  </Badge>
                                  {operation.is_destructive && (
                                    <Badge variant="outline" className="border-red-500/30 text-red-300">
                                      Destructive
                                    </Badge>
                                  )}
                                </div>
                                <p className="mt-2 font-mono text-sm text-zinc-100">{operation.path}</p>
                                <p className="mt-1 text-xs text-zinc-500">{operation.summary || "No summary provided."}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {error && (
          <div className="mt-8 flex items-center justify-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-center text-red-400">
            <AlertCircle className="size-5" />
            {error}
          </div>
        )}
      </main>
    </div>
  );
}
