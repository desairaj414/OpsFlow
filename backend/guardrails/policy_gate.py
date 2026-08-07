"""Policy gate — pure Python rule engine, NO LLM (must be auditable and provably consistent,
per domain-guardrails.md pillar (a)). Evaluates a proposed action against deterministic rules:
change-freeze windows, prod-vs-non-prod, CI criticality, blast-radius threshold, max concurrent
changes, required-approver role. Also encodes the resolved decision that Performance Tuning is
advisory-only and NEVER auto-executes (domain-workflows.md parity table) — this is a hard rule
here, not a UI convention.
"""
from dataclasses import dataclass, field
from datetime import datetime

BLAST_RADIUS_APPROVAL_THRESHOLD = 5
BLAST_RADIUS_BLOCK_THRESHOLD = 15
MAX_CONCURRENT_CHANGES_PROD = 3
APPROVER_ROLES = {"sre_lead", "change_manager"}
ADVISORY_ONLY_ACTION_TYPES = {"tuning"}  # never auto-executes, per domain-workflows.md parity table


@dataclass
class PolicyRequest:
    ci_id: str
    environment: str          # prod | staging | dev
    criticality: str          # P1-P4
    blast_radius_count: int
    action_type: str          # remediation | patching | tuning
    requested_at: str         # ISO-8601
    actor_role: str


@dataclass
class PolicyContext:
    active_changes_in_environment: int = 0
    freeze_windows: list[dict] = field(default_factory=list)  # [{"environment": str, "start": iso, "end": iso}]


@dataclass
class PolicyResult:
    decision: str              # "allow" | "needs_approval" | "block"
    triggered_rules: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def _in_freeze_window(request: PolicyRequest, context: PolicyContext) -> bool:
    requested_at = datetime.fromisoformat(request.requested_at)
    for window in context.freeze_windows:
        if window["environment"] != request.environment:
            continue
        start, end = datetime.fromisoformat(window["start"]), datetime.fromisoformat(window["end"])
        if start <= requested_at <= end:
            return True
    return False


def evaluate_policy(request: PolicyRequest, context: PolicyContext) -> PolicyResult:
    """Deterministic: same request + same context always produces the same decision. Precedence:
    any BLOCK rule wins outright; else any NEEDS_APPROVAL rule applies; else ALLOW."""
    triggered: list[str] = []
    reasons: list[str] = []
    blocked = False
    needs_approval = False

    if _in_freeze_window(request, context):
        blocked = True
        triggered.append("FREEZE_WINDOW")
        reasons.append(f"{request.environment} is in a change-freeze window at {request.requested_at}")

    if request.blast_radius_count > BLAST_RADIUS_BLOCK_THRESHOLD:
        blocked = True
        triggered.append("BLAST_RADIUS_BLOCK")
        reasons.append(f"blast radius {request.blast_radius_count} exceeds hard block threshold {BLAST_RADIUS_BLOCK_THRESHOLD}")
    elif request.blast_radius_count > BLAST_RADIUS_APPROVAL_THRESHOLD:
        needs_approval = True
        triggered.append("BLAST_RADIUS_APPROVAL")
        reasons.append(f"blast radius {request.blast_radius_count} exceeds approval threshold {BLAST_RADIUS_APPROVAL_THRESHOLD}")

    if request.environment == "prod" and context.active_changes_in_environment >= MAX_CONCURRENT_CHANGES_PROD:
        blocked = True
        triggered.append("MAX_CONCURRENT_CHANGES")
        reasons.append(f"{context.active_changes_in_environment} concurrent prod changes already active (limit {MAX_CONCURRENT_CHANGES_PROD})")

    if request.action_type in ADVISORY_ONLY_ACTION_TYPES:
        needs_approval = True
        triggered.append("ADVISORY_ONLY_WORKFLOW")
        reasons.append(f"'{request.action_type}' is advisory-only by design and never auto-executes")

    is_prod = request.environment == "prod"
    is_p1 = request.criticality == "P1"
    has_approver = request.actor_role in APPROVER_ROLES
    if (is_prod or is_p1) and not has_approver:
        needs_approval = True
        triggered.append("REQUIRED_APPROVER_ROLE")
        reasons.append(f"actor role '{request.actor_role}' is not an approver role, required for prod and/or P1 actions")

    if blocked:
        decision = "block"
    elif needs_approval:
        decision = "needs_approval"
    else:
        decision = "allow"

    return PolicyResult(decision=decision, triggered_rules=triggered, reasons=reasons)
