"use client";

import { useEffect, useRef, useState } from "react";
import { MessageCircle, X, Mic, Send, ImagePlus, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api.js";
import { canUseVoice } from "@/lib/providers.js";
import { getProviderMode, INSTANT_DEMO_EXPLANATION } from "@/lib/providerMode.js";

const TICKET_STATUS_LABEL = {
  resolved: "Resolved",
  needs_approval: "Needs approval",
  in_progress: "In progress",
  open: "Open",
};

// Full result table for a query_tickets action — replaces the old truncated "(+N more)" text
// summary so every matching ticket is visible, not just the first 5. Rows open the same Incident
// Workspace view as clicking a row in the Tickets tab (same onOpenTicket path, same trace fetch).
function TicketsTable({ tickets, onOpenTicket }) {
  if (!tickets?.length) return null;
  return (
    <div className="mt-2 max-h-56 overflow-auto rounded-md border border-border">
      <table className="w-full text-left text-xs">
        <thead className="sticky top-0 bg-secondary text-muted-foreground">
          <tr>
            <th className="whitespace-nowrap px-2 py-1 font-medium">Ticket</th>
            <th className="whitespace-nowrap px-2 py-1 font-medium">CI</th>
            <th className="whitespace-nowrap px-2 py-1 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((t) => (
            <tr
              key={t.id}
              className="cursor-pointer border-t border-border hover:bg-secondary/60"
              onClick={() => onOpenTicket?.(t)}
            >
              <td className="whitespace-nowrap px-2 py-1 font-mono">{t.external_id}</td>
              <td className="whitespace-nowrap px-2 py-1">{t.cmdb_ci}</td>
              <td className="whitespace-nowrap px-2 py-1">{TICKET_STATUS_LABEL[t.status_normalized] || t.status_normalized}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Floating assistant — deliberately narrow, not a general chatbot (see main.py's /chat docstring
// for the full reasoning): it only answers from this app's own real ticket data (a deterministic
// DB query the LLM's job is just to build the filters for, never to invent numbers) or a fixed
// description of the app itself, and any approve/reject goes through the exact same audited,
// reason-required, role-gated path Incident Workspace's own approval section uses. Voice input
// (the old Sidebar push-to-talk, moved here) transcribes through the real Whisper+scrub pipeline,
// then the transcript is just handled as a normal chat message — one path, not two parsers. Image
// intake (the old Ops Board drop zone, moved here) is the same /intake/image -> gpt-4o extraction
// -> scrub -> MaintenanceSignal path — one assistant surface carrying every modality, not three.
const GREETING = {
  role: "assistant",
  content:
    "Hi — ask me about tickets/incidents, what a tab or status means, or approve/reject a pending incident by ID. You can also speak (mic) or drop a screenshot (image icon) instead of typing.",
};

export default function ChatWidget({ apiBase, token, incident, onOpenIncident, onOpenTicket }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([GREETING]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [error, setError] = useState("");
  const recorderRef = useRef(null);
  const listRef = useRef(null);
  const imageInputRef = useRef(null);
  // Read once per mount, not per render — the mode only ever changes via a fresh login (page.js
  // reload), never mid-session, so there's no need for this to be reactive state.
  const [mode] = useState(getProviderMode);
  const isInstantDemo = mode.mode === "instant_demo";
  const voiceAvailable = canUseVoice(mode);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, open]);

  async function sendMessage(text) {
    if (isInstantDemo) return;
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    setError("");
    const history = messages.slice(-6).map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    setSending(true);
    try {
      const res = await apiFetch(apiBase, "/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        token,
        body: JSON.stringify({ message: trimmed, history }),
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply, action: data.action }]);
      // A chat-driven approval already updated the shared `run` server-side (a real re-run) — mirror
      // that into the shared incident state so Incident Workspace reflects it if opened, same as
      // any other approval path.
      if (data.action?.type === "approved" && data.action.new_run) {
        incident.setRun(data.action.new_run);
      }
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Something went wrong: ${err.message}` }]);
    } finally {
      setSending(false);
    }
  }

  async function startRecording() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      const chunks = [];
      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
        await transcribeAndSend(blob);
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

  async function transcribeAndSend(blob) {
    setTranscribing(true);
    try {
      const ext = blob.type.includes("webm") ? "webm" : blob.type.includes("ogg") ? "ogg" : "wav";
      const form = new FormData();
      form.append("file", blob, `voice.${ext}`);
      const res = await apiFetch(apiBase, "/intake/voice", {
        method: "POST",
        token,
        body: form,
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      const signal = await res.json();
      // extracted_text is already scrubbed (voice_path.py runs the PII/secret scrubber before this
      // signal is built) — safe to hand straight to the same chat pipeline as typed text.
      await sendMessage(signal.extracted_text || "");
    } catch (err) {
      setError(err.message);
    } finally {
      setTranscribing(false);
    }
  }

  // requires_human_confirmation is unconditional for images (domain-multimodal-intake.md), so this
  // always shows an explicit confirm step — the extraction lands as a chat message with a button,
  // never auto-starts a workflow on its own.
  async function handleImageFile(file) {
    if (!file || !file.type.startsWith("image/")) return;
    setError("");
    const previewUrl = URL.createObjectURL(file);
    setMessages((prev) => [...prev, { role: "user", content: "", image: previewUrl }]);
    setUploadingImage(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await apiFetch(apiBase, "/intake/image", {
        method: "POST",
        token,
        body: form,
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      const signal = await res.json();
      const content = signal.extracted_text
        ? `Extracted: "${signal.extracted_text}"\nCandidate CI: ${signal.candidate_ci_refs?.join(", ") || "none found"}`
        : "Nothing extracted from that image.";
      setMessages((prev) => [...prev, { role: "assistant", content, action: { type: "image_signal", signal } }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Something went wrong: ${err.message}` }]);
    } finally {
      setUploadingImage(false);
    }
  }

  async function confirmImageIncident(msgIndex, signal) {
    const run = await incident.runFromSignal(signal, "incident");
    if (run) {
      setMessages((prev) => prev.map((m, i) => (i === msgIndex ? { ...m, action: { ...m.action, confirmedRun: run } } : m)));
    }
  }

  return (
    <div className="fixed bottom-5 right-5 z-40 flex flex-col items-end gap-3">
      {open && (
        <div className="flex h-[520px] w-96 flex-col overflow-hidden rounded-lg border border-border bg-card shadow-xl">
          <div className="flex shrink-0 items-center justify-between border-b border-border bg-header px-4 py-3 text-header-foreground">
            <div>
              <p className="text-sm font-semibold">Assistant</p>
              <p className="text-xs text-header-foreground/70">Answers grounded in this app&apos;s real data</p>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setMessages([GREETING])}
                aria-label="Restart chat"
                title="Restart chat"
                className="rounded-md p-1 hover:bg-white/10"
              >
                <RotateCcw className="h-4 w-4" />
              </button>
              <button onClick={() => setOpen(false)} aria-label="Close" className="rounded-md p-1 hover:bg-white/10">
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto p-3">
            {messages.map((m, i) => (
              <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                <div
                  className={cn(
                    "rounded-lg px-3 py-2 text-sm",
                    m.action?.type === "query_tickets" ? "w-full" : "max-w-[85%]",
                    m.role === "user" ? "bg-primary text-primary-foreground" : "bg-secondary text-foreground"
                  )}
                >
                  {m.image && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={m.image} alt="Uploaded screenshot" className="max-h-32 rounded-md border border-border" />
                  )}
                  {m.content && <p className="whitespace-pre-wrap">{m.content}</p>}
                  {m.action?.type === "query_tickets" && (
                    <TicketsTable tickets={m.action.tickets} onOpenTicket={onOpenTicket} />
                  )}
                  {m.action?.type === "approved" && m.action.new_run && (
                    <button
                      className="mt-1.5 text-xs underline underline-offset-2"
                      onClick={() => onOpenIncident(m.action.new_run)}
                    >
                      Open Incident Workspace →
                    </button>
                  )}
                  {m.action?.type === "image_signal" && !m.action.confirmedRun && (
                    m.action.signal.candidate_ci_refs?.length > 0 ? (
                      <Button
                        size="sm"
                        className="mt-1.5"
                        onClick={() => confirmImageIncident(i, m.action.signal)}
                        disabled={incident.loading}
                      >
                        {incident.loading ? "Starting…" : "Confirm and start incident"}
                      </Button>
                    ) : (
                      <p className="mt-1 text-xs text-red-500">No CI identifier extracted — cannot start a workflow from this image.</p>
                    )
                  )}
                  {m.action?.type === "image_signal" && m.action.confirmedRun && (
                    <button
                      className="mt-1.5 text-xs underline underline-offset-2"
                      onClick={() => onOpenIncident(m.action.confirmedRun)}
                    >
                      {m.action.confirmedRun.incident_id} started — Open Incident Workspace →
                    </button>
                  )}
                </div>
              </div>
            ))}
            {(sending || uploadingImage) && <p className="text-xs text-muted-foreground">{uploadingImage ? "Extracting…" : "Thinking…"}</p>}
            {error && <p className="text-xs text-red-500">{error}</p>}
          </div>

          <div className="shrink-0 border-t border-border p-2">
            {isInstantDemo ? (
              <p className="px-1 py-2 text-xs leading-relaxed text-muted-foreground">{INSTANT_DEMO_EXPLANATION}</p>
            ) : (
            <div className="flex items-center gap-1.5">
              <input
                ref={imageInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  e.target.value = "";
                  if (file) handleImageFile(file);
                }}
              />
              <button
                onClick={() => imageInputRef.current?.click()}
                disabled={uploadingImage}
                title="Upload a screenshot (e.g. an error dialog citing a CI)"
                className="shrink-0 rounded-md p-2 text-muted-foreground hover:bg-secondary"
              >
                <ImagePlus className="h-4 w-4" />
              </button>
              {voiceAvailable && (
                <button
                  onClick={recording ? stopRecording : startRecording}
                  disabled={transcribing}
                  title={recording ? "Stop recording" : "Speak"}
                  className={cn(
                    "shrink-0 rounded-md p-2 hover:bg-secondary",
                    recording ? "text-red-500" : "text-muted-foreground"
                  )}
                >
                  <Mic className="h-4 w-4" />
                </button>
              )}
              <input
                className="min-w-0 flex-1 rounded-md border border-border bg-background px-2 py-2 text-sm focus:border-accent focus:outline-none"
                placeholder={recording ? "Recording…" : transcribing ? "Transcribing…" : "Ask a question…"}
                value={input}
                disabled={recording || transcribing}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendMessage(input)}
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={sending || !input.trim()}
                title="Send"
                className="shrink-0 rounded-md p-2 text-muted-foreground hover:bg-secondary disabled:opacity-40"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
            )}
            {!isInstantDemo && !voiceAvailable && (
              <p className="mt-1 px-1 text-[11px] text-muted-foreground">
                Voice intake isn&apos;t available on {mode.provider} — switch to a provider that supports transcription (e.g. TCS) to use it.
              </p>
            )}
            {!isInstantDemo && (
            <p className="mt-1 px-1 text-[11px] text-muted-foreground">
              No screenshot handy?{" "}
              <a href="/sample-incident-screenshot.png" download className="underline">
                Download a sample
              </a>{" "}
              citing CI-0056.
            </p>
            )}
          </div>
        </div>
      )}

      <Button
        className="h-12 w-12 rounded-full p-0 shadow-lg"
        onClick={() => setOpen((v) => !v)}
        title="Assistant"
      >
        {open ? <X className="h-5 w-5" /> : <MessageCircle className="h-5 w-5" />}
      </Button>
    </div>
  );
}
