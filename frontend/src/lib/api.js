// Thin fetch wrapper — every API call in this app should go through apiFetch() instead of raw
// fetch(), so the active LLM-provider mode (Instant Demo / Bring Your Own Key / Free Demo Key,
// chosen on the login screen — see LoginModeSelector.jsx and providerMode.js) reaches the backend
// on every request as headers, without threading it through every component's props.
//
// backend/provider_context.py reads these same two header names to resolve which provider (or
// Instant Demo's pregenerated-output short-circuit) a request should use.
import { getProviderMode } from "@/lib/providerMode.js";

export function apiFetch(apiBase, path, { token, headers, ...rest } = {}) {
  const mode = getProviderMode();
  const mergedHeaders = { ...headers };
  if (token) mergedHeaders.Authorization = `Bearer ${token}`;
  if (mode) {
    mergedHeaders["X-LLM-Provider"] = mode.mode === "instant_demo" ? "instant_demo" : mode.provider;
    if (mode.mode === "byok" && mode.byokKey) mergedHeaders["X-LLM-Api-Key"] = mode.byokKey;
    if (mode.mode === "byok" && mode.model) mergedHeaders["X-LLM-Model"] = mode.model;
    if (mode.mode === "byok" && mode.baseUrl) mergedHeaders["X-LLM-Base-Url"] = mode.baseUrl;
  }
  return fetch(`${apiBase}${path}`, { ...rest, headers: mergedHeaders });
}
