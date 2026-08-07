"""Unit tests for the policy gate (backend/guardrails/policy_gate.py). Covers, at minimum, the 4
cases named in prd-phase-2.md's acceptance criteria: freeze-window block, prod-vs-non-prod,
blast-radius-above-threshold, missing-approver-role.

    pytest backend/tests/test_policy_gate.py -v
"""
from guardrails.policy_gate import PolicyContext, PolicyRequest, evaluate_policy


def _request(**overrides) -> PolicyRequest:
    defaults = dict(
        ci_id="CI-0001", environment="staging", criticality="P3", blast_radius_count=1,
        action_type="remediation", requested_at="2026-08-07T12:00:00", actor_role="operator",
    )
    defaults.update(overrides)
    return PolicyRequest(**defaults)


def test_freeze_window_blocks():
    ctx = PolicyContext(freeze_windows=[{"environment": "prod", "start": "2026-08-07T00:00:00", "end": "2026-08-08T00:00:00"}])
    req = _request(environment="prod", requested_at="2026-08-07T12:00:00", actor_role="sre_lead")
    result = evaluate_policy(req, ctx)
    assert result.decision == "block"
    assert "FREEZE_WINDOW" in result.triggered_rules


def test_freeze_window_does_not_affect_other_environments():
    ctx = PolicyContext(freeze_windows=[{"environment": "prod", "start": "2026-08-07T00:00:00", "end": "2026-08-08T00:00:00"}])
    req = _request(environment="staging", requested_at="2026-08-07T12:00:00")
    result = evaluate_policy(req, ctx)
    assert "FREEZE_WINDOW" not in result.triggered_rules


def test_prod_requires_approval_even_with_no_other_issues():
    ctx = PolicyContext()
    req = _request(environment="prod", actor_role="operator")  # not an approver role
    result = evaluate_policy(req, ctx)
    assert result.decision == "needs_approval"
    assert "REQUIRED_APPROVER_ROLE" in result.triggered_rules


def test_non_prod_does_not_require_approval_role():
    ctx = PolicyContext()
    req = _request(environment="staging", criticality="P3", actor_role="operator")
    result = evaluate_policy(req, ctx)
    assert result.decision == "allow"


def test_prod_with_approver_role_and_no_other_issues_is_allowed():
    ctx = PolicyContext()
    req = _request(environment="prod", criticality="P3", actor_role="sre_lead")
    result = evaluate_policy(req, ctx)
    assert result.decision == "allow"


def test_blast_radius_above_approval_threshold():
    ctx = PolicyContext()
    req = _request(blast_radius_count=8, actor_role="sre_lead")  # > 5, <= 15
    result = evaluate_policy(req, ctx)
    assert result.decision == "needs_approval"
    assert "BLAST_RADIUS_APPROVAL" in result.triggered_rules


def test_blast_radius_above_block_threshold():
    ctx = PolicyContext()
    req = _request(blast_radius_count=20, actor_role="sre_lead")  # > 15
    result = evaluate_policy(req, ctx)
    assert result.decision == "block"
    assert "BLAST_RADIUS_BLOCK" in result.triggered_rules


def test_missing_approver_role_for_p1():
    ctx = PolicyContext()
    req = _request(criticality="P1", environment="staging", actor_role="operator")
    result = evaluate_policy(req, ctx)
    assert result.decision == "needs_approval"
    assert "REQUIRED_APPROVER_ROLE" in result.triggered_rules


def test_p1_with_approver_role_is_allowed():
    ctx = PolicyContext()
    req = _request(criticality="P1", environment="staging", actor_role="change_manager")
    result = evaluate_policy(req, ctx)
    assert result.decision == "allow"


def test_max_concurrent_changes_blocks_prod():
    ctx = PolicyContext(active_changes_in_environment=3)
    req = _request(environment="prod", actor_role="sre_lead")
    result = evaluate_policy(req, ctx)
    assert result.decision == "block"
    assert "MAX_CONCURRENT_CHANGES" in result.triggered_rules


def test_tuning_is_always_advisory_never_allowed_outright():
    ctx = PolicyContext()
    req = _request(action_type="tuning", environment="staging", criticality="P4", actor_role="sre_lead")
    result = evaluate_policy(req, ctx)
    assert result.decision == "needs_approval"
    assert "ADVISORY_ONLY_WORKFLOW" in result.triggered_rules


def test_deterministic_same_input_same_output():
    ctx = PolicyContext(active_changes_in_environment=1, freeze_windows=[])
    req = _request(blast_radius_count=6, environment="prod", actor_role="operator")
    r1 = evaluate_policy(req, ctx)
    r2 = evaluate_policy(req, ctx)
    assert r1 == r2
