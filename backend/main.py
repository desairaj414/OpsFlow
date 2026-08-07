# MUST be first — before any langchain/tiktoken import.
import os
os.environ["TIKTOKEN_CACHE_DIR"] = "./token"

# Corporate proxy MITM certs break tiktoken's internal downloader (uses `requests`) too — bypass globally.
import ssl
import requests
import urllib3

ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_orig_request = requests.Session.request


def _unverified_request(self, *args, **kwargs):
    kwargs["verify"] = False
    return _orig_request(self, *args, **kwargs)


requests.Session.request = _unverified_request

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

import config
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


def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=config.JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
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


@app.post("/auth/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Mock only — replace with real user store before production use.
    if not form_data.username or not form_data.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    token = create_access_token(subject=form_data.username)
    return TokenResponse(access_token=token)


@app.get("/auth/me")
def read_me(current_user: str = Depends(get_current_user)):
    return {"username": current_user}


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


# ---------------- Example chat endpoint ----------------
class ChatRequest(BaseModel):
    message: str
    model: str | None = None


@app.post("/chat")
def chat(req: ChatRequest, current_user: str = Depends(get_current_user)):
    llm = get_llm(model=req.model)
    response = llm.invoke(req.message)
    return {"reply": response.content}


# ---------------- Live alert feed (SSE) ----------------
def _fetch_alerts_after(conn: sqlite3.Connection, after_id: str | None, limit: int) -> list[dict]:
    if after_id is None:
        cur = conn.execute(
            "SELECT id, source, raw_payload, received_at, modality FROM alerts ORDER BY id ASC LIMIT ?",
            (limit,),
        )
    else:
        cur = conn.execute(
            "SELECT id, source, raw_payload, received_at, modality FROM alerts WHERE id > ? ORDER BY id ASC LIMIT ?",
            (after_id, limit),
        )
    return [
        {"id": r[0], "source": r[1], "raw_payload": r[2], "received_at": r[3], "modality": r[4]}
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

    # Live tail: poll for rows inserted after the backlog (e.g. by the monitoring simulator).
    while True:
        conn = sqlite3.connect(DB_PATH)
        try:
            new_alerts = _fetch_alerts_after(conn, last_id, limit=20)
        finally:
            conn.close()
        for alert in new_alerts:
            last_id = alert["id"]
            yield f"data: {json.dumps(alert)}\n\n"
        yield ": keep-alive\n\n"
        await asyncio.sleep(3)


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
        payload = alert["raw_payload"]
        if isinstance(payload, dict):
            # Different sources shape raw_payload differently (prometheus: annotations.summary,
            # apm: message, snmp: a flat string) — fall through rather than assume one shape.
            summary = payload.get("annotations", {}).get("summary") or payload.get("message")
            if summary:
                return summary
        return str(payload)[:120]

    candidates = [
        {
            "cluster_id": cluster_id,
            "topology_group": members[0]["topology_group"],
            "category": members[0]["category"],
            "alert_count": len(members),
            "alert_ids": [m["id"] for m in members],
            "representative_summary": _summarize(min(members, key=lambda m: m["received_at"])),
        }
        for cluster_id, members in sorted(clusters.items())
    ]

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


async def _format_workflow_outcome(incident_id: str, outcome: dict, modality: str) -> dict:
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
        "status": outcome["status"],
        "reason": outcome.get("reason"),
        "verification_status": outcome.get("verification_status"),
        "trace": trace,
        "agent_card": agent_card,  # A2A discovery — viewable for the one handoff that used it
    }


@app.post("/workflows/run")
async def workflows_run(req: WorkflowRunRequest, current_user: str = Depends(get_current_user)):
    wire_all_in_process()
    cis, _relationships = _load_cis_and_relationships()
    ci = next((c for c in cis if c["id"] == req.ci_id), None)
    if ci is None:
        raise HTTPException(status_code=404, detail=f"CI {req.ci_id} not found")

    alerts = [a for a in _load_alerts() if a["ci_id"] == req.ci_id and a["category"] == "fault"]
    incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
    outcome = await run_workflow(
        incident_id=incident_id, ci=ci, alerts=alerts,
        workflow_type=req.workflow_type, actor_role=current_user, auto_approve=req.auto_approve,
    )
    return await _format_workflow_outcome(incident_id, outcome, modality="alert")


class WorkflowDecisionRequest(BaseModel):
    incident_id: str
    decision: str  # "approve" | "reject"
    reason: str


@app.post("/workflows/decision")
async def workflows_decision(req: WorkflowDecisionRequest, current_user: str = Depends(get_current_user)):
    # Records a human approve/reject decision with a mandatory reason. NOTE: run_workflow has no
    # checkpointing — this does NOT resume the paused run that produced incident_id. Approving
    # something in the Approval Queue triggers a SEPARATE fresh re-run with auto_approve=true
    # (see the frontend) rather than continuing this exact run; that limitation is deliberate and
    # surfaced in the UI, not hidden here.
    if req.decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision must be 'approve' or 'reject'")
    if not req.reason.strip():
        raise HTTPException(status_code=400, detail="reason is required")

    conn = sqlite3.connect(DB_PATH)
    try:
        write_audit_entry(
            conn, actor=current_user, action=f"human_{req.decision}_plan",
            target_artifact=req.incident_id, approval_ref=req.reason,
        )
    finally:
        conn.close()
    return {"recorded": True}


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


# ---------------- Chunk Inspector (real Chroma runbook chunks, no embedding call needed to browse) ----------------
@app.get("/chunks")
def chunks(runbook_id: str | None = None, current_user: str = Depends(get_current_user)):
    from orchestrator.retrieval import _get_chroma_client

    collection = _get_chroma_client().get_collection("runbooks")
    kwargs = {"where": {"runbook_id": runbook_id}} if runbook_id else {}
    result = collection.get(**kwargs)
    return {
        "total": len(result["ids"]),
        "chunks": [
            {"id": result["ids"][i], "document": result["documents"][i], "metadata": result["metadatas"][i]}
            for i in range(len(result["ids"]))
        ],
    }


# ---------------- Metrics & Eval — real aggregates only, no Phase 5 scenario eval yet ----------------
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
    finally:
        conn.close()

    cis, _rel = _load_cis_and_relationships()
    alerts = _load_alerts()
    topology_groups = build_topology_groups(cis, _rel)
    correlated = correlate_alerts(alerts, topology_groups)
    n_clusters = len({a["cluster_id"] for a in correlated})

    return {
        "total_workflow_runs_this_session": total_runs,
        "completed_runs": completed_runs,
        "stopped_before_completion": total_runs - completed_runs,
        "human_approvals": human_approvals,
        "human_rejections": human_rejections,
        "negative_kb_entries_seeded": negative_kb_count,
        "correlation_noise_reduction_ratio": round(1 - (n_clusters / len(alerts)), 3) if alerts else 0,
        # Honest gap, not filled in: Phase 5 (Scenario Library, Eval & Hardening) hasn't run yet,
        # so there's no scenario pass/fail rate or accuracy metric to show — these are live
        # operational aggregates from this session's real runs, not an eval report.
        "scenario_eval_status": "not_run — Phase 5 not started",
    }


# ---------------- Multimodal intake (voice + image) — real Whisper/gpt-4o, confirmation-gated ----------------
@app.post("/intake/voice")
async def intake_voice(file: UploadFile = File(...), current_user: str = Depends(get_current_user)):
    audio_bytes = await file.read()
    signal = run_voice_intake(audio_bytes, filename=file.filename or "voice.wav")
    return signal.model_dump()


@app.post("/intake/image")
async def intake_image(file: UploadFile = File(...), current_user: str = Depends(get_current_user)):
    image_bytes = await file.read()
    mime_type = file.content_type or "image/png"
    signal = run_vision_intake(image_bytes, mime_type=mime_type)
    return signal.model_dump()


class IntakeConfirmRequest(BaseModel):
    signal: dict
    workflow_type: str = "incident"


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
    return await _format_workflow_outcome(incident_id, outcome, modality=signal.modality)
