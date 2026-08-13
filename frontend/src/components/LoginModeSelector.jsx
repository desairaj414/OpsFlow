"use client";

// First-visit testing-mode picker, shown on the login screen (page.js) below the credentials
// form. Three modes (see .okf/ / README "Try it live" section for the full explanation):
//   - Instant Demo: zero live model calls, replays 6 pre-generated scenarios.
//   - Bring Your Own Key: visitor supplies their own provider + API key, used only in their own
//     browser session (sent as request headers, never stored server-side). The visitor also picks
//     (or fetches) a specific model and must validate the key/model pair before page.js's
//     handleLogin will let them into the cockpit — see validateByokKey()/fetchByokModels().
//   - Free Demo Key: uses a Gemini key the OpsFlow operator controls, with the same graceful
//     fallback behavior the backend already has for gateway outages (models-routing.md).
// Login itself is real either way (providers.js / roles.js already gate what each role can do)
// — the mode only decides which LLM key backs the session. Role quick-fill buttons below let a
// visitor prove login works without hunting for the seeded demo credentials in the README.
import { useState } from "react";
import { CheckCircle2, Eye, EyeOff, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { BYOK_PROVIDER_CHOICES, PROVIDER_INFO, fetchByokModels, validateByokKey } from "@/lib/providers.js";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8765";

const MODES = [
  {
    id: "instant_demo",
    label: "Instant Demo",
    description: "Zero live calls — replays 6 pre-generated scenarios. Always works.",
  },
  {
    id: "free_demo",
    label: "Free Demo Key",
    description: "Live diagnosis, powered by a key the OpsFlow operator provides.",
  },
  {
    id: "byok",
    label: "Bring Your Own Key",
    description: "Use your own OpenAI, Gemini, Grok, or other key — never leaves your browser.",
  },
];

export const QUICK_FILL_ACCOUNTS = {
  ops_engineer: { label: "Ops Engineer", username: "alex.chen", password: "OpsEngineer!123" },
  approver: { label: "Approver", username: "priya.sharma", password: "Approver!123" },
  admin: { label: "Admin", username: "admin", password: "Admin!123" },
};

export default function LoginModeSelector({ mode, onModeChange, onQuickFill }) {
  const [byokProvider, setByokProvider] = useState(mode.mode === "byok" ? mode.provider : "gemini");
  const [byokKey, setByokKey] = useState(mode.byokKey || "");
  const [baseUrl, setBaseUrl] = useState(mode.baseUrl || "");
  const [showKey, setShowKey] = useState(false);
  const [model, setModel] = useState(mode.model || defaultModelFor(mode.mode === "byok" ? mode.provider : "gemini"));
  const [fetchedModels, setFetchedModels] = useState(null);
  const [fetchState, setFetchState] = useState("idle"); // idle | loading | done | error
  const [validateState, setValidateState] = useState("idle"); // idle | loading | ok | error
  const [validateError, setValidateError] = useState("");
  const [capabilities, setCapabilities] = useState(mode.mode === "byok" ? mode.capabilities || null : null);
  // For modelSource "static" (currently just gemini): the curated list covers the common case, but
  // a visitor who specifically wants a dated/preview id (e.g. early access to a new snapshot) can
  // switch to typing one instead — "Validate & Save Key" below is what actually confirms it works,
  // same safety net as every other model choice already gets.
  const [customModelEntry, setCustomModelEntry] = useState(false);
  const CUSTOM_MODEL_SENTINEL = "__custom__";

  const info = PROVIDER_INFO[byokProvider];

  function defaultModelFor(providerId) {
    const choices = PROVIDER_INFO[providerId]?.modelChoices;
    return choices?.[0]?.id || "";
  }

  function selectMode(modeId) {
    if (modeId === "byok") {
      onModeChange({
        mode: "byok",
        provider: byokProvider,
        byokKey,
        model,
        baseUrl,
        validated: validateState === "ok",
        capabilities: validateState === "ok" ? capabilities : null,
      });
    } else if (modeId === "instant_demo") {
      onModeChange({ mode: "instant_demo", provider: "gemini", byokKey: null, model: null, baseUrl: null, validated: true, capabilities: null });
    } else {
      onModeChange({ mode: "free_demo", provider: "gemini", byokKey: null, model: null, baseUrl: null, validated: true, capabilities: null });
    }
  }

  function resetValidation() {
    setValidateState("idle");
    setValidateError("");
    setCapabilities(null);
  }

  function updateByok(next) {
    const merged = {
      provider: next.provider ?? byokProvider,
      byokKey: next.byokKey ?? byokKey,
      model: next.model ?? model,
      baseUrl: next.baseUrl ?? baseUrl,
    };
    setByokProvider(merged.provider);
    setByokKey(merged.byokKey);
    setModel(merged.model);
    setBaseUrl(merged.baseUrl);
    resetValidation();
    onModeChange({ mode: "byok", ...merged, validated: false, capabilities: null });
  }

  function changeProvider(nextProvider) {
    setFetchedModels(null);
    setFetchState("idle");
    setCustomModelEntry(false);
    updateByok({ provider: nextProvider, model: defaultModelFor(nextProvider) });
  }

  async function runFetchModels() {
    if (!byokKey) return;
    setFetchState("loading");
    const models = await fetchByokModels(API_BASE, {
      provider: byokProvider,
      apiKey: byokKey,
      baseUrl: info.needsBaseUrl ? baseUrl : undefined,
    });
    if (models && models.length > 0) {
      setFetchedModels(models);
      setFetchState("done");
      updateByok({ model: models[0] });
    } else {
      setFetchedModels(null);
      setFetchState("error");
    }
  }

  async function runValidate() {
    setValidateState("loading");
    setValidateError("");
    const { ok, error, capabilities } = await validateByokKey(API_BASE, {
      provider: byokProvider,
      apiKey: byokKey,
      model,
      baseUrl: info.needsBaseUrl ? baseUrl : undefined,
    });
    if (ok) {
      setValidateState("ok");
      setCapabilities(capabilities || null);
      onModeChange({
        mode: "byok",
        provider: byokProvider,
        byokKey,
        model,
        baseUrl,
        validated: true,
        capabilities: capabilities || null,
      });
    } else {
      setValidateState("error");
      setValidateError(error || "That key/model didn't work.");
    }
  }

  const canValidate = Boolean(byokKey && model && (!info.needsBaseUrl || baseUrl));

  return (
    <div className="mt-8 border-t border-border pt-6">
      <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">Testing mode</p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => selectMode(m.id)}
            className={cn(
              "rounded-lg border p-3 text-left transition-colors",
              mode.mode === m.id ? "border-primary bg-accent-soft" : "border-border hover:bg-accent-soft/40"
            )}
          >
            <div className="text-sm font-medium text-foreground">{m.label}</div>
            <div className="mt-0.5 text-xs leading-snug text-muted-foreground">{m.description}</div>
          </button>
        ))}
      </div>

      {mode.mode === "byok" && (
        <div className="mt-3 flex flex-col gap-3 rounded-lg border border-border bg-accent-soft/30 p-4">
          <p className="text-xs text-muted-foreground">
            Your key is used for this browser session only — never saved to disk or logged.
          </p>

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Provider</label>
            <select
              value={byokProvider}
              onChange={(e) => changeProvider(e.target.value)}
              className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground"
            >
              {BYOK_PROVIDER_CHOICES.map((p) => (
                <option key={p} value={p}>
                  {PROVIDER_INFO[p].label}
                </option>
              ))}
            </select>
            {(info.keyHintPrefix || info.keyUrlLabel) && (
              <p className="mt-1 text-xs text-muted-foreground">
                {info.keyHintPrefix}
                {info.keyUrlLabel &&
                  (info.keyUrl ? (
                    <a href={info.keyUrl} target="_blank" rel="noreferrer" className="underline hover:text-foreground">
                      {info.keyUrlLabel}
                    </a>
                  ) : (
                    info.keyUrlLabel
                  ))}
                {info.keyHintSuffix}
              </p>
            )}
          </div>

          {info.needsBaseUrl && (
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">Base URL</label>
              <Input
                value={baseUrl}
                onChange={(e) => updateByok({ baseUrl: e.target.value })}
                placeholder="https://your-endpoint.example/v1"
                className="w-full"
              />
            </div>
          )}

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">API key</label>
            <div className="relative">
              <Input
                type={showKey ? "text" : "password"}
                value={byokKey}
                onChange={(e) => updateByok({ byokKey: e.target.value })}
                placeholder="Paste your API key"
                className="w-full pr-10"
              />
              <button
                type="button"
                onClick={() => setShowKey((v) => !v)}
                className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground hover:text-foreground"
                aria-label={showKey ? "Hide key" : "Show key"}
              >
                {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-muted-foreground">Model</label>
            {info.modelSource === "static" && (
              customModelEntry ? (
                <div className="flex flex-col gap-1.5">
                  <Input
                    value={model}
                    onChange={(e) => updateByok({ model: e.target.value })}
                    placeholder="Model id"
                    className="w-full"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      setCustomModelEntry(false);
                      updateByok({ model: defaultModelFor(byokProvider) });
                    }}
                    className="self-start text-xs text-muted-foreground underline hover:text-foreground"
                  >
                    Back to curated list
                  </button>
                  <p className="text-xs text-muted-foreground">
                    Dated/preview model ids can be retired without notice — validate below to confirm
                    it actually works.
                  </p>
                </div>
              ) : (
                <select
                  value={model}
                  onChange={(e) => {
                    if (e.target.value === CUSTOM_MODEL_SENTINEL) {
                      setCustomModelEntry(true);
                      updateByok({ model: "" });
                    } else {
                      updateByok({ model: e.target.value });
                    }
                  }}
                  className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground"
                >
                  {info.modelChoices.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label} ({c.tier})
                    </option>
                  ))}
                  <option value={CUSTOM_MODEL_SENTINEL}>Custom model id…</option>
                </select>
              )
            )}

            {info.modelSource === "manual" && (
              <Input
                value={model}
                onChange={(e) => updateByok({ model: e.target.value })}
                placeholder="Model id"
                className="w-full"
              />
            )}

            {info.modelSource === "fetch" && (
              <div className="flex flex-col gap-2">
                {fetchedModels ? (
                  <select
                    value={model}
                    onChange={(e) => updateByok({ model: e.target.value })}
                    className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground"
                  >
                    {fetchedModels.map((id) => (
                      <option key={id} value={id}>
                        {id}
                      </option>
                    ))}
                  </select>
                ) : (
                  <Input
                    value={model}
                    onChange={(e) => updateByok({ model: e.target.value })}
                    placeholder="Model id"
                    className="w-full"
                  />
                )}
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={!byokKey || (info.needsBaseUrl && !baseUrl) || fetchState === "loading"}
                    onClick={runFetchModels}
                  >
                    {fetchState === "loading" ? (
                      <span className="flex items-center gap-1.5">
                        <Loader2 size={14} className="animate-spin" /> Checking…
                      </span>
                    ) : (
                      "Fetch available models"
                    )}
                  </Button>
                  {fetchState === "error" && (
                    <span className="text-xs text-muted-foreground">
                      Couldn't list models automatically — enter one manually.
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {info.tierHint && <p className="text-xs text-muted-foreground">{info.tierHint}</p>}
          {info.visionUnverified && (
            <p className="text-xs text-muted-foreground">
              Voice support is verified against this endpoint when you validate below. Vision/image
              support is assumed for custom endpoints, not verified — it depends on your model.
            </p>
          )}
          {info.pricingUrl && (
            <p className="text-xs text-muted-foreground">
              Free/paid tiers vary by account and change over time —{" "}
              <a href={info.pricingUrl} target="_blank" rel="noreferrer" className="underline">
                verify current pricing
              </a>{" "}
              before assuming.
            </p>
          )}

          <Button type="button" onClick={runValidate} disabled={!canValidate || validateState === "loading"} className="w-full">
            {validateState === "loading" ? (
              <span className="flex items-center gap-1.5">
                <Loader2 size={16} className="animate-spin" /> Validating…
              </span>
            ) : validateState === "ok" ? (
              <span className="flex items-center gap-1.5">
                <CheckCircle2 size={16} /> Key verified
              </span>
            ) : (
              "Validate & Save Key"
            )}
          </Button>
          {validateState === "error" && <p className="text-xs text-red-500">That key/model didn't work: {validateError}</p>}
        </div>
      )}

      <p className="mb-2 mt-5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        Quick-fill a demo account
      </p>
      <div className="flex flex-wrap gap-2">
        {Object.entries(QUICK_FILL_ACCOUNTS).map(([role, account]) => (
          <button
            key={role}
            type="button"
            onClick={() => onQuickFill(account)}
            className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary hover:text-primary"
          >
            {account.label}
          </button>
        ))}
      </div>
    </div>
  );
}
