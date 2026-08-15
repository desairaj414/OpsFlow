# CLAUDE.md — Hub Index

Thin index only. Do not paste node contents here. Read a node when a step names it; do not
pre-read the whole tree. Product decisions live in `PRD_FINAL.md` (frozen, do not re-decide) —
this `.knowledge/` tree is its execution-ready conversion for an executing AI session.

This repo also has a portable OKF (Open Knowledge Format) v0.2 bundle at [.okf/](.okf/) — a
one-concept-per-file distillation of this tree for outside readers (resume reviewers, anyone
without this session's context). `.knowledge/` stays the authoritative execution log; `.okf/` is
derived from it, not a replacement. See `.okf/index.md` for its entry point.

## Project
- **Name:** my-hackathon-app — TCS AI Fridays S2, Cross-Stack Maintenance Control Plane
- **Stack:** FastAPI (backend, async) + Next.js frontend (App Router, Tailwind v4, Turbopack). The
  original Vite/React scaffold was migrated to Next.js in Phase 4 (human confirmed 2026-08-07; see
  [decisions-log.md](.knowledge/decisions-log.md)) — migration is complete, not a pending item.
- **LLM endpoint:** TCS GenAI Lab (OpenAI-compatible) gateway — `https://genailab.tcs.in/v1` — plus local Ollama SLMs
- **Problem statement:** AI-Powered Multi-Agent Workflow Automation for IT Application Maintenance — see `PRD_FINAL.md`

## Read first, every session
- [.knowledge/state-progress.md](.knowledge/state-progress.md) — live single source of truth. Read this before touching anything.
- [.knowledge/decisions-log.md](.knowledge/decisions-log.md) — resolved decisions, do not re-litigate.
- [.knowledge/state-progress-history.md](.knowledge/state-progress-history.md) — closed-phase/superseded-step detail (Phase 0-3, plus early Phase 4 atomic steps), split out whenever state-progress.md hit ~200 lines. Only open on demand, not every session.

## Standing rules (re-read on every coding step, not once)
- [.knowledge/rules-backend.md](.knowledge/rules-backend.md) — commenting standard, module layout, honesty rule (backend)
- [.knowledge/rules-frontend.md](.knowledge/rules-frontend.md) — commenting standard (frontend)

## Architecture & contracts
- [.knowledge/arch-overview.md](.knowledge/arch-overview.md) — tier diagram, routing principle, orchestration shape, protocol layer
- [.knowledge/architecture-as-built.md](.knowledge/architecture-as-built.md) — as-implemented agent-by-agent breakdown (LLM/SLM/RAG/deterministic, per step) + every Overview-tab metric's exact computation
- [.knowledge/schema-db.md](.knowledge/schema-db.md) — SQLite + Chroma schema
- [.knowledge/api-contract.md](.knowledge/api-contract.md) — canonical `MaintenanceSignal`, MCP tool contracts, A2A Agent Card
- [.knowledge/models-routing.md](.knowledge/models-routing.md) — model routing table, trade-offs, actual `.env` model-id mapping

## Domain nodes
- [.knowledge/domain-workflows.md](.knowledge/domain-workflows.md) — incident / patch / performance-tuning parity
- [.knowledge/domain-agents.md](.knowledge/domain-agents.md) — supervisor + specialist chain, orchestration rules
- [.knowledge/domain-guardrails.md](.knowledge/domain-guardrails.md) — policy gate, confidence floor, Fake Fix Detector, bias mitigations
- [.knowledge/domain-multimodal-intake.md](.knowledge/domain-multimodal-intake.md) — voice (Whisper) + vision (Llama Vision) intake
- [.knowledge/domain-privacy.md](.knowledge/domain-privacy.md) — DPDP basis, scrubber, audit trail, retention

## Phases (execute in order; each gates the next)
- [.knowledge/prd-phase-0.md](.knowledge/prd-phase-0.md) — Environment & Gateway Smoke Test
- [.knowledge/prd-phase-1.md](.knowledge/prd-phase-1.md) — Data, Simulated Systems & MCP Layer
- [.knowledge/prd-phase-2.md](.knowledge/prd-phase-2.md) — Deterministic Core (no LLM)
- [.knowledge/prd-phase-3.md](.knowledge/prd-phase-3.md) — Agent Chain, Supervisor, A2A & Multimodal Intake
- [.knowledge/prd-phase-4.md](.knowledge/prd-phase-4.md) — Cockpit UI
- [.knowledge/prd-phase-5.md](.knowledge/prd-phase-5.md) — Scenario Library, Eval & Hardening
- [.knowledge/prd-phase-6.md](.knowledge/prd-phase-6.md) — Extra Credit (conditional, only if Phase 5 gate is green)
- [.knowledge/prd-phase-7-final.md](.knowledge/prd-phase-7-final.md) — Freeze & Packaging (always run, hard stop)

## Reference / scaffolding
- [.knowledge/glossary.md](.knowledge/glossary.md) — beginner's glossary of tech terms used across this tree
- [.knowledge/env-network.md](.knowledge/env-network.md) — SSL bypass, TIKTOKEN_CACHE_DIR, Ollama, ports, `.env` keys, run commands
- [.knowledge/citations.md](.knowledge/citations.md) — dataset/model provenance for the README
- [.knowledge/extra-credit.md](.knowledge/extra-credit.md) — §8 backlog, INCLUDE/SKIP as decided
- [.knowledge/errors-solved.md](.knowledge/errors-solved.md) — error signature → root cause → fix

## Hard schedule anchors (non-negotiable, computed from H+1:30 @ Fri 10:30)
- Handover: Fri 09:00 (H+0:00)
- Demo-complete checkpoint: Fri 20:30 (H+11:30)
- **FEATURE FREEZE: Sat 09:30 (H+24:30)**
- **SUBMISSION: Sat 11:00 (H+26:00)**

Full per-phase clock times live in each `prd-phase-N.md` and in `state-progress.md`.

---

## Maintenance protocol — standing instructions for every session, every step

1. **Write to `state-progress.md` only after a step is VERIFIED working by the human.** Never
   mark a step done based on the AI's own belief that it worked — "written" and "verified" are
   different states, and the phase acceptance checklists say so explicitly.
2. **Use targeted edits, never full-file rewrites, on knowledge nodes.** A node is a shared
   long-lived artifact; a full rewrite destroys history other steps may depend on.
3. **Read only the nodes a given step names.** Do not preemptively load the whole `.knowledge/`
   tree into context "to be safe" — this index already tells you what a phase needs.
4. **Never echo a node's full contents back into chat.** Quote the one relevant line; the human
   can open the file.
5. **Split any node that exceeds ~200 lines** into two topic files immediately and update this
   index plus the `related:` frontmatter of anything that linked to it.
6. **Never change a product decision recorded in `decisions-log.md` or `PRD_FINAL.md`.** If a
   phase surfaces a reason a decision should change, stop and tell the human — do not silently redecide.
7. **Every node opens with YAML frontmatter** (`type/title/status/updated/related`). Keep
   `status` honest: `draft` until Phase 1 schema freeze, `active` while in use, `done` once its phase is closed.
8. **Secrets never get copied into `.knowledge/` files.** Reference `backend/.env` by key name only.
9. **Keep `.okf/` in sync with `.knowledge/` and the code.** After any code change that affects a
   concept documented in `.okf/` (a new/removed module, changed provider/routing behavior, a new
   endpoint, a schema change), update the corresponding `.okf` concept in the same session — don't
   wait to be asked. Use the `okf` skill's **maintain** mode: update the affected concept's body and
   `generated.at`, fix cross-links, update the relevant `index.md`/`log.md`, then validate with
   `okf:validate --strict` before finishing. Skip the update only for changes with no knowledge
   impact (formatting, typo fixes, dependency bumps that don't change behavior).
