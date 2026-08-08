# PRD DRAFT v2 — Cross-Stack Maintenance Control Plane
### TCS AI Fridays Season 2 — Regional Round
### Problem Statement: AI-Powered Multi-Agent Workflow Automation for IT Application Maintenance

> **STATUS: DRAFT FOR TEAM ARGUMENT.** Not an execution spec. Nothing here is locked.
> Sections 4 and 9 exist to be fought over. Read them first if you are short on time.
> Do not build anything in this document except Phase 0.
>
> **What changed in v2:** competitive research folded in (§2.2); MCP + A2A protocol layer added
> (§3.8, Decisions 4.19–4.20); the real-ServiceNow/Jira question researched and answered (Decision
> 4.21); five new differentiator features added as decisions (4.22–4.26); roadmap resized accordingly.

---

## 0. CONSTRAINTS — STATED ONCE, BINDING ON EVERYTHING BELOW

**Stack**
- Frontend: Next.js + shadcn/ui
- Backend: FastAPI (async)
- Storage: SQLite (transactional/state), Chroma (vector/RAG). Choice per use case, not per habit.

**Models — Handbook-listed only**
- Via the provided gateway (genailab.tcs.in): `gpt-4o-mini`, DeepSeek V3 / R1, Llama Vision, Phi,
  Whisper, `text-embedding-3-large`
- Local SLMs via Ollama, already installed on lab laptops. **Verify with `ollama list`. Never download.**

**The gateway-vs-external distinction — say this out loud to the jury**
> "Every model call in this solution goes to the TCS-provided GenAI Lab gateway or to a model running
> locally on this laptop via Ollama. There is no external Model-as-a-Service dependency anywhere in
> the primary solution. The 'ServiceNow' and 'Jira' systems you see are API-compatible simulators we
> wrote in FastAPI — we are not calling any vendor SaaS. **MCP and A2A are open protocols, not
> services: our MCP servers and A2A endpoints run on this laptop and call nothing outbound.**"

This satisfies Handbook FAQ 13.10.18. A juror who sees a `ServiceNow` panel, or hears "MCP," could
reasonably assume a third-party call. **Pre-empt it in the demo script, on a slide, and in the README.**
Do not wait to be asked. The one place this could stop being true is Decision 4.21 (optional real-Jira
probe) — if we take that option, it must be labelled on screen as an optional external portability
check, outside the primary solution.

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
  confidence cut-offs, guardrail conditions, correlation window sizes, A2A/MCP schema choices.
- No line-by-line narration of obvious code. `# increment counter` is worse than no comment.
- Modular design is graded alongside commenting: `agents/`, `adapters/`, `mcp_servers/`, `guardrails/`,
  `orchestrator/`, `eval/`. One responsibility per module.

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
manual relay race into a repeatable, auditable workflow that runs from "alert fired" to "ticket closed,
CMDB updated, knowledge captured." The prototype has to prove the *coordination*, not just the chat.

### 1.2 Clause-by-clause coverage map

Every clause of the issued statement, with the feature that satisfies it. **Unmapped clauses are
flagged in bold, not dropped.**

#### A. Problem narrative

| # | Clause (near-verbatim) | Feature that satisfies it |
|---|---|---|
| A1 | "recurring tasks such as patch management" | **Patch & Maintenance Window Agent** — groups pending patches by CI dependency and risk, proposes windows |
| A2 | "performance tuning" | **Performance Advisory path** — a distinct workflow branch for degradation-class alerts (slow queries, memory creep) producing tuning recommendations rather than restart-class remediation |
| A3 | "incident resolution" | **Core agent chain**: Correlate → Enrich → Diagnose → Plan → Gate → Execute → Verify → Sync → Learn |
| A4 | "relying on manual procedures and fragmented tools" | **MCP-exposed adapter layer** over four simulated systems + the **Unified Incident Record**, which replaces manual cross-tool copying |
| A5 | "inefficiency, inconsistent execution, delayed issue resolution" | **Runbook-grounded planning** (same input → same plan, reproducibly) + **metrics on manual-steps-avoided and time-to-plan** |
| A6 | "Integrating monitoring data, ticketing systems, and CMDBs is complex" | **Adapter + MCP server pattern** with a shared canonical schema; each adapter swappable and independently testable |
| A7 | "AI-driven multi-agent orchestration" | **Supervisor-and-specialists orchestrator** (deliberately 2-level, §3.4) with typed handoff contracts, **selected handoffs carried over A2A with signed Agent Cards** (§3.8) |
| A8 | "improve consistency, reduce manual effort, accelerate problem resolution" | **Success Metrics panel** (§2.6) instrumented from real run telemetry, never hardcoded |
| A9 | "higher operational costs and reduced system reliability" without automation | **Baseline-vs-automated comparison view** + **cost-per-incident meter** (§8) |

#### B. Data considerations

| # | Clause | Feature |
|---|---|---|
| B1 | "monitoring metrics and alerts" | Synthetic alert stream (JSON), metric time-series per CI |
| B2 | "ticketing and incident management data" | Simulated ITSM + tracker stores with realistic field shapes (`sys_id`, state codes, work notes / Jira issue JSON) |
| B3 | "configuration management databases" | CMDB store: ~200 CIs with relationships, owners, environments, criticality, patch levels |
| B4 | "historical maintenance logs" | 400–600 closed historical tickets + postmortems → RAG corpus |
| B5 | "data volume moderate" | Sized deliberately: hundreds of records, not millions. SQLite + Chroma is the correct call at this volume — present it as a *reasoned* choice, not a shortcut |
| B6 | "quality includes data completeness and accuracy" | **Data Quality Gate** (completeness score, staleness flag) + **Drift Detector** + **Drift-vs-Truth split screen** (§2.4) — our single strongest differentiator lives on this clause |
| B7 | "privacy compliance for operational data" | **PII/Secret Scrubber** at every model boundary + immutable audit trail (§1.5, §2.5) |
| B8 | "preprocessing involves event correlation" | **Deterministic correlation engine** (fingerprint + time-window + topology clustering) — classical ML, not LLM |
| B9 | "preprocessing involves workflow modeling" | **Declarative workflow definitions (YAML/JSON)** — the agent graph is data, not hardcoded control flow. Also delivers the "framework independence" guidance |
| B10 | "synthetic maintenance scenarios for testing" | **Scenario Library** — 8–12 named, replayable scenarios (§6) doubling as the test suite |
| B11 | "synthetic or anonymized data where appropriate" | 100% synthetic, provenance-tracked (§6.4) |

#### C. Solution expectations

| # | Clause | Feature |
|---|---|---|
| C1 | "A web platform" | Next.js cockpit (§7) |
| C2 | "multi-agent workflows automating maintenance tasks" | 7–9 specialist agents under a supervisor |
| C3 | "triggered by monitoring alerts" | Alert ingestion endpoint + live simulator; workflows start on trigger, not on a button |
| C4 | "managing tickets" | Create / enrich / link / comment / transition across both simulated ticket systems |
| C5 | "updating CMDBs" | Proposed CI updates, human-approved, written back with audit entry |
| C6 | "intelligent scheduling" | Maintenance Window Agent — dependency-aware, blackout-aware, SLA-aware |
| C7 | "remediation recommendation" | Ranked plans from the approved runbook catalog with evidence, confidence, blast radius — **filtered against the Negative Knowledge Base** (4.24) |
| C8 | "real-time dashboards" | Live ops board (SSE) + metrics + eval views |
| C9 | "Integrations with monitoring APIs" | Monitoring adapter, exposed as an MCP server |
| C10 | "…ticketing APIs" | ITSM adapter + Tracker adapter, exposed as MCP servers |
| C11 | "…CMDB APIs" | CMDB adapter, exposed as an MCP server |
| C12 | "reduction in manual tasks" | Metric: manual steps avoided per run, derived from each runbook's declared human-step count |
| C13 | "incident resolution time" | Metric: alert→plan and alert→verified-resolution vs a stated manual baseline |
| C14 | "user satisfaction" | **PARTIALLY UNMAPPED — see below** |
| C15 | "prototype demonstrates end-to-end workflow automation" | The golden-path demo scenario, run live |
| C16 | "…and multi-agent coordination" | **Agent Trace Viewer** — visible handoffs are the proof — plus **A2A Agent Cards** as the protocol-level evidence. This is the demo centrepiece |

#### 🚩 FLAGGED — clauses with weak or no coverage

1. **C14 "user satisfaction" as a success metric.** We cannot measure real satisfaction in a hackathon.
   Options: (a) thumbs-up/down + reason on every AI recommendation, aggregated into approval-rate and
   **edit-rate** proxies; (b) a scripted survey instrument presented as a design artifact only;
   (c) drop it and say why. **Recommendation: (a)** — cheap, doubles as the human-feedback loop for the
   "adaptability through feedback loops" guidance, and feeds the Negative Knowledge Base (4.24).
   **Team decision needed.**
2. **A2 "performance tuning"** is the weakest of the three named task families for us. Incident
   resolution and patching have crisp demonstrable workflows; performance tuning is open-ended
   advisory work. Risk: build it thin and a juror ticks it "mentioned but not delivered." See 4.1 —
   and note that v2's added scope makes thinning this the most likely funding source.
3. **B9 "workflow modeling"** is ambiguous in the source text. We read it as *modelling the maintenance
   workflow itself* (declarative agent graph). It could also mean *process-mining historical logs to
   discover the workflow*. The second reading is a much larger build. See Q9.2.

### 1.3 Guidance-block coverage (the jury's implicit rubric)

The GUIDANCES section says "as applicable," but past rounds show it functions as a scorecard.

| Guidance | Where we answer it |
|---|---|
| Intuitive interface aligned to workflow/user journey | §7 cockpit, role-shaped views |
| Conversation / visualization / hybrid | §7 — hybrid: visual cockpit primary, scoped chat secondary |
| Data quality, completeness, preprocessing, context-based retrieval | §6, Drift Detector, structural chunking |
| Suitable storage for structured + unstructured | SQLite + Chroma, justified per data type |
| Aggregation, correlation, summarization | Correlation engine, incident narrative synthesis, Quiet Score (4.23) |
| Pragmatic short/mid-term roadmap | §2.7 |
| Balance autonomy with human oversight | Tiered HITL (4.5) + **Autonomy Promotion Ladder (4.25)** |
| Feedback loops, changing requirements | Approve/edit/reject capture → knowledge index **and Negative KB**; declarative workflows |
| Grounded, referenced, context-aware outputs | Every claim carries artifact IDs; no citation → no claim |
| Guardrails: leakage, unsafe recommendations, unsupported decisions | §2.5 — scrubber, policy gate, confidence floor, runbook-bounded action space |
| Explain reasoning, assumptions, limitations, confidence | Trace viewer + mandatory "what I could not verify" block |
| Separate AI layer / enterprise systems / third-party | §3.5 tier diagram — **draw this, jurors ask** |
| Modular multi-tier architecture | Module layout in §0 |
| Memory, caching, token strategy | §3.6 |
| Framework independence & configurability | **MCP adapter layer + A2A handoffs + declarative workflows** — this trio makes the claim literal rather than aspirational |
| Security, privacy, audit logging, access governance | §1.5, §2.5, 4.6 |
| Rationale, alternatives, trade-offs | §3.7 — **rehearse this, it is a guaranteed question** |
| Test scenarios, edge cases, varied data, automation | §6 Scenario Library = test suite; eval harness (4.10) |
| Demo readiness, code walkthrough, dynamic inputs | Final phase (§5) |
| Show GenAI materially beats conventional approach | §2.2 — the honest version, not the hype version |
| All members can explain full flow | Final phase round-robin rehearsal — **do not skip this** |

### 1.4 Stakeholders implied by the problem

| Stakeholder | What they need | In our UI? |
|---|---|---|
| **L1 Ops / NOC engineer** (primary) | Stop drowning in duplicate alerts; know what to do first | Yes — ops board |
| **L2 / Application SME** | Evidence they can trust, fast, without re-deriving it | Yes — diagnosis + evidence panel |
| **Change / Release Manager** | Nothing risky reaches prod outside a window | Yes — approval queue, blast radius |
| **IT Service Owner / business owner** | MTTR, cost, SLA adherence, "is this working" | Yes — metrics dashboard, cost meter |
| **Developers (tracker side)** | Incidents that are really bugs land in their backlog *with context*, not as copy-paste | Yes — cross-system linkage |
| **CMDB / Configuration Manager** | A CMDB that stops rotting | Yes — drift queue |
| **Monitoring/Observability engineer** | Fewer useless alert rules | Yes — **Quiet Score panel (4.23)**, if adopted |
| **Security / Compliance / DPO** | No secrets or personal data in model calls; provable audit trail | Yes — audit log view |
| **End users / employees who raise tickets** | Their data (name, contact, employee ID) handled lawfully | **Not a UI user — but a data subject.** This is why §1.5 matters |
| **The AI system itself as an actor** | Must be attributable — every write records *which* agent | Yes — every audit row has an actor |

Three of these are easy to forget and each is worth a sentence in the pitch: the **Configuration
Manager** (nobody builds for them, and drift is our differentiator), the **Observability engineer**
(nobody attacks the *cause* of alert noise), and the **ticket-raising employee as data subject**
(which is what turns privacy from decoration into a requirement).

### 1.5 DOMAIN CHECK

**Domain: IT Operations / IT Service Management (ITSM + ITOM). This is NOT Life Sciences, Healthcare,
or any patient/clinical domain.** No PHI is involved. We will not pretend otherwise and will not bolt
on HIPAA-flavoured language that does not apply — a juror will spot padding.

**Privacy is nonetheless a CORE requirement here, on a different and equally real basis. Say this
plainly rather than treating privacy as decoration:**

1. **Ticket data contains personal data of identifiable individuals.** Incident descriptions, work
   notes and requester fields carry employee names, corporate emails, phone numbers, employee IDs and
   manager names. Under India's **DPDP Act, 2023** — operationalised by the **DPDP Rules notified
   November 2025**, with obligations phasing in over an 18-month window into 2027 — this is digital
   personal data and the employer is a Data Fiduciary. Employment processing has a "legitimate uses"
   basis, but **sending that text to a model is a purpose the requester did not contemplate**, and the
   security-safeguard obligation applies regardless of basis. Our position: personal data is redacted
   *before* it crosses a model boundary, so the legitimate-use argument never has to be made.
2. **Operational data carries secrets — a leakage class of its own.** Log excerpts and config dumps
   routinely contain hostnames, internal IPs, connection strings, bearer tokens, API keys and
   service-account names. A prompt containing a live credential is an incident, not a nicety.
3. **Automated action against production requires attributable authorisation.** "Which agent changed
   this CI, on whose approval, citing what evidence" is the question that decides whether a system
   like this is allowed near production at all.

**Therefore, escalated to core requirements (not stretch goals):**
- **Scrub-before-send** at every model boundary — regex for structured secrets and identifiers plus a
  local-SLM pass for free-text names — with **reversible tokenisation** so redaction does not destroy
  usability (`svc-payments-prd` → `[HOST_7]`, restored for display to the authorised human, never to
  the model).
- **Immutable audit trail** — append-only: actor (human user or named agent), action, target artifact,
  timestamp, evidence IDs, model used, approval reference. Viewable in the UI. Small build,
  disproportionately persuasive.
- **Purpose-limited retention** — scrubbed prompts and traces retained; raw payloads not persisted
  beyond the run. Show the config; state the position.
- **Local-model routing for the most sensitive step** — raw log excerpts go to a local Ollama SLM so
  the text never leaves the machine. A privacy *architecture* decision, not a cost one.
- **Consent-and-rights posture, stated honestly** — a full DPDP consent-manager flow is out of scope
  for a prototype and claiming one would be false. We implement data minimisation, purpose limitation
  and auditability; we *document* where a consent/rights layer would attach. Say the second part out
  loud — knowing the boundary of your own build reads as maturity, not as a gap.

---

## 2. RECOMMENDED SOLUTION & THE MOAT

### 2.1 The product in one paragraph

**A vendor-neutral Maintenance Control Plane that sits *above* the monitoring stack, the ITSM system,
the developer tracker and the CMDB — and owns the seam between them.** When alerts fire, a supervisor
agent dispatches specialists that collapse alert noise into candidate incidents, gather evidence from
every system, produce ranked root-cause hypotheses with citations and confidence, draft a remediation
plan from an approved runbook catalog, check it against policy and blast radius, route it to the right
human, execute it, **verify that the underlying fault actually cleared rather than that the alert
merely went quiet**, and write the outcome back to every system as one consistent record plus a
reusable knowledge artifact. Every system it touches is reached through **MCP**; selected agent
handoffs travel over **A2A** with signed Agent Cards, so the same architecture can delegate to a
vendor's own agents. Everything it does is traceable, cited, reversible and logged.

**Target user (primary): the L2 application maintenance engineer on shift.** Not the CIO, not the end
user. The person who currently has eleven browser tabs open and is deciding which of forty alerts is
the actual problem.

**The exact problem we solve:** *the evidence-gathering and cross-system bookkeeping around a
maintenance task takes longer than the fix, and has to be redone from scratch every time because
nothing learned last time is where the next engineer will look.*

### 2.2 "Why is this better than ChatGPT?" — and the harder question, "why is this better than ServiceNow's own AI?"

**vs. a general chat assistant.** A chat assistant is a *single-turn advisor with no hands and no
memory of your estate.* It cannot receive an alert, cannot collapse 50 alerts into 3 incidents, does
not know that `svc-payments` depends on `db-orders-prd`, cannot open a ticket, cannot refuse to act
during a change freeze, leaves no audit trail, and — most importantly — **will confidently answer even
with no evidence.** Our output is structurally different: every hypothesis carries the artifact IDs it
was derived from, and a hypothesis with no supporting artifact is suppressed at generation. That is an
architectural property, not a prompt.

**vs. ServiceNow Now Assist / Atlassian Rovo — the question the jury will actually ask.** Five moves,
delivered *before* being asked:

1. **They are platform-native by design; the problem is cross-platform by nature.** Now Assist's agents
   are built into the Now Platform and reach outside it through IntegrationHub spokes; Rovo is
   Atlassian-native. The industry's own documentation of the ServiceNow↔Jira seam describes exactly
   the failure mode: ops runs ServiceNow for incidents and change, dev runs Jira, tickets get
   duplicated, statuses contradict each other, and someone maintains a reconciliation spreadsheet.
   **A vendor's AI cannot be neutral about which system is the source of truth. Ours can, because it
   owns neither.**
2. **They inherit their own data quality; we interrogate it.** ServiceNow's Context Engine grounds its
   agents in CMDB relationships — genuinely strong architecture. But industry estimates put typical
   CMDB accuracy near **60%**, and manually maintained CMDBs reach **30–40% inaccuracy within six
   months**. A CMDB-grounded agent inherits that error rate *silently*, because a stale CMDB does not
   produce ambiguity — it produces **false clarity**. It still answers; it just answers wrong. **Our
   agents treat the CMDB as a hypothesis to verify against observed reality, flag disagreement as
   drift, and propose reconciliation as a first-class workflow.** The **Drift-vs-Truth split screen**
   (4.26) dramatises this instead of merely citing it. This is the most defensible thing in the design
   and deserves its own slide.
3. **We are honest about autonomy, and that is a feature.** IBM's ITBench found agents built on
   state-of-the-art models resolve only about **13.8% of real SRE scenarios**; independent analysis of
   multi-agent systems reports failure rates of **41–86.7%**, with roughly **79% of production
   breakdowns** traced to specification ambiguity and coordination breakdown rather than model
   capability. A team promising autonomous incident resolution is either uninformed or overselling.
   **We promise the opposite: evidence-first, confidence-gated, human-approved automation — the safety
   architecture that makes partial autonomy shippable — with autonomy earned per runbook by measured
   evidence (4.25).**
4. **⭐ We do not compete with their agents; we can orchestrate them.** A2A is now a Linux Foundation
   project that passed **150+ supporting organisations at its April 2026 one-year mark**, with v1.0
   stable, **signed Agent Cards** for cryptographic identity, and cloud-platform integration across
   Google, Microsoft and AWS — and **ServiceNow is among the participating organisations**. So:
   > *"We're not competing with ServiceNow's agents. We're the neutral orchestrator above them.
   > In production our supervisor discovers a vendor agent through its Agent Card and delegates the
   > vendor-native work to it — while keeping the cross-system reasoning, the policy gate and the
   > audit trail vendor-neutral."*
   This reframes the biggest competitor as a **subordinate component of our architecture.** A juror
   setting up a gotcha now has to concede the design point. **Rehearse this answer verbatim.**
5. **Deployment reality and data residency.** Now Assist delivers most value to organisations already
   standardised on the platform, and practitioner reviews note it needs substantial configuration
   before it delivers. Our layer sits above whatever exists, and its most sensitive processing runs on
   a local model, so operational text never leaves the estate.

**One sentence for the pitch:**
> "Now Assist makes ServiceNow smarter. We make the *space between* ServiceNow, Jira, your monitoring
> stack and your CMDB smarter — we assume your CMDB is 40% wrong, because it is — and when a vendor
> agent is better at its own platform than we are, we delegate to it over A2A instead of competing."

### 2.3 Technical moat — the four pillars

**(a) Domain-specific guardrails.** Not a generic "be safe" prompt. Concrete, deterministic, testable:
- **Runbook-bounded action space.** Agents may only propose steps that exist in the approved runbook
  catalog. A free-text remediation cannot be executed — it can only be raised as a *proposal for a new
  runbook*, routed to a human. This eliminates the whole class of "the LLM invented a destructive
  command."
- **Policy gate (pure Python, no LLM):** change-freeze windows, prod vs non-prod, CI business
  criticality, dependency blast radius above threshold, max concurrent changes, required-approver role.
  Deterministic, unit-tested, shown to the jury as code.
- **Confidence floor with an explicit abstain path.** Below threshold the system does not guess — it
  escalates and names the missing evidence. **"I don't know, and here is what I'd need" is a
  first-class output.**
- **Anti-reward-hacking verification ("Fake Fix Detector").** ITBench analysis found **8 of 18
  mitigation problems (44%)** could be "solved" by a generic pod-restart loop — the alert clears, the
  fault injector loses track, and the agent gets credit despite doing nothing about the defect. Our
  Verification Agent therefore requires **two independent signals**: alert cleared **and** the
  underlying metric/health probe recovered and held through a stabilisation window. If only the alert
  cleared, the incident is marked **"symptom suppressed, root cause unconfirmed"** and stays open.
  Almost no competing team will have considered this. It is cheap. Build it.

**(b) Automated multi-step workflows.** Alert → correlation → enrichment → diagnosis → plan → policy
gate → approval → execution → verification → cross-system sync → knowledge capture. Eleven steps, each
observable, attributable and replayable from stored inputs.

**(c) Zero data leakage.** Scrub-before-send at every model boundary, reversible tokenisation,
local-model routing for the highest-sensitivity content, no raw payload persistence, full audit trail.
Demonstrated live: show the raw log containing a hardcoded credential, then show the exact prompt that
was actually sent.

**(d) Trust and transparency.**
- **Citations.** Every claim references artifact IDs (`ALERT-1043`, `CI-0087`, `INC-2291`, `RB-14 §3`).
  A hypothesis without a citation is suppressed at generation, not filtered afterwards.
- **Calibrated disclaimers, not decorative ones.** "Based on 3 similar historical incidents; confidence
  Medium; not verified against current config" — on the artifact, not in a page footer.
- **Reproducibility.** Temperature 0 for decision steps; every run persists model, prompt version,
  retrieved chunk IDs and raw response. A **Replay** button re-runs a stored scenario and shows whether
  the outcome changed. Reproducibility you can *demonstrate* beats reproducibility you claim.
- **Explicit limitations block** on every diagnosis: "what I could not verify."

### 2.4 The five sharpened differentiators (new in v2)

These are the pitch-level hooks. Each maps to a decision in §4.

| # | Name | The one-line pitch | Decision |
|---|---|---|---|
| D1 | **A2A delegation to vendor agents** | "We don't compete with Now Assist. We can delegate to it." | 4.20 |
| D2 | **Drift-vs-Truth split screen** | Same incident, diagnosed twice — once on the CMDB, once on reality. Watch them diverge. | 4.26 *(recommend core)* |
| D3 | **Quiet Score** | "Everyone else makes you better at handling noise. We make the noise go away." | 4.23 |
| D4 | **Negative Knowledge Base** | Every RAG on earth indexes successes. We index failures, so the system stops re-proposing what already didn't work. | 4.24 |
| D5 | **Autonomy Promotion Ladder** | Autonomy is *earned per runbook by measured evidence*, not switched on globally. | 4.25 |

### 2.5 Bias mitigation — bias that could plausibly enter *this* solution

Generic fairness language will not survive a follow-up question. These are the failure modes actually
available to this system:

| Bias | How it enters here | Mitigation we build |
|---|---|---|
| **Retrieval recency/frequency bias** | RAG over historical incidents surfaces common, recent, well-documented failures; a novel incident gets force-fitted to a familiar root cause because that is what retrieval returned | Diversity-aware retrieval (MMR-style) and an explicit **"no strong precedent found"** state rather than the nearest weak match. Similarity scores shown in the UI |
| **Instrumentation / documentation bias** | Well-monitored services produce richer evidence and therefore higher-confidence diagnoses. Legacy, under-instrumented systems get systematically deprioritised — exactly the systems most likely to fail | Confidence scored **relative to evidence available for that CI**, not absolutely. An explicit "low observability coverage for this CI" flag so thin evidence reads as *unknown*, not *fine* |
| **Historical assignment bias** | Routing to whoever historically closed similar tickets entrenches past mis-routing and workload inequality | Routing suggests **role/queue**, never a named individual; the reason is shown and editable |
| **Alert-verbosity bias** | Modern tools emit rich English; legacy SNMP traps emit terse codes. LLM triage will systematically under-rank the terse ones | Normalise every alert into a canonical schema *before* any model sees it, so ranking is on signal, not prose quality |
| **Severity anchoring** | Whatever the monitoring tool labelled "P1" anchors the model's judgement | Priority recomputed from CI criticality + blast radius + SLA; disagreement with the source label shown as a delta |
| **Automation bias in the human reviewer** | The most likely real-world harm. A confident-looking plan gets rubber-stamped and the HITL gate becomes theatre | The approval screen shows **the strongest counter-hypothesis and the evidence gaps** alongside the recommendation, and requires a reason on *reject or edit*. **Edit rate** is tracked on the dashboard — an approval rate near 100% is a warning sign, not a success, and we say so during the demo |
| **Negative-KB overcorrection** *(new — created by D4)* | If a remediation failed once in one context, blanket-suppressing it could hide the right fix | Negative entries are **scoped to CI class and failure signature**, and are shown as a *caution with reason*, never a silent filter. Worth naming unprompted — it shows we audit our own additions for the biases they introduce |

The last two rows are the ones to lead with if asked. The first shows we know human oversight usually
degrades into rubber-stamping; the second shows we checked our own new feature for the bias it creates.

### 2.6 Commercial value

- **Toil reduction.** Correlation is the highest-leverage step: a single incident routinely triggers
  dozens of alerts across independent tools with no shared context, and industry-reported
  false-positive rates for operational alerting sit in the **60–80%** range. Collapsing an alert storm
  into a handful of candidate incidents removes the most expensive human step — deciding what is even
  happening.
- **Attacking the cause, not the symptom.** The Quiet Score (D3) goes one level further: rank CIs by
  noise ratio and propose alert-rule fixes. Every competitor gets faster at processing noise; this
  reduces the noise.
- **Time-to-evidence, not time-to-fix.** Our honest claim is that we compress the *investigation and
  bookkeeping* phase. AIOps correlation is credited with MTTR reductions in the **40–50%** range in
  vendor and Forrester-commissioned studies — cite these as *industry context for the opportunity*,
  never as our measured result.
- **Data-quality compounding.** ServiceNow's own published figures associate structured CMDB practice
  with ~**38% faster incident resolution** and ~**82% fewer failed changes**. Our drift loop attacks
  the input to every one of those numbers.
- **Unit economics.** Cost-per-incident (§8) against a stated engineer-hour cost. Independent
  benchmarking showed enormous cost premiums for marginal accuracy gains between models, so "we chose
  the cheaper model here, and here is the accuracy we traded" is a mature answer few teams can give.
- **Audit cost.** An append-only attributable action log is the difference between "we think we can
  automate this" and "compliance will let us automate this."

**Success metrics we instrument for real (no fabricated numbers on any slide):**
`alerts ingested → incidents proposed` (noise-reduction ratio) · `manual steps avoided` ·
`time alert→plan` and `alert→verified resolution` vs stated manual baseline · `plan approval rate` and
**`edit rate`** · **`verified-resolved vs symptom-suppressed`** · `% of diagnoses fully cited` ·
`CMDB drift items detected / reconciled` · `runbooks promoted on the autonomy ladder` ·
`tokens + latency + cost per workflow`.

### 2.7 Beyond the hackathon (the "pragmatic roadmap" guidance wants this)

- **Near term:** replace simulators with real ServiceNow / Jira / Prometheus MCP servers — because the
  adapter is already an MCP boundary, this is genuinely a swap, not a rewrite.
- **Mid term:** the Autonomy Promotion Ladder runs continuously, promoting runbooks to auto-execute as
  their verified-resolution rate accumulates. Register vendor agents as A2A peers and delegate
  platform-native work to them.
- **Longer term:** drift reconciliation as a standing service; runbook mining from postmortems;
  Quiet Score feeding back into monitoring-as-code.

---

## 3. TECH STACK & MODEL ROUTING

### 3.1 Routing principle

**Route by task shape, not by model prestige.** Three questions decide every call:
*Is it deterministic? → don't use an LLM at all.* · *Is the content sensitive? → local.* ·
*Does it need multi-step reasoning? → reasoning model, and only there.*

The first question matters most. **Correlation, policy checks, blast-radius computation, Quiet Score
and metric math are deterministic and must be code.** Using an LLM for arithmetic or rule evaluation is
the most common hackathon mistake and a juror will call it out.

### 3.2 Routing table (proposal — challenge it in review; Phase 0 data may rewrite it)

| Task | Model | Why |
|---|---|---|
| Alert normalisation, dedup, correlation clustering | **No LLM** — Python + scikit-learn | Deterministic, fast, reproducible, explainable. Genuine classical ML trained on CPU |
| Policy gate, blast radius, scheduling constraints, Quiet Score | **No LLM** — rule engine / statistics | Must be auditable and provably consistent |
| Entity/PII detection in raw logs | **Local SLM via Ollama** (+ regex first pass) | Highest-sensitivity content never leaves the machine. Privacy-driven routing |
| Incident narrative summarisation | `gpt-4o-mini` (gateway) | High volume, low complexity, latency-sensitive |
| Ticket drafting, work notes, comments | `gpt-4o-mini` | Formatting-heavy, low reasoning demand |
| Embeddings (runbooks, postmortems, tickets, negative KB) | `text-embedding-3-large` | The only embedding model listed; used for all RAG |
| **Root-cause hypothesis generation & ranking** | **DeepSeek R1** (gateway) | The one step that genuinely needs multi-step reasoning over conflicting evidence |
| Remediation plan drafting from runbooks | DeepSeek V3 | Structured generation, strong instruction following, cheaper than R1 |
| Self-check / critique of the plan before the gate | `gpt-4o-mini` or local SLM | Second-pass verification; ITBench data shows verification gaps are a top failure category |
| Offline fallback for demo resilience | Local Ollama SLM | **If the gateway dies mid-demo we must still run.** See §5 |

**Not used, and we should say why if asked:** Llama Vision (no image input unless 4.9 is adopted),
Whisper (no audio unless 4.8). Phase 0 still smoke-tests every one of them, per the handbook.

### 3.3 Trade-offs to state out loud

- **R1 costs latency.** Reasoning models on a busy shared gateway can take tens of seconds. Mitigation:
  R1 runs on **one** step, asynchronously, with the UI streaming progress; everything else stays fast.
- **More thinking is not always better.** On ITBench, higher turn counts did not reliably mean better
  answers — some high-turn models scored *worse*, because dense incident signal leads agents to keep
  surfacing correlated symptoms past the point of commitment. **Design consequence: hard turn caps and
  explicit termination conditions per agent** — which also addresses the MAST failure mode "unaware of
  termination conditions."
- **Local SLMs are weaker.** Use them where the task is narrow (extraction, classification, redaction),
  never where it is open-ended.
- **Cost/latency is a graded artifact, not a footnote.** Log tokens and wall-clock per agent step and
  render it. Roughly 45 minutes of work for a visible maturity signal.

### 3.4 Orchestration shape

**Two levels: one Supervisor + specialist agents. Deliberately NOT a deep hierarchy and NOT a free
agent mesh.** Rationale — a strong answer to "why this design?":
- MAST analysis of 1,600+ multi-agent traces attributes **44.2%** of failures to system-design issues
  and **32.3%** to inter-agent misalignment. The problem is architectural, not model quality.
- Reported amplification: uncoordinated multi-agent systems can amplify errors up to ~**17×**, while
  **centralised architectures with validation bottlenecks contain it to roughly 4.4×**. We are
  deliberately choosing the validation-bottleneck design.
- Practitioner guidance converges on two-level (router + specialists) over both flat and 3+ level
  designs for behavioural consistency.

**Concretely:** agents never call each other directly. Each returns a typed result to the Supervisor,
which validates it against a schema before dispatching the next. Every agent has an explicit
termination condition and turn cap. **Say this in the demo — "we constrained the topology on purpose,
here is the failure data that made us do it" is exactly the design-rationale answer the guidance asks
for.**

### 3.5 Architecture tiers — draw this, jurors ask for it

```
┌──────────────────────────────────────────────────────────────────┐
│  PRESENTATION        Next.js + shadcn/ui cockpit                 │
├──────────────────────────────────────────────────────────────────┤
│  AI SOLUTION LAYER   Supervisor ── A2A ──▶ specialist agents     │
│                      Guardrails · Policy gate · Scrubber         │
│                      Model router · Prompt registry              │
│                      (A2A endpoints are local; signed Agent Cards)│
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
│  (Optional, Decision 4.21: ONE real Jira Cloud portability probe)│
└──────────────────────────────────────────────────────────────────┘
   Models: TCS GenAI Lab gateway ▸ + local Ollama ▸ — no external MaaS
   Protocols: MCP (agent→tools) · A2A (agent→agent) — open specs, local endpoints
```

### 3.6 Memory, caching, token strategy (explicitly graded)

- **Working memory:** current workflow state in SQLite, passed as a compact typed object between agents
  — **never** the full conversation transcript. Full-state rebroadcast between agents is a known token
  sink and a known source of context drift.
- **Episodic memory:** closed incidents + postmortems embedded into Chroma — the feedback loop.
- **Negative memory:** rejected plans and failed remediations, embedded separately and consulted at
  planning time (4.24).
- **Semantic memory:** runbooks + CMDB schema.
- **Caching:** hash `(prompt_version, scrubbed_input)` → response, in SQLite. A replayed alert does not
  re-bill the gateway. Also makes the demo fast and resilient.
- **Token discipline:** evidence bundles truncated to top-k cited chunks; agents see IDs + extracts,
  never whole documents. Per-step token budget with a hard cap.

### 3.7 Alternatives considered (rehearse — near-certain jury question)

| We rejected | Why |
|---|---|
| Single "do-everything" agent with tools | The statement explicitly asks for multi-agent orchestration, and single-agent traces lose role separation and auditability. Honest caveat: research shows single-agent sometimes *outperforms* multi-agent — our justification is auditability and separation of concerns, not raw accuracy |
| Fully autonomous remediation | ~13.8% SRE resolution rate in independent benchmarking. Promising autonomy would be dishonest and fragile on stage |
| LLM-based event correlation | Non-deterministic, expensive, unexplainable, and worse than clustering at the task |
| Off-the-shelf agent framework (LangGraph / CrewAI / AutoGen) | The handbook rewards framework independence and explainability; we want to *show* the orchestrator code, and a thin custom supervisor over MCP + A2A is ~150 lines. **Open to challenge — Q9.4** |
| Routing *all* agent traffic over A2A | Real implementation burden for no marginal jury credit past the first demonstrated handoff. We implement A2A narrowly and honestly (4.20) |
| An MCP server that "coordinates agents" | A common and visible mistake: MCP servers expose tools to agents; they do not orchestrate agents. Coordination is A2A's layer. Getting this boundary right is itself a credibility signal |
| Real ServiceNow PDI / Jira as the primary systems | See Decision 4.21 — hibernation, availability, licence framing and lab-network risk. Mocks are also *better*, because our scenarios cannot be produced on demand in a real instance |
| Postgres / Neo4j | Overkill at moderate volume; SQLite plus an adjacency table covers CI relationships |
| Naive fixed-size RAG chunking | Splits runbook steps and clause-numbered procedures mid-instruction — actively dangerous when the retrieved text is an action to take against production |

### 3.8 Protocol layer — MCP and A2A (new in v2)

**Why this is here at all:** a jury member raised it, the statement is explicitly about multi-agent
work, and both protocols are now settled infrastructure rather than a trend — **MCP and A2A both sit
under the Linux Foundation's Agentic AI Foundation, launched December 2025 with OpenAI, Anthropic,
Google, Microsoft, AWS and Block as co-founders.**

**The distinction, stated correctly (get this right on the slide):**
- **MCP connects an agent to tools.** Created by Anthropic in November 2024, donated to the Agentic AI
  Foundation in December 2025; adopted across every major provider, with SDK downloads in the tens of
  millions.
- **A2A connects an agent to other agents.** Introduced by Google in April 2025, donated to the Linux
  Foundation; **v1.0 stable as of April 2026** with signed Agent Cards, multi-tenancy, JSON-RPC + SSE
  transport and SDKs in five languages.

**How we use them:**

| Layer | Protocol | What we build |
|---|---|---|
| Agent → systems | **MCP** | One local MCP server per simulated system (Monitoring, ITSM, Tracker, CMDB), each exposing typed tools (`get_alerts`, `create_incident`, `get_ci`, `update_ci`…). Agents call tools through MCP, never through bespoke HTTP |
| Agent → agent | **A2A** | Supervisor ↔ 2–3 specialists over A2A with real Agent Cards describing capabilities. The remaining handoffs stay in-process and typed |
| Future / pitch | **A2A** | The delegation story (§2.2 move 4) — a vendor agent registered as an A2A peer |

**Honest scoping, and why:** independent analysis notes that while A2A's headline adoption numbers are
real, the Linux Foundation's announcement gave no production-deployment counts or usage metrics, and a
March 2026 critical analysis attributed its thinner-than-advertised uptake to implementation burden.
**So we implement A2A narrowly and say so:** enough to demonstrate the architecture with genuine
signed Agent Cards, not enough to spend five hours on protocol plumbing. Overclaiming here is the
easiest way to lose the credibility we gain from raising it.

---

## 4. ⭐ FEATURE OPTIONS & DECISIONS NEEDED

**This is the section to spend the review on.** Each item: what it is · why it fits *this* problem ·
effort · recommendation. **Nothing here is decided. Argue, then tell Claude.**

---

### Core scoping

**4.1 — Depth split across the three task families (patch / performance / incident)**
- *What:* how much we build of each named recurring task.
- *Why it matters here:* the statement names all three, and past juries penalise "missing parts of what
  was asked." But three deep workflows in the available time means all three are shallow — **and v2
  added roughly 2–3h of scope, which has to come from somewhere.**
- *Effort:* incident deep **L** · patch medium **M** · performance thin **S**
- **Recommendation: INCLUDE BY DEFAULT — incident deep, patch medium, performance thin-but-genuine**
  (a real advisory workflow on a real degradation scenario, not a stub). **Performance tuning is the
  most likely funding source for v2's additions. Decide this consciously — it is the biggest scoping
  call in the document.**

**4.2 — Local Ollama SLM in the primary path (not just as fallback)**
- *What:* route PII/secret detection on raw logs to a local model so sensitive text never leaves the box.
- *Why here:* turns "we care about privacy" into an architectural fact, is the most natural use of the
  local-SLM capability the handbook provides, and is demo-proof if the gateway wobbles.
- *Effort:* **S–M** (depends entirely on what `ollama list` returns in Phase 0)
- **Recommendation: INCLUDE BY DEFAULT** — highest ratio of credibility to build time in this list.

**4.3 — Live alert simulator (streaming) vs. scripted replay**
- *What:* a background process emitting alerts on a timeline, vs. a "Run Scenario" button.
- *Why here:* the statement says workflows are *triggered by monitoring alerts*. A button-triggered demo
  quietly fails that clause and a sharp juror will notice.
- *Effort:* **M** (SSE + scheduler; the risk is demo flakiness, not build time)
- **Recommendation: INCLUDE BY DEFAULT — with a manual "inject scenario now" override.** Live-looking,
  never dependent on timing under stage pressure.

**4.4 — Cross-system reconciliation view (Unified Incident Record)**
- *What:* one canonical object linking the ITSM incident, the tracker issue, the CI and the alert
  cluster, with contradiction detection when statuses disagree.
- *Why here:* this *is* the differentiator against platform-native AI; the duplicated-ticket,
  contradictory-status problem is well documented in the ServiceNow↔Jira literature.
- *Effort:* **M**
- **Recommendation: INCLUDE BY DEFAULT.** Load-bearing wall of the pitch.

**4.5 — HITL: single mandatory gate vs. tiered autonomy**
- *What:* (a) every action needs approval; (b) three tiers — auto-execute read-only, approve-required
  for changes, dual-approval for production high-blast-radius.
- *Why here:* the guidance asks to "balance AI autonomy with clear human oversight and intervention
  points." Tiering *demonstrates* the balance; a single gate merely asserts it. Tiering also gives the
  demo a moment where the system **refuses** to act — far more memorable than one where it succeeds.
- *Effort:* **M** (mostly policy-gate configuration, since the gate exists either way)
- **Recommendation: INCLUDE BY DEFAULT (tiered).** Script the refusal as a named demo beat.

**4.6 — Role-based access control (L1 / L2 / Change Manager / Auditor)**
- *What:* simulated login, role-shaped views, role-gated approvals.
- *Why here:* "appropriate access governance" is named in the guidance, and approval authority is
  meaningless without roles — a gate anyone can click is not a control.
- *Effort:* **M** with real auth; **S** as a sidebar role switcher with server-side enforcement
- **Recommendation: INCLUDE BY DEFAULT as a role switcher, enforced server-side, no real auth.** Say
  plainly it is simulated identity. Real auth is **SKIP** — zero marginal credit, real cost.

### New in v2 — protocol and instance decisions

**4.19 — MCP as the adapter/tool layer**
- *What:* expose each simulated system as a local MCP server; agents reach tools only through MCP.
- *Why here:* it is precisely what MCP is for, it makes "framework independence and configurability"
  *literally* true rather than aspirational, and swapping a mock for a real system becomes a server
  swap rather than a rewrite. It also directly answers the juror who raised the topic.
- *Effort:* **M** (~2h including four servers and the client wiring)
- **Recommendation: INCLUDE BY DEFAULT.** Also state the boundary correctly — MCP servers expose tools
  to agents; they do not orchestrate agents. Getting that right is itself a credibility signal.

**4.20 — A2A for agent-to-agent handoffs**
- *What:* Supervisor ↔ 2–3 specialists communicating over A2A with genuine signed Agent Cards; the rest
  of the handoffs stay in-process and typed.
- *Why here:* the statement is explicitly about multi-agent coordination and a juror raised the
  protocol by name. Critically, it unlocks the **delegation reframe** (§2.2 move 4) that turns
  ServiceNow from competitor into peer. But adoption analysis flags implementation burden as A2A's
  main drag, so full internal adoption would be hours for no extra credit.
- *Effort:* **M** narrow (~1.5h) · **L** if everything routes over it
- **Recommendation: INCLUDE BY DEFAULT — narrow scope only.** Two or three handoffs, real Agent Cards,
  honest framing: *"we implemented A2A where it demonstrates the architecture; we did not route all
  internal traffic over it, and here is why."* **Do not let this expand.**

**4.21 — Real ServiceNow PDI / Jira Cloud instance instead of (or alongside) mocks**
- *What:* point one or more adapters at a genuine vendor instance.
- *Findings from research:*
  - **Cost is not the blocker.** A ServiceNow Personal Developer Instance is free but explicitly
    non-commercial and *not licensed for organisational or client-delivered work* — a competition entry
    is arguably organisational. Jira Service Management's free plan is genuinely free forever for up to
    3 agents (2GB storage, 100 email notifications/day, 500 automation runs/month, no support).
  - **PDI operational risk is the blocker.** PDIs hibernate after ~24h of inactivity, are released
    entirely after 10 continuous days (taking all data), can go back to sleep ~30 minutes after waking
    if you don't log in, and may not be available immediately — you can be put on a waitlist.
  - **Network risk.** We already need an SSL bypass to reach our own gateway. Betting the demo on
    outbound access to two external SaaS platforms from that network is a coin flip.
  - **The positive argument for mocks, which is the one to make on stage:** we cannot manufacture a
    50-alert storm, a six-month-drifted CMDB, or a planted credential in a log file inside a real PDI.
    The demo *depends* on injecting exactly those conditions on cue.
- *Effort:* ServiceNow PDI **M–L** and high risk · Jira Cloud free **S** and low risk
- **Recommendation: SKIP ServiceNow PDI entirely. Jira Cloud free = INCLUDE IF TIME PERMITS, as a
  30-minute timeboxed portability probe in Phase 0 only.** If the lab network reaches `atlassian.net`,
  point **one** adapter at real Jira so thirty seconds of the demo shows an agent-created ticket
  appearing in actual Jira — a clean kill for the "it's all fake" objection at near-zero risk, because
  if it breaks we simply don't show it. **Hard rule: 30 minutes, then abandon permanently.** Label it
  on screen as an optional external check, outside the primary solution (§0).

### New in v2 — differentiator features

**4.22 — Cost-per-incident meter** *(D-list item E)*
- *What:* token spend and latency per resolved incident, displayed against a stated engineer-hour cost.
- *Why here:* almost no hackathon team shows unit economics, and independent benchmarking found large
  cost premiums for marginal accuracy gains between models — so "we chose the cheaper model here and
  here is the accuracy we traded" is a genuinely mature answer.
- *Effort:* **S** (the telemetry already exists for §3.3)
- **Recommendation: INCLUDE IF TIME PERMITS — Extra Credit (§8).** Cheap, but not structural.

**4.23 — Quiet Score (alert-noise ranking + alert-rule fix proposals)** *(D3)*
- *What:* rank every CI/monitor by alert-noise ratio; propose changes to the alert rules themselves.
- *Why here:* everyone else's AI triages the flood faster; this reduces the flood. Given operational
  false-positive rates in the 60–80% band, this is where the money actually is — and it introduces a
  stakeholder (the observability engineer) that nobody else will have built for.
- *Effort:* **S** (statistics over the alert store; no LLM needed for the score, one LLM call to draft
  the proposed rule change)
- **Recommendation: INCLUDE IF TIME PERMITS — strong candidate for promotion to core.** Pitch line:
  *"Every other tool makes you better at handling noise. We make the noise go away."* **Team call.**

**4.24 — Negative Knowledge Base** *(D4)*
- *What:* capture rejected plans and failed remediations with reasons; consult them at planning time so
  the system stops re-proposing what already didn't work.
- *Why here:* every RAG system indexes successes; almost none index failures. It is a `rejected_reason`
  field plus a second Chroma collection and one retrieval filter — and it makes the human-feedback loop
  load-bearing rather than decorative, which is exactly what the "feedback loops" guidance asks for.
- *Effort:* **S**
- **Recommendation: INCLUDE BY DEFAULT.** Note the bias it introduces and the scoping mitigation
  (§2.5, last row) — raising that unprompted is worth more than the feature itself.

**4.25 — Autonomy Promotion Ladder** *(D5)*
- *What:* a runbook starts at *approval-required*; after N verified resolutions with zero rejections it
  graduates to *auto-execute with notification*. Visible in the UI as a ladder showing each runbook's
  position.
- *Why here:* the single best answer to "balance AI autonomy with human oversight" — **autonomy is
  earned per runbook by measured evidence, not toggled on globally.** It also gives the mid-term
  roadmap (§2.7) a concrete mechanism rather than an aspiration.
- *Effort:* **S–M** (state column + promotion rule + one UI panel; the verification data already exists)
- **Recommendation: INCLUDE BY DEFAULT.** Even with only 2–3 scenarios run, the ladder *moving* on
  stage is a memorable beat.

**4.26 — Drift-vs-Truth split screen** *(D2)*
- *What:* run the same incident twice — once against the CMDB as-is, once against ground truth — and
  show the diagnoses diverging side by side.
- *Why here:* it *dramatises* the 60%-accuracy statistic instead of citing it. Our strongest
  differentiator currently lives in a table; this puts it on screen.
- *Effort:* **S** if the drift detector (4.11) exists, since ground truth is already in our synthetic
  data by construction
- **Recommendation: INCLUDE BY DEFAULT.** Probably the best single visual moment available to us.

### Remaining open calls

**4.7 — Multilingual support**
- *What:* Hindi/regional-language intake for user-reported tickets.
- *Why here:* honestly weak. This problem is machine-to-machine — alerts, CIs, logs, runbooks are all
  English. The only real surface is a human-raised ticket description.
- *Effort:* **S** (translate-on-intake) to **M** (end-to-end)
- **Recommendation: SKIP.** *Counter-argument worth 60 seconds: if any juror weights India-context
  inclusivity, a single translate-on-intake step is cheap insurance.*

**4.8 — Voice input (Whisper is on the approved list)**
- *What:* an on-call engineer dictates a handover note or field observation; it becomes structured input.
- *Why here:* a genuine scenario (hands full during an outage), but a side door into a workflow that
  starts from alerts, and it eats demo time.
- *Effort:* **M** — **Recommendation: SKIP for core; Extra Credit only (§8).**

**4.9 — Screenshot/vision ingestion (Llama Vision is on the approved list)**
- *What:* paste a dashboard screenshot or error dialog; extract signal into the incident.
- *Why here:* extremely common in real ops, and uses an approved model that would otherwise go unused.
- *Effort:* **M** — **Recommendation: INCLUDE IF TIME PERMITS.** Real and demo-friendly, not on the
  critical path.

**4.10 — Eval dashboard depth**
- *What:* (a) simple run metrics; (b) scenario pass/fail vs expected root cause; (c) full harness —
  per-scenario accuracy, **symptom-suppressed vs verified-resolved split**, citation coverage,
  hallucination checks, token/latency/cost.
- *Why here:* "Testing and QA" is an explicit guidance block that most teams will skip entirely, and
  (c) is where the anti-reward-hacking insight becomes visible.
- *Effort:* (a) **S** · (b) **M** · (c) **L**
- **Recommendation: (b) INCLUDE BY DEFAULT; (c) INCLUDE IF TIME PERMITS — but pull the
  symptom-suppressed vs verified-resolved metric forward into (b).** That one metric carries most of
  the value.

**4.11 — CMDB drift detection & reconciliation agent**
- *What:* compare CMDB attributes against observed state; flag drift; propose approved corrections;
  write back on approval.
- *Why here:* satisfies "updating CMDBs" and "data completeness and accuracy," and it is the engine
  behind 4.26 and behind our strongest competitive argument.
- *Effort:* **M**
- **Recommendation: INCLUDE BY DEFAULT.** If time collapses, keep *detection* and drop *automatic
  reconciliation* — detection alone still makes the argument and still powers the split screen.

**4.12 — Classical ML component (CPU-trained, genuinely)**
- *What:* (a) alert clustering for correlation — unsupervised, no training needed; (b) a change/patch
  **risk classifier** trained on synthetic historical change outcomes (logistic regression / gradient
  boosting on tabular features).
- *Why here:* the handbook rewards standard ML alongside GenAI, and here it is *genuinely the right
  tool* rather than decoration. (b) also feeds the scheduling agent a real number.
- *Effort:* (a) **S** · (b) **S–M**
- **Recommendation: (a) INCLUDE BY DEFAULT. (b) INCLUDE IF TIME PERMITS.** Both are honest CPU work
  and neither requires claiming anything about LLM training.

**4.13 — Scoped chat alongside the cockpit**
- *What:* a conversational panel ("why did you rank this first?", "show me similar past incidents")
  grounded strictly in the current incident's evidence.
- *Why here:* the guidance names "conversation, visualization, or a hybrid model." Risk: an unscoped
  chatbot re-opens the "so it's ChatGPT" objection §2.2 spends its energy closing.
- *Effort:* **M**
- **Recommendation: INCLUDE BY DEFAULT — strictly scoped, and it visibly refuses out-of-scope
  questions.** The refusal is the point.

**4.14 — Simulated vs. actually-executed remediation**
- *What:* (a) execution simulated with a real state change; (b) real scripts against a local sandbox.
- *Why here:* (b) is more impressive and makes verification meaningful, but it is a large time sink,
  introduces environment risk, and can fail on stage.
- *Effort:* (a) **S** · (b) **L**
- **Recommendation: (a) INCLUDE BY DEFAULT.** Make simulation *credible*: the simulated target holds
  real state and real metrics that actually change, so verification is genuine rather than scripted.
  **Never imply it is real infrastructure.**

**4.15 — Admin panel (ingestion, model config, prompt registry, thresholds)**
- *What:* sidebar admin for uploading runbooks, tuning thresholds, viewing prompt versions, switching
  models.
- *Why here:* demonstrates "configurability and framework independence" and makes the demo interactive
  — a juror changing a threshold and watching behaviour change is a strong moment.
- *Effort:* **M** full · **S** scoped to model switch + thresholds + runbook upload
- **Recommendation: INCLUDE BY DEFAULT at the S scope.** Full admin CRUD is **SKIP**.

**4.16 — Notification / workflow connectivity**
- *What:* approval requests and resolution summaries pushed to a simulated channel.
- *Why here:* the handbook rewards "connectivity with an existing workflow"; cheap to fake convincingly.
- *Effort:* **S** — **Recommendation: INCLUDE IF TIME PERMITS** (Extra Credit, §8).

**4.17 — Post-incident knowledge capture written back into RAG**
- *What:* on closure, generate a structured postmortem and embed it, so the next similar incident
  retrieves it.
- *Why here:* the "feedback loop / adaptability" guidance made concrete and *demonstrable* — run
  scenario A, close it, run similar scenario A′, show it retrieving its own prior learning.
- *Effort:* **S–M**
- **Recommendation: INCLUDE BY DEFAULT.** The A → A′ beat is one of the strongest in the deck per hour
  spent, and it pairs with the Negative KB (4.24) as the positive/negative halves of one loop.

**4.18 — Advanced prompting (self-consistency / ReAct-style)**
- *What:* sample the root-cause step N times and keep hypotheses that recur; or explicit
  reason-act-observe loops.
- *Why here:* self-consistency is a real accuracy lever exactly where we need it and yields an honest
  confidence signal (agreement rate). ReAct is riskier given the "more turns made it worse" finding.
- *Effort:* self-consistency **S** · ReAct **M–L**
- **Recommendation: self-consistency INCLUDE IF TIME PERMITS (strong candidate); ReAct SKIP.**

---

## 5. PROPOSED ROADMAP (relative durations only)

Total working budget ~16–18h. **Everything between Phase 0 and the Final Phase is a proposal driven by
Section 4 and is open to being merged, resequenced or dropped.** v2 adds ~2–3h of scope; §4.1 is the
most likely place to reclaim it.

### PHASE 0 — Environment & Gateway Smoke Test · ~1h (+30 min optional probe) · **FIXED · STARTS NOW · PARALLEL WITH THIS REVIEW**
**Independent of every decision in this document. One person starts before the team finishes reading.**
1. `ollama list` — record exact model names and sizes. **Never download.**
2. Gateway auth: one successful call to **every** handbook-listed model — `gpt-4o-mini`, DeepSeek V3,
   DeepSeek R1, Llama Vision, Phi, Whisper, `text-embedding-3-large`. *Every* one, not just the ones
   this PRD needs; a model we dismissed today may become tonight's fallback.
3. Confirm the `httpx` SSL bypass and the `TIKTOKEN_CACHE_DIR` fix.
4. Record **latency and token cost per model** — this data rewrites §3.2 for real.
5. Verify `text-embedding-3-large` → Chroma round-trip end to end.
6. Scaffold: FastAPI skeleton, Next.js + shadcn init, SQLite schema stub, repo structure.
7. **Optional, hard-timeboxed 30 minutes (Decision 4.21):** can the lab network reach `atlassian.net`?
   If yes, create the free Jira instance and one API token. **If it isn't working at 30 minutes,
   abandon permanently — do not revisit.**
8. **Deliverable: a one-page `PHASE0_FINDINGS.md`.** Any model that fails here is dead to us; the
   routing table gets rewritten around what actually responded.

### PHASE 1 — Data, Simulated Systems & MCP Layer · ~3h
Synthetic data generation (§6); the four simulated systems; **four local MCP servers wrapping them**;
canonical schemas frozen (everything downstream depends on this); SQLite + Chroma populated; structural
chunking verified by eyeballing retrieved chunks by hand.
*Gate: an agent-free script can drive a full scenario through the MCP tools end to end.*

### PHASE 2 — Deterministic Core (no LLM) · ~2h
Correlation engine, policy gate, blast-radius computation, audit log, PII/secret scrubber with unit
tests, Quiet Score statistics if adopted. **Deliberately before any agent work** — this is the layer
everything else is validated against, and the layer that still works when models misbehave.
*Gate: alert storm → correlated clusters, reproducibly. Scrubber unit tests green.*

### PHASE 3 — Agent Chain, Supervisor & A2A · ~4.5h
Supervisor, typed handoff contracts, turn caps, termination conditions. **A2A narrow implementation
(4.20) with signed Agent Cards on 2–3 handoffs.** Specialists in demo-importance order:
Enrichment → Diagnosis (R1) → Remediation Planner → Verification → Sync → Knowledge (+ Negative KB).
Citation enforcement built in from the first agent, never retrofitted.
*Gate: one scenario runs alert → verified resolution → cross-system sync, fully traced, with at least
one handoff demonstrably travelling over A2A.*

### PHASE 4 — Cockpit UI · ~3.5h
Ops board, Unified Incident Record, **Agent Trace Viewer (highest-priority component)**, approval
queue, drift queue + **Drift-vs-Truth split screen**, **Autonomy Ladder panel**, metrics dashboard,
admin strip. Wire the live alert feed.
*Gate: the golden-path demo is clickable start to finish by someone who did not build it.*
**⚠ This phase is the most likely place the plan breaks — see Q9.3.**

### PHASE 5 — Scenario Library, Eval & Hardening · ~2.5h
Remaining scenarios including edge cases (conflicting evidence, no precedent, policy refusal, scrubber
catch, drift, prompt-injection line). Eval harness. Caching. Fallback path.
**Full run of every scenario, twice.**
*Gate: every scenario passes twice consecutively. Anything flaky gets cut, not debugged at 2am.*

### PHASE 6 — Extra Credit · ~1–2h · **conditional, only if the Phase 5 gate is green**
Pull from §8 in listed order. **Hard stop; borrows nothing from the Final Phase.**

### FINAL PHASE — Freeze & Packaging · ~2h · **FIXED · LAST**
**Feature work stops. No exceptions — a feature added here has broken more demos than it has saved.**
- README, including the explicit gateway-vs-external statement, the "simulated systems" disclaimer, and
  the **"MCP/A2A are open protocols running locally, not external services"** line
- Notebook / execution-flow walkthrough; deck; architecture diagram (§3.5)
- Demo script with named beats, including: the **alert-storm collapse** opener, the **refusal beat**,
  the **Drift-vs-Truth split screen**, the **A→A′ learning beat**, and the **A2A delegation answer**
- **Round-robin rehearsal: all five members explain the full flow end to end.** The guidance names this
  explicitly and it is the cheapest marks in the competition.
- Backup: recorded demo video + cached-response mode, in case the gateway is down at judging time.

---

## 6. SYNTHETIC DATA STRATEGY

### 6.1 What we generate

| Artifact | Format | Volume | Contents |
|---|---|---|---|
| CMDB (as-recorded) | JSON → SQLite | ~200 CIs | Apps, services, DBs, hosts; relationships; owner, env, criticality, patch level, last-verified date |
| **CMDB ground truth** | JSON | same | The *actual* state, differing from the recorded CMDB on ~35% of CIs — **this is what makes 4.26 possible and it costs nothing extra to generate** |
| Alert stream | JSON | ~500 across scenarios | Multi-source shapes (Prometheus-like, SNMP-terse, APM-verbose) — **deliberately heterogeneous to exercise the alert-verbosity bias mitigation**, and with noise ratios varied per CI to give the Quiet Score something real to rank |
| Metric series | CSV | per CI | Enough shape for pre/post verification to be meaningful |
| Ticket history | CSV/JSON | 400–600 closed | Incidents + changes: symptoms, root cause, resolution, timings, assignment — the RAG corpus and the risk-classifier training set |
| **Failed-remediation records** | JSON | ~40 | What was tried and why it didn't work — seeds the Negative KB so 4.24 has content on day one rather than after three demo runs |
| Runbooks | Markdown + 2–3 PDF | 15–20 | Numbered, clause-structured procedures with declared human-step counts (feeds the manual-steps-avoided metric) |
| Postmortems | Markdown | 8–10 | Narrative RCA documents |
| Change calendar | JSON | — | Freeze windows, blackout periods, approval matrix |
| Patch inventory | CSV | — | Pending patches per CI, severity, dependencies |

### 6.2 Deliberately embedded sensitive data (to prove the scrubber)

Planted at known locations so the demo is deterministic and the eval is checkable:
- **Personal data:** employee names, corporate emails, phone numbers, employee IDs, manager names in
  ticket descriptions and work notes
- **Secrets:** a connection string with an inline password, an API key in a config dump, a bearer token
  in a log excerpt, private IP ranges, internal hostnames
- **Adversarial edge case (build one deliberately):** a log line containing text that *looks* like a
  prompt instruction — e.g. an error message quoting user input saying "ignore previous instructions."
  Show that the scrubber and the typed-contract boundary contain it. **A prompt-injection-resilience
  beat costs almost nothing and very few teams will have one.**
- Register every planted item in `pii_ground_truth.json` so the eval computes real precision/recall on
  the scrubber instead of us asserting that it works.

### 6.3 RAG chunking — structural, never naive

Runbooks and postmortems are chunked on **structural boundaries: headings, numbered steps, clause
numbers.** A fixed-character split that cuts step 4 in half is not merely lossy here — the retrieved
text is *an action a human may take against production*. Each chunk carries `doc_id`, `section_id`,
`heading path` and `step range`, so citations point at a step rather than a byte offset. Verify by
inspecting retrieved chunks by hand in Phase 1; do not assume.

### 6.4 Provenance (Handbook §8.3)

**Everything is synthetic and generated by us.** Maintain `data/PROVENANCE.md` recording, per dataset:
generator script, generation date, schema rationale, and — where a schema imitates a real product's API
shape (ServiceNow incident fields, Jira issue JSON) — a note that **the shape is modelled on publicly
documented field structures and contains no real, customer or proprietary data.** No scraped data. No
real ticket exports. No customer names, even as jokes. If any library or dataset is added later, its
licence goes in this file the moment it is added. If Decision 4.21's Jira probe is taken, note that the
only data sent to it is synthetic data generated by us.

---

## 7. UI/UX DESIGN

**We keep the decoupled enterprise cockpit default — it is the right shape for this problem, and here
is the specific reasoning rather than "it's our template":** the primary user is an operator triaging
concurrent work under time pressure while carrying an approval responsibility. That is a *monitoring
and decision* job, not a *conversation* job. A chat-first interface would force serialised,
one-question-at-a-time interaction onto a fundamentally parallel task — and would hand the jury the
"so it's a ChatGPT wrapper" framing for free.

**One deliberate departure from the default template, and it matters:** the centrepiece is not the
execution panel — it is the **Agent Trace Viewer**. The problem statement asks the prototype to
demonstrate *multi-agent coordination*, and coordination is invisible in a results panel. So the trace
is a first-class, always-visible workspace object, not a debug drawer. With 4.20 adopted, the trace
also renders **which handoffs travelled over A2A and shows the Agent Card** — the protocol becomes
something the jury can see rather than something we claim.

**Layout**

- **Sidebar:** role switcher (4.6) · ingestion/admin (4.15) · model & threshold config · scenario
  launcher · audit log · settings
- **Main — tabbed workspace:**
  - **Ops Board** — live alert feed left, correlated incident candidates right, noise-reduction ratio
    as a headline number. *Opening shot of the demo: dozens of alerts collapsing into three cards.*
  - **Incident Workspace** — the Unified Incident Record: evidence panel with citations; ranked
    hypotheses with confidence and an explicit "could not verify" block; the proposed plan with blast
    radius and **any Negative-KB caution attached**; and the linked ITSM/tracker/CI records side by
    side with contradictions highlighted
  - **Agent Trace** — horizontal timeline of handoffs; click any step for inputs, scrubbed prompt,
    model used, tokens, latency, output, validation result, and transport (in-process vs A2A). Includes
    a **Replay** control. **This is the screen that wins the "show me the coordination" question**
  - **Approval Queue** — HITL: recommendation *plus counter-hypothesis plus evidence gaps*;
    approve / edit / reject with a mandatory reason on edit-or-reject (which feeds the Negative KB)
  - **Drift Queue + Drift-vs-Truth split screen** — CMDB disagreements with reality, proposed
    corrections, and the two-column diagnosis comparison
  - **Autonomy Ladder** — every runbook and its current tier, with progress toward promotion
  - **Maintenance Planner** — patch grouping, proposed windows, dependency/conflict view
    *(first candidate for demotion to a panel if Phase 4 runs long)*
  - **Quiet Score** *(if 4.23 adopted)* — noisiest monitors ranked, with proposed rule changes
  - **Metrics & Eval** — §2.6 metrics; verified-resolved vs symptom-suppressed split; token/cost/latency
- **Scoped chat (4.13):** a right-hand drawer bound to the current incident's evidence only, which
  visibly declines out-of-scope questions.

**Design principles:** confidence is always visible and always accompanied by its evidence basis;
nothing AI-generated appears in the same visual register as verified fact (distinct treatments for
`AI proposed` / `human approved` / `system verified`); every number is clickable through to its source
artifact; the system's refusals are displayed as prominently as its successes.

---

## 8. EXTRA CREDIT BACKLOG

> **Every item: attempt ONLY after the Phase 5 gate is green. None may borrow time from the core
> roadmap or the Final Phase. If in doubt, don't.**

Ordered by value per hour:

1. **Simple HTML quick-view launcher** (**S**) — one static `demo.html` with big buttons to launch each
   scenario and jump to the right screen. Removes all navigation fumbling on stage. *Highest ROI item
   here.*
2. **Cost-per-incident meter** (4.22, **S**) — unit economics next to a stated engineer-hour cost. Very
   few teams show this and it directly supports the commercial-value slide.
3. **Self-consistency on root-cause ranking** (4.18, **S**) — sample N times, keep recurring
   hypotheses, report agreement rate as an honest confidence signal.
4. **Notification connectivity** (4.16, **S**) — approvals and summaries to a simulated channel;
   satisfies "connectivity with an existing workflow."
5. **Prompt-injection resilience demo beat** (**S**) — surface the §6.2 adversarial log line as a named
   moment. Cheap, distinctive, memorable.
6. **Change-risk classifier** (4.12b, **S–M**) — CPU-trained tabular model over synthetic change
   history, feeding the scheduler a real risk score. Genuine standard-ML-alongside-GenAI content.
7. **"Nobody asked for it" feature — the Shift Handover Brief** (**S–M**) — one click generates a
   handover summary of the shift: open incidents, what the agents did, what awaits approval, what was
   refused and why. Nothing in the statement asks for it; every real ops team does it manually every
   day. *Strong candidate for the "useful small feature" category — obviously useful the moment a juror
   sees it.*
8. **Screenshot ingestion via Llama Vision** (4.9, **M**) — also puts an otherwise-unused approved model
   to work.
9. **Voice intake via Whisper** (4.8, **M**).
10. **Full eval harness** (4.10c, **L**) — only if genuinely everything else is done.

---

## 9. OPEN QUESTIONS & ASSUMPTIONS

**Answer these in the review. Where I guessed, I have said so — nothing is buried in prose elsewhere.**

**Questions for the team / to verify against the handbook**
1. **Team split across 5 people.** I have not proposed one, because I do not know your individual
   strengths. Phases 1–4 parallelise cleanly (data + simulators + MCP / deterministic core / agents +
   A2A / UI) but **only if the canonical schemas are frozen at the end of Phase 1.** **Who owns what?**
2. **"Workflow modeling" (clause B9)** — declarative agent-graph modelling (my reading, ~S) or
   process-mining historical logs to discover the workflow (~L)? I assumed the first. **Confirm.**
3. **Is there a required submission artifact list** (notebook? specific README sections? deck
   template?) in the handbook that should shape the Final Phase? I do not have the handbook text —
   **someone check §8 and the submission section and tell me what to add.**
4. **Custom orchestrator vs. an agent framework.** I recommended custom (§3.7). If someone on the team
   already knows LangGraph well, that judgement flips — familiarity beats purity at hour 12.
   **Speak up now, not in Phase 3.** Note that MCP + A2A reduce the argument for a framework, since the
   interop the framework would have given us now comes from the protocols.
5. **Do we have anyone who has touched MCP or A2A before?** The estimates in 4.19/4.20 assume reading
   the SDK docs cold. If someone has used either, both estimates drop materially and 4.23 becomes
   affordable as core.
6. **One laptop or several for the demo?** Affects whether the simulated systems and MCP servers run as
   separate processes or in-process, and it affects the fallback plan.
7. **Is there a hard demo time limit?** It determines how many scenarios make the script and therefore
   how much of §4 is worth building at all.

**Assumptions I made (challenge any of them)**
- The four "external" systems are **ours, simulated, API-compatible** — not real vendor instances
  (except the optional 4.21 probe). Everything in §2.2 depends on this being clearly disclosed.
- MCP and A2A servers/endpoints run **locally**, so they are not an external dependency under FAQ
  13.10.18. I am confident in this reading, but **someone should sanity-check it against the handbook
  text**, because the whole protocol layer rests on it.
- Moderate data volume means hundreds-to-low-thousands of records, so SQLite + Chroma is correct.
- "Real-time dashboards" means live-updating within the demo session, not sub-second streaming SLAs.
- The gateway is reachable and reasonably fast from the lab network. **Phase 0 proves or kills this**,
  and if it is slow the routing table changes materially — R1 may become unaffordable.
- No deployment requirement; localhost is acceptable for judging.
- English-only content (drives the 4.7 recommendation).
- The ISU being listed as LSHC does **not** change this statement's domain (§1.5). If anyone believes
  the jury will read it through a healthcare lens, say so now — it would change §1.5 substantially.

**Things I am genuinely uncertain about**
- Whether **4.1** (three-family depth split) is right, and it is now more pressing because v2 added
  scope. I could argue the other way: two families done excellently may beat three done unevenly.
- Whether **A2A (4.20) earns its 1.5h.** The delegation reframe is the strongest competitive answer we
  have — but that answer works as a *slide and a spoken argument* even without the implementation. If
  Phase 3 runs long, **cut the implementation and keep the argument.** Be honest if asked: "we designed
  for it and did not implement it in the time available" is a perfectly good answer; implying we built
  it would be fatal.
- Whether **Quiet Score (4.23)** should be core rather than optional. It is the only feature that
  attacks the *cause* of alert fatigue rather than the symptom, which is a strong story — but it is
  also the easiest thing to cut without breaking the golden path.
- Whether **Phase 4 (UI, ~3.5h)** is realistic for a beginner-to-intermediate team across this many
  screens. **This remains the most likely place the plan breaks.** Pre-agree the demotion order now:
  Maintenance Planner → panel, Quiet Score → cut, Autonomy Ladder → static display rather than live.

---

## 10. NEXT STEPS

**Read sections 4 and 9 together as a team.** Tell Claude your decisions in plain language and it will
revise this document. Repeat until it's right.

**Budget roughly 60–90 minutes for this. Every minute here should be preventing a wrong direction, not
polishing prose — and it should never run past 2 hours.**

Meanwhile, **Phase 0 starts now**, in parallel, regardless of anything in this document.

When everyone is satisfied, say **"finalize"** and Claude will save the complete, current version of
this document to `/PRD_FINAL.md` exactly as agreed, ready for the conversion step.

---

### Appendix — external sources informing §2, §3 and Decision 4.21

Used for framing, positioning and feasibility only. No external system is a dependency of the primary
solution.

- **Agent benchmarks:** IBM ITBench (arXiv:2502.05352) — agents resolve ~13.8% of SRE scenarios;
  ITBench-AA independent leaderboard (Artificial Analysis); Stratus finding that 8/18 mitigation
  problems are "solvable" by a generic pod-restart loop
- **Multi-agent reliability:** MAST failure taxonomy (arXiv:2503.13657) — 14 failure modes over 1,600+
  traces; 44.2% system design, 32.3% inter-agent misalignment; 41–86.7% failure rates; error
  amplification ~17× uncoordinated vs ~4.4× with a centralised validation bottleneck
- **Protocols:** Linux Foundation A2A one-year announcement, April 2026 — 150+ organisations, v1.0
  stable, signed Agent Cards, five-language SDKs, ServiceNow among participants; MCP donated to the
  Agentic AI Foundation, December 2025; independent adoption analysis noting A2A's implementation
  burden and absence of published production-deployment counts
- **Competitive:** ServiceNow Now Assist / AI Agents documentation and 2026 practitioner reviews
  (Context Engine, IntegrationHub, configuration prerequisites); ServiceNow↔Jira integration literature
  on duplicated tickets and contradictory statuses
- **CMDB quality:** ~60% typical accuracy; 30–40% inaccuracy within six months in manually maintained
  environments; ServiceNow-published CMDB-practice outcomes (~38% faster incident resolution, ~82%
  fewer failed changes)
- **Alert fatigue / AIOps:** 60–80% false-positive medians; 40–58% MTTR reduction claims
- **Developer instances (4.21):** ServiceNow PDI free but non-commercial and not licensed for
  organisational work; hibernation after ~24h inactivity, release after 10 days, possible waitlist;
  Jira Service Management free plan free forever for up to 3 agents with 2GB storage, 100 email
  notifications/day and 500 automation runs/month
- **Privacy:** India DPDP Act 2023 + DPDP Rules notified November 2025; phased compliance into 2027
