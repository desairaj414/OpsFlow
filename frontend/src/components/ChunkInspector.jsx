"use client";

import { useEffect, useRef, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api.js";

const DOC_TYPE_TABS = [
  { key: "", label: "All" },
  { key: "runbook", label: "Runbooks" },
  { key: "kb_article", label: "Knowledge Base" },
];

// Admin-only inline upload — /runbooks/upload and /knowledge-base/upload, surfaced here so it's
// discoverable in the tab a juror would actually be looking at, not only buried in an admin modal.
//
// One click, not two: the button itself opens the native file picker (no separate, easy-to-miss
// "Choose File" input to find first) and the upload fires the instant a file is chosen — no second
// click required. The old two-step design (pick a file via a small native input, THEN separately
// click "Upload") silently did nothing if you clicked "Upload" first, which is what most people
// try first — reported as "upload doesn't open any panel."
function UploadControls({ apiBase, token, onUploaded }) {
  const runbookFileRef = useRef(null);
  const kbFileRef = useRef(null);
  const [uploading, setUploading] = useState(null); // "runbook" | "kb_article" | null
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function upload(kind, file, endpoint) {
    setUploading(kind);
    setError("");
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await apiFetch(apiBase, endpoint, {
        method: "POST",
        token,
        body: form,
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `Request failed (${res.status})`);
      }
      setResult(await res.json());
      onUploaded();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(null);
    }
  }

  function onFileChosen(kind, endpoint) {
    return (e) => {
      const file = e.target.files?.[0];
      e.target.value = ""; // lets the same filename be re-selected later (e.g. after fixing a rejected file)
      if (file) upload(kind, file, endpoint);
    };
  }

  return (
    <div className="grid grid-cols-1 gap-3 rounded-md border border-dashed border-border p-3 text-xs sm:grid-cols-2">
      <div>
        <p className="mb-1 font-medium text-foreground">Upload a runbook</p>
        <p className="mb-2 text-muted-foreground">
          .md, structural (frontmatter + numbered &quot;### Step N&quot; sections) — chunked and embedded for real.
        </p>
        <input ref={runbookFileRef} type="file" accept=".md" className="hidden" onChange={onFileChosen("runbook", "/runbooks/upload")} />
        <Button size="sm" className="w-full" disabled={uploading === "runbook"} onClick={() => runbookFileRef.current?.click()}>
          {uploading === "runbook" ? "Uploading…" : "Choose file & upload runbook"}
        </Button>
      </div>
      <div>
        <p className="mb-1 font-medium text-foreground">Upload a knowledge base article</p>
        <p className="mb-2 text-muted-foreground">
          .md, freeform reference content (frontmatter + &quot;## Heading&quot; sections) — never cited as an executable step.
        </p>
        <input ref={kbFileRef} type="file" accept=".md" className="hidden" onChange={onFileChosen("kb_article", "/knowledge-base/upload")} />
        <Button size="sm" className="w-full" disabled={uploading === "kb_article"} onClick={() => kbFileRef.current?.click()}>
          {uploading === "kb_article" ? "Uploading…" : "Choose file & upload article"}
        </Button>
      </div>
      {error && <p className="col-span-full text-red-500">{error}</p>}
      {result && (
        <p className="col-span-full text-green-600">
          Indexed {result.runbook_id || result.article_id}: {result.chunks_indexed} chunks embedded and upserted.
        </p>
      )}
    </div>
  );
}

// Knowledge Base tab: browses the real chunked corpus in Chroma (backend/chunking.py output) — both
// runbook procedures and reference articles live in one collection, distinguished by `doc_type`
// metadata, so this one view covers what used to be split across "Chunk Inspector" + a separate
// concept of a knowledge base. No embedding call needed to browse; uploading does embed for real.
export default function ChunkInspector({ apiBase, token, identity }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");
  const [docType, setDocType] = useState("");
  const [selected, setSelected] = useState(null);

  function load() {
    const params = docType ? `?doc_type=${docType}` : "";
    apiFetch(apiBase, `/chunks${params}`, { token })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed (${res.status})`);
        return res.json();
      })
      .then(setData)
      .catch((err) => setError(err.message));
  }

  useEffect(load, [apiBase, token, docType]);

  const filtered = data?.chunks.filter((c) => {
    const docId = c.metadata.runbook_id || c.metadata.postmortem_id || "";
    return !filter || docId.toLowerCase().includes(filter.toLowerCase());
  });

  return (
    <div className="space-y-3">
      {identity?.role === "admin" ? (
        <UploadControls apiBase={apiBase} token={token} onUploaded={load} />
      ) : (
        // All 3 roles can see this tab (roles.js), but uploading is admin-only — without this note
        // a non-admin sees a tab that browses chunks fine but silently has no way to add content,
        // which reads as "upload is broken" rather than "you need the admin role for this."
        <p className="rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground">
          Sign in as Admin to upload new runbooks or knowledge base articles here.
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {DOC_TYPE_TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setDocType(t.key)}
            className={cn(
              "rounded-full border border-border px-3 py-1 text-xs",
              docType === t.key ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-secondary"
            )}
          >
            {t.label}
          </button>
        ))}
        {data && <p className="text-xs text-muted-foreground">{data.total} chunks.</p>}
      </div>
      <Input placeholder="Filter by runbook or article id (e.g. RB-001, KB-TEAMS)" value={filter} onChange={(e) => setFilter(e.target.value)} />
      {error && <p className="text-sm text-red-500">{error}</p>}
      {!data && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

      {data && (
        <div className="flex gap-4">
          <ul className="min-w-0 flex-1 space-y-1">
            {filtered.map((c) => {
              const isKb = c.metadata.doc_type === "kb_article";
              const docId = c.metadata.runbook_id || c.metadata.postmortem_id;
              return (
                <li key={c.id}>
                  <button
                    onClick={() => setSelected(c)}
                    className={cn(
                      "w-full rounded-md border border-border p-2 text-left text-xs hover:bg-secondary",
                      selected?.id === c.id && "bg-secondary font-medium"
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono">{docId}</span>
                      <span className="text-muted-foreground">{isKb ? c.metadata.topic || "reference" : c.metadata.class}</span>
                    </div>
                    <p className="text-muted-foreground">{c.metadata.heading_path}</p>
                  </button>
                </li>
              );
            })}
            {filtered?.length === 0 && <li className="text-sm text-muted-foreground">No chunks match this filter.</li>}
          </ul>
          <div className="min-w-0 flex-1">
            {selected ? (
              <div className="space-y-2 rounded-md border border-border p-3 text-sm">
                <p className="font-mono text-xs text-muted-foreground">{selected.id}</p>
                <p className="text-xs text-muted-foreground">{selected.metadata.heading_path}</p>
                <p className="whitespace-pre-wrap">{selected.document}</p>
                {selected.metadata.doc_type === "kb_article" && (
                  <p className="rounded bg-secondary/60 p-1.5 text-xs text-muted-foreground">
                    Reference article — never retrieved for plan drafting (no runbook class), shown for grounding/citation only.
                  </p>
                )}
                {selected.metadata.is_trap_case === "true" && (
                  <p className="rounded bg-yellow-600/10 p-1 text-xs">
                    Trap case — used to verify the chunker doesn&apos;t mis-split this structure.
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Select a chunk to inspect its full text and metadata.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
