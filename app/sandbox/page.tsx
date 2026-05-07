"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { Activity, FlaskConical, Loader2, Play, RadioTower, RotateCcw, ShieldAlert, type LucideIcon } from "lucide-react";

import { BlastRadiusGraph } from "@/components/BlastRadiusGraph";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const FaultyTerminal = dynamic(() => import("@/components/FaultyTerminal"), { ssr: false });

type SandboxEvent = {
  type: string;
  message: string;
  payload: SandboxPayload;
};

type SandboxPayload = {
  message?: string;
  test_case?: { method?: string; path?: string; url?: string };
  result?: { passed?: boolean; chaos_type?: string };
  [key: string]: unknown;
};

const defaultSpec = JSON.stringify(
  {
    openapi: "3.0.0",
    info: { title: "Sandbox API", version: "1.0" },
    paths: {
      "/api/v1/orders": {
        get: {
          operationId: "getOrders",
          responses: {
            "200": {
              description: "ok",
              content: {
                "application/json": {
                  schema: {
                    type: "object",
                    properties: {
                      id: { type: "integer" },
                      status: { type: "string" },
                    },
                  },
                },
              },
            },
            "503": { description: "service unavailable" },
          },
        },
      },
    },
  },
  null,
  2
);

export default function SandboxPage() {
  const [specText, setSpecText] = useState(defaultSpec);
  const [method, setMethod] = useState("GET");
  const [path, setPath] = useState("/api/v1/orders");
  const [faultRate, setFaultRate] = useState(0.75);
  const [latencyMs, setLatencyMs] = useState(8000);
  const [malformed, setMalformed] = useState("empty_body,wrong_type,oversized_payload");
  const [events, setEvents] = useState<SandboxEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const summary = useMemo(() => {
    const chaos = events.filter((event) => event.type === "chaos");
    return {
      total: events.length,
      chaos: chaos.length,
      failed: chaos.filter((event) => event.payload.result?.passed === false).length,
    };
  }, [events]);

  const blastData = useMemo(
    () => ({
      blast_radius_by_schema: {
        SandboxTarget: [`${method} ${path}`],
        ReplayTraffic: events.filter((event) => event.type === "replay").map((event) => event.payload.test_case?.url ?? path),
        ChaosFaults: events.filter((event) => event.type === "chaos").map((event) => event.payload.result?.chaos_type ?? "fault"),
      },
    }),
    [events, method, path]
  );

  const runSandbox = async () => {
    setRunning(true);
    setError("");
    setEvents([]);
    try {
      const spec = JSON.parse(specText);
      const response = await fetch("/api/v1/sandbox/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          spec_raw: spec,
          target_method: method,
          target_path: path,
          fault_rate: faultRate,
          latency_ms: latencyMs,
          malformed_payload_types: malformed.split(",").map((item) => item.trim()).filter(Boolean),
          traffic_samples: [{ method, path, status_code: 200, headers: { "x-sandbox": "true" } }],
        }),
      });
      if (!response.ok || !response.body) throw new Error(`Sandbox failed (${response.status})`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";
        for (const chunk of chunks) {
          const eventType = chunk.match(/^event: (.+)$/m)?.[1] ?? "message";
          const data = chunk.match(/^data: (.+)$/m)?.[1];
          if (!data) continue;
          const payload = JSON.parse(data);
          setEvents((current) => [...current, { type: eventType, message: payload.message ?? eventType, payload }]);
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Sandbox run failed.");
    } finally {
      setRunning(false);
    }
  };

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="border-b border-zinc-800 bg-zinc-950/95 px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-md bg-red-500/15 text-red-300">
              <ShieldAlert className="size-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold">Blast Radius Sandbox</h1>
              <p className="text-sm text-zinc-500">Replay traffic and inject faults against a target endpoint.</p>
            </div>
          </div>
          <Button onClick={runSandbox} disabled={running || !path.trim()} className="bg-red-500 text-white hover:bg-red-400">
            {running ? <Loader2 className="animate-spin" /> : <Play />}
            Run Sandbox
          </Button>
        </div>
      </div>

      <div className="mx-auto grid max-w-7xl gap-4 px-6 py-6 xl:grid-cols-[420px_minmax(0,1fr)]">
        <section className="space-y-4">
          <Card className="border-zinc-800 bg-zinc-900/60">
            <CardHeader className="border-b border-zinc-800 pb-4">
              <CardTitle className="flex items-center gap-2 text-base"><FlaskConical className="size-4" /> Parameters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 p-5">
              <div className="grid grid-cols-[110px_1fr] gap-3">
                <div className="space-y-2">
                  <Label>Method</Label>
                  <Select value={method} onValueChange={setMethod}>
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {["GET", "POST", "PUT", "PATCH", "DELETE"].map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Target Endpoint</Label>
                  <Input value={path} onChange={(event) => setPath(event.target.value)} />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Fault Injection Rate: {Math.round(faultRate * 100)}%</Label>
                <input className="w-full accent-red-500" type="range" min="0" max="1" step="0.05" value={faultRate} onChange={(event) => setFaultRate(Number(event.target.value))} />
              </div>
              <div className="space-y-2">
                <Label>Latency Spike ms</Label>
                <Input type="number" value={latencyMs} onChange={(event) => setLatencyMs(Number(event.target.value))} />
              </div>
              <div className="space-y-2">
                <Label>Malformed Payload Types</Label>
                <Input value={malformed} onChange={(event) => setMalformed(event.target.value)} />
              </div>
            </CardContent>
          </Card>

          <Card className="border-zinc-800 bg-zinc-900/60">
            <CardHeader className="border-b border-zinc-800 pb-4">
              <CardTitle className="text-base">OpenAPI Spec</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <textarea
                value={specText}
                onChange={(event) => setSpecText(event.target.value)}
                spellCheck={false}
                className="h-[420px] w-full resize-none bg-zinc-950 p-4 font-mono text-xs text-zinc-300 outline-none"
              />
            </CardContent>
          </Card>
        </section>

        <section className="space-y-4">
          <div className="grid gap-3 md:grid-cols-3">
            <Metric icon={Activity} label="Events" value={summary.total} />
            <Metric icon={RadioTower} label="Chaos Findings" value={summary.chaos} />
            <Metric icon={ShieldAlert} label="Undocumented" value={summary.failed} tone="red" />
          </div>

          <Card className="relative h-[360px] overflow-hidden border-zinc-800 bg-black">
            <FaultyTerminal tint="#ff4d4d" scale={1.5} gridMul={[2, 1]} brightness={0.8} className="" style={{}} />
            <div className="absolute inset-0 overflow-auto bg-black/55 p-4 font-mono text-xs">
              {events.length === 0 ? (
                <p className="text-zinc-500">sandbox idle</p>
              ) : (
                events.map((event, index) => (
                  <div key={`${event.type}-${index}`} className="mb-2 flex gap-2">
                    <span className="text-zinc-500">{String(index + 1).padStart(2, "0")}</span>
                    <Badge variant="outline" className="h-5 border-zinc-700 text-[10px] text-zinc-300">{event.type}</Badge>
                    <span className={event.type === "error" ? "text-red-300" : "text-zinc-200"}>{event.message}</span>
                  </div>
                ))
              )}
            </div>
          </Card>

          {error && <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</div>}

          <BlastRadiusGraph data={blastData} />

          <Button variant="outline" onClick={() => setEvents([])} disabled={running}>
            <RotateCcw />
            Clear Output
          </Button>
        </section>
      </div>
    </main>
  );
}

function Metric({ icon: Icon, label, value, tone = "zinc" }: { icon: LucideIcon; label: string; value: number; tone?: "zinc" | "red" }) {
  return (
    <Card className="border-zinc-800 bg-zinc-900/60">
      <CardContent className="flex items-center justify-between p-4">
        <div>
          <p className="text-xs text-zinc-500">{label}</p>
          <p className={`mt-1 text-2xl font-semibold ${tone === "red" ? "text-red-300" : "text-zinc-100"}`}>{value}</p>
        </div>
        <Icon className={tone === "red" ? "size-5 text-red-300" : "size-5 text-zinc-400"} />
      </CardContent>
    </Card>
  );
}
