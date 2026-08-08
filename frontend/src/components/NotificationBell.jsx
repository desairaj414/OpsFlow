"use client";

import { useEffect, useRef, useState } from "react";
import { Bell } from "lucide-react";
import { cn } from "@/lib/utils";

const STATUS_LABEL = {
  running: "Diagnosing…",
  done: "Done",
  error: "Failed",
};

const STATUS_STYLE = {
  running: "bg-accent-soft text-primary",
  done: "bg-status-good/10 text-status-good",
  error: "bg-status-warning/10 text-status-warning",
};

function formatWhen(iso) {
  const diffMin = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  return new Date(iso).toLocaleTimeString();
}

// Header-level bell — visible from any tab, since auto-diagnosed alerts can happen while you're
// looking at something else entirely. Click a notification to jump straight to its Incident
// Workspace record (same shared `incident.run` state Ops Board's Diagnose button uses).
export default function NotificationBell({ notifications, onOpenNotification }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const unread = notifications.filter((n) => n.status === "running").length;

  useEffect(() => {
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative rounded-md p-2 text-header-foreground/80 hover:bg-secondary/40"
        title="Auto-diagnosed alerts"
      >
        <Bell className="h-4 w-4" />
        {notifications.length > 0 && (
          <span
            className={cn(
              "absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-medium",
              unread > 0 ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground"
            )}
          >
            {notifications.length > 9 ? "9+" : notifications.length}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-20 mt-2 w-80 rounded-lg border border-border bg-card p-2 text-foreground shadow-lg">
          <p className="mb-1.5 px-1 text-xs font-medium text-muted-foreground">
            New alerts auto-diagnosed this session
          </p>
          <div className="max-h-96 space-y-1 overflow-y-auto">
            {notifications.map((n) => (
              <button
                key={n.id}
                onClick={() => {
                  onOpenNotification(n);
                  setOpen(false);
                }}
                disabled={n.status !== "done"}
                className="w-full rounded-md p-2 text-left text-xs hover:bg-secondary disabled:cursor-default disabled:hover:bg-transparent"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{n.ciDisplayName}</span>
                  <span className={cn("shrink-0 rounded-full px-2 py-0.5", STATUS_STYLE[n.status])}>
                    {STATUS_LABEL[n.status]}
                  </span>
                </div>
                <p className="mt-0.5 text-muted-foreground">
                  {n.run ? `${n.run.incident_id} — ${n.run.status}` : "Gathering evidence…"} · {formatWhen(n.createdAt)}
                </p>
              </button>
            ))}
            {notifications.length === 0 && (
              <p className="p-2 text-xs text-muted-foreground">
                Nothing yet — new incoming alerts will diagnose themselves and show up here.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
