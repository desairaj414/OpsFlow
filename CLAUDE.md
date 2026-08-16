# CLAUDE.md — Hub Index

Thin index only. Do not paste node contents here. Read a node when a step names it; do not
pre-read the whole tree. Product decisions live in [PRD_INITIAL.md](.knowledge/reference/PRD_INITIAL.md)
(frozen, do not re-decide; moved+renamed from root `PRD_FINAL.md` 2026-08-17) — this `.knowledge/`
tree is its execution-ready conversion for an executing AI session.

`.knowledge/` is organized by category, not flat: top-level for the highest-frequency files
(state-progress, decisions-log, rules), `domain/` for domain-behavior nodes, `architecture/` for
system-design nodes, `reference/` for everything else (glossary, provenance, historical records).
Restructured 2026-08-17 — see `decisions-log.md`'s newest entry.

This repo also has a portable OKF (Open Knowledge Format) v0.2 bundle at [.okf/](.okf/) — a
one-concept-per-file distillation of this tree for outside readers (resume reviewers, anyone
without this session's context). `.knowledge/` stays the authoritative execution log; `.okf/` is
derived from it, not a replacement. See `.okf/index.md` for its entry point.

## Project
- **Name:** my-hackathon-app — TCS AI Fridays S2, Cross-Stack Maintenance Control Plane
- **Stack:** FastAPI (backend, async) + Next.js frontend (App Router, Tailwind v4, Turbopack). The
  original Vite/React scaffold was migrated to Next.js in Phase 4 (human confirmed 2026-08-07; see
  [decisions-log.md](.knowledge/decisions-log.md)) — migration is complete, not a pending item.
- **LLM endpoint:** originally a single hardcoded TCS GenAI Lab gateway; post-submission (see
  `.knowledge/state-progress.md`'s POST-SUBMISSION WORK note) pivoted to a 6-provider registry
  (`backend/providers.py` — Gemini default, OpenRouter fallback, TCS retained as a legacy/gated
  option, plus OpenAI/Grok/custom for Bring Your Own Key) so the app runs as a public demo, not
  just on the TCS network. Local Ollama SLMs still back the offline-fallback chain and the PII
  scrubber's name-detection pass. See `.okf/architecture/provider-registry.md` for the full table.
- **Problem statement:** AI-Powered Multi-Agent Workflow Automation for IT Application Maintenance — see [PRD_INITIAL.md](.knowledge/reference/PRD_INITIAL.md)

## Read first, every session
- [.knowledge/state-progress.md](.knowledge/state-progress.md) — live single source of truth. Read this before touching anything.
- [.knowledge/decisions-log.md](.knowledge/decisions-log.md) — resolved decisions, do not re-litigate.
- [.knowledge/state-progress-history.md](.knowledge/state-progress-history.md) — closed/superseded-step detail (everything through the original hackathon build, plus the archived phase-by-phase narrative from before phase-based tracking was retired 2026-08-17), split out whenever state-progress.md hit ~200 lines. Only open on demand, not every session.
- [.knowledge/decisions-log-history.md](.knowledge/decisions-log-history.md) — every 2026-08-07 (hackathon-day) decision, split out whenever decisions-log.md hit ~200 lines. Only open on demand.

## Standing rules (re-read on every coding step, not once)
- [.knowledge/rules-backend.md](.knowledge/rules-backend.md) — commenting standard, module layout, honesty rule (backend)
- [.knowledge/rules-frontend.md](.knowledge/rules-frontend.md) — commenting standard (frontend)

## Architecture & contracts (`.knowledge/architecture/`)
- [arch-overview.md](.knowledge/architecture/arch-overview.md) — tier diagram, routing principle, orchestration shape, protocol layer
- [architecture-as-built.md](.knowledge/architecture/architecture-as-built.md) — as-implemented agent-by-agent breakdown (LLM/SLM/RAG/deterministic, per step)
- [architecture-as-built-metrics.md](.knowledge/architecture/architecture-as-built-metrics.md) — every Overview-tab metric's exact computation (split out of architecture-as-built.md)
- [schema-db.md](.knowledge/architecture/schema-db.md) — SQLite + Chroma schema
- [api-contract.md](.knowledge/architecture/api-contract.md) — canonical `MaintenanceSignal`, MCP tool contracts, A2A Agent Card
- [models-routing.md](.knowledge/architecture/models-routing.md) — model routing table, trade-offs, actual `.env` model-id mapping

## Domain nodes (`.knowledge/domain/`)
- [domain-workflows.md](.knowledge/domain/domain-workflows.md) — incident / patch / performance-tuning parity
- [domain-agents.md](.knowledge/domain/domain-agents.md) — supervisor + specialist chain, orchestration rules
- [domain-guardrails.md](.knowledge/domain/domain-guardrails.md) — policy gate, confidence floor, Fake Fix Detector, bias mitigations
- [domain-multimodal-intake.md](.knowledge/domain/domain-multimodal-intake.md) — voice (Whisper) + vision (Llama Vision) intake
- [domain-privacy.md](.knowledge/domain/domain-privacy.md) — DPDP basis, scrubber, audit trail, retention

## Reference / scaffolding (`.knowledge/reference/`)
- [glossary.md](.knowledge/reference/glossary.md) — beginner's glossary of tech terms used across this tree
- [env-network.md](.knowledge/reference/env-network.md) — SSL bypass, TIKTOKEN_CACHE_DIR, Ollama, ports, `.env` keys, run commands
- [citations.md](.knowledge/reference/citations.md) — dataset/model provenance for the README
- [future-plans.md](.knowledge/reference/future-plans.md) — scoped, not-yet-built backlog (what used to be tracked as Phase 6 "extra credit")
- [errors-solved.md](.knowledge/reference/errors-solved.md) — error signature → root cause → fix
- [session-workflow.md](.knowledge/reference/session-workflow.md) — copy-paste session close-out / start-up prompts that keep `.knowledge/`+`.okf/` in sync across a fresh-session split
- [session-log.md](.knowledge/reference/session-log.md) — human-facing "what happened each session" journal, git-commit-anchored, exempt from the 200-line rule
- [TCS_HACKATHON_FINDINGS.md](.knowledge/reference/TCS_HACKATHON_FINDINGS.md) — initial gateway/model/environment verification (moved from root `PHASE0_FINDINGS.md`)

**No more phase-gated execution plan.** The original PRD was executed as a numbered phase sequence
(Phase 0 through a Final Phase) through the hackathon's actual submission (commit `6299a26`,
2026-08-08). Phase-based tracking was retired 2026-08-17 once every remaining phase item was
individually triaged (build it, recognize it was already done elsewhere, or scope it into
`future-plans.md`) — see `decisions-log.md`'s 2026-08-17 entry and `state-progress.md`'s top note.
[PRD_INITIAL.md](.knowledge/reference/PRD_INITIAL.md) remains the frozen original product spec; it
is read for context, not executed step-by-step anymore.

---

## Maintenance protocol — standing instructions for every session, every step

1. **Write to `state-progress.md` only after a step is VERIFIED working by the human.** Never
   mark a step done based on the AI's own belief that it worked — "written" and "verified" are
   different states.
2. **Use targeted edits, never full-file rewrites, on knowledge nodes.** A node is a shared
   long-lived artifact; a full rewrite destroys history other steps may depend on.
3. **Read only the nodes a given step names.** Do not preemptively load the whole `.knowledge/`
   tree into context "to be safe" — this index already tells you what's relevant.
4. **Never echo a node's full contents back into chat.** Quote the one relevant line; the human
   can open the file.
5. **Split any node that exceeds ~200 lines** into two topic files immediately and update this
   index plus the `related:` frontmatter of anything that linked to it.
6. **Never change a product decision recorded in `decisions-log.md` or `PRD_INITIAL.md`.** If new
   work surfaces a reason a decision should change, stop and tell the human — do not silently redecide.
7. **Every node opens with YAML frontmatter** (`type/title/status/updated/related`). Keep
   `status` honest: `draft` while still being defined, `active` while in use, `done` once genuinely closed.
8. **Secrets never get copied into `.knowledge/` files.** Reference `backend/.env` by key name only.
9. **Keep `.okf/` in sync with `.knowledge/` and the code.** After any code change that affects a
   concept documented in `.okf/` (a new/removed module, changed provider/routing behavior, a new
   endpoint, a schema change), update the corresponding `.okf` concept in the same session — don't
   wait to be asked. Use the `okf` skill's **maintain** mode: update the affected concept's body and
   `generated.at`, fix cross-links, update the relevant `index.md`/`log.md`, then validate with
   `okf:validate --strict` before finishing. Skip the update only for changes with no knowledge
   impact (formatting, typo fixes, dependency bumps that don't change behavior).
