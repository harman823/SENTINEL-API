"use client";

import { useState, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
    UploadCloud,
    FileJson,
    X,
    ArrowLeft,
    CheckCircle2,
    AlertCircle,
    Loader2,
    Github,
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

export default function DropPage() {
    const [files, setFiles] = useState<UploadedFile[]>([]);
    const [githubUrl, setGithubUrl] = useState("");
    const [isDragOver, setIsDragOver] = useState(false);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [error, setError] = useState("");
    const inputRef = useRef<HTMLInputElement>(null);
    const router = useRouter();

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
        setError("");

        try {
            if (githubUrl) {
                // Handle GitHub URL
                const res = await fetch("http://localhost:8000/api/v1/github-run", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ url: githubUrl, approve: true, live: true })
                });

                if (!res.ok) {
                    throw new Error("Failed to analyze GitHub URL");
                }
                const data = await res.json();
                sessionStorage.setItem("autoapi_report", JSON.stringify(data.report));
                router.push("/results");
            } else if (files.length > 0) {
                // Handle File Upload
                const formData = new FormData();
                formData.append("file", files[0].file);
                formData.append("approve", "true");
                formData.append("live", "true");

                const res = await fetch("http://localhost:8000/api/v1/upload", {
                    method: "POST",
                    body: formData
                });

                if (!res.ok) {
                    throw new Error("Failed to upload and analyze file");
                }
                const data = await res.json();
                sessionStorage.setItem("autoapi_report", JSON.stringify(data.report));
                router.push("/results");
            }
        } catch (err: any) {
            setError(err.message || "An error occurred during analysis.");
            setIsAnalyzing(false);
        }
    };

    const readyCount = files.filter((f) => f.status === "ready").length;

    return (
        <div className="min-h-screen bg-black text-white">
            {/* Top bar */}
            <nav className="flex items-center justify-between px-8 py-6 max-w-5xl mx-auto">
                <Link
                    href="/"
                    className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors"
                >
                    <ArrowLeft className="size-4" />
                    Back
                </Link>
                <span className="text-xl font-bold tracking-tight">
                    <span className="text-emerald-400">Auto</span>API
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
