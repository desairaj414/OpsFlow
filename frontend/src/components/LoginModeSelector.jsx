"use client";

// First-visit testing-mode picker, shown on the login screen (page.js) below the credentials
// form. Three modes (see .okf/ / README "Try it live" section for the full explanation):
//   - Instant Demo: zero live model calls, replays 6 pre-generated scenarios.
//   - Bring Your Own Key: visitor supplies their own provider + API key, used only in their own
//     browser session (sent as request headers, never stored server-side).
//   - Free Demo Key: uses a Gemini key the OpsFlow operator controls, with the same graceful
//     fallback behavior the backend already has for gateway outages (models-routing.md).
// Login itself is real either way (providers.js / roles.js already gate what each role can do)
// — the mode only decides which LLM key backs the session. Role quick-fill buttons below let a
// visitor prove login works without hunting for the seeded demo credentials in the README.
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { BYOK_PROVIDER_CHOICES, PROVIDER_INFO } from "@/lib/providers.js";

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
    description: "Use your own Gemini, OpenRouter, or TCS key — never leaves your browser.",
  },
];

export const QUICK_FILL_ACCOUNTS = {
  ops_engineer: { label: "Ops Engineer", username: "alex.chen", password: "OpsEngineer!123" },
  approver: { label: "Approver", username: "priya.sharma", password: "Approver!123" },
  admin: { label: "Admin", username: "admin", password: "Admin!123" },
};

export default function LoginModeSelector({ mode, onModeChange, onQuickFill }) {
  const [byokProvider, setByokProvider] = useState(mode.provider !== "gemini" || mode.mode === "byok" ? mode.provider : "gemini");
  const [byokKey, setByokKey] = useState(mode.byokKey || "");

  function selectMode(modeId) {
    if (modeId === "byok") {
      onModeChange({ mode: "byok", provider: byokProvider, byokKey });
    } else if (modeId === "instant_demo") {
      onModeChange({ mode: "instant_demo", provider: "gemini", byokKey: null });
    } else {
      onModeChange({ mode: "free_demo", provider: "gemini", byokKey: null });
    }
  }

  function updateByok(nextProvider, nextKey) {
    setByokProvider(nextProvider);
    setByokKey(nextKey);
    onModeChange({ mode: "byok", provider: nextProvider, byokKey: nextKey });
  }

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
        <div className="mt-3 flex flex-col gap-2 rounded-lg border border-border bg-accent-soft/30 p-3 sm:flex-row">
          <select
            value={byokProvider}
            onChange={(e) => updateByok(e.target.value, byokKey)}
            className="h-9 rounded-md border border-border bg-background px-2 text-sm text-foreground"
          >
            {BYOK_PROVIDER_CHOICES.map((p) => (
              <option key={p} value={p}>
                {PROVIDER_INFO[p].label}
              </option>
            ))}
          </select>
          <Input
            type="password"
            placeholder={PROVIDER_INFO[byokProvider].keyHint}
            value={byokKey}
            onChange={(e) => updateByok(byokProvider, e.target.value)}
            className="flex-1"
          />
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
