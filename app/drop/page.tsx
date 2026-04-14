"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import SentinelLoader from "@/components/SentinelLoader";
import {
    UploadCloud,
    FileJson,
    X,
    ArrowLeft,
    CheckCircle2,
    AlertCircle,
    Loader2,
    Github,
    Brain,
    Shield,
    Bug,
    FileSearch,
    BarChart3,
    Zap,
    Network,
    FlaskConical,
    GitCompare,
    FileCheck,
    Sparkles,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

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

    // Animate dots
    useEffect(() => {
        const iv = setInterval(() => {
            setThinkingDots((d) => (d.length >= 3 ? "" : d + "."));
        }, 400);
        return () => clearInterval(iv);
    }, []);

    // Step progression
    useEffect(() => {
        if (activeStep >= PIPELINE_STEPS.length) {
            onComplete?.();
            return;
        }

        const timer = setTimeout(() => {
            setCompletedSteps((prev) => new Set([...prev, activeStep]));
            setTimeout(() => {
                setActiveStep((s) => s + 1);
            }, 200);
        }, PIPELINE_STEPS[activeStep].duration);

        return () => clearTimeout(timer);
    }, [activeStep, onComplete]);

    return (
        <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-xl flex items-center justify-center">
            <div className="w-full max-w-lg mx-auto px-6">
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="flex justify-center mb-4">
                        <SentinelLoader size={40} />
                    </div>
                    <div className="inline-flex items-center gap-2 mb-3">
                        <span className="text-emerald-400 text-sm font-semibold tracking-widest uppercase">
                            SENTINEL-API Pipeline
                        </span>
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-1">
                        Thinking{thinkingDots}
                    </h2>
                    <p className="text-zinc-500 text-sm">
                        {completedSteps.size} of {PIPELINE_STEPS.length} processes completed
                    </p>
                </div>

                {/* Progress bar */}
                <div className="h-1 bg-zinc-800 rounded-full mb-8 overflow-hidden">
                    <div
                        className="h-full bg-gradient-to-r from-emerald-500 to-cyan-400 rounded-full transition-all duration-500 ease-out"
                        style={{
                            width: `${(completedSteps.size / PIPELINE_STEPS.length) * 100}%`,
                        }}
                    />
                </div>

                {/* Steps */}
                <div className="space-y-1.5 max-h-[50vh] overflow-y-auto pr-2 custom-scrollbar">
                    {PIPELINE_STEPS.map((step, i) => {
                        const isCompleted = completedSteps.has(i);
                        const isActive = activeStep === i && !isCompleted;
                        const isPending = i > activeStep;
                        const Icon = step.icon;

                        return (
                            <div
                                key={step.id}
                                className={`
                                    flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-500
                                    ${isActive ? "bg-emerald-500/10 border border-emerald-500/30 scale-[1.02]" : ""}
                                    ${isCompleted ? "opacity-100" : ""}
                                    ${isPending ? "opacity-30" : ""}
                                `}
                                style={{
                                    animationDelay: `${i * 80}ms`,
                                    animation: isPending ? "none" : "fadeSlideIn 0.3s ease-out forwards",
                                }}
                            >
                                {/* Status icon */}
                                <div className="shrink-0 size-7 rounded-lg flex items-center justify-center">
                                    {isCompleted ? (
                                        <CheckCircle2 className="size-5 text-emerald-400 animate-scaleIn" />
                                    ) : isActive ? (
                                        <Loader2 className="size-5 text-emerald-400 animate-spin" />
                                    ) : (
                                        <div className="size-2 rounded-full bg-zinc-700" />
                                    )}
                                </div>

                                {/* Step icon */}
                                <div
                                    className={`shrink-0 size-8 rounded-lg flex items-center justify-center transition-colors duration-300 ${isCompleted
                                        ? "bg-emerald-500/20 text-emerald-400"
                                        : isActive
                                            ? "bg-emerald-500/15 text-emerald-400"
                                            : "bg-zinc-800/50 text-zinc-600"
                                        }`}
                                >
                                    <Icon className="size-4" />
                                </div>

                                {/* Label */}
                                <span
                                    className={`text-sm font-medium transition-colors duration-300 ${isCompleted
                                        ? "text-zinc-300"
                                        : isActive
                                            ? "text-white"
                                            : "text-zinc-600"
                                        }`}
                                >
                                    {step.label}
                                </span>

                                {/* Completed badge */}
                                {isCompleted && (
                                    <span className="ml-auto text-[10px] text-emerald-500/70 font-mono">
                                        done
                                    </span>
                                )}
                                {isActive && (
                                    <span className="ml-auto text-[10px] text-emerald-400 font-mono animate-pulse">
                                        running
                                    </span>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Inline CSS for custom animations */}
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
    const [isDragOver, setIsDragOver] = useState(false);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [showProgress, setShowProgress] = useState(false);
    const [animationDone, setAnimationDone] = useState(false);
    const [apiDone, setApiDone] = useState(false);
    const [error, setError] = useState("");
    const inputRef = useRef<HTMLInputElement>(null);
    const router = useRouter();

    // Redirect when BOTH animation and API are done
    useEffect(() => {
        if (animationDone && apiDone) {
            router.push("/results");
        }
    }, [animationDone, apiDone, router]);

    const addFiles = useCallback((incoming: FileList | null) => {
        if (!incoming) return;
        const newFiles: UploadedFile[] = Array.from(incoming)
            .filter((f) => /\.(ya?ml|json)$/i.test(f.name))
            .map((f) => ({
                id: crypto.randomUUID(),
                file: f,
                status: "ready" as const,
            }));
        setFiles((prev) => [...prev, ...newFiles]);
    }, []);

    const removeFile = useCallback((id: string) => {
        setFiles((prev) => prev.filter((f) => f.id !== id));
    }, []);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            setIsDragOver(false);
            addFiles(e.dataTransfer.files);
        },
        [addFiles]
    );

    const handleAnalyze = async () => {
        setIsAnalyzing(true);
        setShowProgress(true);
        setAnimationDone(false);
        setApiDone(false);
        setError("");

        try {
            let fetchPromise: Promise<Response>;

            if (githubUrl) {
                if (!githubUrl.startsWith("http")) {
                    throw new Error("Please enter a valid URL starting with http:// or https://");
                }

                fetchPromise = fetch("http://localhost:8000/api/v1/github-run", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ url: githubUrl, approve: true, live: false }),
                });
            } else if (files.length > 0) {
                const formData = new FormData();
                formData.append("file", files[0].file);
                formData.append("approve", "true");
                formData.append("live", "false");

                fetchPromise = fetch("http://localhost:8000/api/v1/upload", {
                    method: "POST",
                    body: formData,
                });
            } else {
                return;
            }

            const res = await fetchPromise!;

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

            sessionStorage.setItem("autoapi_report", JSON.stringify(data.report));
            sessionStorage.setItem("autoapi_response", JSON.stringify(data));
            setApiDone(true);
        } catch (err: any) {
            setError(err.message || "An error occurred during analysis.");
            setIsAnalyzing(false);
            setShowProgress(false);
        }
    };

    const handleProgressComplete = useCallback(() => {
        setAnimationDone(true);
    }, []);

    const readyCount = files.filter((f) => f.status === "ready").length;

    return (
        <div className="min-h-screen bg-black text-white bg-sentinel-pattern">
            {/* Pipeline progress overlay */}
            {showProgress && <PipelineProgress onComplete={handleProgressComplete} />}

            {/* Top bar */}
            <nav className="flex items-center justify-between px-8 py-6 max-w-5xl mx-auto">
                <Link
                    href="/"
                    className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors"
                >
                    <ArrowLeft className="size-4" />
                    Back
                </Link>
                <span className="text-xl font-bold tracking-tight inline-flex items-center gap-3">
                    <SentinelLoader size={24} />
                    <span><span className="text-emerald-400">SENTINEL</span>-API</span>
                </span>
                <div className="w-16" /> {/* spacer */}
            </nav>

            <main className="max-w-3xl mx-auto px-6 pb-20">
                {/* Heading */}
                <div className="text-center mb-10 animate-fadeIn">
                    <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-4">
                        Upload Your{" "}
                        <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                            API Spec
                        </span>
                    </h1>
                    <p className="text-zinc-400 text-lg max-w-lg mx-auto">
                        Drop your OpenAPI specification file below and we&apos;ll run a full
                        AI-driven analysis pipeline on it.
                    </p>
                </div>

                {/* Drop zone */}
                <Card className="border-zinc-800 bg-zinc-900/60 backdrop-blur-md mb-8">
                    <CardContent className="p-0">
                        <div
                            onDragOver={(e) => {
                                e.preventDefault();
                                setIsDragOver(true);
                            }}
                            onDragLeave={() => setIsDragOver(false)}
                            onDrop={handleDrop}
                            onClick={() => inputRef.current?.click()}
                            className={`
                relative flex flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed
                cursor-pointer transition-all duration-300 py-20 px-6 m-6
                ${isDragOver
                                    ? "border-emerald-400 bg-emerald-500/10 scale-[1.01]"
                                    : "border-zinc-700 hover:border-zinc-500 hover:bg-zinc-800/40"
                                }
              `}
                        >
                            <div
                                className={`size-16 rounded-2xl flex items-center justify-center transition-colors ${isDragOver
                                    ? "bg-emerald-500/20 text-emerald-400"
                                    : "bg-zinc-800 text-zinc-400"
                                    }`}
                            >
                                <UploadCloud className="size-8" />
                            </div>
                            <div className="text-center">
                                <p className="font-medium text-lg mb-1">
                                    {isDragOver ? "Drop it here!" : "Drag & drop your file"}
                                </p>
                                <p className="text-sm text-zinc-500">
                                    or click to browse · YAML, YML, JSON
                                </p>
                            </div>
                            <input
                                ref={inputRef}
                                type="file"
                                accept={ACCEPT}
                                multiple
                                className="hidden"
                                onChange={(e) => {
                                    addFiles(e.target.files);
                                    e.target.value = "";
                                }}
                            />
                        </div>
                    </CardContent>
                </Card>

                {/* GitHub URL Input */}
                <div className="flex items-center gap-4 mb-8">
                    <div className="h-px bg-zinc-800 flex-1"></div>
                    <span className="text-zinc-500 text-sm font-medium">OR</span>
                    <div className="h-px bg-zinc-800 flex-1"></div>
                </div>

                <Card className="border-zinc-800 bg-zinc-900/60 backdrop-blur-md mb-8">
                    <CardContent className="p-6">
                        <label className="block text-sm font-medium text-zinc-300 mb-2 flex items-center gap-2">
                            <Github className="size-4" /> Fetch from GitHub URL
                        </label>
                        <Input
                            type="url"
                            value={githubUrl}
                            onChange={(e) => setGithubUrl(e.target.value)}
                            placeholder="https://github.com/user/repo/blob/main/openapi.yaml"
                            className="bg-zinc-800/50 border-zinc-700 text-white placeholder:text-zinc-600 focus:border-emerald-500 focus:ring-emerald-500"
                        />
                    </CardContent>
                </Card>

                {/* File list */}
                {files.length > 0 && (
                    <Card className="border-zinc-800 bg-zinc-900/60 backdrop-blur-md mb-8 animate-fadeIn">
                        <CardHeader>
                            <CardTitle className="text-base">Uploaded Files</CardTitle>
                            <CardDescription className="text-zinc-500">
                                {files.length} file{files.length > 1 ? "s" : ""} selected
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            {files.map((f) => (
                                <div
                                    key={f.id}
                                    className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-800/40 px-4 py-3 group"
                                >
                                    <FileJson className="size-5 text-emerald-400 shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium truncate">
                                            {f.file.name}
                                        </p>
                                        <p className="text-xs text-zinc-500">
                                            {(f.file.size / 1024).toFixed(1)} KB
                                        </p>
                                    </div>
                                    {f.status === "ready" && (
                                        <Badge
                                            variant="outline"
                                            className="text-zinc-400 border-zinc-700"
                                        >
                                            Ready
                                        </Badge>
                                    )}
                                    {f.status === "uploading" && (
                                        <Loader2 className="size-4 text-emerald-400 animate-spin" />
                                    )}
                                    {f.status === "done" && (
                                        <CheckCircle2 className="size-4 text-emerald-400" />
                                    )}
                                    {f.status === "error" && (
                                        <AlertCircle className="size-4 text-red-400" />
                                    )}
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            removeFile(f.id);
                                        }}
                                        className="opacity-0 group-hover:opacity-100 transition-opacity text-zinc-500 hover:text-red-400"
                                    >
                                        <X className="size-4" />
                                    </button>
                                </div>
                            ))}
                        </CardContent>
                    </Card>
                )}

                {error && (
                    <div className="p-4 mb-8 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-center flex items-center justify-center gap-2">
                        <AlertCircle className="size-5" />
                        {error}
                    </div>
                )}

                {/* Analyze button */}
                {(readyCount > 0 || githubUrl.length > 5) && (
                    <div className="flex justify-center animate-fadeIn">
                        <Button
                            onClick={handleAnalyze}
                            disabled={isAnalyzing}
                            className="h-12 px-10 rounded-xl bg-emerald-500 text-black font-semibold text-base hover:bg-emerald-400 transition-all hover:scale-105 shadow-lg shadow-emerald-500/25 disabled:opacity-60 disabled:scale-100"
                        >
                            {isAnalyzing ? (
                                <><Loader2 className="size-5 animate-spin" /> Analyzing...</>
                            ) : (
                                <>Analyze {(readyCount > 0) ? `${readyCount} File${readyCount > 1 ? "s" : ""}` : "URL"} →</>
                            )}
                        </Button>
                    </div>
                )}
            </main>
        </div>
    );
}
