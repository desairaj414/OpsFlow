"use client";

import { useRef, useState } from "react";
import { Mic, Radio, Settings, PlayCircle, ScrollText, UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn, findTraceEntry } from "@/lib/utils";

const ROLES = ["Ops Engineer", "Approver", "Admin"];

const NAV_ITEMS = [
  { key: "ingestion", label: "Ingestion / Admin", icon: UploadCloud },
  { key: "config", label: "Model & Threshold Config", icon: Settings },
  { key: "scenarios", label: "Scenario Launcher", icon: PlayCircle },
  { key: "audit", label: "Audit Log", icon: ScrollText },
];

// Every one of the 6 closed-vocabulary voice intents (backend/intake/voice_intent.py) gets an
// honest outcome here — only approve_x/reject_x are actually wired to an action. The other 4 are
// recognized and shown, not silently ignored, but this build has no incidents-list/scenario-library
// endpoint to act on them with.
const ACTIONABLE_INTENTS = new Set(["approve_x", "reject_x"]);

// Global push-to-talk (PRD §7): records via the browser mic, transcribes+parses through the real
// backend pipeline (Whisper -> scrub -> closed-vocabulary intent parser), and requires an explicit
// on-screen confirmation before any side-effecting intent commits — never fires on a raw transcript.
function PushToTalk({ apiBase, token, incident }) {
  const [recording, setRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [signal, setSignal] = useState(null);
  const [error, setError] = useState("");
  const [committed, setCommitted] = useState(null); // "approved" | "rejected"
  const recorderRef = useRef(null);

  async function startRecording() {
    setError("");
    setSignal(null);
    setCommitted(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      const chunks = [];
      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        await submitVoice(blob);
      };
      recorder.start();
      recorderRef.current = recorder;
      setRecording(true);
    } catch (err) {
      setError(`Microphone access failed: ${err.message}`);
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    setRecording(false);
  }

  async function submitVoice(blob) {
    setLoading(true);
    try {
      const ext = blob.type.includes("webm") ? "webm" : blob.type.includes("ogg") ? "ogg" : "wav";
      const form = new FormData();
      form.append("file", blob, `voice.${ext}`);
      const res = await fetch(`${apiBase}/intake/voice`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      setSignal(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const run = incident.run;
  const targetId = signal?.candidate_alert_refs?.[0];
  const targetMatchesPending = run?.status === "pending_approval" && targetId === run.incident_id;

  async function commit() {
    if (!targetMatchesPending) return;
    const decision = signal.parsed_intent === "approve_x" ? "approve" : "reject";
    // MaintenanceSignal doesn't carry the reject intent's captured "reason" group separately
    // (voice_path.py only lifts ci_id/target_id into the signal) — the full transcript already
    // contains it verbatim for a "reject X with reason Y" command, so use that, not a fabricated field.
    const reason = `voice-${decision}d: "${signal.extracted_text}"`;
    try {
      const res = await fetch(`${apiBase}/workflows/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ incident_id: run.incident_id, decision, reason }),
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      setCommitted(decision === "approve" ? "approved" : "rejected");
      if (decision === "approve") {
        const enrichment = findTraceEntry(run.trace, "enrichment");
        const ciId = enrichment?.result?.evidence?.[0]?.artifact_id;
        if (ciId) await incident.triggerRun(ciId, "incident", true);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="space-y-2">
      <Button
        variant="outline"
        className="w-full justify-start gap-2"
        onClick={recording ? stopRecording : startRecording}
        disabled={loading}
      >
        <Mic className={cn("h-4 w-4", recording && "text-red-500")} />
        {recording ? "Stop recording" : loading ? "Transcribing…" : "Push to talk"}
      </Button>
      {error && <p className="text-xs text-red-500">{error}</p>}
      {signal && (
        <div className="space-y-1 rounded-md border border-border p-2 text-xs">
          <p>
            Heard: <span className="italic">&quot;{signal.extracted_text}&quot;</span>
          </p>
          <p>
            Parsed intent: <span className="font-mono">{signal.parsed_intent}</span>
          </p>
          {!committed && ACTIONABLE_INTENTS.has(signal.parsed_intent) && (
            targetMatchesPending ? (
              <Button size="sm" onClick={commit}>
                Confirm {signal.parsed_intent === "approve_x" ? "approval" : "rejection"}
              </Button>
            ) : (
              <p className="text-red-500">
                Target ({targetId ?? "none"}) doesn&apos;t match a pending incident — not acting on it.
              </p>
            )
          )}
          {!committed && signal.parsed_intent !== "unrecognized" && !ACTIONABLE_INTENTS.has(signal.parsed_intent) && (
            <p className="text-muted-foreground">
              Recognized, but not wired to an action in this build (no incidents-list/scenario-library endpoint yet).
            </p>
          )}
          {!committed && signal.parsed_intent === "unrecognized" && (
            <p className="text-red-500">Not recognized as one of the 6 supported commands.</p>
          )}
          {committed && <p className="text-green-600">Committed: {committed}.</p>}
        </div>
      )}
    </div>
  );
}

// Sidebar shell for the cockpit: role switcher, real push-to-talk, and nav into the admin-ish
// side panels. Panel content behind each nav item is built in later steps.
export default function Sidebar({ role, onRoleChange, connectionStatus, apiBase, token, incident }) {
  const [activePanel, setActivePanel] = useState(null);

  return (
    <aside className="flex w-64 shrink-0 flex-col gap-6 overflow-y-auto border-r border-border bg-card p-4">
      <div>
        <label className="mb-1 block text-xs font-medium text-muted-foreground">Role</label>
        <select
          className="w-full rounded-md border border-border bg-background px-2 py-2 text-sm focus:border-accent focus:outline-none"
          value={role}
          onChange={(e) => onRoleChange(e.target.value)}
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2 rounded-md border border-border bg-secondary/50 p-3">
        <Radio
          className={cn(
            "h-4 w-4",
            connectionStatus === "live" ? "text-green-600" : "text-red-500"
          )}
        />
        <span className="text-xs text-muted-foreground">
          Live feed: {connectionStatus === "live" ? "connected" : connectionStatus}
        </span>
      </div>

      <PushToTalk apiBase={apiBase} token={token} incident={incident} />

      <nav className="flex flex-col gap-1">
        {NAV_ITEMS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActivePanel(activePanel === key ? null : key)}
            className={cn(
              "flex items-center gap-2 rounded-md border-l-2 border-transparent px-3 py-2 text-left text-sm text-muted-foreground hover:bg-secondary hover:text-foreground",
              activePanel === key && "border-accent bg-accent-soft font-medium text-foreground"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </nav>

      {activePanel && (
        <p className="rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground">
          {NAV_ITEMS.find((n) => n.key === activePanel)?.label} panel not yet built.
        </p>
      )}
    </aside>
  );
}
