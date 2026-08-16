---
type: reference
title: Beginner's Glossary
status: active
updated: 2026-08-16
related: [../architecture/../architecture/arch-overview.md, ../architecture/../architecture/api-contract.md, ../domain/../domain/domain-agents.md, ../domain/../domain/domain-guardrails.md, ../domain/../domain/domain-privacy.md]
---

Plain-language definitions for terms used across the `.knowledge/` tree, written for a
beginner-to-intermediate developer. Not a spec — see the linked node for the real contract.

- **LLM / SLM** — Large/Small Language Model. LLM = the big reasoning-capable models reached
  through whichever provider is active for a session (Gemini, OpenRouter, or the legacy TCS
  gateway — see Gateway/Provider below; originally GPT-4o/DeepSeek R1 on TCS only). SLM = smaller
  local Ollama models, used for narrow tasks (redaction, classification) where a full LLM is
  overkill or where data shouldn't leave the machine.
- **Gateway / Provider** — originally `https://genailab.tcs.in/v1`, the TCS GenAI Lab's
  OpenAI-compatible proxy, called like OpenAI's API with a different base URL. Since the
  multi-provider pivot (`backend/providers.py`), this is one of **6** providers
  (gemini/openrouter/openai/grok/custom/tcs) selectable per session; Gemini is the public-deploy
  default, TCS is a legacy/gated option reachable only on the TCS network. See models-routing.md.
- **Ollama** — a local server that runs SLMs directly on this machine, no network call. Check
  what's installed with `ollama list`; never download new ones mid-hackathon.
- **MCP (Model Context Protocol)** — a standard way for an agent to call an external tool/system
  (here: our 4 simulators) with typed, declared functions — instead of hand-rolled API glue.
  One local MCP server per simulated system (Monitoring, ITSM, Tracker, CMDB).
- **A2A (Agent-to-Agent)** — a standard envelope/handshake for one agent to hand work to another
  agent (with an "Agent Card" describing what it can do). We use exactly **one** A2A handoff
  (Supervisor → one specialist) to prove the pattern, not to route all traffic.
- **Supervisor / specialist agents** — our orchestration shape: one Supervisor agent receives a
  signal, decides which specialist agent handles it, and validates the specialist's typed result
  before acting. Specialists never call each other directly.
- **MaintenanceSignal** — the one canonical data shape every intake path (alert, voice, image)
  gets converted into before anything else touches it. Defined in `api-contract.md`.
- **RAG (Retrieval-Augmented Generation)** — instead of asking a model to "know" our runbooks,
  we search (retrieve) the relevant chunks first and hand them to the model as context.
- **Chroma** — the vector database that stores embedded chunks (runbooks, postmortems, ticket
  history) so we can semantically search them ("find runbooks like this incident").
- **Embedding** — turning text into a list of numbers (a vector) that captures its meaning, so
  similar texts end up numerically close. We use `text-embedding-3-large` via the gateway.
- **Chunking (structural)** — splitting a long runbook into pieces small enough to retrieve
  individually, cut at heading/step boundaries (not mid-instruction) — so a retrieved chunk is
  never half of a dangerous production step.
- **Negative knowledge base** — a Chroma collection of remediations that were tried and *failed*,
  so agents can avoid repeating a known-bad fix, not just find known-good ones.
- **Blast radius** — how much of the system a proposed action could affect if it goes wrong
  (used to decide whether an action needs human approval).
- **Policy gate / guardrails** — deterministic (non-LLM) checks that run before any action is
  allowed to execute — confidence floor, blast-radius limits, the "Fake Fix Detector."
- **Fake Fix Detector** — a guardrail that catches remediations that *look* plausible but don't
  actually match the evidence (a specific anti-hallucination check, see `domain-guardrails.md`).
- **Autonomy ladder** — a staged trust model (e.g., suggest-only → approve-to-run → auto-run for
  low-risk actions). We display its state; we do not build a live auto-promotion engine.
- **DPDP** — India's Digital Personal Data Protection Act; the legal basis referenced in
  `domain-privacy.md` for why we scrub personal data before it reaches any model.
- **Scrubber** — the step that strips/masks personal data out of intake content, run right after
  any modality (voice/image) is converted to text, before anything else sees it.
- **Whisper** — the speech-to-text model used for voice intake.
- **Llama Vision** — the original image-understanding model picked for image/screenshot intake;
  its deployment was later confirmed permanently gone (see models-routing.md). Now a historical/
  legacy label — the vision role's actual model is provider-dependent (see Gateway/Provider above),
  and only the legacy `tcs` provider's vision role still traces back to that original substitution
  (gpt-4o).
- **CMDB (Configuration Management Database)** — inventory of IT assets ("Configuration Items")
  and how they relate to each other; here it's a simulator, not a real one.
- **ITSM (IT Service Management)** — the ticketing/incident system category; here, our own
  FastAPI simulator standing in for something like ServiceNow.
- **Simulator** — our own thin FastAPI app that mimics a real external system's API shape
  (real field names, realistic data) — never a real third-party SaaS, always labelled as such.
- **JWT (JSON Web Token)** — the signed token issued at login and sent on every API call to prove
  who's making the request; here, auth is simulated (no real identity provider).
- **SSL bypass (`verify=False`)** — corporate network's proxy breaks normal HTTPS certificate
  checks, so outbound calls disable verification; a hackathon-network workaround, not a
  production practice.
- **`TIKTOKEN_CACHE_DIR`** — tiktoken (OpenAI's tokenizer library) normally downloads data files
  from the internet on first use; pointing this env var at a local folder avoids that blocked download.
- **Turn cap** — a hard limit on how many reasoning steps/tool calls an agent can take before it
  must stop, to prevent runaway loops (research shows more turns isn't reliably better).
- **Provenance** (`data/PROVENANCE.md`) — a record of which script generated which synthetic
  dataset and when, so nothing looks like unexplained/mystery data at judging time.
