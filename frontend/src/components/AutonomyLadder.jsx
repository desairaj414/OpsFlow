"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api.js";

const TIER_LABELS = {
  suggest_only: "Suggest only",
  auto_with_approval: "Auto (needs approval)",
  auto_no_approval: "Fully autonomous",
};

// Static status display only — PRD §4.0 trade ledger explicitly cuts a live promotion engine.
// This tab reads backend/guardrails' autonomy_ladder table as-is; it never writes to it.
export default function AutonomyLadder({ apiBase, token }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    apiFetch(apiBase, "/autonomy-ladder", { token })
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
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        Current authority level per runbook. No runbook has been promoted yet in this session.
      </p>
      {error && <p className="text-sm text-red-500">{error}</p>}
      {!data && !error && <p className="text-sm text-muted-foreground">Loading…</p>}
      {data && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                <th className="py-1 pr-4">Runbook</th>
                <th className="py-1 pr-4">Class</th>
                <th className="py-1 pr-4">Tier</th>
                <th className="py-1 pr-4">Verified resolutions</th>
                <th className="py-1 pr-4">Last promoted</th>
              </tr>
            </thead>
            <tbody>
              {data.runbooks.map((r) => (
                <tr key={r.runbook_id} className="border-b border-border/50">
                  <td className="py-1 pr-4 font-mono">{r.runbook_id}</td>
                  <td className="py-1 pr-4">{r.class}</td>
                  <td className="py-1 pr-4">{TIER_LABELS[r.current_tier] ?? r.current_tier}</td>
                  <td className="py-1 pr-4">{r.verified_resolution_count}</td>
                  <td className="py-1 pr-4 text-muted-foreground">{r.last_promoted_at ?? "never"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
