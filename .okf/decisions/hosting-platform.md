---
type: Decision
title: Hosting — One Platform, Two Service Types
description: Backend and frontend both deploy to Render — a Web Service for the backend, a static-exported Site for the frontend — rather than splitting across Render and Vercel or merging into one process.
tags: [hosting, deployment, architecture]
status: stable
generated: { by: "claude-sonnet-5/okf-maintain", at: "2026-08-14T00:00:00Z" }
sources:
  - id: render-yaml
    resource: render.yaml
    title: render.yaml
    last_modified: 2026-08-14
  - id: next-config
    resource: frontend/next.config.mjs
    title: frontend/next.config.mjs
    last_modified: 2026-08-14
---

# Decision

Both services deploy to [Render](https://render.com), defined together in one `render.yaml`
Blueprint: `opsflow-backend` as a Python **Web Service**, `opsflow-frontend` as a **Static Site**
(Next.js built with `output: "export"`, no Node server).[^render-yaml] [^next-config]

# Alternatives considered

1. **Vercel (frontend) + Render (backend)** — the original plan. Confirmed via 2026 market research
   as the standard pattern for this app shape (a frontend-optimized platform paired with a
   backend-optimized one), and Vercel's edge network is marginally faster globally for static
   assets than Render's.
2. **One Render Web Service serving both** — FastAPI mounting the built frontend as static files,
   one process, one URL, no CORS.
3. **Fully serverless** (Vercel/Netlify Functions for the backend too) — rejected outright, not
   seriously considered.

# Rationale

The backend cannot be serverless regardless of platform: SQLite and Chroma are opened once and
held across requests by a single long-running process (not rebuilt per-invocation), and
`/alerts/stream` is a persistent SSE connection — both need a traditional container/VM-style host,
which rules out Vercel/Netlify Functions for the backend specifically. That part of the split was
never a platform preference.

Whether the *frontend* also needed a separate platform was the actual question, and the answer
turned out to be no. `frontend/src/app/` has exactly one route, no `app/api/`, no middleware, and
no `next/image` usage — a clean fit for Next.js static export, confirmed by an end-to-end
Playwright pass against the exported `out/` build served statically (login, real backend login,
a live scenario run, zero console errors). Once static export is viable, Render's free **Static
Site** tier is strictly better for this app than paying for Render's Node Web Service tier
(**$7/mo minimum, confirmed live** — Render's free tier has no free option for a Node web service)
or reaching for a second platform: it's genuinely free, always-warm (no idle-sleep, unlike the
backend's free Web Service), and CDN-backed. The only thing that ever cold-starts is the backend,
which needs a boot step anyway (rebuilding SQLite/Chroma from seed data — see
[Provenance](/data/) and `render.yaml`'s own comments) — the frontend was never going to avoid that
regardless of where it's hosted, so putting it on an always-warm static host is a pure win, not a
tradeoff.

Option 2 (single process serving both) was rejected because it would make the *entire app*,
frontend included, subject to the backend's cold-start sleep on Render's free tier — strictly worse
UX than keeping the frontend on a host that never sleeps, for no offsetting benefit (still one
platform either way).

# Consequence

Two Render service URLs to cross-wire manually once, post-creation (`FRONTEND_ORIGIN` on the
backend, `NEXT_PUBLIC_API_BASE_URL` on the frontend — the latter needs a rebuild, not just a
restart, since Next.js bakes `NEXT_PUBLIC_*` values into the static bundle at build time) — see
README §9. If the frontend ever needs a genuine server-side route (an API route, middleware, SSR
with per-request data), this decision would need revisiting; nothing here rules that out for a
future phase, it just isn't needed today.

[^render-yaml]: render.yaml
[^next-config]: frontend/next.config.mjs
