"use client";

import { useEffect, useMemo, useState } from "react";
import { Edit3, Loader2, Plus, RefreshCw, Save, ShieldCheck, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type ApiPolicy = {
  id: number;
  name: string;
  category: string;
  rule_type: string;
  severity: string;
  description: string;
  config: Record<string, unknown>;
  enabled: boolean;
};

const emptyPolicy: Omit<ApiPolicy, "id"> = {
  name: "",
  category: "governance",
  rule_type: "required_header",
  severity: "warning",
  description: "",
  config: { header: "x-request-id" },
  enabled: true,
};

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<ApiPolicy[]>([]);
  const [selectedId, setSelectedId] = useState<number | "new">("new");
  const [draft, setDraft] = useState<Omit<ApiPolicy, "id">>(emptyPolicy);
  const [configText, setConfigText] = useState(JSON.stringify(emptyPolicy.config, null, 2));
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const selectedPolicy = useMemo(
    () => policies.find((policy) => policy.id === selectedId),
    [policies, selectedId]
  );

  const loadPolicies = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/v1/policies");
      if (!response.ok) throw new Error(`Failed to load policies (${response.status})`);
      const data = await response.json();
      setPolicies(data.policies ?? []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not load policies.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadPolicies();
  }, []);

  useEffect(() => {
    if (selectedPolicy) {
      const next = {
        name: selectedPolicy.name,
        category: selectedPolicy.category,
        rule_type: selectedPolicy.rule_type,
        severity: selectedPolicy.severity,
        description: selectedPolicy.description,
        config: selectedPolicy.config,
        enabled: selectedPolicy.enabled,
      };
      setDraft(next);
      setConfigText(JSON.stringify(next.config, null, 2));
      return;
    }
    setDraft(emptyPolicy);
    setConfigText(JSON.stringify(emptyPolicy.config, null, 2));
  }, [selectedPolicy]);

  const savePolicy = async () => {
    setSaving(true);
    setError("");
    try {
      const parsedConfig = JSON.parse(configText || "{}");
      const body = { ...draft, config: parsedConfig };
      const response = await fetch(
        selectedId === "new" ? "/api/v1/policies" : `/api/v1/policies/${selectedId}`,
        {
          method: selectedId === "new" ? "POST" : "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      );
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `Save failed (${response.status})`);
      }
      const saved = await response.json();
      await loadPolicies();
      setSelectedId(saved.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not save policy.");
    } finally {
      setSaving(false);
    }
  };

  const deletePolicy = async () => {
    if (selectedId === "new") return;
    setSaving(true);
    setError("");
    try {
      const response = await fetch(`/api/v1/policies/${selectedId}`, { method: "DELETE" });
      if (!response.ok) throw new Error(`Delete failed (${response.status})`);
      setSelectedId("new");
      await loadPolicies();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not delete policy.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="border-b border-zinc-800 bg-zinc-950/95 px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-md bg-emerald-500/15 text-emerald-300">
              <ShieldCheck className="size-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold">API Policies</h1>
              <p className="text-sm text-zinc-500">Central rules used by Sentinel policy evaluation.</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={loadPolicies} disabled={loading}>
              <RefreshCw className={loading ? "animate-spin" : ""} />
              Refresh
            </Button>
            <Button onClick={() => setSelectedId("new")} className="bg-emerald-500 text-black hover:bg-emerald-400">
              <Plus />
              New Policy
            </Button>
          </div>
        </div>
      </div>

      <div className="mx-auto grid max-w-7xl gap-4 px-6 py-6 lg:grid-cols-[420px_minmax(0,1fr)]">
        <Card className="h-fit border-zinc-800 bg-zinc-900/60">
          <CardHeader className="border-b border-zinc-800 pb-4">
            <CardTitle className="text-base">Rules</CardTitle>
          </CardHeader>
          <CardContent className="p-2">
            {loading ? (
              <div className="flex items-center gap-2 px-3 py-4 text-sm text-zinc-500">
                <Loader2 className="size-4 animate-spin" /> Loading policies
              </div>
            ) : policies.length === 0 ? (
              <div className="px-3 py-4 text-sm text-zinc-500">No policies yet.</div>
            ) : (
              <div className="space-y-1">
                {policies.map((policy) => (
                  <button
                    key={policy.id}
                    onClick={() => setSelectedId(policy.id)}
                    className={`w-full rounded-md border px-3 py-3 text-left transition-colors ${
                      selectedId === policy.id
                        ? "border-emerald-500/40 bg-emerald-500/10"
                        : "border-transparent hover:border-zinc-800 hover:bg-zinc-950/60"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="truncate text-sm font-medium">{policy.name}</span>
                      <Badge variant="outline" className={policy.enabled ? "border-emerald-500/30 text-emerald-300" : "border-zinc-700 text-zinc-500"}>
                        {policy.enabled ? "Enabled" : "Paused"}
                      </Badge>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Badge variant="outline" className="border-zinc-700 text-zinc-400">{policy.rule_type}</Badge>
                      <Badge variant="outline" className="border-zinc-700 text-zinc-400">{policy.severity}</Badge>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900/60">
          <CardHeader className="border-b border-zinc-800 pb-4">
            <CardTitle className="flex items-center gap-2 text-base">
              <Edit3 className="size-4 text-emerald-300" />
              {selectedId === "new" ? "Create Policy" : "Edit Policy"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5 p-6">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Category</Label>
                <Input value={draft.category} onChange={(event) => setDraft({ ...draft, category: event.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>Rule Type</Label>
                <Select value={draft.rule_type} onValueChange={(value) => setDraft({ ...draft, rule_type: value })}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="required_header">Required Header</SelectItem>
                    <SelectItem value="auth_required">Auth Required</SelectItem>
                    <SelectItem value="high_risk">High Risk Approval</SelectItem>
                    <SelectItem value="destructive_endpoints">Destructive Endpoint</SelectItem>
                    <SelectItem value="naming_convention">Naming Convention</SelectItem>
                    <SelectItem value="custom">Custom</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Severity</Label>
                <Select value={draft.severity} onValueChange={(value) => setDraft({ ...draft, severity: value })}>
                  <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="info">Info</SelectItem>
                    <SelectItem value="warning">Warning</SelectItem>
                    <SelectItem value="error">Error</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Description</Label>
              <textarea
                value={draft.description}
                onChange={(event) => setDraft({ ...draft, description: event.target.value })}
                className="min-h-20 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm outline-none focus:border-emerald-500"
              />
            </div>

            <div className="space-y-2">
              <Label>Rule Config JSON</Label>
              <textarea
                value={configText}
                onChange={(event) => setConfigText(event.target.value)}
                spellCheck={false}
                className="min-h-44 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 font-mono text-sm outline-none focus:border-emerald-500"
              />
            </div>

            <label className="flex items-center gap-3 text-sm text-zinc-300">
              <input
                type="checkbox"
                checked={draft.enabled}
                onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })}
                className="size-4 accent-emerald-500"
              />
              Enabled for policy evaluation
            </label>

            {error && <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</div>}

            <div className="flex justify-between gap-3 border-t border-zinc-800 pt-5">
              <Button variant="destructive" onClick={deletePolicy} disabled={selectedId === "new" || saving}>
                <Trash2 />
                Delete
              </Button>
              <Button onClick={savePolicy} disabled={saving || !draft.name.trim()} className="bg-emerald-500 text-black hover:bg-emerald-400">
                {saving ? <Loader2 className="animate-spin" /> : <Save />}
                Save Policy
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
