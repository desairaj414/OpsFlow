"use client";

import { useEffect, useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

function AlertFeed({ alerts, connectionStatus }) {
  return (
    <div className="min-w-0 flex-1 space-y-2">
      <p className="text-xs text-muted-foreground">
        Live alert feed — {alerts.length} received this session ({connectionStatus}).
      </p>
      <ul className="space-y-2">
        {alerts.map((alert) => (
          <li key={alert.id} className="rounded-md border border-border p-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="font-medium">{alert.id}</span>
              <span className="text-xs text-muted-foreground">{alert.source}</span>
            </div>
            <p className="mt-1 truncate text-xs text-muted-foreground">{alert.raw_payload}</p>
          </li>
        ))}
        {alerts.length === 0 && (
          <li className="text-sm text-muted-foreground">Waiting for alerts…</li>
        )}
      </ul>
    </div>
  );
}

function CorrelatedCandidates({ apiBase, token }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetch(`${apiBase}/alerts/correlated`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed (${res.status})`);
        return res.json();
      })
      .then((json) => {
        if (!cancelled) setData(json);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [apiBase, token]);

  return (
    <div className="min-w-0 flex-1 space-y-3">
      {data && (
        <div className="rounded-md border border-border p-3">
          <p className="text-2xl font-semibold">{Math.round(data.noise_reduction_ratio * 100)}%</p>
          <p className="text-xs text-muted-foreground">
            noise reduction — {data.total_alerts} alerts → {data.total_clusters} candidate clusters
            (deterministic correlation, no LLM)
          </p>
        </div>
      )}
      {error && <p className="text-sm text-red-500">{error}</p>}
      <ul className="space-y-2">
        {data?.candidates.slice(0, 30).map((c) => (
          <li key={c.cluster_id} className="rounded-md border border-border p-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="font-medium">Cluster {c.cluster_id}</span>
              <span className="text-xs text-muted-foreground">
                {c.alert_count} alert{c.alert_count === 1 ? "" : "s"} · {c.category}
              </span>
            </div>
            <p className="mt-1 truncate text-xs text-muted-foreground">{c.representative_summary}</p>
          </li>
        ))}
        {!data && !error && <li className="text-sm text-muted-foreground">Loading…</li>}
      </ul>
    </div>
  );
}

// Real vision intake: image -> gpt-4o extraction -> scrub -> MaintenanceSignal (backend/intake/
// vision_path.py). requires_human_confirmation is unconditional for images, so this always shows
// an explicit confirm step before anything reaches a workflow (domain-multimodal-intake.md).
function ImageDropZone({ apiBase, token, incident }) {
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState(null);
  const [signal, setSignal] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [confirmedRun, setConfirmedRun] = useState(null);
  const inputRef = useRef(null);

  async function handleFiles(files) {
    const file = files?.[0];
    if (!file || !file.type.startsWith("image/")) return;
    setPreview(URL.createObjectURL(file));
    setSignal(null);
    setConfirmedRun(null);
    setError("");
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${apiBase}/intake/image`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      setSignal(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function confirmAndStart() {
    const run = await incident.runFromSignal(signal, "incident");
    if (run) setConfirmedRun(run);
  }

  return (
    <div className="space-y-2">
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed p-6 text-center text-sm text-muted-foreground",
          dragOver ? "border-primary bg-secondary" : "border-border"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <UploadCloud className="h-6 w-6" />
        <p>Drop a screenshot here, or click to browse (e.g. an error dialog citing a CI)</p>
        <p className="text-xs">
          No screenshot handy?{" "}
          <a href="/sample-incident-screenshot.png" download className="underline" onClick={(e) => e.stopPropagation()}>
            download a sample
          </a>{" "}
          citing CI-0056.
        </p>
        {preview && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={preview} alt="Dropped preview" className="mt-2 max-h-32 rounded-md border border-border" />
        )}
      </div>

      {uploading && <p className="text-sm text-muted-foreground">Extracting…</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}

      {signal && !confirmedRun && (
        <div className="space-y-2 rounded-md border border-border p-3 text-sm">
          <p className="text-xs font-medium text-muted-foreground">Extracted (unconfirmed):</p>
          <p>{signal.extracted_text || "(nothing extracted)"}</p>
          <p className="text-xs text-muted-foreground">
            Candidate CI: {signal.candidate_ci_refs?.join(", ") || "none found"} · signal_id:{" "}
            <span className="font-mono">{signal.signal_id}</span>
          </p>
          {signal.candidate_ci_refs?.length > 0 ? (
            <Button size="sm" onClick={confirmAndStart} disabled={incident.loading}>
              {incident.loading ? "Starting…" : "Confirm and start incident"}
            </Button>
          ) : (
            <p className="text-xs text-red-500">No CI identifier extracted — cannot start a workflow from this image.</p>
          )}
        </div>
      )}

      {confirmedRun && (
        <p className="rounded-md border border-green-600/40 bg-green-600/10 p-2 text-sm">
          Confirmed — {confirmedRun.incident_id} started (modality: image). Check Incident
          Workspace / Agent Trace for the {signal.signal_id}-cited evidence.
        </p>
      )}
    </div>
  );
}

// Ops Board tab: live alert feed + correlated candidates + noise-reduction headline + image drop
// zone (PRD §7). Correlation reuses the tested Phase 2 engine via GET /alerts/correlated. The
// image path shares the CockpitShell's `incident` state, so a confirmed image becomes the active
// golden-path incident, visible from Incident Workspace / Agent Trace too.
export default function OpsBoard({ apiBase, token, alerts, connectionStatus, incident }) {
  return (
    <div className="space-y-4">
      <ImageDropZone apiBase={apiBase} token={token} incident={incident} />
      <div className="flex gap-4">
        <AlertFeed alerts={alerts} connectionStatus={connectionStatus} />
        <CorrelatedCandidates apiBase={apiBase} token={token} />
      </div>
    </div>
  );
}
