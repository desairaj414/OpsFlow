// Persists the visitor's chosen testing mode (Instant Demo / Bring Your Own Key / Free Demo Key,
// picked on the login screen — see LoginModeSelector.jsx) across the session. Read by api.js on
// every request and by components that need to know the active mode (voice-intake gating,
// Instant-Demo action restrictions).
const STORAGE_KEY = "opsflow_provider_mode";

// { mode: "instant_demo" | "byok" | "free_demo", provider: "gemini"|"openai"|"openrouter"|"grok"|
//   "tcs"|"custom", byokKey: string|null, model: string|null, baseUrl: string|null,
//   validated: boolean, capabilities: {supports_transcription: boolean|null}|null }
// `model`/`baseUrl` are only ever set for mode "byok" (see LoginModeSelector.jsx's fetch/validate
// step); `validated` gates page.js's handleLogin — a visitor can't reach the cockpit on an
// unverified or bad BYOK key (see providers.js's PROVIDER_INFO + main.py's /providers/validate-key).
// `capabilities` is what main.py's /providers/validate-key actually returned for this session —
// the registry's static value for known providers, or a real probe result for `custom` (see
// providers.py's probe_transcription_support()). canUseVoice() prefers this over the static
// PROVIDER_INFO default when present.
const DEFAULT_MODE = {
  mode: "free_demo",
  provider: "gemini",
  byokKey: null,
  model: null,
  baseUrl: null,
  validated: true,
  capabilities: null,
};

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
