"use client";

import { Fragment, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api.js";

function DriftListItem({ ci, selected, onClick }) {
  return (
    <li>
      <button
        onClick={onClick}
        className={cn(
          "w-full rounded-md border border-border p-2 text-left text-sm hover:bg-secondary",
          selected && "bg-secondary font-medium"
        )}
      >
        <div className="flex items-center justify-between">
          <span>{ci.ci_id}</span>
          <span className="text-xs text-muted-foreground">{Object.keys(ci.diffs).length} field(s)</span>
        </div>
        <p className="text-xs text-muted-foreground">{ci.name}</p>
      </button>
    </li>
  );
}

function SplitScreen({ ci }) {
  if (!ci) {
    return (
      <p className="text-sm text-muted-foreground">Select a CI from the Drift Queue to compare.</p>
    );
  }
  const fields = Object.entries(ci.diffs);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          {ci.ci_id} — Drift vs Truth
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-2 text-sm">
          <span className="font-medium text-xs text-muted-foreground">Field</span>
          <span className="font-medium text-xs text-muted-foreground">Recorded (CMDB)</span>
          <span className="font-medium text-xs text-muted-foreground">Ground Truth</span>
          {fields.map(([field, { recorded, ground_truth }]) => (
            <Fragment key={field}>
              <span className="text-xs">{field}</span>
              <span className="rounded bg-red-600/10 px-2 py-1 text-xs font-mono">{recorded}</span>
              <span className="rounded bg-green-600/10 px-2 py-1 text-xs font-mono">{ground_truth}</span>
            </Fragment>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// Drift Queue + Drift-vs-Truth split screen (PRD §7): recorded CMDB state vs a planted ground
// truth (backend/data_gen/cmdb.py deliberately diverges ~35% of CIs) — a real gap, not simulated.
export default function DriftQueue({ apiBase, token }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let cancelled = false;
    apiFetch(apiBase, "/cmdb/drift", { token })
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
    <div className="space-y-4">
      {data && (
        <div className="rounded-md border border-border p-3">
          <p className="text-2xl font-semibold">{Math.round(data.drift_rate * 100)}%</p>
          <p className="text-xs text-muted-foreground">
            {data.drifted_count} of {data.total_cis} CIs have recorded state that diverges from
            ground truth
          </p>
        </div>
      )}
      {error && <p className="text-sm text-red-500">{error}</p>}
      {!data && !error && <p className="text-sm text-muted-foreground">Loading…</p>}

      {data && (
        <div className="flex gap-4">
          <ul className="min-w-0 flex-1 space-y-2">
            {data.drifted.map((ci) => (
              <DriftListItem
                key={ci.ci_id}
                ci={ci}
                selected={selected?.ci_id === ci.ci_id}
                onClick={() => setSelected(ci)}
              />
            ))}
          </ul>
          <div className="min-w-0 flex-1">
            <SplitScreen ci={selected} />
          </div>
        </div>
      )}
    </div>
  );
}
