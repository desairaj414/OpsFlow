"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

// Model & Threshold Config (admin-only). Policy thresholds are genuinely live-editable — they're
// read by guardrails/policy_gate.py's evaluate_policy() on every call, so a save here changes
// behavior for the very next workflow run, in this process (in-memory, resets on backend restart).
// Model routing is READ-ONLY by design: live-editing which model each agent calls would mean
// touching frozen, tested agent modules (backend/agents/*.py's DIAGNOSIS_MODEL/PLANNER_MODEL
// constants) — shown honestly here rather than faked as editable.
export default function ModelThresholdConfigPanel({ apiBase, token }) {
  const [config, setConfig] = useState(null);
  const [form, setForm] = useState(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [integrations, setIntegrations] = useState(null);
  const [integrationsForm, setIntegrationsForm] = useState(null);
  const [savingIntegrations, setSavingIntegrations] = useState(false);
  const [savedIntegrations, setSavedIntegrations] = useState(false);

  async function load() {
    try {
      const res = await fetch(`${apiBase}/config/thresholds`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error(res.status === 403 ? "Admin role required." : `Request failed (${res.status})`);
      const data = await res.json();
      setConfig(data);
      setForm(data.thresholds);
    } catch (err) {
      setError(err.message);
    }
  }

  async function loadIntegrations() {
    const res = await fetch(`${apiBase}/config/integrations`, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) return;
    const data = await res.json();
    setIntegrations(data);
    setIntegrationsForm({ servicenow_instance_url: data.servicenow_instance_url || "", jira_instance_url: data.jira_instance_url || "" });
  }

  useEffect(() => {
    load();
    loadIntegrations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, token]);

  async function saveIntegrations() {
    setSavingIntegrations(true);
    setSavedIntegrations(false);
    try {
      const res = await fetch(`${apiBase}/config/integrations`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          servicenow_instance_url: integrationsForm.servicenow_instance_url || null,
          jira_instance_url: integrationsForm.jira_instance_url || null,
        }),
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      setIntegrations(await res.json());
      setSavedIntegrations(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingIntegrations(false);
    }
  }

  async function save() {
    setSaving(true);
    setSaved(false);
    try {
      const res = await fetch(`${apiBase}/config/thresholds`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      const data = await res.json();
      setForm(data.thresholds);
      setSaved(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (error) return <p className="text-xs text-red-500">{error}</p>;
  if (!config || !form) return <p className="text-xs text-muted-foreground">Loading…</p>;

  return (
    <div className="space-y-4 text-xs">
      <div>
        <p className="mb-1 font-medium text-foreground">Policy thresholds (live)</p>
        <p className="mb-2 text-muted-foreground">
          Applies immediately to the next run in this session — in-memory only, resets on backend restart.
        </p>
        <div className="space-y-2">
          {Object.entries(form).map(([key, value]) => (
            <label key={key} className="flex items-center justify-between gap-2">
              <span className="text-muted-foreground">{key.replaceAll("_", " ")}</span>
              <input
                type="number"
                className="w-20 rounded-md border border-border bg-background px-2 py-1 text-right focus:border-accent focus:outline-none"
                value={value}
                onChange={(e) => setForm((f) => ({ ...f, [key]: Number(e.target.value) }))}
              />
            </label>
          ))}
        </div>
        <Button size="sm" className="mt-2 w-full" onClick={save} disabled={saving}>
          {saving ? "Saving…" : saved ? "Saved" : "Save thresholds"}
        </Button>
      </div>
      <div>
        <p className="mb-1 font-medium text-foreground">Model routing (read-only)</p>
        <p className="mb-2 text-muted-foreground">{config.note}</p>
        <div className="space-y-1">
          {Object.entries(config.model_routing).map(([role, model]) => (
            <div key={role} className="flex items-center justify-between gap-2 border-t border-border py-1">
              <span className="text-muted-foreground">{role}</span>
              <span className="truncate font-mono" title={model}>{model}</span>
            </div>
          ))}
        </div>
      </div>

      {integrationsForm && (
        <div>
          <p className="mb-1 font-medium text-foreground">ServiceNow / Jira integration</p>
          <p className="mb-2 text-muted-foreground">
            Tickets and knowledge base articles are stored locally, in the same shape a connected
            instance would use. Set an instance URL below to record where a live system would
            connect — once set, the Knowledge Base tab will offer &quot;sync from
            ServiceNow/Jira&quot; alongside manual upload.
            {integrations?.last_synced_at
              ? ` Last synced: ${new Date(integrations.last_synced_at).toLocaleString()}.`
              : " Last synced: never."}
          </p>
          <div className="space-y-2">
            <label className="block">
              <span className="mb-1 block text-muted-foreground">ServiceNow instance URL</span>
              <input
                className="w-full rounded-md border border-border bg-background px-2 py-1 focus:border-accent focus:outline-none"
                placeholder="https://your-instance.service-now.com"
                value={integrationsForm.servicenow_instance_url}
                onChange={(e) => setIntegrationsForm((f) => ({ ...f, servicenow_instance_url: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-muted-foreground">Jira instance URL</span>
              <input
                className="w-full rounded-md border border-border bg-background px-2 py-1 focus:border-accent focus:outline-none"
                placeholder="https://your-domain.atlassian.net"
                value={integrationsForm.jira_instance_url}
                onChange={(e) => setIntegrationsForm((f) => ({ ...f, jira_instance_url: e.target.value }))}
              />
            </label>
          </div>
          <Button size="sm" className="mt-2 w-full" onClick={saveIntegrations} disabled={savingIntegrations}>
            {savingIntegrations ? "Saving…" : savedIntegrations ? "Saved" : "Save instance URLs"}
          </Button>
          <Button size="sm" variant="outline" className="mt-1.5 w-full" disabled title="Connect an instance to enable">
            Sync now (connect an instance to enable)
          </Button>
        </div>
      )}
    </div>
  );
}
