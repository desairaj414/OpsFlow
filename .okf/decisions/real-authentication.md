---
type: Decision
title: Real Authentication, Superseding "No Real Auth"
description: Reverses an earlier PRD call ("mock JWT + free role-switcher, zero marginal credit for real auth") — implements a real users table with salted PBKDF2 password hashes, POST /auth/login that actually rejects bad credentials, and one fixed role per account, plus a scoped admin-only "View as" impersonation control.
tags: [architecture, auth, security]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: decisions-log
    resource: .knowledge/decisions-log.md
    title: Decisions Log
    last_modified: 2026-08-07
  - id: schema-sql
    resource: backend/db/schema.sql
    title: backend/db/schema.sql
    last_modified: 2026-08-08
---

# Decision

Supersedes the original PRD position that real authentication had "zero marginal credit, real cost"
and that a simulated-identity, self-service role picker was sufficient. Implements a real `users`
table (replacing an earlier `profiles` table) with per-account salted PBKDF2-HMAC-SHA256 password
hashes (stdlib `hashlib`, no new dependency), a `POST /auth/login` that actually validates
username+password and returns 401 on bad credentials, and one fixed role per account — no more
self-service role-picking at login or in the sidebar. Admin retains a scoped, audited "View as"
impersonation control for demo/testing, rather than the earlier free-for-all profile switcher any
logged-in user could use to grant themselves elevated access.[^decisions-log]

# Alternatives considered

Keep the original mock/simulated-identity design and only fix the login page's explanatory copy. A
full third-party auth provider (OAuth/SSO) — rejected as disproportionate scope for a prototype with
no real user base.[^decisions-log]

# Rationale

The mock-login-plus-free-role-switcher combination read as confusing on review and, on reflection,
insecure: any authenticated session could self-elevate to Admin. PBKDF2 via the Python standard
library was chosen over `bcrypt`/`passlib` specifically to avoid a new pip dependency in an
environment where package installs had repeatedly hit corporate-proxy SSL friction.[^decisions-log]

# Consequence

`ROLE_TO_ACTOR_ROLE` in `main.py` maps the UI-facing role vocabulary
(`ops_engineer`/`approver`/`admin`) to [Policy Gate](/guardrails/policy-gate.md)'s separate,
frozen `actor_role` vocabulary (`operator`/`sre_lead`/`change_manager`) — a real fix, since the
system previously passed the raw logged-in username as `actor_role`, meaning the policy gate's
approver check could never match any real login and every prod/P1 action silently required
approval regardless of who was actually logged in.

[^decisions-log]: Decisions Log
