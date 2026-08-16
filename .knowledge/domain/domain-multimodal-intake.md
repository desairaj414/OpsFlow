---
type: domain
title: Domain — Multimodal Intake (Voice + Vision)
status: active
updated: 2026-08-16
related: [../architecture/../architecture/api-contract.md, ../architecture/../architecture/models-routing.md, domain-privacy.md]
---

From PRD §2.4 D1 (core, not stretch) and §3.2. One `intake/` component, three entry paths, one
canonical [`MaintenanceSignal`](../architecture/api-contract.md) object — this is why voice+vision is affordable:
they share the normaliser, the scrubber, and everything downstream.

## Alert path (primary, unchanged)
HTTP ingestion from the monitoring simulator. Clause C3 is not weakened by adding voice/image — the
alert trigger remains primary.

## Voice path (Whisper) — scoped to commands, not free-form dictation
Audio → Whisper → text → **deterministic closed-vocabulary intent parser** (no LLM, see
[models-routing.md](../architecture/models-routing.md)) → an action against an existing API.
Supported intents (do not expand this list without the human's sign-off — it is a deliberate,
audited scope):
- show open incidents / show P1s
- show incident X
- approve X
- reject X with reason
- what changed on CI Y
- start scenario Z

Every voice action lands in the audit log with `modality: voice`. **Destructive or approving
intents are confirmed on screen before executing** — a misheard "approve" must never commit a
production change.

## Vision path (originally Llama Vision — model is provider-dependent since the multi-provider
pivot, see "Implemented 2026-08-07" below and models-routing.md)
Paste/upload a screenshot (error dialog, stack trace, monitoring chart). Model extracts error text,
identifiers, timestamps, apparent service names → normalised into `MaintenanceSignal` → **shown to
the user for confirmation before entering a workflow** → cited thereafter as `IMG-nnn` so provenance
survives into the diagnosis.

## Both paths are additive
Alert trigger stays primary (clause C3). Voice and image are additional entry points, never replacements.

## Implemented 2026-08-07
- Voice: `backend/intake/voice_path.py` + `voice_intent.py` (Phase 2). Real Whisper call, scrub
  runs before intent parsing (tested). **No real recorded speech sample exists in this repo** —
  see PRD §6.1 test-data requirement below, still owed before Phase 5.
- Vision: `backend/intake/vision_path.py`, `api_client.get_llm(role="vision", ...)` — model is
  provider-dependent (`backend/providers.py`): Gemini (public-deploy default) uses
  `gemini-flash-lite-latest`, OpenRouter uses `nvidia/nemotron-nano-12b-v2-vl:free`, OpenAI/Grok/
  Custom fetch or accept a manual model id, and only the legacy `tcs` provider resolves to gpt-4o
  (the original Llama Vision substitute, see models-routing.md). Real extraction tested against a
  synthetic error-dialog screenshot with genuine readable text.
- Bridge into a real workflow: `backend/orchestrator/intake_adapter.py` — enforces the
  confirmation gate in code (an unconfirmed signal is rejected, tested), not just as a UI convention.

## Bias created by this feature (must be raised unprompted, see [domain-guardrails.md](domain-guardrails.md))
Accent/speech-pattern bias (voice) and image-context bias (vision) — mitigations listed in
[domain-guardrails.md](domain-guardrails.md), not repeated here.

## Test data requirement (PRD §6.1)
At least 2 deliberately noisy/accented voice samples and 1 low-quality/legacy-UI screenshot in the
scenario library (PRD §5 Phase 5) — these exist because §2.5 claims the system handles them; an
untested accessibility claim is a liability.

## Do not re-decide
Command-scoped voice (not free dictation), mandatory confirmation-before-action on both paths, and
"alert stays primary" are resolved decisions — see [decisions-log.md](../decisions-log.md).
