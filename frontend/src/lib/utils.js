import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// Shared by every component that reads a workflow run's trace (IncidentWorkspace and its
// approval section, Sidebar's push-to-talk) — avoids three copies of the same one-liner.
export function findTraceEntry(trace, agentName) {
  return trace?.find((e) => e.agent_name === agentName);
}

// Reads the (unencrypted, base64url-encoded) payload of a JWT for display purposes only — this is
// NOT verification, just the same trust level the frontend already has in a token it just received
// from the server. Actual enforcement of role/username always happens server-side (main.py
// require_role), never here.
export function decodeJwtPayload(token) {
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(base64));
  } catch {
    return null;
  }
}
