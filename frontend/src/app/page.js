"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LogoMark } from "@/components/Logo.jsx";
import CockpitShell from "@/components/CockpitShell.jsx";
import LoginModeSelector from "@/components/LoginModeSelector.jsx";
import { useTheme } from "@/hooks/useTheme.js";
import { apiFetch } from "@/lib/api.js";
import { getProviderMode, setProviderMode } from "@/lib/providerMode.js";
import { PROVIDER_INFO, validateByokKey } from "@/lib/providers.js";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8765";

// The same 5 stages shown for real after sign-in (IncidentWorkspace.jsx's flow pipeline,
// domain-workflows.md's reference chain) — used here as the brand panel's process motif, distinct
// from the logo (which is the brand mark, not the process).
const PIPELINE_STAGES = ["Correlate", "Enrich", "Diagnose", "Plan", "Verify"];

function PipelineMotif() {
  return (
    <div className="mt-10 flex items-center gap-0" aria-hidden="true">
      {PIPELINE_STAGES.map((stage, i) => (
        <div key={stage} className="flex items-center">
          <div className="flex flex-col items-center gap-2">
            <div
              className="h-2.5 w-2.5 rounded-full bg-primary motion-safe:animate-pulse"
              style={{ animationDelay: `${i * 300}ms` }}
            />
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">{stage}</span>
          </div>
          {i < PIPELINE_STAGES.length - 1 && <div className="mb-4 h-px w-8 bg-border sm:w-12" />}
        </div>
      ))}
    </div>
  );
}

// A large, faint version of the logo's scope-ring — the brand panel's signature: the same
// instrument that brings a true signal into focus, oversized and quiet, watching over the sign-in.
function RingWatermark() {
  return (
    <svg
      viewBox="0 0 400 400"
      aria-hidden="true"
      className="pointer-events-none absolute -right-24 -top-24 h-[420px] w-[420px] opacity-[0.06] md:right-[-140px] md:top-1/2 md:-translate-y-1/2"
    >
      <circle cx="200" cy="200" r="180" stroke="hsl(var(--primary))" strokeWidth="16" fill="none" />
      <circle cx="200" cy="200" r="105" stroke="hsl(var(--primary))" strokeWidth="16" fill="none" />
      <circle cx="200" cy="200" r="20" fill="hsl(var(--primary))" />
    </svg>
  );
}

// Matches the server default (free_demo/gemini) so the initial client render before hydration
// can't mismatch the server-rendered HTML — the real localStorage-backed mode is picked up after
// mount (see the useEffect below), same pattern theme.js's toggle uses for the same reason.
const SERVER_SAFE_DEFAULT_MODE = { mode: "free_demo", provider: "gemini", byokKey: null, model: null, baseUrl: null, validated: true };

export default function Home() {
  const { theme, toggleTheme } = useTheme();
  const [token, setToken] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loggingIn, setLoggingIn] = useState(false);
  const [mode, setMode] = useState(SERVER_SAFE_DEFAULT_MODE);
  // Free-tier backends (Render) sleep after 15min idle and can take up to ~60s to cold-start. This
  // used to only get triggered by the "Log in" click itself, so the very first visitor after a
  // sleep saw nothing but a stuck "Signing in…" with no explanation. Pinging /health immediately on
  // page load starts that wake-up in parallel with the visitor reading/filling the form, and the
  // banner below explains the wait instead of it reading as broken.
  const [backendAwake, setBackendAwake] = useState(null);

  useEffect(() => {
    setMode(getProviderMode());
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function pingUntilAwake() {
      while (!cancelled) {
        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 8000);
          const res = await fetch(`${API_BASE}/health`, { signal: controller.signal });
          clearTimeout(timeoutId);
          if (res.ok) {
            if (!cancelled) setBackendAwake(true);
            return;
          }
        } catch {
          // Still waking up (or a transient network hiccup) — keep retrying below.
        }
        if (!cancelled) await new Promise((resolve) => setTimeout(resolve, 2500));
      }
    }
    pingUntilAwake();
    return () => {
      cancelled = true;
    };
  }, []);

  function handleModeChange(nextMode) {
    setMode(nextMode);
    setProviderMode(nextMode);
  }

  function handleQuickFill(account) {
    setUsername(account.username);
    setPassword(account.password);
  }

  async function handleLogin(e) {
    e.preventDefault();
    setError("");

    // Bring Your Own Key must be checked before this screen ever navigates to the cockpit — a
    // missing or bad key/model used to only surface much later, on the first live workflow call.
    if (mode.mode === "byok") {
      const info = PROVIDER_INFO[mode.provider];
      if (!mode.byokKey) {
        setError("Enter an API key for Bring Your Own Key mode, or switch to another testing mode.");
        return;
      }
      if (info?.needsBaseUrl && !mode.baseUrl) {
        setError("Enter a base URL for the Custom provider.");
        return;
      }
      if (!mode.model) {
        setError("Select or enter a model for Bring Your Own Key mode.");
        return;
      }
      if (!mode.validated) {
        setLoggingIn(true);
        const { ok, error: validateErr, capabilities } = await validateByokKey(API_BASE, {
          provider: mode.provider,
          apiKey: mode.byokKey,
          model: mode.model,
          baseUrl: mode.baseUrl,
        });
        if (!ok) {
          setError(`That key/model didn't work: ${validateErr}`);
          setLoggingIn(false);
          return;
        }
        const validatedMode = { ...mode, validated: true, capabilities: capabilities || null };
        setMode(validatedMode);
        setProviderMode(validatedMode);
      }
    }

    setLoggingIn(true);
    try {
      const body = new URLSearchParams({ username, password });
      const res = await apiFetch(API_BASE, "/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      if (res.status === 401) throw new Error("Invalid username or password.");
      if (!res.ok) throw new Error(`Sign-in failed (${res.status}).`);
      const data = await res.json();
      setToken(data.access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoggingIn(false);
    }
  }

  if (token) {
    return (
      <CockpitShell
        token={token}
        onTokenChange={setToken}
        apiBase={API_BASE}
        username={username}
        onLogout={() => setToken(null)}
      />
    );
  }

  return (
    <div className="grid min-h-screen md:grid-cols-2">
      {/* Fixed, not part of either column's flow, so it stays put regardless of scroll — same
          toggle Sidebar.jsx uses post-login, just not tucked inside a sidebar here. */}
      <button
        onClick={toggleTheme}
        title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
        className="fixed right-4 top-4 z-10 rounded-md border border-border bg-background/80 p-2 text-muted-foreground backdrop-blur hover:bg-secondary hover:text-foreground"
      >
        {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
      </button>

      {/* Brand panel — light, matching the app's own surface, with the logo's ring motif oversized
          and faint in the background rather than a heavy dark block. */}
      {/* Sticky + viewport-height on md+ so this panel stays pinned in place instead of stretching
          to match the sign-in column's height — the BYOK panel below can make that column taller
          than one viewport, and this column previously grew (and re-centered) right along with it. */}
      <div className="relative flex flex-col justify-center overflow-hidden bg-accent-soft/40 px-8 py-12 sm:px-14 md:sticky md:top-0 md:h-screen md:py-0">
        <RingWatermark />
        <div className="relative mx-auto w-full max-w-sm md:mx-0">
          <LogoMark size={40} />
          <h1 className="mt-5 text-3xl font-semibold leading-tight text-foreground">OpsFlow</h1>
          <p className="mt-1 text-sm text-muted-foreground">AI-verified operations console</p>
          <p className="mt-6 max-w-xs text-sm leading-relaxed text-muted-foreground">
            Every incident correlated, diagnosed, and resolved by an auditable AI agent chain — with
            a human in the loop wherever it matters.
          </p>
          <PipelineMotif />
        </div>
      </div>

      {/* Sign-in panel */}
      <div className="flex items-center justify-center bg-background px-6 py-12">
        <div className="w-full max-w-sm">
          <h2 className="text-xl font-semibold text-foreground">Sign in</h2>
          <p className="mt-1 text-sm text-muted-foreground">Enter your credentials to access your workspace.</p>

          {backendAwake !== true && (
            <p className="mt-3 rounded-md border border-accent/30 bg-accent-soft px-3 py-2 text-xs text-muted-foreground">
              Connecting to the server — first load can take up to a minute if it's been idle. Feel
              free to fill in your details below while it wakes up.
            </p>
          )}

          <form className="mt-6 space-y-4" onSubmit={handleLogin}>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="username">
                Username
              </label>
              <Input id="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground" htmlFor="password">
                Password
              </label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error && <p className="text-sm text-red-500">{error}</p>}
            <Button type="submit" className="w-full" disabled={loggingIn}>
              {loggingIn ? "Signing in…" : "Log in"}
            </Button>
          </form>

          <LoginModeSelector mode={mode} onModeChange={handleModeChange} onQuickFill={handleQuickFill} />
        </div>
      </div>
    </div>
  );
}
