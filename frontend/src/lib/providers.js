// Client-side mirror of backend/providers.py's capability flags (labels, vision/transcription
// support, key hints) — NOT the model-role map or base URLs, which are backend-only concerns the
// frontend never needs. Keep in sync by hand if the backend registry's provider set changes.
export const PROVIDER_INFO = {
  gemini: {
    label: "Google Gemini",
    supportsTranscription: false,
    vision: true,
    keyHint: "Get a free key at aistudio.google.com/apikey",
  },
  openrouter: {
    label: "OpenRouter",
    supportsTranscription: false,
    vision: true,
    keyHint: "Get a free key at openrouter.ai/keys",
  },
  tcs: {
    label: "TCS GenAI Lab (legacy, internal network only)",
    supportsTranscription: true,
    vision: true,
    keyHint: "TCS-issued key; only reachable from the TCS network",
  },
};

export const BYOK_PROVIDER_CHOICES = ["gemini", "openrouter", "tcs"];

// Instant Demo makes no live calls at all, so voice/vision capability there is moot — its intake
// endpoints are disabled server-side regardless (see main.py's _INSTANT_DEMO_INTAKE_MESSAGE).
export function canUseVoice(mode) {
  if (!mode || mode.mode === "instant_demo") return false;
  return Boolean(PROVIDER_INFO[mode.provider]?.supportsTranscription);
}
