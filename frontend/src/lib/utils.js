import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// Shared by every component that reads a workflow run's trace (IncidentWorkspace, ApprovalQueue,
// Sidebar's push-to-talk) — avoids three copies of the same one-liner.
export function findTraceEntry(trace, agentName) {
  return trace?.find((e) => e.agent_name === agentName);
}
