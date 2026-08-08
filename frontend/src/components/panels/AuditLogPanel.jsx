"use client";

import { useEffect, useState } from "react";

// Audit Log (approver/admin only, enforced server-side by GET /audit-log): the append-only trail
// of every agent handoff and human decision — audit_log is written to on every real run already,
// this panel is a read view over it, not new data.
export default function AuditLogPanel({ apiBase, token }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${apiBase}/audit-log?limit=50`, { headers: { Authorization: `Bearer ${token}` } });
        if (!res.ok) throw new Error(res.status === 403 ? "Your role cannot view the audit log." : `Request failed (${res.status})`);
        const data = await res.json();
        if (!cancelled) setEntries(data.entries);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [apiBase, token]);

  if (loading) return <p className="text-xs text-muted-foreground">Loading audit log…</p>;
  if (error) return <p className="text-xs text-red-500">{error}</p>;

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        Most recent {entries.length} entries — every agent handoff and human decision, append-only
        (the DB rejects any UPDATE/DELETE on this table).
      </p>
      <div className="max-h-96 space-y-1.5 overflow-y-auto">
        {entries.map((e) => (
          <div key={e.id} className="rounded-md border border-border p-2 text-xs">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">{e.action}</span>
              <span className="text-muted-foreground">{new Date(e.timestamp).toLocaleTimeString()}</span>
            </div>
            <p className="text-muted-foreground">
              actor: {e.actor}
              {e.target_artifact ? ` · ${e.target_artifact}` : ""}
            </p>
            {e.approval_ref && <p className="italic text-muted-foreground">&quot;{e.approval_ref}&quot;</p>}
          </div>
        ))}
        {entries.length === 0 && <p className="text-xs text-muted-foreground">No actions recorded yet this session.</p>}
      </div>
    </div>
  );
}
