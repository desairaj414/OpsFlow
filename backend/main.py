# MUST be first — before any langchain/tiktoken import. config.py sets TIKTOKEN_CACHE_DIR and the
# TCS-network-only SSL bypass (gated behind TCS_NETWORK, see config.py) as import-time side effects
# — this used to be duplicated here unconditionally; now there is exactly one copy of this logic.
import os
import config  # noqa: E402

import asyncio
import json
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, Field

import mcp_servers.itsm_mcp as itsm_mcp
import provider_context
import providers
from a2a.client import fetch_agent_card
from api_client import get_llm
from correlation.cluster import _load_alerts, _load_cis_and_relationships, build_topology_groups, correlate_alerts
from db.init_db import DB_PATH
from intake.vision_path import run_vision_intake
from intake.voice_path import run_voice_intake
from orchestrator.audit import write_audit_entry
from orchestrator.contracts import MaintenanceSignal
from orchestrator.intake_adapter import start_workflow_from_confirmed_signal
from orchestrator.mcp_wiring import wire_all_in_process
from orchestrator.supervisor import run_workflow

app = FastAPI(title="Hackathon Boilerplate API")

# --- CORS: allow the Next.js/Vite frontend origin ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# ---------------- Mock JWT auth ----------------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_access_token(
    subject: str, role: str | None = None, display_name: str | None = None,
    real_username: str | None = None, real_role: str | None = None, real_display_name: str | None = None,
) -> str:
    expire = datetime.utcnow() + timedelta(minutes=config.JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    if role is not None:
        payload["role"] = role
        payload["display_name"] = display_name
    if real_username is not None:
        # Set only by POST /auth/view-as — lets the token honestly carry "who's really logged in"
        # alongside "who they're currently viewing as", so the UI can show an impersonation banner
        # instead of silently pretending the admin IS the other user.
        payload["real_username"] = real_username
        payload["real_role"] = real_role
        payload["real_display_name"] = real_display_name
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ---------------- Roles & real authentication ----------------
# decisions-log.md: real-auth decision supersedes the original "no real authentication" PRD call.
# UI-facing role vocabulary kept deliberately separate from guardrails/policy_gate.py's actor_role
# vocabulary (operator|sre_lead|change_manager, frozen/tested) via ROLE_TO_ACTOR_ROLE, so the
# policy gate never has to learn about "users" as a concept.
ROLES = {"ops_engineer", "approver", "admin"}
ROLE_TO_ACTOR_ROLE = {"ops_engineer": "operator", "approver": "sre_lead", "admin": "change_manager"}


class Identity(BaseModel):
    username: str
    role: str = "ops_engineer"
    display_name: str | None = None
    real_username: str | None = None  # set only while an admin is viewing-as another user
    real_role: str | None = None
    real_display_name: str | None = None


def get_current_identity(token: str = Depends(oauth2_scheme)) -> Identity:
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return Identity(
            username=username, role=payload.get("role", "ops_engineer"), display_name=payload.get("display_name"),
            real_username=payload.get("real_username"), real_role=payload.get("real_role"),
            real_display_name=payload.get("real_display_name"),
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_role(identity: Identity, allowed: set[str]) -> None:
    if identity.role not in allowed:
        raise HTTPException(status_code=403, detail=f"role '{identity.role}' cannot perform this action (requires one of {sorted(allowed)})")


class UserOut(BaseModel):
    id: str
    username: str
    display_name: str
    role: str
    created_at: str


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str
    role: str


@app.get("/users", response_model=list[UserOut])
def list_users(identity: Identity = Depends(get_current_identity)):
    require_role(identity, {"admin"})
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute("SELECT id, username, display_name, role, created_at FROM users ORDER BY created_at").fetchall()
    finally:
        conn.close()
    return [UserOut(id=r[0], username=r[1], display_name=r[2], role=r[3], created_at=r[4]) for r in rows]


@app.post("/users", response_model=UserOut)
def create_user(req: UserCreate, identity: Identity = Depends(get_current_identity)):
    require_role(identity, {"admin"})
    if req.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"role must be one of {sorted(ROLES)}")
    if not req.username.strip() or not req.display_name.strip():
        raise HTTPException(status_code=400, detail="username and display_name are required")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="password must be at least 8 characters")
    from auth_utils import hash_password

    user_id = f"USR-{uuid.uuid4().hex[:8].upper()}"
    created_at = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    try:
        try:
            conn.execute(
                "INSERT INTO users (id, username, password_hash, display_name, role, created_at) VALUES (?,?,?,?,?,?)",
                (user_id, req.username, hash_password(req.password), req.display_name, req.role, created_at),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail=f"username '{req.username}' already exists")
    finally:
        conn.close()
    return UserOut(id=user_id, username=req.username, display_name=req.display_name, role=req.role, created_at=created_at)


@app.delete("/users/{user_id}")
def delete_user(user_id: str, identity: Identity = Depends(get_current_identity)):
    require_role(identity, {"admin"})
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT username, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="user not found")
        username, role = row
        if username == identity.username:
            raise HTTPException(status_code=400, detail="cannot delete your own account")
        if role == "admin":
            admin_count = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="cannot delete the last remaining admin account")
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
    return {"deleted": True}


class ViewAsRequest(BaseModel):
    user_id: str


@app.post("/auth/view-as", response_model=TokenResponse)
def view_as(req: ViewAsRequest, identity: Identity = Depends(get_current_identity)):
    # Admin-only, scoped impersonation for demo/testing — NOT a general self-service role switch.
    # The old design (POST /auth/select-profile) let ANY logged-in user grant themselves Admin;
    # real auth means only an already-authenticated Admin can borrow another role, and the token
    # honestly carries who they really are via real_* claims for the UI's "viewing as" banner.
    require_role(identity, {"admin"})
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT username, display_name, role FROM users WHERE id = ?", (req.user_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    target_username, target_display_name, target_role = row
    token = create_access_token(
        subject=target_username, role=target_role, display_name=target_display_name,
        real_username=identity.username, real_role=identity.role, real_display_name=identity.display_name,
    )
    return TokenResponse(access_token=token)


@app.post("/auth/stop-view-as", response_model=TokenResponse)
def stop_view_as(identity: Identity = Depends(get_current_identity)):
    if not identity.real_username:
        raise HTTPException(status_code=400, detail="not currently viewing as another user")
    token = create_access_token(subject=identity.real_username, role=identity.real_role, display_name=identity.real_display_name)
    return TokenResponse(access_token=token)


@app.post("/auth/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    from auth_utils import verify_password

    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT username, password_hash, display_name, role FROM users WHERE username = ?", (form_data.username,)
        ).fetchone()
    finally:
        conn.close()
    if row is None or not verify_password(form_data.password, row[1]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    username, _password_hash, display_name, role = row
    token = create_access_token(subject=username, role=role, display_name=display_name)
    return TokenResponse(access_token=token)


class FetchModelsRequest(BaseModel):
    provider: str
    api_key: str
    base_url: str | None = None  # only meaningful for provider="custom"


class ValidateKeyRequest(BaseModel):
    provider: str
    api_key: str
    model: str
    base_url: str | None = None


@app.post("/providers/fetch-models")
def fetch_provider_models(req: FetchModelsRequest):
    """Called from the login screen's Bring Your Own Key panel (LoginModeSelector.jsx) before a
    visitor has authenticated — no Depends(get_current_identity), deliberately. Never logs req.api_key."""
    if req.provider not in providers.PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{req.provider}'")
    return {"models": providers.fetch_models(req.provider, req.api_key, req.base_url)}


@app.post("/providers/validate-key")
def validate_provider_key(req: ValidateKeyRequest):
    """Same pre-login context as fetch_provider_models — lets the login screen catch a bad BYOK
    key/model before the visitor ever reaches the cockpit, instead of failing silently on the first
    real workflow run.

    Also returns `capabilities.supports_transcription` — the registry's static, verified value for
    every curated provider (no extra network call), or a real 404-vs-not probe result for `custom`,
    where it can't be known ahead of time (see providers.probe_transcription_support()). The
    frontend's canUseVoice() prefers this returned value over its own static default when present."""
    if req.provider not in providers.PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{req.provider}'")
    ok, error = providers.validate_key(req.provider, req.api_key, req.model, req.base_url)
    capabilities = {}
    if ok:
        capabilities["supports_transcription"] = providers.probe_transcription_support(
            req.provider, req.api_key, req.base_url
        )
    return {"ok": ok, "error": error, "capabilities": capabilities}


@app.get("/auth/me")
def read_me(identity: Identity = Depends(get_current_identity)):
    return identity.model_dump()


def get_current_user_from_query_token(token: str) -> str:
    # EventSource (browser SSE) cannot set an Authorization header, so the live-feed
    # endpoint takes the JWT as a query param instead of reusing get_current_user's
    # header-based Depends.
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ---------------- Health ----------------
@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------- Live alert feed (SSE) ----------------
_ALERT_COLUMNS = "alerts.id, source, raw_payload, received_at, modality, ci_id, category, severity, summary"


def _fetch_alerts_after(conn: sqlite3.Connection, after_id: str | None, limit: int) -> list[dict]:
    if after_id is None:
        cur = conn.execute(
            f"SELECT {_ALERT_COLUMNS}, cmdb_ci.display_name FROM alerts LEFT JOIN cmdb_ci ON cmdb_ci.id = alerts.ci_id "
            "ORDER BY alerts.id ASC LIMIT ?",
            (limit,),
        )
    else:
        cur = conn.execute(
            f"SELECT {_ALERT_COLUMNS}, cmdb_ci.display_name FROM alerts LEFT JOIN cmdb_ci ON cmdb_ci.id = alerts.ci_id "
            "WHERE alerts.id > ? ORDER BY alerts.id ASC LIMIT ?",
            (after_id, limit),
        )
    return [
        {
            "id": r[0], "source": r[1], "raw_payload": r[2], "received_at": r[3], "modality": r[4],
            "ci_id": r[5], "category": r[6], "severity": r[7], "summary": r[8], "ci_display_name": r[9],
        }
        for r in cur.fetchall()
    ]


async def _alert_event_stream():
    last_id: str | None = None
    # Catch-up burst: replay recent history quickly so the Ops Board isn't empty on first load.
    conn = sqlite3.connect(DB_PATH)
    try:
        backlog = _fetch_alerts_after(conn, None, limit=20)
    finally:
        conn.close()
    for alert in backlog:
        last_id = alert["id"]
        yield f"data: {json.dumps(alert)}\n\n"
        await asyncio.sleep(0.15)

    # Live tail: one alert every 5s, not a burst — this is meant to read as live monitoring
    # arriving at a human-watchable pace, not a firehose replay of the remaining backlog. Was
    # up to 20 alerts every 3s, which blew through the rest of the 500-alert seed file in under
    # two minutes and made both the feed and auto-triage (useAutoTriage.js) fire far faster than
    # anyone could reasonably watch; 10s (a later revision) read as too slow for a live demo.
    while True:
        conn = sqlite3.connect(DB_PATH)
        try:
            new_alerts = _fetch_alerts_after(conn, last_id, limit=1)
        finally:
            conn.close()
        for alert in new_alerts:
            last_id = alert["id"]
            yield f"data: {json.dumps(alert)}\n\n"
        yield ": keep-alive\n\n"
        await asyncio.sleep(5)


@app.get("/alerts/stream")
async def alerts_stream(token: str = Query(...)):
    get_current_user_from_query_token(token)  # raises 401 before opening the stream if invalid
    return StreamingResponse(_alert_event_stream(), media_type="text/event-stream")


# ---------------- Correlated alert candidates (Ops Board right pane) ----------------
@app.get("/alerts/correlated")
def alerts_correlated(current_user: str = Depends(get_current_user)):
    # Reuses the Phase 2 correlation engine as-is (backend/correlation/cluster.py, DBSCAN +
    # CMDB-topology connected components, no LLM) rather than reimplementing clustering here.
    cis, relationships = _load_cis_and_relationships()
    alerts = _load_alerts()
    topology_groups = build_topology_groups(cis, relationships)
    correlated = correlate_alerts(alerts, topology_groups)

    clusters: dict[int, list[dict]] = {}
    for alert in correlated:
        clusters.setdefault(alert["cluster_id"], []).append(alert)

    def _summarize(alert: dict) -> str:
        # Alerts already carry a human-readable "summary" (data_gen/alerts.py) — prefer it over
        # parsing the vendor-shaped raw_payload, which stays around for the technical-details view.
        if alert.get("summary"):
            return alert["summary"]
        payload = alert["raw_payload"]
        if isinstance(payload, dict):
            # Different sources shape raw_payload differently (prometheus: annotations.summary,
            # apm: message, snmp: a flat string) — fall through rather than assume one shape.
            summary = payload.get("annotations", {}).get("summary") or payload.get("message")
            if summary:
                return summary
        return str(payload)[:120]

    ci_display_names = {ci["id"]: ci.get("display_name", ci["name"]) for ci in cis}

    def _build_candidate(cluster_id: int, members: list[dict]) -> dict:
        earliest = min(members, key=lambda m: m["received_at"])
        latest = max(members, key=lambda m: m["received_at"])
        return {
            "cluster_id": cluster_id,
            "topology_group": members[0]["topology_group"],
            "category": members[0]["category"],
            "alert_count": len(members),
            "alert_ids": [m["id"] for m in members],
            "ci_id": members[0]["ci_id"],
            "ci_display_name": ci_display_names.get(members[0]["ci_id"], members[0]["ci_id"]),
            "representative_summary": _summarize(earliest),
            # Groups are time-bounded (15-min DBSCAN window, cluster.py) — surfacing the span is what
            # makes it legible that two same-CI/same-category alerts weeks apart are genuinely two
            # different groups, not a clustering miss.
            "first_seen": earliest["received_at"],
            "last_seen": latest["received_at"],
        }

    candidates = [_build_candidate(cluster_id, members) for cluster_id, members in sorted(clusters.items())]

    n_alerts = len(alerts)
    n_clusters = len(clusters)
    return {
        "total_alerts": n_alerts,
        "total_clusters": n_clusters,
        "noise_reduction_ratio": round(1 - (n_clusters / n_alerts), 3) if n_alerts else 0,
        "candidates": candidates,
    }


# ---------------- Workflow runs (Agent Trace Viewer, Scenario Launcher) ----------------
class WorkflowRunRequest(BaseModel):
    ci_id: str
    workflow_type: str = "incident"
    auto_approve: bool = False


# ---------------- Instant Demo mode: pregenerated, zero-live-call output ----------------
# See backend/scripts/pregenerate_demo_outputs.py — runs the real pipeline once (real Gemini key)
# against the 6 named scenarios plus a voice/image PII-scrubbing sample, so a visitor in Instant
# Demo mode gets a real, previously-verified result with no live model call at all.
_DEMO_OUTPUTS_PATH = os.path.join(os.path.dirname(DB_PATH), "demo_outputs.json")
_demo_outputs_cache: dict | None = None


def _load_demo_outputs() -> dict:
    global _demo_outputs_cache
    if _demo_outputs_cache is None:
        try:
            with open(_DEMO_OUTPUTS_PATH, encoding="utf-8") as f:
                _demo_outputs_cache = json.load(f)
        except FileNotFoundError:
            _demo_outputs_cache = {}
    return _demo_outputs_cache


async def _format_workflow_outcome(incident_id: str, outcome: dict, modality: str, workflow_type: str = "incident") -> dict:
    """Shared response shape for every path that produces a workflow outcome (direct CI trigger,
    or a confirmed voice/image signal via intake_adapter) — joins model_used in from audit_log
    (not on SpecialistResult itself) and attaches the real signed A2A Agent Card."""
    agent_card = await fetch_agent_card()

    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT actor, model_used FROM audit_log WHERE target_artifact = ? AND model_used IS NOT NULL",
            (incident_id,),
        ).fetchall()
    finally:
        conn.close()
    model_by_agent = {actor.removeprefix("agent:"): model for actor, model in rows}

    trace = []
    for r in outcome["trace"]:
        entry = r.model_dump()
        entry["model_used"] = model_by_agent.get(entry["agent_name"])
        trace.append(entry)

    return {
        "incident_id": incident_id,
        "modality": modality,  # alert | voice | image — the signal that started this run
        "workflow_type": workflow_type,  # incident | patch | performance — drives the frontend's Maintenance Planner panel
        "status": outcome["status"],
        "reason": outcome.get("reason"),
        "verification_status": outcome.get("verification_status"),
        "trace": trace,
        "agent_card": agent_card,  # A2A discovery — viewable for the one handoff that used it
    }


def _normalize_ticket_status(outcome: dict) -> str:
    # Mirrors sync.py's own resolved/in-progress split (agents/sync.py _RESOLVED_STATE/_IN_PROGRESS_STATE)
    # rather than re-deriving it from the raw itsm state code, so the two never drift apart.
    # `needs_approval` is its own bucket (not folded into `in_progress`) so Ops Board's status
    # filter can actually surface "what needs a human decision right now" — previously
    # indistinguishable from ordinary in-progress work. Everything else short of a confirmed
    # verified_resolved (policy-blocked, a fake fix caught by verification, stuck before a
    # hypothesis existed) still reads as in_progress: it needs a person, just not an approval
    # specifically.
    if outcome["status"] == "complete" and outcome.get("verification_status") == "verified_resolved":
        return "resolved"
    if outcome["status"] == "pending_approval":
        return "needs_approval"
    return "in_progress"


async def _persist_ticket_snapshot(incident_id: str, ci: dict, workflow_type: str, outcome: dict, formatted: dict) -> None:
    """Additive local record of the ticket(s) supervisor.py/sync.py already created/updated in the
    (simulated) ITSM system — does not change that frozen flow, just mirrors its result locally so it
    survives a backend restart and can be listed/reopened (GET /tickets) without touching the tested
    orchestrator contracts. See decisions-log.md's newest entry."""
    sys_id = outcome.get("sys_id")
    if not sys_id:
        return  # enrichment failed before any ticket existed — nothing to record

    ticket = (await itsm_mcp.get_ticket(sys_id=sys_id))["result"]
    status_normalized = _normalize_ticket_status(outcome)
    now = datetime.now(timezone.utc).isoformat()
    trace_json = json.dumps(formatted)

    conn = sqlite3.connect(DB_PATH)
    try:
        # Approving a plan has no checkpointing to resume (see IncidentWorkspace.jsx's
        # ApprovalSection) — the frontend re-triggers a completely fresh /workflows/run for the
        # same CI instead, which lands here a second time with a new incident_id. Left as a plain
        # INSERT, that second call orphaned a duplicate: the original ticket stayed stuck at
        # needs_approval forever (nothing ever revisits it) while the real outcome showed up as an
        # unrelated-looking second row. Since 'needs_approval' is exclusively a live-run status —
        # never present in bulk-seeded historical data — a CI with a row still sitting at
        # needs_approval right now is (in the normal Ops Board flow, which hides Diagnose once a
        # CI already has an open ticket) almost certainly this same approval's own pending ticket.
        # Update that row in place instead of inserting an orphan. Matched on cmdb_ci alone (not
        # also workflow_type) because the approval re-run doesn't currently preserve the original
        # plan's workflow_type. Narrow edge case this doesn't cover: a second, genuinely unrelated
        # diagnosis kicked off for the same CI (outside the normal UI guard, e.g. directly via API)
        # while an earlier one is still pending — rare enough not to be worth more machinery here.
        pending = conn.execute(
            "SELECT id FROM local_tickets WHERE cmdb_ci = ? AND status_normalized = 'needs_approval' "
            "ORDER BY id DESC LIMIT 1",
            (ci["id"],),
        ).fetchone()
        if pending:
            conn.execute(
                "UPDATE local_tickets SET system = ?, external_id = ?, workflow_type = ?, status_raw = ?, "
                "status_normalized = ?, priority = ?, summary = ?, closed_at = ?, linked_incident_id = ?, "
                "trace_snapshot = ? WHERE id = ?",
                ("itsm", sys_id, workflow_type, ticket["state"], status_normalized, ticket["priority"],
                 ticket["short_description"], ticket["closed_at"], incident_id, trace_json, pending[0]),
            )
        else:
            conn.execute(
                "INSERT INTO local_tickets (system, external_id, cmdb_ci, workflow_type, status_raw, status_normalized, "
                "priority, summary, opened_at, closed_at, linked_incident_id, trace_snapshot, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("itsm", sys_id, ci["id"], workflow_type, ticket["state"], status_normalized, ticket["priority"],
                 ticket["short_description"], ticket["opened_at"], ticket["closed_at"], incident_id, trace_json, now),
            )
        conn.commit()
    finally:
        conn.close()


@app.post("/workflows/run")
async def workflows_run(
    req: WorkflowRunRequest,
    identity: Identity = Depends(get_current_identity),
    provider_ctx: provider_context.ProviderContext = Depends(provider_context.get_provider_context),
):
    if provider_ctx.is_instant_demo:
        # Keyed by ci_id+workflow_type, not ci_id alone — SCEN-01 (incident) and SCEN-04 (patch)
        # both target CI-0059, so ci_id alone would collide between two different scenarios.
        demo = _load_demo_outputs().get(f"{req.ci_id}:{req.workflow_type}")
        if demo is None:
            raise HTTPException(
                status_code=400,
                detail=f"Instant Demo only covers the pre-generated scenarios — {req.ci_id} ({req.workflow_type}) "
                       "isn't one of them. Switch to Bring Your Own Key or Free Demo Key mode for live, ad-hoc diagnosis.",
            )
        return demo

    wire_all_in_process()
    cis, _relationships = _load_cis_and_relationships()
    ci = next((c for c in cis if c["id"] == req.ci_id), None)
    if ci is None:
        raise HTTPException(status_code=404, detail=f"CI {req.ci_id} not found")

    alerts = [a for a in _load_alerts() if a["ci_id"] == req.ci_id and a["category"] == "fault"]
    incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
    # Real fix, not cosmetic: this used to pass the raw username as actor_role, so the policy
    # gate's approver check (guardrails/policy_gate.py APPROVER_ROLES) could never match any real
    # login — every prod/P1 action silently required approval regardless of who was "logged in".
    outcome = await run_workflow(
        incident_id=incident_id, ci=ci, alerts=alerts,
        workflow_type=req.workflow_type, actor_role=ROLE_TO_ACTOR_ROLE[identity.role], auto_approve=req.auto_approve,
    )
    formatted = await _format_workflow_outcome(incident_id, outcome, modality="alert", workflow_type=req.workflow_type)
    await _persist_ticket_snapshot(incident_id, ci, req.workflow_type, outcome, formatted)
    return formatted


class WorkflowDecisionRequest(BaseModel):
    incident_id: str
    decision: str  # "approve" | "reject"
    reason: str


@app.post("/workflows/decision")
async def workflows_decision(req: WorkflowDecisionRequest, identity: Identity = Depends(get_current_identity)):
    # Records a human approve/reject decision with a mandatory reason. NOTE: run_workflow has no
    # checkpointing — this does NOT resume the paused run that produced incident_id. Approving
    # something in the Approval Queue triggers a SEPARATE fresh re-run with auto_approve=true
    # (see the frontend) rather than continuing this exact run; that limitation is deliberate and
    # surfaced in the UI, not hidden here.
    require_role(identity, {"approver", "admin"})
    if req.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'reject'")
    if not req.reason.strip():
        raise HTTPException(status_code=400, detail="reason is required")

    conn = sqlite3.connect(DB_PATH)
    try:
        write_audit_entry(
            conn, actor=identity.username, action=f"human_{req.decision}_plan",
            target_artifact=req.incident_id, approval_ref=req.reason,
        )
    finally:
        conn.close()
    return {"recorded": True}


# ---------------- Local ticket history (Ops Board "Diagnose" + Ticket history) ----------------
_TICKET_LIST_COLUMNS = (
    "id, system, external_id, cmdb_ci, workflow_type, status_raw, status_normalized, priority, "
    "summary, opened_at, closed_at, linked_incident_id, created_at"
)


@app.get("/tickets")
def list_tickets(
    status: str | None = None, ci_id: str | None = None, workflow_type: str | None = None,
    current_user: str = Depends(get_current_user),
):
    query = f"SELECT {_TICKET_LIST_COLUMNS} FROM local_tickets WHERE 1=1"
    params: list[str] = []
    if status:
        query += " AND status_normalized = ?"
        params.append(status)
    if ci_id:
        query += " AND cmdb_ci = ?"
        params.append(ci_id)
    if workflow_type:
        query += " AND workflow_type = ?"
        params.append(workflow_type)
    query += " ORDER BY id DESC"

    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()
    cols = [c.strip() for c in _TICKET_LIST_COLUMNS.split(",")]
    return {"tickets": [dict(zip(cols, r)) for r in rows]}


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int, current_user: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            f"SELECT {_TICKET_LIST_COLUMNS}, trace_snapshot FROM local_tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"no ticket {ticket_id}")
    cols = [c.strip() for c in _TICKET_LIST_COLUMNS.split(",")] + ["trace_snapshot"]
    ticket = dict(zip(cols, row))
    ticket["trace_snapshot"] = json.loads(ticket["trace_snapshot"])
    return ticket


# ---------------- Pending patches (Ops Board "Pending Patches" — the patch workflow's own entry
# point, parallel to the alert feed's "Diagnose" for incident/performance) ----------------
@app.get("/patches/pending")
def list_pending_patches(ci_id: str | None = None, current_user: str = Depends(get_current_user)):
    query = (
        "SELECT patch_inventory.id, patch_inventory.ci_id, cmdb_ci.display_name, patch_inventory.vendor, "
        "patch_inventory.title, patch_inventory.severity, patch_inventory.cve_ids, patch_inventory.released_at, "
        "patch_inventory.sla_days, patch_inventory.status "
        "FROM patch_inventory LEFT JOIN cmdb_ci ON cmdb_ci.id = patch_inventory.ci_id "
        "WHERE patch_inventory.status = 'pending'"
    )
    params: list[str] = []
    if ci_id:
        query += " AND patch_inventory.ci_id = ?"
        params.append(ci_id)
    # Worst severity first, then oldest release first — the two things that would actually drive
    # which CI a human patches first (SLA pressure isn't a stored column, severity is its proxy).
    query += (
        " ORDER BY CASE patch_inventory.severity "
        "WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, "
        "patch_inventory.released_at ASC"
    )

    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()
    return {
        "patches": [
            {
                "id": r[0], "ci_id": r[1], "ci_display_name": r[2], "vendor": r[3], "title": r[4],
                "severity": r[5], "cve_ids": json.loads(r[6]) if r[6] else [], "released_at": r[7],
                "sla_days": r[8], "status": r[9],
            }
            for r in rows
        ]
    }


# ---------------- Integration settings (future real ServiceNow/Jira instance — inert until set) ----------------
class IntegrationSettingsRequest(BaseModel):
    servicenow_instance_url: str | None = None
    jira_instance_url: str | None = None


@app.get("/config/integrations")
def get_integration_settings(current_user: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT servicenow_instance_url, jira_instance_url, last_synced_at FROM integration_settings WHERE id = 1"
        ).fetchone()
    finally:
        conn.close()
    return {"servicenow_instance_url": row[0], "jira_instance_url": row[1], "last_synced_at": row[2]}


@app.post("/config/integrations")
def set_integration_settings(req: IntegrationSettingsRequest, identity: Identity = Depends(get_current_identity)):
    # Deliberately does not attempt to reach the URL or start syncing anything (decisions-log.md) —
    # this only records where a real instance *would* be, for when one exists. last_synced_at stays
    # untouched: nothing here has ever actually synced.
    require_role(identity, {"admin"})
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE integration_settings SET servicenow_instance_url = ?, jira_instance_url = ? WHERE id = 1",
            (req.servicenow_instance_url, req.jira_instance_url),
        )
        conn.commit()
    finally:
        conn.close()
    return get_integration_settings(current_user=identity.username)


@app.post("/tickets/sync")
def sync_tickets(current_user: str = Depends(get_current_user)):
    """"Pull latest" for the Tickets tab. Honest about what this actually is: no real ServiceNow/
    Jira instance is connected (integration_settings' URLs are inert, decisions-log.md) — this
    reads the same local `local_tickets` record every real `/workflows/run` already writes to, and
    stamps `last_synced_at` so the UI can show a genuine "last pulled" time, the way a real
    periodic sync job would. It does not fabricate new tickets or reach out anywhere."""
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("UPDATE integration_settings SET last_synced_at = ? WHERE id = 1", (now,))
        conn.commit()
        rows = conn.execute(f"SELECT {_TICKET_LIST_COLUMNS} FROM local_tickets ORDER BY id DESC").fetchall()
    finally:
        conn.close()
    cols = [c.strip() for c in _TICKET_LIST_COLUMNS.split(",")]
    return {"synced_at": now, "tickets": [dict(zip(cols, r)) for r in rows]}


# ---------------- Assistant (floating chat) ----------------
# Deliberately NOT a general-purpose chatbot (decisions-log.md's original "cut the chat drawer"
# call, PRD §2.2's "vs. a general chat assistant" argument: no hands, no memory of the estate,
# confidently answers with no evidence). Reversed by explicit human request, but built to keep the
# same properties that argument relied on: (1) ticket/incident answers come from a real deterministic
# DB query, never an LLM inventing numbers — the LLM only extracts filters, the same "LLM proposes,
# code executes" split as Diagnosis/Planner; (2) approve/reject reuses the exact same audited,
# reason-required, role-gated path as Incident Workspace's own ApprovalSection, never a shortcut;
# (3) app-help answers are grounded in a fixed description of this app only, told explicitly not to
# answer general IT/ServiceNow/Jira questions outside that.
#
# Both chat LLM calls below go through api_client.get_llm()'s role dispatch (providers.py) rather
# than a literal model constant, same as every other agent — intent classification uses "structured"
# (must return valid JSON, same intent the old CHAT_MODEL constant served), app-help uses "default"
# (a free-text answer, not JSON).

APP_HELP_CONTEXT = """
OpsFlow is an AI-verified IT operations console for a Microsoft 365 / Power Platform estate
(SharePoint, OneDrive, Power Platform, Teams, Exchange, Dataverse, Azure AD).

Main tabs:
- Overview: session-wide health — workflow runs, completions, human approvals, CMDB drift rate,
  manual steps avoided, incident resolution timing, a human-satisfaction-rate proxy (approval rate,
  not a real survey — this app has no real end users to survey).
- Ops Board: the live incoming-alert feed. Each alert shows its own triage status inline (not yet
  diagnosed / needs approval / in progress / resolved) with a Diagnose button or a clickable ticket
  status pill. Filterable by alert type (fault/degradation) and status.
- Tickets: the ServiceNow system of record — every ticket a diagnosis has raised, browsable with a
  "Pull latest" button that re-reads local records and stamps when it last did (no live ServiceNow/
  Jira instance is actually connected in this build).
- Incident Workspace: the full record of one incident — evidence with citations, ranked hypotheses,
  the drafted plan with blast radius and policy-gate result, and (for patch workflows) a Maintenance
  Planner panel. If the plan needs a human decision, an inline "Needs approval" section appears
  there with Approve/Reject (mandatory reason, audited) — only an Approver or Admin can decide it.
  A "View full Agent Trace" button opens the full per-agent handoff detail (model, tokens, latency,
  confidence, citations) in a popup.
- Drift Queue: compares the CMDB's recorded state against verified ground truth, since real CMDBs
  drift from reality over time.
- Autonomy Ladder: shows how much independent authority the AI currently holds per runbook/action
  type, from "always ask a human" up to "auto-execute."

Sidebar panels (icon rail, left edge): Ingestion/Admin (user management, runbook/article upload,
admin-only), Model & Threshold Config, Scenario Launcher (replays named test scenarios), Audit Log,
Knowledge Base (browse the chunked runbook/reference-article library the AI can actually cite).

ID scheme: CI-nnnn is a resource in the CMDB (a SharePoint site, Power Platform environment, etc).
ALERT-nnnn is one raw signal from a monitor. INC-XXXXXXXX is this app's own case id for one
agent-chain run. TCK-nnnn is a ServiceNow-style ticket. Ticket/alert status is one of: untriaged
(no ticket yet), needs_approval (a human decision is pending), in_progress, resolved.

Workflow types: incident (a fault alert, remediated via the full agent chain, can reach
auto-execute once trusted), patch (scheduled maintenance, always needs approval, includes an
intelligent-scheduling maintenance window), performance (tuning recommendations, advisory-only —
deliberately never auto-executes, since tuning changes have delayed/ambiguous effects).

The agent chain, every workflow: Correlate -> Enrich -> Diagnose -> Plan -> Policy Gate ->
(Approve, if required) -> Execute -> Verify -> Sync -> Knowledge. Verification has a "Fake Fix
Detector" — it distinguishes an alert that cleared but the underlying health probe never actually
recovered (symptom_suppressed) from a genuinely verified fix (verified_resolved).
""".strip()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = Field(default_factory=list)  # [{"role": "user"|"assistant", "content": str}, ...]


def _chat_json_parse(raw: str) -> dict:
    content = raw.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
    try:
        return json.loads(content)
    except (TypeError, ValueError):
        return {"intent": "unrecognized"}


async def _classify_chat_intent(message: str, history: list[dict]) -> dict:
    llm = get_llm(role="structured", temperature=0)
    history_block = "\n".join(f"{h.get('role', 'user')}: {h.get('content', '')}" for h in history[-6:])
    prompt = f"""Classify this message from a user of an IT-operations console into ONE intent and
extract its parameters. Respond with ONLY valid JSON (no markdown fences), this exact shape:
{{"intent": "query_tickets" | "approve_incident" | "reject_incident" | "app_help" | "unrecognized",
  "days_back": <int or null, convert relative time like "last month"=30, "last week"=7, "today"=1>,
  "workflow_type": "incident" | "patch" | "performance" | null,
  "status": "needs_approval" | "in_progress" | "resolved" | null,
  "system": "itsm" | null,
  "cmdb_ci": "<a CI-nnnn id if one is literally mentioned, else null>",
  "target_ref": "<an INC-xxxxxxxx or TCK-nnnn id if one is literally mentioned, else null>",
  "reason": "<the reason given for an approve/reject, else null>",
  "help_topic": "<the question, verbatim, if intent is app_help>"}}

- "query_tickets": any question about how many/which tickets or incidents exist, filtered by time,
  type, status, or CI. Also use this if they just say something like "show pending approvals".
- "approve_incident" / "reject_incident": they want to approve or reject a SPECIFIC incident/ticket
  (by its INC-/TCK- id, or "the last one" — leave target_ref null if genuinely ambiguous, don't guess an id).
- "app_help": a question about what this app/a tab/a status/a concept means.
- "unrecognized": anything else (small talk, out of scope, unclear).

Recent conversation:
{history_block}

User message: {message}
"""
    response = await llm.ainvoke(prompt)
    return _chat_json_parse(response.content)


def _query_tickets_for_chat(filters: dict) -> list[dict]:
    query = f"SELECT {_TICKET_LIST_COLUMNS} FROM local_tickets WHERE 1=1"
    params: list[str] = []
    if filters.get("days_back"):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=int(filters["days_back"]))).isoformat()
        query += " AND created_at >= ?"
        params.append(cutoff)
    # column name on the right is fixed/hardcoded per key, never built from the filters dict itself
    for key, column in (("workflow_type", "workflow_type"), ("status", "status_normalized"), ("system", "system"), ("cmdb_ci", "cmdb_ci")):
        value = filters.get(key)
        if value:
            query += f" AND {column} = ?"
            params.append(value)
    query += " ORDER BY id DESC LIMIT 200"
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()
    cols = [c.strip() for c in _TICKET_LIST_COLUMNS.split(",")]
    return [dict(zip(cols, r)) for r in rows]


def _format_ticket_query_reply(tickets: list[dict]) -> str:
    # Deterministic, not a second LLM call — every number here comes straight from the query above,
    # so there is nothing for a model to invent.
    if not tickets:
        return "No tickets match that."
    by_status = Counter(t["status_normalized"] for t in tickets)
    status_line = ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in by_status.items())
    table_note = " Full list below." if len(tickets) > 5 else ""
    return f"Found {len(tickets)} ticket(s) — {status_line}.{table_note}"


async def _chat_handle_decision(target_ref: str | None, decision: str, reason: str | None, identity: Identity) -> tuple[str, dict | None]:
    if identity.role not in ("approver", "admin"):
        return "Only an Approver or Admin can approve or reject — you're signed in as an Ops Engineer.", None
    if not reason or not reason.strip():
        return "I can do that, but I need a reason first (it's logged to the audit trail) — what's the reason?", None
    if not target_ref:
        pending = _query_tickets_for_chat({"status": "needs_approval"})
        if not pending:
            return "Nothing is currently pending approval.", None
        listing = "; ".join(f"{t['external_id']} ({t['cmdb_ci']})" for t in pending[:8])
        return f"Which one? Currently pending approval: {listing}.", None

    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            f"SELECT {_TICKET_LIST_COLUMNS} FROM local_tickets WHERE (external_id = ? OR linked_incident_id = ?) "
            "AND status_normalized = 'needs_approval' ORDER BY id DESC LIMIT 1",
            (target_ref, target_ref),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        pending = _query_tickets_for_chat({"status": "needs_approval"})
        if not pending:
            return f"I couldn't find a pending-approval ticket matching '{target_ref}', and nothing is currently pending approval.", None
        listing = "; ".join(f"{t['external_id']} ({t['cmdb_ci']})" for t in pending[:8])
        return f"I couldn't find a pending-approval ticket matching '{target_ref}'. Currently pending: {listing}.", None

    cols = [c.strip() for c in _TICKET_LIST_COLUMNS.split(",")]
    ticket = dict(zip(cols, row))
    incident_id = ticket["linked_incident_id"]

    # Same write path as POST /workflows/decision — same audit action name, same mandatory reason,
    # not a shortcut around either.
    conn = sqlite3.connect(DB_PATH)
    try:
        write_audit_entry(conn, actor=identity.username, action=f"human_{decision}_plan", target_artifact=incident_id, approval_ref=reason)
    finally:
        conn.close()

    if decision == "reject":
        return f"Rejected {ticket['external_id']} ({ticket['cmdb_ci']}). Reason logged to the audit trail. No execution follows.", {
            "type": "rejected", "incident_id": incident_id,
        }

    # Approve -> same "fresh re-run with auto_approve" the frontend's ApprovalSection triggers
    # (run_workflow has no checkpointing — see IncidentWorkspace.jsx — this is not a shortcut,
    # it's the same real limitation every approval path already has).
    cis, _relationships = _load_cis_and_relationships()
    ci = next((c for c in cis if c["id"] == ticket["cmdb_ci"]), None)
    if ci is None:
        return f"Approved {ticket['external_id']} — reason logged — but couldn't find CI {ticket['cmdb_ci']} to re-run automatically.", {
            "type": "approved", "incident_id": incident_id, "new_run": None,
        }
    wire_all_in_process()
    alerts = [a for a in _load_alerts() if a["ci_id"] == ci["id"] and a["category"] == "fault"]
    new_incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
    outcome = await run_workflow(
        incident_id=new_incident_id, ci=ci, alerts=alerts, workflow_type=ticket["workflow_type"],
        actor_role=ROLE_TO_ACTOR_ROLE[identity.role], auto_approve=True,
    )
    formatted = await _format_workflow_outcome(new_incident_id, outcome, modality="alert", workflow_type=ticket["workflow_type"])
    await _persist_ticket_snapshot(new_incident_id, ci, ticket["workflow_type"], outcome, formatted)
    status_note = f" ({outcome['verification_status']})" if outcome.get("verification_status") else ""
    return (
        f"Approved {ticket['external_id']} ({ticket['cmdb_ci']}). Reason logged. Re-ran as {new_incident_id}: "
        f"{outcome['status']}{status_note}.",
        {"type": "approved", "incident_id": incident_id, "new_run": formatted},
    )


async def _chat_app_help(question: str) -> str:
    llm = get_llm(role="default", temperature=0)
    prompt = f"""You are a help assistant embedded in the OpsFlow IT-ops console. Answer ONLY
using the facts below about THIS app. If the question isn't covered by these facts, say plainly
that you don't have that information rather than guessing — never answer general IT/ServiceNow/
Jira questions unrelated to this specific app. Keep the answer to 2-4 sentences.

{APP_HELP_CONTEXT}

Question: {question}
"""
    response = await llm.ainvoke(prompt)
    return response.content.strip()


@app.post("/chat")
async def chat(
    req: ChatRequest,
    identity: Identity = Depends(get_current_identity),
    provider_ctx: provider_context.ProviderContext = Depends(provider_context.get_provider_context),
):
    if provider_ctx.is_instant_demo:
        return {
            "reply": "Instant Demo replays 6 pre-generated scenarios (see the Scenarios panel) with no live "
                     "model calls — live chat needs Bring Your Own Key or Free Demo Key mode.",
            "action": None,
        }

    wire_all_in_process()
    classification = await _classify_chat_intent(req.message, req.history)
    intent = classification.get("intent", "unrecognized")

    if intent == "query_tickets":
        tickets = _query_tickets_for_chat(classification)
        return {"reply": _format_ticket_query_reply(tickets), "action": {"type": "query_tickets", "tickets": tickets}}

    if intent in ("approve_incident", "reject_incident"):
        decision = "approve" if intent == "approve_incident" else "reject"
        reply, action = await _chat_handle_decision(classification.get("target_ref"), decision, classification.get("reason"), identity)
        return {"reply": reply, "action": action}

    if intent == "app_help":
        reply = await _chat_app_help(classification.get("help_topic") or req.message)
        return {"reply": reply, "action": None}

    return {
        "reply": "I can answer questions about tickets/incidents (e.g. \"how many incidents in the last 30 days\"), "
        "explain what a tab or status means, or approve/reject a specific pending incident by its ID — "
        "try rephrasing?",
        "action": None,
    }


# ---------------- Drift Queue (recorded CMDB state vs planted ground truth) ----------------
_CMDB_DRIFT_FIELDS = ["environment", "criticality", "patch_level", "owner", "name", "last_verified_at"]


@app.get("/cmdb/drift")
def cmdb_drift(current_user: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    try:
        recorded = {
            r[0]: dict(zip(["id", "name", "type", "owner", "environment", "criticality", "patch_level", "last_verified_at"], r))
            for r in conn.execute("SELECT id, name, type, owner, environment, criticality, patch_level, last_verified_at FROM cmdb_ci")
        }
        truth = {
            r[0]: dict(zip(["id", "name", "type", "owner", "environment", "criticality", "patch_level", "last_verified_at"], r))
            for r in conn.execute("SELECT id, name, type, owner, environment, criticality, patch_level, last_verified_at FROM cmdb_ci_ground_truth")
        }
    finally:
        conn.close()

    drifted = []
    for ci_id, rec in recorded.items():
        gt = truth.get(ci_id)
        if not gt:
            continue
        diffs = {f: {"recorded": rec[f], "ground_truth": gt[f]} for f in _CMDB_DRIFT_FIELDS if rec[f] != gt[f]}
        if diffs:
            drifted.append({"ci_id": ci_id, "name": rec["name"], "type": rec["type"], "diffs": diffs})

    return {
        "total_cis": len(recorded),
        "drifted_count": len(drifted),
        "drift_rate": round(len(drifted) / len(recorded), 3) if recorded else 0,
        "drifted": sorted(drifted, key=lambda d: d["ci_id"]),
    }


# ---------------- Autonomy Ladder (static status display, PRD §4.0 — not a live promotion engine) ----------------
@app.get("/autonomy-ladder")
def autonomy_ladder(current_user: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT a.runbook_id, r.class, a.current_tier, a.verified_resolution_count, a.last_promoted_at "
            "FROM autonomy_ladder a JOIN runbooks r ON a.runbook_id = r.id ORDER BY a.runbook_id"
        ).fetchall()
    finally:
        conn.close()
    return {
        "runbooks": [
            {
                "runbook_id": r[0], "class": r[1], "current_tier": r[2],
                "verified_resolution_count": r[3], "last_promoted_at": r[4],
            }
            for r in rows
        ]
    }


# ---------------- Knowledge Base (real Chroma chunks — runbook procedures + reference articles,
# no embedding call needed to browse) ----------------
@app.get("/chunks")
def chunks(runbook_id: str | None = None, doc_type: str | None = None, current_user: str = Depends(get_current_user)):
    from orchestrator.retrieval import _get_chroma_client

    collection = _get_chroma_client().get_collection("runbooks")
    conditions = []
    if runbook_id:
        conditions.append({"runbook_id": runbook_id})
    if doc_type:
        conditions.append({"doc_type": doc_type})
    where = {"$and": conditions} if len(conditions) > 1 else (conditions[0] if conditions else None)
    result = collection.get(where=where)
    return {
        "total": len(result["ids"]),
        "chunks": [
            {"id": result["ids"][i], "document": result["documents"][i], "metadata": result["metadatas"][i]}
            for i in range(len(result["ids"]))
        ],
    }


# ---------------- Metrics & Eval — real aggregates only, no Phase 5 scenario eval yet ----------------
def _compute_resolution_timing(conn: sqlite3.Connection) -> dict:
    """Real elapsed time per incident, computed from audit_log's own timestamps — no fabricated
    numbers (PRD §2.6/C13: "signal->plan and signal->verified-resolution vs a stated manual
    baseline"). We only ever show the automated side of that comparison for real; a "manual
    baseline" would be an assumption someone states, not something this session can measure, so it
    is deliberately NOT invented here."""
    rows = conn.execute(
        "SELECT target_artifact, action, timestamp FROM audit_log "
        "WHERE action IN ('correlate', 'draft_plan', 'verify_resolution') AND target_artifact IS NOT NULL "
        "ORDER BY target_artifact, id"
    ).fetchall()
    by_incident: dict[str, dict[str, str]] = {}
    for target, action, ts in rows:
        # First occurrence only per (incident, action) — a re-run under the same incident_id
        # shouldn't happen, but guard against it skewing the average if it ever does.
        by_incident.setdefault(target, {}).setdefault(action, ts)

    signal_to_plan: list[float] = []
    signal_to_verified: list[float] = []
    for events in by_incident.values():
        if "correlate" not in events:
            continue
        start = datetime.fromisoformat(events["correlate"])
        if "draft_plan" in events:
            signal_to_plan.append((datetime.fromisoformat(events["draft_plan"]) - start).total_seconds())
        if "verify_resolution" in events:
            signal_to_verified.append((datetime.fromisoformat(events["verify_resolution"]) - start).total_seconds())

    def _avg(xs: list[float]) -> float | None:
        return round(sum(xs) / len(xs), 2) if xs else None

    return {
        "avg_signal_to_plan_seconds": _avg(signal_to_plan),
        "avg_signal_to_verified_resolution_seconds": _avg(signal_to_verified),
        "incidents_with_plan_timing": len(signal_to_plan),
        "incidents_with_resolution_timing": len(signal_to_verified),
    }


def _compute_manual_steps_avoided(conn: sqlite3.Connection) -> int:
    """Sum of runbook step counts across every real `execute_plan` audit entry this session —
    each step is a manual action (log into the console, run the command, note the ticket...) a
    human didn't have to do by hand. Real count from `evidence_ids` (supervisor.py passes
    `[s["cites_runbook_step"] for s in planner_result.result["steps"]]` at execute_plan time), not
    an estimate."""
    rows = conn.execute("SELECT evidence_ids FROM audit_log WHERE action = 'execute_plan'").fetchall()
    total = 0
    for (evidence_ids_json,) in rows:
        try:
            total += len(json.loads(evidence_ids_json or "[]"))
        except (TypeError, ValueError):
            pass
    return total


@app.get("/metrics/summary")
def metrics_summary(current_user: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    try:
        action_counts = dict(conn.execute("SELECT action, COUNT(*) FROM audit_log GROUP BY action").fetchall())
        total_runs = action_counts.get("correlate", 0)
        completed_runs = action_counts.get("execute_plan", 0)
        human_approvals = action_counts.get("human_approve_plan", 0)
        human_rejections = action_counts.get("human_reject_plan", 0)
        negative_kb_count = conn.execute("SELECT COUNT(*) FROM negative_kb_entries").fetchone()[0]
        timing = _compute_resolution_timing(conn)
        manual_steps_avoided = _compute_manual_steps_avoided(conn)
    finally:
        conn.close()

    cis, _rel = _load_cis_and_relationships()
    alerts = _load_alerts()
    topology_groups = build_topology_groups(cis, _rel)
    correlated = correlate_alerts(alerts, topology_groups)
    n_clusters = len({a["cluster_id"] for a in correlated})

    total_decisions = human_approvals + human_rejections
    return {
        "total_workflow_runs_this_session": total_runs,
        "completed_runs": completed_runs,
        "stopped_before_completion": total_runs - completed_runs,
        "human_approvals": human_approvals,
        "human_rejections": human_rejections,
        "negative_kb_entries_seeded": negative_kb_count,
        "correlation_noise_reduction_ratio": round(1 - (n_clusters / len(alerts)), 3) if alerts else 0,
        "manual_steps_avoided": manual_steps_avoided,
        **timing,
        # Approval rate as a real, labeled PROXY for "would a human be satisfied with what the AI
        # proposed" — not a satisfaction survey (no real end users exist to survey in this
        # synthetic demo). None (not 0%) when no decisions exist yet, so the frontend can render
        # "no data yet" instead of a misleading 0%.
        "approval_rate_satisfaction_proxy": round(human_approvals / total_decisions, 3) if total_decisions else None,
        "scenario_eval_status": _read_scenario_eval_status(),
    }


def _read_scenario_eval_status() -> str:
    """Reads the eval harness's last report (backend/eval/harness.py, run manually — not on every
    request) instead of computing anything live here. Honest placeholder if it's never been run in
    this environment, same spirit as the "not_run" string this replaced."""
    report_path = os.path.join(os.path.dirname(DB_PATH), "eval_report.json")
    try:
        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)
    except FileNotFoundError:
        return "not_run — run backend/eval/harness.py to generate a report"
    return (
        f"{report['passed']}/{report['total_scenarios']} scenarios passed (run {report['run_label']}, "
        f"{report['generated_at']}) — verified_resolved={report['verified_resolved']} "
        f"symptom_suppressed={report['symptom_suppressed']} citation_coverage={report['citation_coverage']:.0%} "
        f"cache_hits={report['cache_hits']}/{report['cache_checks']}"
    )


# ---------------- Multimodal intake (voice + image) — real Whisper/gpt-4o, confirmation-gated ----------------
_INSTANT_DEMO_INTAKE_MESSAGE = (
    "Instant Demo has no live model calls, so voice/image intake isn't available in this mode — "
    "switch to Bring Your Own Key or Free Demo Key mode, or try the pre-generated voice/image "
    "samples in the Scenarios panel."
)


@app.post("/intake/voice")
async def intake_voice(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
    provider_ctx: provider_context.ProviderContext = Depends(provider_context.get_provider_context),
):
    if provider_ctx.is_instant_demo:
        raise HTTPException(status_code=400, detail=_INSTANT_DEMO_INTAKE_MESSAGE)
    if not providers.PROVIDERS[provider_ctx.provider]["supports_transcription"]:
        raise HTTPException(
            status_code=400,
            detail=f"{providers.PROVIDERS[provider_ctx.provider]['label']} does not support voice transcription — switch provider.",
        )
    audio_bytes = await file.read()
    signal = run_voice_intake(audio_bytes, filename=file.filename or "voice.wav")
    return signal.model_dump()


@app.post("/intake/image")
async def intake_image(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
    provider_ctx: provider_context.ProviderContext = Depends(provider_context.get_provider_context),
):
    if provider_ctx.is_instant_demo:
        raise HTTPException(status_code=400, detail=_INSTANT_DEMO_INTAKE_MESSAGE)
    image_bytes = await file.read()
    mime_type = file.content_type or "image/png"
    signal = run_vision_intake(image_bytes, mime_type=mime_type)
    return signal.model_dump()


class IntakeConfirmRequest(BaseModel):
    signal: dict
    workflow_type: str = "incident"


@app.get("/demo/pii-sample")
def demo_pii_sample(current_user: str = Depends(get_current_user)):
    """The one PII-scrubbing demo fixture in data/demo_outputs.json (built by
    scripts/pregenerate_demo_outputs.py) — a real MaintenanceSignal from the unmodified vision-intake
    pipeline, so Instant Demo mode can show the scrubber actually redacting a name/email without any
    live model call. Available in every mode, not just Instant Demo — it's just most relevant there."""
    sample = _load_demo_outputs().get("image_pii_demo")
    if sample is None:
        raise HTTPException(status_code=404, detail="Demo outputs not generated yet — run scripts/pregenerate_demo_outputs.py.")
    return sample


@app.get("/audit-log")
def audit_log(limit: int = 100, identity: Identity = Depends(get_current_identity)):
    require_role(identity, {"approver", "admin"})
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT id, actor, action, target_artifact, timestamp, evidence_ids, model_used, approval_ref, input_modality "
            "FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return {
        "entries": [
            {
                "id": r[0], "actor": r[1], "action": r[2], "target_artifact": r[3], "timestamp": r[4],
                "evidence_ids": r[5], "model_used": r[6], "approval_ref": r[7], "input_modality": r[8],
            }
            for r in rows
        ]
    }


# ---------------- Scenario Launcher (Phase 5 scenario library) ----------------
@app.get("/scenarios")
def list_scenarios(current_user: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute("SELECT id, name, workflow_type, is_edge_case, fixture_path FROM scenarios ORDER BY id").fetchall()
    finally:
        conn.close()
    data_dir = os.path.dirname(DB_PATH)
    scenarios = []
    for r in rows:
        with open(os.path.join(data_dir, r[4]), encoding="utf-8") as f:
            fixture = json.load(f)
        scenarios.append({
            "id": r[0], "name": r[1], "workflow_type": r[2], "is_edge_case": bool(r[3]),
            "ci_id": fixture.get("ci_id"), "auto_approve": fixture.get("auto_approve", False),
            "expected": fixture.get("expected"),
        })
    return {"scenarios": scenarios}


# ---------------- Model & Threshold Config (admin-only) ----------------
# Read-only display of per-role model routing (models-routing.md) — reflects whichever provider is
# active on this request (providers.py's role map), not a hand-maintained TCS-only constant, since
# the routing table now genuinely differs per provider. Still not LIVE-editable — that would touch
# frozen/tested agent contracts (backend/agents/*.py). Thresholds below ARE genuinely live-editable.
def _model_routing_display(provider_name: str) -> dict:
    if provider_name == provider_context.INSTANT_DEMO:
        return {"note": "Instant Demo replays pre-generated output — no live model calls are made."}
    provider_cfg = providers.PROVIDERS[provider_name]
    # A BYOK visitor's explicit model choice (openai/grok/custom have no curated roles map at all —
    # see providers.py) overrides every role uniformly, same as providers.resolve_model() does for
    # the actual LLM calls; Free Demo Key / Instant Demo never set this, so they fall through to the
    # curated per-role map below unchanged.
    override_model = provider_context.get_active_model()

    def _model_for(role: str, supported: bool) -> str:
        if not supported:
            return "not supported by this provider"
        if override_model:
            return override_model
        return provider_cfg["roles"].get(role, "not set — Bring Your Own Key sessions must select a model")

    display = {
        "provider": provider_cfg["label"],
        "diagnosis": _model_for("reasoning", True),
        "planner": _model_for("structured", True),
        "vision_intake": _model_for("vision", provider_cfg["vision"]),
    }
    display["voice_intake"] = provider_cfg.get("whisper_model", "not supported by this provider") if provider_cfg["supports_transcription"] else "not supported by this provider"
    return display


@app.get("/config/thresholds")
def get_config_thresholds(
    identity: Identity = Depends(get_current_identity),
    provider_ctx: provider_context.ProviderContext = Depends(provider_context.get_provider_context),
):
    require_role(identity, {"admin"})
    from guardrails.policy_gate import ADVISORY_ONLY_ACTION_TYPES, APPROVER_ROLES, get_thresholds

    return {
        "thresholds": get_thresholds(),
        "approver_roles": sorted(APPROVER_ROLES),
        "advisory_only_action_types": sorted(ADVISORY_ONLY_ACTION_TYPES),
        "model_routing": _model_routing_display(provider_ctx.provider),
        "model_routing_editable": False,
        "note": "Model routing is read-only in this build — live-editing it would touch frozen, tested "
                "agent modules. Thresholds are live-editable and apply immediately to subsequent runs "
                "(in-memory only, resets on backend restart).",
    }


class ThresholdUpdate(BaseModel):
    blast_radius_approval_threshold: int | None = None
    blast_radius_block_threshold: int | None = None
    max_concurrent_changes_prod: int | None = None


@app.post("/config/thresholds")
def update_config_thresholds(req: ThresholdUpdate, identity: Identity = Depends(get_current_identity)):
    require_role(identity, {"admin"})
    from guardrails.policy_gate import set_thresholds

    return {"thresholds": set_thresholds(**req.model_dump())}


# ---------------- Ingestion / Admin (runbook upload — admin-only) ----------------
@app.get("/runbooks")
def list_runbooks(current_user: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute("SELECT id, class, declared_human_step_count, content_ref FROM runbooks ORDER BY id").fetchall()
    finally:
        conn.close()
    return {"runbooks": [{"id": r[0], "class": r[1], "declared_human_step_count": r[2], "content_ref": r[3]} for r in rows]}


class RunbookUploadResponse(BaseModel):
    runbook_id: str
    chunks_indexed: int


@app.post("/runbooks/upload", response_model=RunbookUploadResponse)
async def upload_runbook(file: UploadFile = File(...), identity: Identity = Depends(get_current_identity)):
    require_role(identity, {"admin"})
    if not file.filename or not file.filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="expected a .md runbook file (frontmatter: runbook_id/class/declared_human_step_count, then '## Prerequisites' / '## Steps' with '### Step N' sections — see chunking.py)")
    content = (await file.read()).decode("utf-8")

    data_dir = os.path.dirname(DB_PATH)
    runbooks_dir = os.path.join(data_dir, "runbooks")
    dest_path = os.path.join(runbooks_dir, file.filename)
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(content)

    from chunking import chunk_runbook
    from orchestrator.retrieval import _embed, _get_chroma_client

    chunks = chunk_runbook(dest_path)
    if not chunks:
        os.remove(dest_path)
        raise HTTPException(status_code=400, detail="no '### Step N' sections found — not a valid runbook, upload rejected")

    # hnsw:search_ef=500 avoids a real hnswlib crash on filtered queries with a large candidate pool
    # — see db/load_chroma.py's comment on the same call, and errors-solved.md.
    collection = _get_chroma_client().get_or_create_collection("runbooks", metadata={"hnsw:search_ef": 500})
    collection.upsert(
        ids=[c.chunk_id for c in chunks],
        embeddings=[_embed(c.content) for c in chunks],
        documents=[c.content for c in chunks],
        metadatas=[{**c.metadata, "heading_path": c.heading_path, "doc_type": "runbook"} for c in chunks],
    )

    rb_id = chunks[0].metadata["runbook_id"]
    rb_class = chunks[0].metadata["class"]
    declared_step_count = len(chunks)
    for line in content.splitlines():
        if line.startswith("declared_human_step_count:"):
            declared_step_count = int(line.split(":", 1)[1].strip())
            break

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO runbooks (id, class, declared_human_step_count, content_ref) VALUES (?,?,?,?)",
            (rb_id, rb_class, declared_step_count, f"runbooks/{file.filename}"),
        )
        conn.commit()
    finally:
        conn.close()

    return RunbookUploadResponse(runbook_id=rb_id, chunks_indexed=len(chunks))


class KnowledgeBaseUploadResponse(BaseModel):
    article_id: str
    chunks_indexed: int


@app.post("/knowledge-base/upload", response_model=KnowledgeBaseUploadResponse)
async def upload_knowledge_base_article(file: UploadFile = File(...), identity: Identity = Depends(get_current_identity)):
    # Same upload+chunk+embed+upsert pipeline as /runbooks/upload, but for reference articles
    # (chunk_postmortem's heading-based split, not chunk_runbook's numbered-step split) — no
    # `class` metadata is ever written here, so agents/planner.py's `where={"class": runbook_class}`
    # retrieval filter can never surface one of these as an executable runbook step.
    require_role(identity, {"admin"})
    if not file.filename or not file.filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="expected a .md article file (frontmatter: postmortem_id, then '## Heading' sections — see chunking.py's chunk_postmortem)")
    content = (await file.read()).decode("utf-8")

    data_dir = os.path.dirname(DB_PATH)
    kb_dir = os.path.join(data_dir, "knowledge_base")
    os.makedirs(kb_dir, exist_ok=True)
    dest_path = os.path.join(kb_dir, file.filename)
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(content)

    from chunking import chunk_postmortem
    from orchestrator.retrieval import _embed, _get_chroma_client

    chunks = chunk_postmortem(dest_path)
    if not chunks:
        os.remove(dest_path)
        raise HTTPException(status_code=400, detail="no '## Heading' sections found — not a valid article, upload rejected")
    if any(c.metadata.get("class") for c in chunks):
        os.remove(dest_path)
        raise HTTPException(status_code=400, detail="a knowledge base article must not declare a 'class' field — that vocabulary is reserved for runbooks")

    # hnsw:search_ef=500 avoids a real hnswlib crash on filtered queries with a large candidate pool
    # — see db/load_chroma.py's comment on the same call, and errors-solved.md.
    collection = _get_chroma_client().get_or_create_collection("runbooks", metadata={"hnsw:search_ef": 500})
    collection.upsert(
        ids=[c.chunk_id for c in chunks],
        embeddings=[_embed(c.content) for c in chunks],
        documents=[c.content for c in chunks],
        metadatas=[{**c.metadata, "heading_path": c.heading_path, "doc_type": "kb_article"} for c in chunks],
    )

    return KnowledgeBaseUploadResponse(article_id=chunks[0].metadata["postmortem_id"], chunks_indexed=len(chunks))


@app.post("/intake/confirm")
async def intake_confirm(req: IntakeConfirmRequest, current_user: str = Depends(get_current_user)):
    # The caller (frontend) is asserting the human has already confirmed on screen — this endpoint
    # doesn't re-derive that, it just forces the flag and lets start_workflow_from_confirmed_signal
    # do its own enforcement (raises if candidate_ci_refs is empty, etc).
    wire_all_in_process()
    signal = MaintenanceSignal.model_validate({**req.signal, "requires_human_confirmation": False})
    try:
        outcome = await start_workflow_from_confirmed_signal(signal, workflow_type=req.workflow_type)
    except ValueError as e:
        # intake_adapter.py raises exactly these two ValueErrors for genuine client-input problems
        # (confirmation gate, no resolvable CI). Anything else that happens to also be a ValueError
        # — e.g. json.JSONDecodeError, which IS a ValueError subclass, from a transient gateway
        # hiccup deep in the agent chain (embeddings/chat call) — is not a 400, and mislabeling it
        # as one hides a real transient failure behind a confusing "bad request" message.
        msg = str(e)
        if "requires human confirmation" in msg or "no resolvable CI reference" in msg:
            raise HTTPException(status_code=400, detail=msg)
        raise HTTPException(status_code=502, detail=f"Downstream call failed, likely transient — try again. ({msg})")
    incident_id = outcome.pop("incident_id")
    return await _format_workflow_outcome(incident_id, outcome, modality=signal.modality, workflow_type=req.workflow_type)
