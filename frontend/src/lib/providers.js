// Client-side mirror of backend/providers.py's capability flags (labels, vision/transcription
// support, key hints, model picker mode) — NOT the model-role map or base URLs (those stay
// backend-only, except `custom`'s base_url, which the visitor supplies here and it's sent as the
// X-LLM-Base-Url header). Keep in sync by hand if the backend registry's provider set changes.
//
// modelSource mirrors backend/providers.py's field:
//   "static" - a hand-curated, pre-verified list (modelChoices) — no fetch needed/reliable.
//   "fetch"  - LoginModeSelector.jsx calls POST /providers/fetch-models with the visitor's key;
//              on success shows a dropdown of returned ids, on failure/no-key falls back to a
//              manual text field.
//   "manual" - no listing exists to fetch; always a manual text field.
export const PROVIDER_INFO = {
  gemini: {
    label: "Google Gemini",
    supportsTranscription: false,
    vision: true,
    keyHintPrefix: "Get a free key at ",
    keyUrlLabel: "aistudio.google.com/apikey",
    keyUrl: "https://aistudio.google.com/apikey",
    pricingUrl: "https://ai.google.dev/gemini-api/docs/pricing",
    modelSource: "static",
    modelChoices: [
      { id: "gemini-flash-lite-latest", label: "Flash-Lite Latest", tier: "free" },
      { id: "gemini-flash-latest", label: "Flash Latest (reasoning model)", tier: "free" },
      { id: "gemini-pro-latest", label: "Pro Latest (higher quality, slower)", tier: "paid" },
    ],
  },
  openai: {
    label: "OpenAI",
    supportsTranscription: true,
    vision: true,
    keyHintPrefix: "Get a key at ",
    keyUrlLabel: "platform.openai.com/api-keys",
    keyUrl: "https://platform.openai.com/api-keys",
    keyHintSuffix: " (paid, no free tier)",
    pricingUrl: "https://openai.com/api/pricing/",
    modelSource: "fetch",
  },
  openrouter: {
    label: "OpenRouter",
    supportsTranscription: false,
    vision: true,
    keyHintPrefix: "Get a free key at ",
    keyUrlLabel: "openrouter.ai/keys",
    keyUrl: "https://openrouter.ai/keys",
    tierHint: "Model ids ending in :free are free tier; everything else is paid, billed to your OpenRouter credits.",
    pricingUrl: "https://openrouter.ai/models",
    modelSource: "fetch",
  },
  grok: {
    label: "xAI Grok",
    supportsTranscription: false,
    vision: true,
    keyHintPrefix: "Get a key at ",
    keyUrlLabel: "console.x.ai",
    keyUrl: "https://console.x.ai",
    keyHintSuffix: " (paid, no free tier)",
    pricingUrl: "https://x.ai/api",
    modelSource: "fetch",
  },
  tcs: {
    label: "TCS GenAI Lab (legacy, internal network only)",
    supportsTranscription: true,
    vision: true,
    keyHintPrefix: "TCS-issued key; only reachable from the TCS network",
    modelSource: "manual",
  },
  custom: {
    label: "Custom (OpenAI-compatible)",
    // Neither flag is verifiable for an arbitrary endpoint the way the curated providers' are:
    // transcription gets a real 404-vs-not probe at validate-key time (providers.py's
    // probe_transcription_support(), surfaced via canUseVoice() — see providerMode.js), so
    // `false` here is only the fallback before that probe runs. Vision has no equivalent reliable
    // check (it rides the same /chat/completions path as text, so a rejected test image can't be
    // told apart from "unsupported") — `true` here is a bare assumption, not a verified fact.
    supportsTranscription: false,
    vision: true,
    visionUnverified: true,
    keyHintPrefix: "Any OpenAI-compatible chat completions endpoint",
    modelSource: "fetch",
    needsBaseUrl: true,
  },
};

// Gemini leads — it's the one BYOK provider with a genuinely free tier; OpenAI/Grok have none,
// and OpenRouter's free models are real but rate-limited/flaky (models-routing.md).
export const BYOK_PROVIDER_CHOICES = ["gemini", "openai", "openrouter", "grok", "tcs", "custom"];

// Instant Demo makes no live calls at all, so voice/vision capability there is moot — its intake
// endpoints are disabled server-side regardless (see main.py's _INSTANT_DEMO_INTAKE_MESSAGE).
//
// A verified capability from main.py's /providers/validate-key (mode.capabilities — the registry's
// static value for known providers, or a real 404-vs-not probe for `custom`, see
// providers.py's probe_transcription_support()) wins over the static PROVIDER_INFO default here.
// For known providers those two values always agree; for `custom` this is what makes the mic button
// reflect that specific endpoint's real behavior instead of the blanket "no" PROVIDER_INFO guesses.
export function canUseVoice(mode) {
  if (!mode || mode.mode === "instant_demo") return false;
  const probed = mode.capabilities?.supports_transcription;
  if (typeof probed === "boolean") return probed;
  return Boolean(PROVIDER_INFO[mode.provider]?.supportsTranscription);
}

// Shared by LoginModeSelector.jsx's inline "Validate & Save Key" button and page.js's login-gate
// (a visitor must not reach the cockpit on a key that was never checked or that main.py's
// /providers/validate-key already rejected — plain fetch(), not apiFetch(), since these calls
// establish the BYOK mode rather than using an already-established one).
export async function fetchByokModels(apiBase, { provider, apiKey, baseUrl }) {
  const res = await fetch(`${apiBase}/providers/fetch-models`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, api_key: apiKey, base_url: baseUrl || null }),
  });
  if (!res.ok) return null;
  const data = await res.json();
  return data.models;
}

export async function validateByokKey(apiBase, { provider, apiKey, model, baseUrl }) {
  const res = await fetch(`${apiBase}/providers/validate-key`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, api_key: apiKey, model, base_url: baseUrl || null }),
  });
  if (!res.ok) return { ok: false, error: `Request failed (${res.status})` };
  return res.json();
}
