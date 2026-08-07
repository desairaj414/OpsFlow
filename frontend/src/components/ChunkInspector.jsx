"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

// Browses the real chunked runbook corpus in Chroma (backend/chunking.py output, Phase 1) —
// no embedding call needed, this lists chunks directly rather than semantic-searching them.
export default function ChunkInspector({ apiBase, token }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${apiBase}/chunks`, { headers: { Authorization: `Bearer ${token}` } })
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

  const filtered = data?.chunks.filter(
    (c) => !filter || c.metadata.runbook_id.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="space-y-3">
      {data && (
        <p className="text-xs text-muted-foreground">{data.total} chunks in the runbooks collection.</p>
      )}
      <Input placeholder="Filter by runbook id (e.g. RB-001)" value={filter} onChange={(e) => setFilter(e.target.value)} />
      {error && <p className="text-sm text-red-500">{error}</p>}
      {!data && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

      {data && (
        <div className="flex gap-4">
          <ul className="min-w-0 flex-1 space-y-1">
            {filtered.map((c) => (
              <li key={c.id}>
                <button
                  onClick={() => setSelected(c)}
                  className={cn(
                    "w-full rounded-md border border-border p-2 text-left text-xs hover:bg-secondary",
                    selected?.id === c.id && "bg-secondary font-medium"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono">{c.id}</span>
                    <span className="text-muted-foreground">{c.metadata.class}</span>
                  </div>
                  <p className="text-muted-foreground">{c.metadata.heading_path}</p>
                </button>
              </li>
            ))}
          </ul>
          <div className="min-w-0 flex-1">
            {selected ? (
              <div className="space-y-2 rounded-md border border-border p-3 text-sm">
                <p className="font-mono text-xs text-muted-foreground">{selected.id}</p>
                <p className="text-xs text-muted-foreground">{selected.metadata.heading_path}</p>
                <p className="whitespace-pre-wrap">{selected.document}</p>
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
