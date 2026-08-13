// Persists the visitor's chosen testing mode (Instant Demo / Bring Your Own Key / Free Demo Key,
// picked on the login screen — see LoginModeSelector.jsx) across the session. Read by api.js on
// every request and by components that need to know the active mode (voice-intake gating,
// Instant-Demo action restrictions).
const STORAGE_KEY = "opsflow_provider_mode";

// { mode: "instant_demo" | "byok" | "free_demo", provider: "gemini"|"openrouter"|"tcs", byokKey: string|null }
const DEFAULT_MODE = { mode: "free_demo", provider: "gemini", byokKey: null };

export function getProviderMode() {
  if (typeof window === "undefined") return DEFAULT_MODE;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : DEFAULT_MODE;
  } catch {
    return DEFAULT_MODE;
  }
}

export function setProviderMode(mode) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(mode));
}

export const INSTANT_DEMO_EXPLANATION =
  "Instant Demo replays 6 pre-generated scenarios with no live model calls — switch to Bring Your Own Key or Free Demo Key mode for live diagnosis, chat, and voice/image intake.";
