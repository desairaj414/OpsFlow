> **Moved and renamed 2026-08-17** from the repo root (`PRD_FINAL.md`) to `.knowledge/PRD_INITIAL.md`
> — "initial" because this is the original hackathon-submission spec, frozen and superseded in
> practice by everything post-submission work has actually built (multi-provider architecture,
> public hosting, etc. — see `decisions-log.md`). Content below is otherwise byte-identical to the
> original; still frozen, still not re-decided, still the source `.knowledge/` was originally
> distilled from. See `CLAUDE.md`'s hub index for how this fits the rest of the knowledge tree.

# PRD FINAL — Cross-Stack Maintenance Control Plane
### TCS AI Fridays Season 2 — Regional Round
### Problem Statement: AI-Powered Multi-Agent Workflow Automation for IT Application Maintenance

---

## 0. CONSTRAINTS — STATED ONCE, BINDING ON EVERYTHING BELOW

**Stack**
- Frontend: Next.js + shadcn/ui
- Backend: FastAPI (async)
- Storage: SQLite (transactional/state), Chroma (vector/RAG). Choice per use case, not per habit.

**Models — Handbook-listed only**
- Via the provided gateway (genailab.tcs.in): `gpt-4o-mini`, DeepSeek V3 / R1, **Llama Vision**, Phi,
  **Whisper**, `text-embedding-3-large`
- Local SLMs via Ollama, already installed on lab laptops. **Verify with `ollama list`. Never download.**
- **With voice and vision now in core, we use six of the seven listed models in the primary path.**
  Say that out loud — it demonstrates we read the toolbox rather than defaulting to one chat model.

**The gateway-vs-external distinction — say this out loud to the jury**
> "Every model call goes to the TCS-provided GenAI Lab gateway or to a model running locally on this
> laptop via Ollama. There is no external Model-as-a-Service dependency anywhere in the primary
> solution. The 'ServiceNow' and 'Jira' systems you see are API-compatible simulators we wrote in
> FastAPI — we are not calling any vendor SaaS. **MCP and A2A are open protocols, not services: our
> MCP servers and A2A endpoints run on this laptop and call nothing outbound.**"

This satisfies Handbook FAQ 13.10.18. A juror seeing a `ServiceNow` panel, or hearing "MCP," could
reasonably assume a third-party call. **Pre-empt it in the demo script, on a slide, and in the README.**
The single exception is the optional real-Jira portability probe (§4.21) — if taken, it must be
labelled on screen as an optional external check outside the primary solution.

**Network fixes (Phase 0 verifies both)**
- `httpx.Client(verify=False)` / `httpx.AsyncClient(verify=False)` — SSL verification bypass
- `os.environ["TIKTOKEN_CACHE_DIR"] = "<local path>"` — set before any tiktoken-dependent import

**Honesty rule — non-negotiable**
Lab machines are CPU-only. We have **not** trained or fine-tuned any LLM and will never say we have.
Our work is: **prompting, model routing, RAG, deterministic rule engines, protocol implementation, and
— only where genuinely executed — lightweight classical ML trained on CPU (scikit-learn scale).** If a
slide, README line, or spoken answer implies fine-tuning, it is a bug. Fix it.

**Code commenting standard (Handbook §8.5 grades this)**
- Every function / React component: one short purpose comment (what it is for, not what each line does).
- Inline comments explain **WHY**, reserved for non-obvious logic: regex patterns, routing thresholds,
  confidence cut-offs, guardrail conditions, correlation window sizes, chunk-boundary rules, MCP/A2A
  schema choices.
- No line-by-line narration of obvious code. `# increment counter` is worse than no comment.
- Module layout: `agents/`, `adapters/`, `mcp_servers/`, `guardrails/`, `orchestrator/`, `intake/`,
  `chunking/`, `eval/`. One responsibility per module.

**Working method — how Claude is used across this build**
Claude is a build participant, not just a document generator. Concretely, for every phase in §5 there
is a named "Claude assists with" line, and across the event Claude will: write the synthetic-data
generators; write the four simulated systems (ITSM, Tracker, Monitoring, CMDB) and their MCP servers;
write the A2A Agent Card and endpoint; write the chunker and its build-failing assertion script; write
the scrubber and its unit tests; write agent prompts and the orchestrator; write the Next.js
components; write the eval harness; and debug whatever breaks. **Two rules that make this work:**
1. **Freeze the canonical schemas at the end of Phase 1 and paste them into every later request.**
   Claude has no memory of your repo between sessions; the schemas are the shared context.
2. **Ask for one module at a time with its purpose comment standard restated.** Whole-app requests
   produce code nobody on the team can walk a juror through — and §8.5 grades exactly that walkthrough.

---

## 1. PROBLEM RESTATEMENT & COVERAGE MAP

### 1.1 Restatement in our own words

IT application maintenance teams repeat the same three classes of work forever — patching systems,
tuning performance, and resolving incidents — but they do it by hand, across tools that do not talk to
each other. The monitoring stack knows something is wrong, the ticketing system holds the human
conversation about it, and the CMDB is supposed to know what is actually deployed and what depends on
what; none of these three agree with each other, and stitching them together is itself a hard
engineering problem. The result is slow, inconsistent, expensive work where the same incident gets
diagnosed from scratch by a different engineer every time. The proposition is that a coordinated team
of AI agents — each owning one narrow step, handing off to the next under supervision — can turn that
manual relay race into a repeatable, auditable workflow that runs from "signal received" to "ticket
closed, CMDB updated, knowledge captured." The prototype has to prove the *coordination*, not just the
chat.

### 1.2 Clause-by-clause coverage map

Every clause of the issued statement, with the feature that satisfies it. **Unmapped clauses are
flagged in bold, not dropped.**

#### A. Problem narrative

| # | Clause (near-verbatim) | Feature that satisfies it |
|---|---|---|
| A1 | "recurring tasks such as patch management" | **Patch & Maintenance Window workflow** — groups pending patches by CI dependency and risk, proposes windows, routes for approval |
| A2 | "performance tuning" | **Performance Tuning workflow — full parity, not a stub.** Same agent chain, different runbook class and a different verification criterion (sustained metric improvement over a window, not alert-cleared). See §2.4 |
| A3 | "incident resolution" | **Incident Resolution workflow** — the reference chain: Correlate → Enrich → Diagnose → Plan → Gate → Approve → Execute → Verify → Sync → Learn |
| A4 | "relying on manual procedures and fragmented tools" | **MCP-exposed adapter layer** over four simulated systems + the **Unified Incident Record**, replacing manual cross-tool copying |
| A5 | "inefficiency, inconsistent execution, delayed issue resolution" | **Runbook-grounded planning** (same input → same plan, reproducibly) + metrics on manual-steps-avoided and time-to-plan |
| A6 | "Integrating monitoring data, ticketing systems, and CMDBs is complex" | **Adapter + MCP server pattern** with a shared canonical schema; each adapter swappable and independently testable |
| A7 | "AI-driven multi-agent orchestration" | **Supervisor-and-specialists orchestrator** (deliberately 2-level, §3.4) with typed handoff contracts; **one handoff carried over A2A with a signed Agent Card** (§3.8) |
| A8 | "improve consistency, reduce manual effort, accelerate problem resolution" | **Success Metrics panel** (§2.6) instrumented from real run telemetry, never hardcoded |
| A9 | "higher operational costs and reduced system reliability" without automation | **Baseline-vs-automated comparison view** + cost-per-incident meter (§8) |

#### B. Data considerations

| # | Clause | Feature |
|---|---|---|
| B1 | "monitoring metrics and alerts" | Synthetic alert stream (JSON), metric time-series per CI |
| B2 | "ticketing and incident management data" | Simulated ITSM + tracker stores with realistic field shapes (`sys_id`, state codes, work notes / Jira issue JSON) |
| B3 | "configuration management databases" | CMDB store: ~200 CIs with relationships, owners, environments, criticality, patch levels |
| B4 | "historical maintenance logs" | 400–600 closed historical tickets + postmortems → RAG corpus |
| B5 | "data volume moderate" | Sized deliberately: hundreds of records, not millions. SQLite + Chroma is the correct call at this volume — present it as a *reasoned* choice, not a shortcut |
| B6 | "quality includes data completeness and accuracy" | **Data Quality Gate** (completeness score, staleness flag) + **Drift Detector** + **Drift-vs-Truth split screen** (§2.4) |
| B7 | "privacy compliance for operational data" | **PII/Secret Scrubber** at every model boundary + immutable audit trail (§1.5, §2.5) |
| B8 | "preprocessing involves event correlation" | **Deterministic correlation engine** (fingerprint + time-window + topology clustering) — classical ML, not LLM |
| B9 | "preprocessing involves workflow modeling" | **Declarative workflow definitions (YAML/JSON)** — the agent graph is data, not hardcoded control flow. This is also what makes A2 affordable at full parity |
| B10 | "synthetic maintenance scenarios for testing" | **Scenario Library** — 10–12 named replayable scenarios (§6) doubling as the test suite, covering all three task families |
| B11 | "synthetic or anonymized data where appropriate" | 100% synthetic, provenance-tracked (§6.5) |

#### C. Solution expectations

| # | Clause | Feature |
|---|---|---|
| C1 | "A web platform" | Next.js cockpit (§7) |
| C2 | "multi-agent workflows automating maintenance tasks" | 7–9 specialist agents under a supervisor, across three workflow types |
| C3 | "triggered by monitoring alerts" | Alert ingestion endpoint + live simulator; workflows start on trigger, not on a button. **Voice and image intake are additional entry points, never replacements** |
| C4 | "managing tickets" | Create / enrich / link / comment / transition across both simulated ticket systems |
| C5 | "updating CMDBs" | Proposed CI updates, human-approved, written back with audit entry |
| C6 | "intelligent scheduling" | Maintenance Window logic — dependency-aware, blackout-aware, SLA-aware |
| C7 | "remediation recommendation" | Ranked plans from the approved runbook catalog with evidence, confidence and blast radius — **filtered against the Negative Knowledge Base** (§2.4) |
| C8 | "real-time dashboards" | Live ops board (SSE) + metrics + eval views |
| C9 | "Integrations with monitoring APIs" | Monitoring adapter, exposed as an MCP server |
| C10 | "…ticketing APIs" | ITSM adapter + Tracker adapter, exposed as MCP servers |
| C11 | "…CMDB APIs" | CMDB adapter, exposed as an MCP server |
| C12 | "reduction in manual tasks" | Metric: manual steps avoided per run, from each runbook's declared human-step count |
| C13 | "incident resolution time" | Metric: signal→plan and signal→verified-resolution vs a stated manual baseline |
| C14 | "user satisfaction" | **Approval rate + edit rate** captured from every HITL decision, with reason capture. Stated honestly as a *proxy*, not a satisfaction survey — see flag 1 |
| C15 | "prototype demonstrates end-to-end workflow automation" | The golden-path demo, run live, plus one scenario from each of the other two task families |
| C16 | "…and multi-agent coordination" | **Agent Trace Viewer** — visible handoffs are the proof — plus the **A2A Agent Card** as protocol-level evidence |

#### 🚩 FLAGGED — clauses with residual weakness

1. **C14 "user satisfaction."** We cannot measure real satisfaction in a hackathon. We implement
   thumbs-up/down with reason capture on every AI recommendation, and report **approval rate and edit
   rate** as the proxy. **Say the word "proxy" out loud.** The data also feeds the Negative Knowledge
   Base, so the feedback loop is load-bearing rather than decorative.
2. **B9 "workflow modeling"** is ambiguous in the source text. We read it as *modelling the maintenance
   workflow itself* (declarative agent graph). It could also mean *process-mining historical logs to
   discover the workflow*. If a juror presses, acknowledge the second reading and explain why we chose
   the first. See Q9.2.
3. **Nothing else is unmapped.** With performance tuning restored to parity, every named clause of the
   statement now has a feature behind it. That sentence itself is worth saying in the pitch — the
   briefing flagged "not all aspects being tackled" as a past-round failure, so demonstrating complete
   coverage is a scored behaviour, not just good hygiene.

### 1.3 Guidance-block coverage (the jury's implicit rubric)

| Guidance | Where we answer it |
|---|---|
| Intuitive interface aligned to workflow/user journey | §7 cockpit, role-shaped views |
| Conversation / visualization / hybrid | §7 — hybrid: visual cockpit primary, **voice commands** as the conversational modality |
| Data quality, completeness, preprocessing, context-based retrieval | §6, Drift Detector, §6.4 chunking spec |
| Suitable storage for structured + unstructured | SQLite + Chroma, justified per data type |
| Aggregation, correlation, summarization | Correlation engine, incident narrative synthesis |
| Pragmatic short/mid-term roadmap | §2.7 |
| Balance autonomy with human oversight | Tiered HITL + Autonomy Ladder (§2.4) |
| Feedback loops, changing requirements | Approve/edit/reject capture → knowledge index **and Negative KB**; declarative workflows |
| Grounded, referenced, context-aware outputs | Every claim carries artifact IDs; no citation → no claim |
| Guardrails: leakage, unsafe recommendations, unsupported decisions | §2.5 — scrubber, policy gate, confidence floor, runbook-bounded action space |
| Explain reasoning, assumptions, limitations, confidence | Trace viewer + mandatory "what I could not verify" block |
| Separate AI layer / enterprise systems / third-party | §3.5 tier diagram — **draw this, jurors ask** |
| Modular multi-tier architecture | Module layout, §0 |
| Memory, caching, token strategy | §3.6 |
| Framework independence & configurability | MCP adapter layer + A2A handoff + declarative workflows — makes the claim literal |
| Security, privacy, audit logging, access governance | §1.5, §2.5, role switcher |
| Rationale, alternatives, trade-offs | §3.7 — **rehearse this, it is a guaranteed question** |
| Test scenarios, edge cases, varied data, automation | §6 Scenario Library = test suite; eval harness §5 Phase 5 |
| Demo readiness, code walkthrough, dynamic inputs | Final phase (§5) |
| Show GenAI materially beats conventional approach | §2.2 — the honest version, not the hype version |
| **Voice-based commands (accessibility & inclusion)** | **§2.4 Multimodal Intake — CORE** |
| **Image-based input where only text was specified** | **§2.4 Multimodal Intake — CORE** |
| All members can explain full flow | Final phase round-robin rehearsal — **do not skip this** |

### 1.4 Stakeholders implied by the problem

| Stakeholder | What they need | In our UI? |
|---|---|---|
| **L1 Ops / NOC engineer** (primary) | Stop drowning in duplicate alerts; know what to do first | Yes — ops board |
| **L2 / Application SME** | Evidence they can trust, fast, without re-deriving it | Yes — diagnosis + evidence panel |
| **Change / Release Manager** | Nothing risky reaches prod outside a window | Yes — approval queue, blast radius |
| **IT Service Owner / business owner** | MTTR, cost, SLA adherence, "is this working" | Yes — metrics dashboard |
| **Developers (tracker side)** | Incidents that are really bugs land in their backlog *with context* | Yes — cross-system linkage |
| **CMDB / Configuration Manager** | A CMDB that stops rotting | Yes — drift queue |
| **Engineer with hands full, or with a disability affecting keyboard use** | To act without typing | **Yes — voice commands (§2.4). This is the accessibility-and-inclusion stakeholder and it should be named as such in the pitch, not left implicit** |
| **Security / Compliance / DPO** | No secrets or personal data in model calls; provable audit trail | Yes — audit log view |
| **End users / employees who raise tickets** | Their data handled lawfully | **Not a UI user — but a data subject.** This is why §1.5 matters |
| **The AI system itself as an actor** | Must be attributable — every write records *which* agent | Yes — every audit row has an actor |

### 1.5 DOMAIN CHECK

**Domain: IT Operations / IT Service Management (ITSM + ITOM). This is NOT Life Sciences, Healthcare,
or any patient/clinical domain.** No PHI is involved. We will not pretend otherwise and will not bolt
on HIPAA-flavoured language that does not apply — a juror will spot padding.

**Privacy is nonetheless a CORE requirement here, on a different and equally real basis:**

1. **Ticket data contains personal data of identifiable individuals.** Incident descriptions, work notes
   and requester fields carry employee names, corporate emails, phone numbers, employee IDs and manager
   names. Under India's **DPDP Act, 2023** — operationalised by the **DPDP Rules notified November
   2025**, phasing in over an 18-month window into 2027 — this is digital personal data and the
   employer is a Data Fiduciary. Employment processing has a "legitimate uses" basis, but **sending
   that text to a model is a purpose the requester did not contemplate**, and the security-safeguard
   obligation applies regardless. Our position: personal data is redacted *before* it crosses a model
   boundary, so the legitimate-use argument never has to be made.
2. **Operational data carries secrets — a leakage class of its own.** Log excerpts and config dumps
   routinely contain hostnames, internal IPs, connection strings, bearer tokens, API keys and
   service-account names. A prompt containing a live credential is an incident, not a nicety.
3. **Voice and image intake widen the exposure surface, and this must be handled, not just noted.**
   A voice note may name a colleague; a screenshot may contain a whole terminal session, a logged-in
   username, or a token in a URL bar. **Both paths therefore transcribe/extract first, then scrub, then
   pass downstream** — the scrubber sits after the modality converter, never before it. Raw audio and
   raw images are held in memory for the duration of the run and never persisted. *Building the
   accessibility feature and then leaking through it would be the worst possible outcome; say this
   pairing out loud, because it shows the features were designed together rather than bolted on.*
4. **Automated action against production requires attributable authorisation.** "Which agent changed
   this CI, on whose approval, citing what evidence" is the question that decides whether a system like
   this is allowed near production at all.

**Core requirements (not stretch goals):**
- **Scrub-before-send** at every model boundary — regex for structured secrets and identifiers plus a
  local-SLM pass for free-text names — with **reversible tokenisation** so redaction does not destroy
  usability (`svc-payments-prd` → `[HOST_7]`, restored for display to the authorised human, never to
  the model).
- **Immutable audit trail** — append-only: actor (human user or named agent), action, target artifact,
  timestamp, evidence IDs, model used, approval reference, **input modality**. Viewable in the UI.
- **Purpose-limited retention** — scrubbed prompts and traces retained; raw payloads, audio and images
  not persisted beyond the run. Show the config; state the position.
- **Local-model routing for the most sensitive step** — raw log excerpts go to a local Ollama SLM so the
  text never leaves the machine. A privacy *architecture* decision, not a cost one.
- **Consent-and-rights posture, stated honestly** — a full DPDP consent-manager flow is out of scope for
  a prototype and claiming one would be false. We implement data minimisation, purpose limitation and
  auditability; we *document* where a consent/rights layer would attach. Say the second part out loud.

---

## 2. RECOMMENDED SOLUTION & THE MOAT

### 2.1 The product in one paragraph

**A vendor-neutral Maintenance Control Plane that sits *above* the monitoring stack, the ITSM system,
the developer tracker and the CMDB — and owns the seam between them.** Work enters through whichever
door fits the moment: an alert fires, an engineer pastes a screenshot of an error, or an engineer with
hands full speaks a command. A supervisor agent then dispatches specialists that collapse alert noise
into candidate incidents, gather evidence from every system, produce ranked root-cause hypotheses with
citations and confidence, draft a plan from an approved runbook catalog, check it against policy and
blast radius, route it to the right human, execute it, **verify the underlying fault actually cleared
rather than that the alert merely went quiet**, and write the outcome back to every system as one
consistent record plus a reusable knowledge artifact. Every system it touches is reached through
**MCP**; one agent handoff travels over **A2A** with a signed Agent Card, so the same architecture can
delegate to a vendor's own agents. The identical machinery runs three workflow types — incident
resolution, patch management and performance tuning — because the workflow is data, not code.

**Target user (primary): the L2 application maintenance engineer on shift.** Not the CIO, not the end
user. The person who currently has eleven browser tabs open and is deciding which of forty alerts is
the actual problem.

**The exact problem we solve:** *the evidence-gathering and cross-system bookkeeping around a
maintenance task takes longer than the fix, and has to be redone from scratch every time because
nothing learned last time is where the next engineer will look.*

### 2.2 "Why is this better than ChatGPT?" — and "why is this better than ServiceNow's own AI?"

**vs. a general chat assistant.** A chat assistant is a *single-turn advisor with no hands and no memory
of your estate.* It cannot receive an alert, cannot collapse 50 alerts into 3 incidents, does not know
that `svc-payments` depends on `db-orders-prd`, cannot open a ticket, cannot refuse to act during a
change freeze, leaves no audit trail, and — most importantly — **will confidently answer even with no
evidence.** Our output is structurally different: every hypothesis carries the artifact IDs it derives
from, and a hypothesis with no supporting artifact is suppressed at generation. That is an
architectural property, not a prompt.

**vs. ServiceNow Now Assist / Atlassian Rovo — five moves, delivered *before* being asked:**

1. **They are platform-native by design; the problem is cross-platform by nature.** Now Assist's agents
   are built into the Now Platform and reach outside it through IntegrationHub spokes; Rovo is
   Atlassian-native. The industry's own documentation of the ServiceNow↔Jira seam describes exactly the
   failure: ops runs ServiceNow for incidents and change, dev runs Jira, tickets get duplicated,
   statuses contradict each other, and someone maintains a reconciliation spreadsheet. **A vendor's AI
   cannot be neutral about which system is the source of truth. Ours can, because it owns neither.**
2. **They inherit their own data quality; we interrogate it.** ServiceNow's Context Engine grounds its
   agents in CMDB relationships — genuinely strong architecture. But industry estimates put typical CMDB
   accuracy near **60%**, and manually maintained CMDBs reach **30–40% inaccuracy within six months**.
   A CMDB-grounded agent inherits that error rate *silently*, because a stale CMDB does not produce
   ambiguity — it produces **false clarity**. It still answers; it just answers wrong. **Our agents
   treat the CMDB as a hypothesis to verify against observed reality, flag disagreement as drift, and
   propose reconciliation as a first-class workflow.** The **Drift-vs-Truth split screen** dramatises
   this instead of citing it. Give this its own slide.
3. **We are honest about autonomy, and that is a feature.** IBM's ITBench found agents built on
   state-of-the-art models resolve only about **13.8% of real SRE scenarios**; independent analysis of
   multi-agent systems reports failure rates of **41–86.7%**, with roughly **79% of production
   breakdowns** traced to specification ambiguity and coordination breakdown rather than model
   capability. A team promising autonomous incident resolution is either uninformed or overselling.
   **We promise the opposite: evidence-first, confidence-gated, human-approved automation — with
   autonomy earned per runbook by measured evidence.**
4. **⭐ We do not compete with their agents; we can orchestrate them.** A2A is a Linux Foundation project
   that passed **150+ supporting organisations at its April 2026 one-year mark**, with v1.0 stable,
   **signed Agent Cards** for cryptographic identity, and cloud integration across Google, Microsoft and
   AWS — and **ServiceNow is among the participating organisations**. So:
   > *"We're not competing with ServiceNow's agents. We're the neutral orchestrator above them. In
   > production our supervisor discovers a vendor agent through its Agent Card and delegates the
   > vendor-native work to it — while keeping the cross-system reasoning, the policy gate and the audit
   > trail vendor-neutral."*
   This reframes the biggest competitor as a **subordinate component of our architecture.**
   **Rehearse this answer verbatim.**
5. **Deployment reality and data residency.** Now Assist delivers most value to organisations already
   standardised on the platform, and practitioner reviews note it needs substantial configuration
   before it delivers. Our layer sits above whatever exists, and its most sensitive processing runs on a
   local model, so operational text never leaves the estate.

**One sentence for the pitch:**
> "Now Assist makes ServiceNow smarter. We make the *space between* ServiceNow, Jira, your monitoring
> stack and your CMDB smarter — we assume your CMDB is 40% wrong, because it is — and when a vendor
> agent is better at its own platform than we are, we delegate to it over A2A instead of competing."

### 2.3 Technical moat — the four pillars

**(a) Domain-specific guardrails.** Concrete, deterministic, testable:
- **Runbook-bounded action space.** Agents may only propose steps that exist in the approved runbook
  catalog. A free-text remediation cannot be executed — only raised as a *proposal for a new runbook*,
  routed to a human. This eliminates the entire class of "the LLM invented a destructive command."
- **Policy gate (pure Python, no LLM):** change-freeze windows, prod vs non-prod, CI criticality,
  dependency blast radius above threshold, max concurrent changes, required-approver role.
  Deterministic, unit-tested, shown to the jury as code.
- **Confidence floor with an explicit abstain path.** Below threshold the system does not guess — it
  escalates and names the missing evidence. **"I don't know, and here is what I'd need" is a
  first-class output.**
- **Anti-reward-hacking verification ("Fake Fix Detector").** ITBench analysis found **8 of 18
  mitigation problems (44%)** could be "solved" by a generic pod-restart loop — the alert clears, the
  fault injector loses track, and the agent gets credit despite doing nothing about the defect. Our
  Verification Agent requires **two independent signals**: alert cleared **and** the underlying metric
  or health probe recovered and held through a stabilisation window. If only the alert cleared, the
  incident is marked **"symptom suppressed, root cause unconfirmed"** and stays open.

**(b) Automated multi-step workflows** across three task families. Eleven steps, each observable,
attributable and replayable from stored inputs.

**(c) Zero data leakage.** Scrub-before-send at every model boundary — including after voice
transcription and image extraction — reversible tokenisation, local-model routing for the
highest-sensitivity content, no raw payload persistence, full audit trail. Demonstrated live: show the
raw log containing a hardcoded credential, then show the exact prompt that was actually sent.

**(d) Trust and transparency.**
- **Citations.** Every claim references artifact IDs (`ALERT-1043`, `CI-0087`, `INC-2291`, `RB-14 §3`).
  A hypothesis without a citation is suppressed at generation, not filtered afterwards.
- **Calibrated disclaimers, not decorative ones.** "Based on 3 similar historical incidents; confidence
  Medium; not verified against current config" — on the artifact, not in a page footer.
- **Reproducibility.** Temperature 0 for decision steps; every run persists model, prompt version,
  retrieved chunk IDs and raw response. A **Replay** button re-runs a stored scenario and shows whether
  the outcome changed.
- **Explicit limitations block** on every diagnosis: "what I could not verify."

### 2.4 The seven differentiators

| # | Name | The one-line pitch |
|---|---|---|
| D1 | **Multimodal Intake — voice + vision** ⭐ **CORE** | Three doors into the same workflow: an alert, a spoken command, or a pasted screenshot. One intake component, three modalities, one canonical schema |
| D2 | **A2A delegation to vendor agents** | "We don't compete with Now Assist. We can delegate to it." |
| D3 | **Drift-vs-Truth split screen** | Same incident, diagnosed twice — once on the CMDB, once on reality. Watch them diverge |
| D4 | **Fake Fix Detector** | Alert-cleared is not root-cause-resolved, and we are the only ones measuring the difference |
| D5 | **Negative Knowledge Base** | Every RAG on earth indexes successes. We index failures, so the system stops re-proposing what already didn't work |
| D6 | **Autonomy Promotion Ladder** | Autonomy is *earned per runbook by measured evidence*, not switched on globally |
| D7 | **Three workflows, one engine** | Incident, patch and performance run the same agent chain over different declarative definitions — that is what "workflow modeling" bought us |

**D1 — Multimodal Intake, specified (core build)**

One `intake/` component, three entry paths, one canonical `MaintenanceSignal` object. This is why it is
affordable: voice and vision share the normaliser, the scrubber, and everything downstream.

- **Alert path** — the primary trigger, unchanged. HTTP ingestion from the monitoring simulator.
- **Voice path (Whisper)** — **scoped to commands, not free-form dictation.** Audio → Whisper → text →
  a small deterministic intent parser → an action against an existing API. Supported intents:
  *show open incidents / show P1s* · *show incident X* · *approve X* · *reject X with reason* ·
  *what changed on CI Y* · *start scenario Z*. Every voice action lands in the audit log with
  `modality: voice`, and **destructive or approving intents are confirmed on screen before executing** —
  a misheard "approve" must never commit a production change. Framed explicitly as
  **accessibility and hands-free operation**, because that is the category the briefing rewards.
- **Vision path (Llama Vision)** — paste or upload a screenshot of an error dialog, a stack trace, or a
  monitoring chart. The model extracts error text, identifiers, timestamps and apparent service names;
  the result is normalised into the same signal object, **shown to the user for confirmation before it
  enters a workflow**, and cited thereafter as `IMG-nnn` so its provenance survives into the diagnosis.
  This is the "processing image-based inputs when only text was specified" item, and it is genuinely
  realistic — engineers and users paste screenshots constantly.
- **Both paths are additive.** The alert trigger remains the primary path; clause C3 is not weakened.

**D7 — Performance tuning at full parity, and why it is affordable**

The briefing flagged "not all aspects being tackled" as a past-round failure, and the statement names
performance tuning alongside the other two. Restoring it costs less than it appears **because of the
declarative workflow decision (B9)**: the same supervisor, the same specialists and the same guardrails
run all three. What differs is data, not code.

| | Incident Resolution | Patch Management | Performance Tuning |
|---|---|---|---|
| Trigger | Fault alert / voice / image | Patch inventory + schedule | Degradation alert (latency, memory creep, slow query) |
| Runbook class | `remediation` | `patching` | `tuning` |
| Key evidence | Alerts, logs, CI graph, past incidents | Patch inventory, dependencies, change calendar | Metric trend, query stats, resource history |
| Plan output | Remediation steps | Grouped maintenance window | Ranked tuning recommendations |
| **Verification criterion** | Alert cleared **and** health probe recovered | Patch applied **and** no new alerts in window | **Sustained metric improvement across a window** — not a binary clear |
| Autonomy tier | Up to auto-execute (ladder) | Approval required | **Advisory only — never auto-executes** |

That last row is worth saying out loud: **performance tuning is deliberately advisory-only**, because
tuning changes are judgement calls with delayed, ambiguous effects. Choosing *not* to automate
something is a design decision jurors notice.

### 2.5 Bias mitigation — bias that could plausibly enter *this* solution

| Bias | How it enters here | Mitigation we build |
|---|---|---|
| **Retrieval recency/frequency bias** | RAG over historical incidents surfaces common, recent, well-documented failures; a novel incident gets force-fitted to a familiar root cause | Diversity-aware retrieval (MMR-style) and an explicit **"no strong precedent found"** state rather than the nearest weak match. Similarity scores shown in the UI |
| **Instrumentation / documentation bias** | Well-monitored services produce richer evidence and higher-confidence diagnoses; legacy under-instrumented systems get deprioritised — exactly the systems most likely to fail | Confidence scored **relative to evidence available for that CI**, not absolutely, with a "low observability coverage" flag so thin evidence reads as *unknown*, not *fine* |
| **Historical assignment bias** | Routing to whoever historically closed similar tickets entrenches past mis-routing and workload inequality | Routing suggests **role/queue**, never a named individual; reason shown and editable |
| **Alert-verbosity bias** | Modern tools emit rich English; legacy SNMP traps emit terse codes, so LLM triage under-ranks the terse ones | Normalise every signal into the canonical schema *before* any model ranks it |
| **Severity anchoring** | Whatever the monitoring tool labelled "P1" anchors the model's judgement | Priority recomputed from CI criticality + blast radius + SLA; disagreement shown as a delta |
| **Automation bias in the human reviewer** | The most likely real-world harm: a confident-looking plan gets rubber-stamped and the HITL gate becomes theatre | The approval screen shows **the strongest counter-hypothesis and the evidence gaps** alongside the recommendation, and requires a reason on reject-or-edit. **Edit rate** is tracked — an approval rate near 100% is a warning sign, not a success, and we say so during the demo |
| **Accent and speech-pattern bias** *(new — created by D1 voice)* | ASR accuracy varies by accent, and non-native or atypical speech is transcribed worse — so an accessibility feature can be *inaccessible* to exactly the users who need it most | **Voice is command-scoped, not free-form**, so the intent parser matches against a small closed vocabulary rather than requiring perfect transcription; every voice action **displays the parsed intent for confirmation before executing**; keyboard parity for every voice action. **Raise this unprompted — an accessibility feature whose bias you have not examined is a liability, and naming it is exactly the "inclusion" the briefing is asking for** |
| **Image-context bias** *(new — created by D1 vision)* | Screenshots from well-designed modern dashboards extract cleanly; terminal dumps and legacy UIs extract poorly, quietly reintroducing the verbosity bias through a new door | Extraction confidence surfaced to the user, mandatory human confirmation before the signal enters a workflow, and low-confidence extractions marked as unverified evidence in the diagnosis |
| **Negative-KB overcorrection** *(created by D5)* | A remediation that failed once in one context could be blanket-suppressed, hiding the right fix | Negative entries **scoped to CI class and failure signature**, shown as a *caution with reason*, never a silent filter |

The last four rows are the ones to lead with: each is a bias **we introduced by adding a feature**, and
we found it ourselves. That reads as engineering maturity in a way a generic fairness paragraph never
will.

### 2.6 Commercial value

- **Toil reduction.** Correlation is the highest-leverage step: a single incident routinely triggers
  dozens of alerts across independent tools with no shared context, and industry-reported false-positive
  rates for operational alerting sit in the **60–80%** range. Collapsing an alert storm into a handful
  of candidates removes the most expensive human step — deciding what is even happening.
- **Time-to-evidence, not time-to-fix.** Our honest claim is that we compress the *investigation and
  bookkeeping* phase. AIOps correlation is credited with MTTR reductions in the **40–50%** range in
  vendor and Forrester-commissioned studies — cite as *industry context for the opportunity*, never as
  our measured result.
- **Data-quality compounding.** ServiceNow's own published figures associate structured CMDB practice
  with ~**38% faster incident resolution** and ~**82% fewer failed changes**. Our drift loop attacks the
  input to every one of those numbers.
- **Accessibility as commercial value, not charity.** Hands-free operation is a real operational benefit
  during an outage, and accessible tooling widens who can hold an on-call rota.
- **Audit cost.** An append-only attributable action log is the difference between "we think we can
  automate this" and "compliance will let us automate this."

**Success metrics we instrument for real (no fabricated numbers on any slide):**
`alerts ingested → incidents proposed` · `manual steps avoided` · `time signal→plan` and
`signal→verified resolution` vs stated manual baseline · `plan approval rate` and **`edit rate`** ·
**`verified-resolved vs symptom-suppressed`** · `% of diagnoses fully cited` ·
`CMDB drift items detected / reconciled` · `runbooks promoted on the autonomy ladder` ·
`signals by modality (alert / voice / image)` · `tokens + latency + cost per workflow`.

### 2.7 Beyond the hackathon

- **Near term:** replace simulators with real ServiceNow / Jira / Prometheus MCP servers — because the
  adapter is already an MCP boundary, this is a swap, not a rewrite.
- **Mid term:** the Autonomy Promotion Ladder runs continuously, promoting runbooks as their
  verified-resolution rate accumulates. Register vendor agents as A2A peers and delegate platform-native
  work to them.
- **Longer term:** drift reconciliation as a standing service; runbook mining from postmortems;
  expanding voice from a closed command set to open dictation once ASR quality is measured per accent
  rather than assumed.

---

## 3. TECH STACK & MODEL ROUTING

### 3.1 Routing principle

**Route by task shape, not by model prestige.** *Is it deterministic? → don't use an LLM at all.* ·
*Is the content sensitive? → local.* · *Does it need multi-step reasoning? → reasoning model, and only
there.* The first question matters most: **correlation, policy checks, blast radius, voice-intent
parsing and metric math are deterministic and must be code.** Using an LLM for arithmetic or rule
evaluation is the most common hackathon mistake and a juror will call it out.

### 3.2 Routing table (Phase 0 data may rewrite this)

| Task | Model | Why |
|---|---|---|
| Alert normalisation, dedup, correlation clustering | **No LLM** — Python + scikit-learn | Deterministic, fast, reproducible, explainable. Genuine classical ML on CPU |
| Policy gate, blast radius, scheduling constraints | **No LLM** — rule engine | Must be auditable and provably consistent |
| **Voice transcription** | **Whisper** (gateway) | Purpose-built; the only speech model listed |
| **Voice intent parsing** | **No LLM** — closed-vocabulary matcher | A misheard command must never become an unintended action. Deterministic parsing is a *safety* choice, not a cost one |
| **Screenshot / error-image extraction** | **Llama Vision** (gateway) | The only vision model listed; extraction into the canonical schema |
| Entity/PII detection in text, transcripts and extractions | **Local SLM via Ollama** (+ regex first pass) | Highest-sensitivity content never leaves the machine |
| Incident narrative summarisation | `gpt-4o-mini` (gateway) | High volume, low complexity, latency-sensitive |
| Ticket drafting, work notes, comments | `gpt-4o-mini` | Formatting-heavy, low reasoning demand |
| Embeddings (runbooks, postmortems, tickets, negative KB) | `text-embedding-3-large` | The only embedding model listed |
| **Root-cause hypothesis generation & ranking** | **DeepSeek R1** (gateway) | The one step genuinely needing multi-step reasoning over conflicting evidence |
| Remediation / tuning plan drafting from runbooks | DeepSeek V3 | Structured generation, strong instruction following, cheaper than R1 |
| Self-check / critique of the plan before the gate | `gpt-4o-mini` or local SLM | Verification gaps are a top failure category in the literature |
| Offline fallback for demo resilience | Local Ollama SLM | **If the gateway dies mid-demo we must still run** |

Only **Phi** is unused in the primary path — and Phase 0 still smoke-tests it, per the handbook. Six of
seven listed models in genuine use is a talking point.

### 3.3 Trade-offs to state out loud

- **R1 costs latency.** Reasoning models on a busy shared gateway can take tens of seconds. Mitigation:
  R1 runs on **one** step, asynchronously, with the UI streaming progress.
- **More thinking is not always better.** On ITBench, higher turn counts did not reliably mean better
  answers — some high-turn models scored *worse*, because dense incident signal leads agents to keep
  surfacing correlated symptoms past the point of commitment. **Design consequence: hard turn caps and
  explicit termination conditions per agent** — which also addresses the MAST failure mode "unaware of
  termination conditions."
- **Whisper and Llama Vision add latency to their entry paths, not to the main loop.** Both run once at
  intake and produce a normalised object; nothing downstream waits on them again.
- **Local SLMs are weaker.** Use them where the task is narrow (extraction, classification, redaction),
  never where it is open-ended.
- **Cost/latency is a graded artifact, not a footnote.** Log tokens and wall-clock per agent step and
  render it.

### 3.4 Orchestration shape

**Two levels: one Supervisor + specialist agents. Deliberately NOT a deep hierarchy and NOT a free agent
mesh.** Rationale:
- MAST analysis of 1,600+ multi-agent traces attributes **44.2%** of failures to system-design issues
  and **32.3%** to inter-agent misalignment. The problem is architectural, not model quality.
- Uncoordinated multi-agent systems can amplify errors up to ~**17×**, while **centralised architectures
  with validation bottlenecks contain it to roughly 4.4×**. We deliberately chose the
  validation-bottleneck design.
- Practitioner guidance converges on two-level (router + specialists) over both flat and 3+ level designs.

**Concretely:** agents never call each other directly. Each returns a typed result to the Supervisor,
which validates against a schema before dispatching the next. Every agent has an explicit termination
condition and turn cap. **"We constrained the topology on purpose, and here is the failure data that
made us do it" is exactly the design-rationale answer the guidance asks for.**

### 3.5 Architecture tiers — draw this, jurors ask for it

```
┌──────────────────────────────────────────────────────────────────┐
│  PRESENTATION        Next.js + shadcn/ui cockpit                 │
├──────────────────────────────────────────────────────────────────┤
│  INTAKE LAYER        Alert HTTP │ Voice (Whisper) │ Image (Vision)│
│                      → one canonical MaintenanceSignal           │
│                      → SCRUBBER (always after modality convert)  │
├──────────────────────────────────────────────────────────────────┤
│  AI SOLUTION LAYER   Supervisor ── A2A ──▶ one specialist        │
│                      (others in-process, typed contracts)        │
│                      Guardrails · Policy gate · Model router     │
├──────────────────────────────────────────────────────────────────┤
│  ENTERPRISE KNOWLEDGE          │  TRANSACTIONAL SYSTEMS          │
│  Chroma: runbooks,             │  SQLite: incidents, approvals,  │
│  postmortems, history,         │  audit log, workflow state,     │
│  NEGATIVE knowledge base       │  autonomy ladder state          │
├──────────────────────────────────────────────────────────────────┤
│  TOOL / INTEGRATION LAYER — MCP servers (local, one per system)  │
│  Monitoring │ ITSM │ Tracker │ CMDB                              │
├──────────────────────────────────────────────────────────────────┤
│  SIMULATED EXTERNAL SYSTEMS (our FastAPI mocks)                  │
│  ⚠ NOT third-party SaaS. Labelled in UI and README.              │
│  (Optional §4.21: ONE real Jira Cloud portability probe, Ph. 6)  │
└──────────────────────────────────────────────────────────────────┘
   Models: TCS GenAI Lab gateway ▸ + local Ollama ▸ — no external MaaS
   Protocols: MCP (agent→tools) · A2A (agent→agent) — open specs, local endpoints
```

### 3.6 Memory, caching, token strategy

- **Working memory:** current workflow state in SQLite, passed as a compact typed object between agents
  — **never** the full conversation transcript. Full-state rebroadcast is a known token sink and a known
  source of context drift.
- **Episodic memory:** closed incidents + postmortems embedded into Chroma — the feedback loop.
- **Negative memory:** rejected plans and failed remediations, embedded separately, consulted at planning.
- **Semantic memory:** runbooks + CMDB schema.
- **Caching:** hash `(prompt_version, scrubbed_input)` → response, in SQLite. Applies to Whisper and
  Vision too — a replayed demo screenshot does not re-bill the gateway, which also makes the demo fast
  and resilient.
- **Token discipline:** evidence bundles truncated to top-k cited chunks; agents see IDs + extracts,
  never whole documents. Per-step token budget with a hard cap.

### 3.7 Alternatives considered (rehearse — near-certain jury question)

| We rejected | Why |
|---|---|
| Single "do-everything" agent with tools | The statement asks for multi-agent orchestration, and single-agent traces lose role separation and auditability. Honest caveat: research shows single-agent sometimes *outperforms* multi-agent — our justification is auditability and separation of concerns, not raw accuracy |
| Fully autonomous remediation | ~13.8% SRE resolution rate in independent benchmarking |
| LLM-based event correlation | Non-deterministic, expensive, unexplainable, worse than clustering at the task |
| **LLM-based voice intent parsing** | A misheard command reaching an approval action is an unacceptable failure mode. Closed-vocabulary deterministic parsing, with on-screen confirmation |
| **Free-form voice dictation** | Higher ASR error exposure, worse accent robustness, and no clear operational benefit over typing. Command scope is the accessible choice, not the lazy one |
| Off-the-shelf agent framework (LangGraph / CrewAI / AutoGen) | The handbook rewards framework independence and explainability; MCP + A2A already provide the interop a framework would have given us |
| Routing *all* agent traffic over A2A | Real implementation burden for no marginal credit past the first demonstrated handoff |
| An MCP server that "coordinates agents" | A common and visible mistake: MCP exposes tools to agents; coordination is A2A's layer |
| Real ServiceNow PDI as a primary system | Hibernation after ~24h, release after 10 days, possible waitlist, licence framing, lab-network risk — and mocks are *better*, because our scenarios cannot be produced on demand in a real instance |
| Postgres / Neo4j | Overkill at moderate volume; SQLite plus an adjacency table covers CI relationships |
| Naive fixed-size RAG chunking | See §6.4. Splits runbook steps mid-instruction — actively dangerous when the retrieved text is an action to take against production |

### 3.8 Protocol layer — MCP and A2A

**MCP and A2A both sit under the Linux Foundation's Agentic AI Foundation, launched December 2025 with
OpenAI, Anthropic, Google, Microsoft, AWS and Block as co-founders.**

- **MCP connects an agent to tools.** Created by Anthropic (November 2024), donated to the AAIF
  (December 2025); adopted across every major provider.
- **A2A connects an agent to other agents.** Introduced by Google (April 2025), donated to the Linux
  Foundation; **v1.0 stable as of April 2026** with signed Agent Cards, JSON-RPC + SSE transport and
  SDKs in five languages.

| Layer | Protocol | What we build |
|---|---|---|
| Agent → systems | **MCP** | Four local MCP servers (Monitoring, ITSM, Tracker, CMDB) exposing typed tools. Agents call tools through MCP, never bespoke HTTP |
| Agent → agent | **A2A** | **One** Supervisor ↔ specialist handoff over A2A with a real signed Agent Card. The rest stay in-process and typed |
| Future / pitch | **A2A** | The delegation story (§2.2 move 4) |

**Honest scoping:** independent analysis notes A2A's headline adoption numbers are real, but the Linux
Foundation announcement gave no production-deployment counts, and a March 2026 critical analysis
attributed thinner-than-advertised uptake to implementation burden. **So we implement one handoff and
say so.** If Phase 3 runs long, **cut the implementation and keep the argument** — "we designed for it
and did not implement it in the time available" is a perfectly good answer; implying we built it would
be fatal.

---

## 4. FEATURE DECISIONS — RESOLVED

Section 4 of the draft was the argument. This is the outcome. **The trade ledger is here because a
juror may ask what we cut and why — having an answer is worth more than having built everything.**

### 4.0 Trade ledger

v2 of the draft was already at ~17.5h against a 16–18h budget. Voice, vision and full-parity
performance tuning add ~3h. Funded by:

| Cut / reduced | Saved | Why it was affordable |
|---|---|---|
| Scoped chat drawer (was 4.13) | ~1h | **Voice is now our conversational modality**, so the "conversation / visualization / hybrid" guidance is still satisfied — and this removes the "so it's a chatbot" surface we spend §2.2 closing |
| A2A: three handoffs → one | ~0.75h | The architectural claim and the delegation argument need exactly one demonstrated handoff |
| Autonomy Ladder → status panel, not live promotion engine | ~0.5h | The ladder *displayed* makes the point; live promotion is a mid-term roadmap item |
| Maintenance Planner → panel inside Incident Workspace | ~0.5h | It was a screen serving one scenario |
| Simulator field fidelity thinned to ~12 demo-relevant fields | ~0.5h | Authentic field *names* matter to jurors; full data-model coverage does not |

### 4.1 INCLUDED IN CORE

| Feature | Note |
|---|---|
| **Multimodal Intake — voice (Whisper) + vision (Llama Vision)** | §2.4 D1. Briefing awards both explicitly. One component, three modalities |
| **All three task families at parity** — incident, patch, performance | §2.4 D7. Declarative workflows make this cheap |
| **MCP adapter layer** — four local servers | §3.8 |
| **A2A — one handoff, signed Agent Card** | §3.8, cuttable under §4.0 rules |
| **Deterministic correlation (classical ML, CPU)** | §3.2 |
| **PII/secret scrubber + reversible tokenisation + local-SLM routing** | §1.5 |
| **Immutable audit trail with modality recorded** | §1.5 |
| **Policy gate + tiered HITL (incl. a scripted refusal beat)** | §2.3 |
| **Fake Fix Detector (two-signal verification)** | §2.3 |
| **CMDB drift detection + Drift-vs-Truth split screen** | §2.4 D3 |
| **Negative Knowledge Base** | §2.4 D5 |
| **Post-incident knowledge capture (A → A′ beat)** | §7 |
| **Autonomy Ladder — status panel** | §2.4 D6, reduced scope |
| **Role switcher (L1 / L2 / Change Manager / Auditor), server-side enforced** | Simulated identity, stated as such |
| **Live alert simulator with manual inject override** | §5 Phase 1 |
| **Admin strip — model switch, thresholds, runbook upload** | Live model-switch is a demo beat |
| **Eval: scenario pass/fail + symptom-suppressed vs verified-resolved** | §5 Phase 5 |
| **Structural chunking with build-failing assertion + chunk inspector** | §6.4 |

### 4.2 DEFERRED TO EXTRA CREDIT (§8)

Cost-per-incident meter · self-consistency on root-cause ranking · notification connectivity ·
change-risk classifier · Shift Handover Brief · prompt-injection demo beat · full eval harness ·
HTML quick-view launcher · real-Jira portability wiring.

### 4.3 EXPLICITLY NOT BUILT — and the reasons, in case we are asked

- **Multilingual intake** — this problem is machine-to-machine; alerts, CIs, logs and runbooks are all
  English. *If a juror raises India-context inclusivity, the honest answer is that we invested our
  inclusion effort in accessibility (voice) rather than translation, and we would add translate-on-intake
  next.*
- **Real ServiceNow PDI** — §3.7 and §4.21.
- **Real script execution against live infrastructure** — simulated execution with genuine state and
  genuine metric movement, so verification is real rather than scripted. **Never imply it is real
  infrastructure.**
- **ReAct-style open loops** — the "more turns made it worse" finding; we cap turns instead.
- **Real authentication** — zero marginal credit, real cost.

### 4.21 The real-instance question — settled

- **ServiceNow PDI: NOT USED.** Free but explicitly non-commercial and not licensed for organisational
  work; hibernates after ~24h inactivity, released entirely after 10 continuous days, can re-sleep ~30
  minutes after waking, and may require a waitlist. Against a Saturday-morning judging slot on a
  restricted network, that is an unacceptable dependency.
- **Jira Cloud free: optional 30-minute probe in Phase 0, wiring in Phase 6 only.** Genuinely free
  forever for up to 3 agents. If the lab network reaches `atlassian.net`, one adapter points at real
  Jira so thirty seconds of the demo shows an agent-created ticket appearing in actual Jira — a clean
  kill for "it's all fake" at near-zero risk, because if it breaks we simply don't show it.
  **Hard rules: 30 minutes in Phase 0 to prove reachability, then abandon permanently if unproven; and
  wiring never touches the critical path.**
- **The positive argument, for the stage:** *"We simulated the systems because the scenarios we needed —
  a fifty-alert storm, a six-month-drifted CMDB, a credential planted in a log — cannot be produced on
  demand inside a real instance."* Say it that way. It is true, and it converts an apparent shortcut
  into a design decision.

---

## 5. ROADMAP (relative durations only)

Total working budget ~16–18h. Two phases are fixed; everything between is driven by §4 and remains open
to resequencing if Phase 0 findings demand it.

### PHASE 0 — Environment & Gateway Smoke Test · ~1h (+30 min optional probe) · **FIXED · FIRST · PARALLEL WITH ANY REMAINING DISCUSSION**
1. `ollama list` — record exact model names and sizes. **Never download.**
2. Gateway auth: one successful call to **every** handbook-listed model — `gpt-4o-mini`, DeepSeek V3,
   DeepSeek R1, **Llama Vision**, Phi, **Whisper**, `text-embedding-3-large`. Voice and vision are now
   core, so **Whisper and Llama Vision are blocking checks, not curiosity** — if either fails, §2.4
   changes today, not tonight.
3. Confirm the `httpx` SSL bypass and the `TIKTOKEN_CACHE_DIR` fix.
4. Record **latency and token cost per model** — this rewrites §3.2 for real.
5. Verify `text-embedding-3-large` → Chroma round-trip end to end.
6. Scaffold: FastAPI skeleton, Next.js + shadcn init, SQLite schema stub, repo structure.
7. **Optional, hard-timeboxed 30 minutes:** can the network reach `atlassian.net`? If yes, create the
   free Jira instance and one API token, record them, and stop. **Do not wire anything yet.**
8. **Deliverable: `PHASE0_FINDINGS.md`.**
> **Claude assists with:** the smoke-test script that calls all seven models and writes the findings
> file; the repo scaffold; the SSL/tiktoken boilerplate. Paste any error verbatim — gateway errors are
> usually one config line.

### PHASE 1 — Data, Simulated Systems & MCP Layer · ~3h · **THIS IS WHERE THE SIMULATORS ARE BUILT**
**They are not later integration work.** Every canonical schema, every MCP server and every agent
contract descends from them, so they must exist before anything else is designed against them.
- Synthetic data generation (§6), including CMDB ground truth and failed-remediation seeds
- The four simulated systems — **thin but authentic: model the ~12 fields the demo actually touches,
  using real field names (`sys_id`, `short_description`, `assignment_group`, Jira `fields.status.name`),
  not the full vendor data model**
- Four local MCP servers wrapping them
- **Canonical schemas frozen at the end of this phase** — including `MaintenanceSignal`, which voice and
  vision must both produce
- SQLite + Chroma populated; chunker built and its assertion script passing (§6.4)
- **One person owns simulators + MCP servers for the whole event**, because they will be answering "how
  faithful is this to the real API?" on Saturday
*Gate: an agent-free script drives a full scenario through the MCP tools end to end, and the chunk
assertion passes.*
> **Claude assists with:** all four simulators and their MCP servers; the data generators; the chunker
> and the assertion script. Give Claude the field list you want and it writes the FastAPI services.

### PHASE 2 — Deterministic Core (no LLM) · ~2h
Correlation engine, policy gate, blast-radius computation, audit log, **voice intent parser
(closed-vocabulary)**, PII/secret scrubber with unit tests. **Deliberately before any agent work** —
this is the layer everything else is validated against, and the layer that still works when models
misbehave.
*Gate: alert storm → correlated clusters, reproducibly. Scrubber unit tests green against
`pii_ground_truth.json`.*
> **Claude assists with:** the correlation clustering, the policy rule engine, the scrubber and its
> tests, the intent parser. These are the highest-value modules to have Claude write and the team read
> closely — they are the ones you will be asked to walk through.

### PHASE 3 — Agent Chain, Supervisor, A2A & Multimodal Intake · ~5h
- Supervisor, typed handoff contracts, turn caps, termination conditions
- **Declarative workflow definitions for all three task families** — build incident first, then derive
  patch and performance from it. *If this derivation is not nearly free, the B9 design was wrong; find
  out early.*
- Specialists in demo-importance order: Enrichment → Diagnosis (R1) → Planner → Verification → Sync →
  Knowledge (+ Negative KB)
- **Multimodal intake: Whisper voice path and Llama Vision image path into `MaintenanceSignal`**,
  scrubber after conversion, confirmation-before-action on both
- **A2A: one handoff, real signed Agent Card**
- Citation enforcement built in from the first agent, never retrofitted
*Gate: one scenario from each family runs end to end; one signal enters by voice and one by image; one
handoff demonstrably travels over A2A.*
> **Claude assists with:** agent prompts, the supervisor and its schema validation, the workflow YAML
> definitions, the Whisper and Vision intake paths, the A2A Agent Card and endpoint.

### PHASE 4 — Cockpit UI · ~3.5h
Ops board, Unified Incident Record (with Maintenance Planner as a panel), **Agent Trace Viewer —
highest-priority component**, approval queue, drift queue + **Drift-vs-Truth split screen**, Autonomy
Ladder panel, **multimodal intake controls (mic button + image drop zone)**, chunk inspector, metrics
dashboard, admin strip. Wire the live alert feed.
*Gate: the golden path is clickable start to finish by someone who did not build it.*
**⚠ Most likely place the plan breaks. Pre-agreed demotion order if it runs long: chunk inspector →
static screenshot; Autonomy Ladder → static; metrics dashboard → single summary card.**
> **Claude assists with:** every React component, the SSE wiring, the shadcn layout. Give it the API
> response shape and ask for one component at a time.

### PHASE 5 — Scenario Library, Eval & Hardening · ~2.5h
Remaining scenarios including edge cases: conflicting evidence, no precedent, policy refusal, scrubber
catch, drift, prompt-injection line, **a deliberately noisy/accented voice sample, and a low-quality
screenshot** — the last two matter because §2.5 claims we handle them. Eval harness. Caching. Fallback
path. **Full run of every scenario, twice.**
*Gate: every scenario passes twice consecutively. Anything flaky gets cut, not debugged at 2am.*
> **Claude assists with:** the eval harness, edge-case scenario data, and debugging.

### PHASE 6 — Extra Credit · ~1–1.5h · **conditional on a green Phase 5 gate**
Pull from §8 in order. Real-Jira wiring, if the Phase 0 probe succeeded, belongs here and nowhere else.
**Hard stop; borrows nothing from the Final Phase.**

### FINAL PHASE — Freeze & Packaging · ~2h · **FIXED · LAST**
**Feature work stops. No exceptions.**
- README: gateway-vs-external statement, "simulated systems" disclaimer, "MCP/A2A are open protocols
  running locally" line, and the honest note on what is simulated vs real
- Notebook / execution-flow walkthrough; deck; architecture diagram (§3.5)
- Demo script with named beats: **alert-storm collapse** opener → **screenshot intake** →
  **voice-approved action** → **policy refusal** → **Drift-vs-Truth split screen** → **Fake Fix
  Detector catching a suppressed symptom** → **A→A′ learning** → **A2A delegation answer**
- **Round-robin rehearsal: all five members explain the full flow end to end.** The guidance names this
  explicitly and it is the cheapest marks in the competition
- Backup: recorded demo video + cached-response mode, in case the gateway is down at judging time
> **Claude assists with:** README, deck outline, demo script, and dry-run questions to test whether
> everyone can actually explain the flow.

---

## 6. SYNTHETIC DATA STRATEGY

### 6.1 What we generate

| Artifact | Format | Volume | Contents |
|---|---|---|---|
| CMDB (as-recorded) | JSON → SQLite | ~200 CIs | Apps, services, DBs, hosts; relationships; owner, env, criticality, patch level, last-verified date |
| **CMDB ground truth** | JSON | same | The *actual* state, differing on ~35% of CIs — makes the Drift-vs-Truth screen possible at no extra cost |
| Alert stream | JSON | ~500 across scenarios | Multi-source shapes (Prometheus-like, SNMP-terse, APM-verbose) — deliberately heterogeneous to exercise the verbosity-bias mitigation |
| Metric series | CSV | per CI | Enough shape for pre/post verification — **including slow-degradation curves, which the performance-tuning workflow needs and the incident workflow does not** |
| Ticket history | CSV/JSON | 400–600 closed | Incidents, changes **and tuning tasks**: symptoms, root cause, resolution, timings, assignment |
| Failed-remediation records | JSON | ~40 | What was tried and why it didn't work — seeds the Negative KB so it has content on day one |
| Runbooks | Markdown + 2–3 PDF | 18–22 | Three classes: `remediation`, `patching`, `tuning`. Numbered, clause-structured, with declared human-step counts |
| Postmortems | Markdown | 8–10 | Narrative RCA documents |
| Change calendar | JSON | — | Freeze windows, blackout periods, approval matrix |
| Patch inventory | CSV | — | Pending patches per CI, severity, dependencies |
| **Voice samples** | WAV/MP3 | 8–10 | Command phrases, **including at least two deliberately noisy or accented**, to test what §2.5 claims |
| **Error screenshots** | PNG | 8–10 | Error dialogs, stack traces, dashboard charts — **including one low-quality/legacy-UI capture** and one containing a visible credential, to prove scrub-after-extraction |

### 6.2 Deliberately embedded sensitive data (to prove the scrubber)

Planted at known locations so the demo is deterministic and the eval checkable:
- **Personal data:** employee names, corporate emails, phone numbers, employee IDs, manager names in
  ticket descriptions and work notes — **and one voice sample that names a colleague**
- **Secrets:** a connection string with an inline password, an API key in a config dump, a bearer token
  in a log excerpt, private IP ranges, internal hostnames — **and one screenshot with a token visible
  in a URL bar**
- **Adversarial edge case:** a log line containing text that *looks* like a prompt instruction — an
  error message quoting user input saying "ignore previous instructions." Show that the scrubber and
  the typed-contract boundary contain it
- Register every planted item in `pii_ground_truth.json` so the eval computes real precision/recall on
  the scrubber instead of us asserting that it works

### 6.3 Provenance (Handbook §8.3)

**Everything is synthetic and generated by us**, including voice samples (recorded by team members, who
consent, and who are the only people audible) and screenshots (captured from our own simulators, never
from a real system). Maintain `data/PROVENANCE.md` recording per dataset: generator script, generation
date, schema rationale, and — where a schema imitates a real product's API shape — a note that **the
shape is modelled on publicly documented field structures and contains no real, customer or proprietary
data.** No scraped data. No real ticket exports. No customer names, even as jokes. If the Jira probe is
used, note that the only data sent to it is synthetic data generated by us.

### 6.4 CHUNKING — IMPLEMENTATION SPEC, NOT AN INTENTION

The briefing calls out that chunking is not straightforward and jurors have been trained to look for
naive fixed-size failures. **This is therefore specified as buildable, testable behaviour, and it has a
test that can fail the build.**

**Why it matters more here than in a typical RAG demo:** the retrieved text is *an action a human may
take against production*. A chunk that begins at "…then restart the primary node" without the preceding
"only if the replica has caught up" is not merely lossy — it is dangerous. Say it that way if asked.

**Rules:**
1. **Split on structural boundaries only** — heading hierarchy (`#`/`##`/`###`), numbered step blocks,
   and clause numbers. Never on a character or token count.
2. **A numbered step is atomic.** A step and its sub-bullets, conditions and warnings travel together.
   If a single step exceeds the size budget, it stays whole and over-budget rather than being split.
3. **Heading path carried as metadata**, so a chunk knows it is `Runbook 14 › Rollback › Step 3` and
   citations can point at a step rather than a byte offset.
4. **Preamble inheritance** — prerequisites and warnings stated before a procedure are attached to
   every step chunk in that procedure. This is the rule that prevents the dangerous case above.
5. **Tables and code blocks are never split.**
6. **PDFs get their own path** — extract text with structure preserved, then apply the same rules; if
   structure cannot be recovered from a given PDF, that document is flagged and excluded rather than
   naively split. **An honest exclusion beats a silent bad chunk.**
7. **Overlap only at section boundaries**, carrying the section heading forward — not a blind sliding
   window.

**Verification — three layers, because claiming is not proving:**
- `scripts/assert_chunks.py` — **fails the build** if any chunk begins mid-step, if a numbered list is
  split across chunks, if a chunk lacks a heading path, or if a code block is broken. Run it in Phase 1
  and again in Phase 5.
- **Chunk inspector in the UI** — a screen showing any document with its chunk boundaries drawn.
  **When a juror asks about chunking, show them this rather than describing it.** *(First item on the
  Phase 4 demotion list, but demote to a static screenshot rather than dropping it entirely.)*
- **A deliberate trap in the corpus** — one runbook whose step 4 spans a page break and would be cut by
  a naive splitter. Keep it as a named test case, and mention it during the walkthrough.

---

## 7. UI/UX DESIGN

**We keep the decoupled enterprise cockpit — and here is the specific reasoning rather than "it's our
template":** the primary user triages concurrent work under time pressure while carrying an approval
responsibility. That is a *monitoring and decision* job, not a *conversation* job. A chat-first
interface would force serialised interaction onto a parallel task, and would hand the jury the
"ChatGPT wrapper" framing for free.

**Two deliberate departures from the default template:**
1. **The centrepiece is the Agent Trace Viewer, not the execution panel.** The statement asks the
   prototype to demonstrate *multi-agent coordination*, and coordination is invisible in a results
   panel. The trace is a first-class, always-visible workspace object showing each handoff, its inputs,
   the scrubbed prompt, model, tokens, latency, validation result, **input modality**, and **transport
   (in-process vs A2A, with the Agent Card viewable)**.
2. **The conversational modality is voice, not a chat box.** We cut the chat drawer deliberately. Voice
   commands satisfy the hybrid-interaction guidance while serving accessibility — and unlike a chat
   panel, they cannot be mistaken for a general-purpose chatbot.

**Layout**
- **Sidebar:** role switcher · **mic button (push-to-talk) with the parsed intent shown before
  execution** · ingestion/admin · model & threshold config · scenario launcher · audit log
- **Main — tabbed workspace:**
  - **Ops Board** — live alert feed left, correlated candidates right, noise-reduction ratio as a
    headline number, and an **image drop zone** for screenshot intake. *Opening shot: dozens of alerts
    collapsing into three cards.*
  - **Incident Workspace** — the Unified Incident Record: evidence with citations (including `IMG-nnn`
    when a screenshot contributed); ranked hypotheses with confidence and an explicit "could not
    verify" block; the plan with blast radius and any Negative-KB caution; linked ITSM/tracker/CI
    records side by side with contradictions highlighted; **Maintenance Planner panel** for patch runs
  - **Agent Trace** — as above, with **Replay**
  - **Approval Queue** — recommendation *plus counter-hypothesis plus evidence gaps*;
    approve / edit / reject with mandatory reason (feeding the Negative KB); **approvable by voice, with
    on-screen confirmation**
  - **Drift Queue + Drift-vs-Truth split screen**
  - **Autonomy Ladder** — every runbook and its current tier
  - **Chunk Inspector** — document with chunk boundaries drawn
  - **Metrics & Eval** — §2.6 metrics; verified-resolved vs symptom-suppressed; signals by modality
- **Accessibility, since we are claiming it:** every voice action has keyboard parity, focus states are
  visible, and the confirmation step before any voice-initiated action is mandatory, not a preference.
  *Claiming accessibility and shipping something only usable by mouse would be worse than not claiming
  it.*

**Design principles:** confidence is always visible with its evidence basis; nothing AI-generated
appears in the same visual register as verified fact (`AI proposed` / `human approved` /
`system verified`); every number clicks through to its source artifact; refusals are displayed as
prominently as successes.

---

## 8. EXTRA CREDIT BACKLOG

> **Attempt ONLY after the Phase 5 gate is green. Nothing here borrows from the core roadmap or the
> Final Phase. If in doubt, don't.**

1. **HTML quick-view launcher** (**S**) — one static `demo.html` with buttons to launch each scenario
   and jump to the right screen. Removes navigation fumbling on stage. *Highest ROI here.*
2. **Cost-per-incident meter** (**S**) — unit economics against a stated engineer-hour cost. Independent
   benchmarking showed large cost premiums for marginal accuracy gains, so "we chose the cheaper model
   here and here is what we traded" is a mature answer few teams can give.
3. **Real-Jira portability wiring** (**S**) — only if the Phase 0 probe succeeded. Thirty seconds of
   demo showing an agent-created ticket in actual Jira.
4. **Self-consistency on root-cause ranking** (**S**) — sample N times, keep recurring hypotheses,
   report agreement rate as an honest confidence signal.
5. **Prompt-injection resilience beat** (**S**) — surface the §6.2 adversarial log line as a named moment.
6. **Notification connectivity** (**S**) — approvals and summaries to a simulated channel; satisfies
   "connectivity with an existing workflow."
7. **Change-risk classifier** (**S–M**) — CPU-trained tabular model over synthetic change history,
   feeding the scheduler a real risk score. Genuine standard-ML-alongside-GenAI content.
8. **Shift Handover Brief** (**S–M**) — the "nobody asked for it" feature: one click generates a
   handover summary of the shift — open incidents, what the agents did, what awaits approval, what was
   refused and why. Nothing in the statement asks for it; every real ops team does it manually every
   day.
9. **Full eval harness** (**L**) — per-scenario accuracy, citation coverage, hallucination checks.

---

## 9. OPEN QUESTIONS & ASSUMPTIONS

**Still open — answer as Phase 0 runs**
1. **Team split across 5 people.** Phases 1–4 parallelise cleanly (data + simulators + MCP /
   deterministic core / agents + intake / UI) but **only if the canonical schemas freeze at the end of
   Phase 1.** One person owns simulators + MCP for the whole event (§5). **Assign the other four.**
2. **"Workflow modeling" (B9)** — we read it as declarative agent-graph modelling, not process mining.
   If a juror presses, acknowledge the alternative reading and explain the choice.
3. **Does anyone have prior MCP, A2A, or Whisper experience?** All three estimates assume reading docs
   cold. Prior experience frees time that should go to Phase 4, which is the tightest phase.
4. **Handbook submission artifacts** — is there a required notebook format, README structure or deck
   template shaping the Final Phase? **Someone confirm against §8 and the submission section.**
5. **Hard demo time limit?** Determines how many of the three workflows get shown live versus described.
6. **One laptop or several?** Affects whether simulators and MCP servers run as separate processes, and
   affects the fallback plan.

**Assumptions (challenge if wrong)**
- The four "external" systems are ours, simulated, API-compatible — everything in §2.2 depends on this
  being clearly disclosed.
- MCP and A2A endpoints running locally are not an external dependency under FAQ 13.10.18. **Confident,
  but sanity-check against the handbook text** — the whole protocol layer rests on it.
- Whisper and Llama Vision are reachable and usable through the gateway. **Phase 0 step 2 is now a
  blocking check**; if either fails, §2.4 changes the same morning.
- Moderate data volume means hundreds-to-low-thousands of records; SQLite + Chroma is correct.
- "Real-time dashboards" means live-updating within the demo session, not sub-second streaming SLAs.
- No deployment requirement; localhost is acceptable for judging.
- The ISU being listed as LSHC does not change this statement's domain (§1.5).

**Known risks, named rather than hidden**
- **Phase 4 (UI, ~3.5h) is the most likely breakage point.** Demotion order pre-agreed in §5.
- **Voice on a noisy demo floor.** Mitigation: push-to-talk, closed vocabulary, on-screen confirmation,
  and a pre-recorded sample as fallback if the room is loud. **Rehearse the voice beat in the actual
  room if you get the chance.**
- **A2A could over-run.** Cut the implementation, keep the argument (§3.8).
- **Three workflows could dilute rather than demonstrate.** Mitigation: one deep golden-path scenario
  (incident) shown fully, the other two shown in compressed form. Coverage is proven by the eval
  dashboard and the coverage map, not by three full live runs.

---

## 10. NEXT STEPS

Phase 0 starts immediately, in parallel with anything else. Phase 1 begins the moment the gateway checks
pass — and the simulators are the first thing built, because everything else is defined against them.

If Phase 0 findings, or the team, change any decision in §4, say so in plain language and this document
gets revised. Nothing here is more important than being right.

**Working with Claude through the build:** freeze the canonical schemas at the end of Phase 1 and paste
them into every later request — Claude has no memory of your repo between sessions, so the schemas are
the shared context. Ask for one module at a time, restate the commenting standard from §0 with each
request, and read what comes back closely enough to walk a juror through it. Every phase in §5 names
what Claude will help with; when something breaks, paste the error verbatim rather than describing it.

---

### Appendix — external sources informing §2, §3 and §4.21

Used for framing, positioning and feasibility only. No external system is a dependency of the primary
solution.

- **Agent benchmarks:** IBM ITBench (arXiv:2502.05352) — ~13.8% SRE scenario resolution; ITBench-AA
  independent leaderboard (Artificial Analysis); Stratus finding that 8/18 mitigation problems are
  "solvable" by a generic pod-restart loop
- **Multi-agent reliability:** MAST failure taxonomy (arXiv:2503.13657) — 14 failure modes over 1,600+
  traces; 44.2% system design, 32.3% inter-agent misalignment; 41–86.7% failure rates; error
  amplification ~17× uncoordinated vs ~4.4× with a centralised validation bottleneck
- **Protocols:** Linux Foundation A2A one-year announcement, April 2026 — 150+ organisations, v1.0
  stable, signed Agent Cards, five-language SDKs, ServiceNow among participants; MCP donated to the
  Agentic AI Foundation, December 2025; independent adoption analysis noting A2A's implementation burden
- **Competitive:** ServiceNow Now Assist / AI Agents documentation and 2026 practitioner reviews;
  ServiceNow↔Jira integration literature on duplicated tickets and contradictory statuses
- **CMDB quality:** ~60% typical accuracy; 30–40% inaccuracy within six months in manually maintained
  environments; ServiceNow-published outcomes (~38% faster incident resolution, ~82% fewer failed changes)
- **Alert fatigue / AIOps:** 60–80% false-positive medians; 40–58% MTTR reduction claims
- **Developer instances:** ServiceNow PDI free but non-commercial and not licensed for organisational
  work, hibernation ~24h, release after 10 days, possible waitlist; Jira Service Management free plan
  free forever for up to 3 agents (2GB storage, 100 email notifications/day, 500 automation runs/month)
- **Privacy:** India DPDP Act 2023 + DPDP Rules notified November 2025; phased compliance into 2027
