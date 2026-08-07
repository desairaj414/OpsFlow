"""Generates runbooks (3 classes: remediation/patching/tuning) and postmortems, including ONE
deliberate trap runbook whose step 4 spans a simulated page break (PRD §6.4 / domain-guardrails.md
"Chunking" spec) — the chunker built later in Phase 1 must not split that step. Numbered,
clause-structured, each declares its human step count in frontmatter. Fully synthetic, fixed seed.

    python data_gen/runbooks.py

Writes:
    data/runbooks/RB-*.md       18-22 runbooks
    data/postmortems/PM-*.md    8-10 postmortems
"""
import os
import random

random.seed(20260807)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
RUNBOOKS_DIR = os.path.join(DATA_DIR, "runbooks")
POSTMORTEMS_DIR = os.path.join(DATA_DIR, "postmortems")

CI_CONTEXTS = ["sharepoint-site", "power-platform-environment", "dataverse-instance", "exchange-online-connector", "power-automate-gateway", "onedrive-sync-cache", "teams-notification-queue"]

REMEDIATION_STEPS = [
    "Confirm the alert against the monitoring simulator: check current status and severity for the affected CI before taking any action.",
    "Identify the top resource-consuming or failing process on the CI via the process/health snapshot.",
    "If the failure matches a known signature (see Negative KB first — do not repeat a fix already recorded as failed for this CI class), apply the corrective action: restart the affected service.",
    "Wait 5 minutes and re-check both the alert status and the underlying health probe. **Only if X**: if the alert cleared but the health probe has not recovered, do NOT close — mark `symptom_suppressed, root cause unconfirmed` and keep the incident open (Fake Fix Detector).",
    "If the health probe has recovered and holds through the stabilisation window, proceed to close. If not recovered after one restart attempt, escalate to on-call SRE — do not restart a second time without approval.",
    "Log the action taken, evidence cited, and outcome in the ticket work notes.",
]
PATCHING_STEPS = [
    "Confirm the target CI's current patch level against the patch inventory and identify the available version gap.",
    "Confirm a change-calendar window exists and is approved for this CI; do not patch outside an approved window (Policy Gate).",
    "Take a state snapshot / backup point before applying anything, so the rollback step below is possible.",
    "Apply the patch to the target CI.",
    "Verify service health post-patch: health probe recovered, no new alerts raised in the window.",
    "If verification fails, execute the rollback procedure to the pre-patch snapshot and re-open the change as failed; if verification passes, update the CMDB patch_level to reflect the new version.",
]
TUNING_STEPS = [
    "Gather the baseline metric window for the affected CI (CPU, memory, latency, error rate) covering at least the period before the degradation trend began.",
    "Identify the specific bottleneck resource or query pattern responsible for the trend — do not propose a change without a specific, cited cause.",
    "Draft the tuning recommendation with an explicit expected effect and how it will be measured.",
    "**Advisory only — this workflow never auto-executes.** Present the recommendation for human judgement; do not apply automatically even if confidence is high.",
    "If approved and applied, monitor the same metrics across a sustained post-change window — a single improved data point is not sufficient, verification requires sustained improvement.",
    "Document the outcome (improved / no change / regressed) and cite the before/after metric window in the postmortem or ticket.",
]

CLASS_STEP_POOLS = {"remediation": REMEDIATION_STEPS, "patching": PATCHING_STEPS, "tuning": TUNING_STEPS}
CLASS_COUNTS = {"remediation": 9, "patching": 7, "tuning": 6}  # totals 22, within 18-22

PAGE_BREAK_MARKER = "<!-- PAGE BREAK (simulated PDF page boundary — this step must stay atomic, see domain-guardrails.md) -->"


def _runbook_md(rb_id: str, rb_class: str, ci_context: str, steps: list[str], is_trap: bool) -> str:
    title = f"{rb_class.title()} — {ci_context}"
    body_steps = []
    for i, step_text in enumerate(steps, start=1):
        if is_trap and i == 4:
            # Deliberate trap: step 4's own text is split by a simulated page break mid-sentence.
            # A correct chunker (built later, PRD §6.4) must keep this step whole regardless.
            half = len(step_text) // 2
            step_text = step_text[:half] + f"\n\n{PAGE_BREAK_MARKER}\n\n" + step_text[half:]
        body_steps.append(f"### Step {i}\n{step_text}")
    steps_md = "\n\n".join(body_steps)
    return f"""---
runbook_id: {rb_id}
class: {rb_class}
declared_human_step_count: {len(steps)}
is_trap_case: {str(is_trap).lower()}
---

# {rb_id}: {title}

## Prerequisites
- Confirm the CI ID and class match this runbook's scope before proceeding.
- Only proceed if the incident/change has passed the Policy Gate for this CI's environment and criticality.

## Steps

{steps_md}
"""


def generate_runbooks() -> list[str]:
    os.makedirs(RUNBOOKS_DIR, exist_ok=True)
    written = []
    counter = 1
    trap_assigned = False
    for rb_class, count in CLASS_COUNTS.items():
        for _ in range(count):
            rb_id = f"RB-{counter:03d}"
            ci_context = random.choice(CI_CONTEXTS)
            steps = list(CLASS_STEP_POOLS[rb_class])
            # Assign the one deliberate trap case to the first remediation runbook (step 4 exists
            # in all 3 pools since each has >=6 steps).
            is_trap = (rb_class == "remediation" and not trap_assigned and counter == 1)
            if is_trap:
                trap_assigned = True
            content = _runbook_md(rb_id, rb_class, ci_context, steps, is_trap)
            path = os.path.join(RUNBOOKS_DIR, f"{rb_id}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            written.append(rb_id)
            counter += 1
    return written


POSTMORTEM_COUNT = 9


def _postmortem_md(pm_id: str, ci_context: str) -> str:
    return f"""---
postmortem_id: {pm_id}
related_ci_context: {ci_context}
---

# {pm_id}: Incident postmortem — {ci_context}

## Summary
An incident affecting a {ci_context} was detected, diagnosed, and resolved. This document records
the root cause and the verification evidence used to confirm resolution (not just alert-clear).

## Timeline
- Alert received and correlated to the affected CI.
- Diagnosis identified the contributing factor via cited evidence (metric history, CI relationships, past ticket history).
- Remediation plan drafted from the applicable runbook, passed the Policy Gate, approved.
- Executed; verified via both alert-clear and health-probe recovery across a stabilisation window (Fake Fix Detector — symptom suppression was explicitly ruled out before closing).

## Root cause
A specific, cited contributing factor for this {ci_context} instance (not a generic "restart fixed
it" — the two-signal verification requirement means the actual cause had to be confirmed).

## Follow-up actions
- Runbook reference updated if a step proved ambiguous during execution.
- Negative KB updated if any attempted fix failed before the successful one.
"""


def generate_postmortems() -> list[str]:
    os.makedirs(POSTMORTEMS_DIR, exist_ok=True)
    written = []
    for i in range(1, POSTMORTEM_COUNT + 1):
        pm_id = f"PM-{i:03d}"
        ci_context = random.choice(CI_CONTEXTS)
        content = _postmortem_md(pm_id, ci_context)
        path = os.path.join(POSTMORTEMS_DIR, f"{pm_id}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        written.append(pm_id)
    return written


def main() -> None:
    runbooks = generate_runbooks()
    postmortems = generate_postmortems()
    print(f"runbooks/: {len(runbooks)} files ({CLASS_COUNTS})")
    print(f"postmortems/: {len(postmortems)} files")


if __name__ == "__main__":
    main()

    rb_files = [f for f in os.listdir(RUNBOOKS_DIR) if f.endswith(".md")]
    assert 18 <= len(rb_files) <= 22, f"runbook count {len(rb_files)} outside 18-22 band"
    pm_files = [f for f in os.listdir(POSTMORTEMS_DIR) if f.endswith(".md")]
    assert 8 <= len(pm_files) <= 10, f"postmortem count {len(pm_files)} outside 8-10 band"

    trap_files = []
    for fname in rb_files:
        with open(os.path.join(RUNBOOKS_DIR, fname), encoding="utf-8") as f:
            content = f.read()
        if "is_trap_case: true" in content:
            trap_files.append(fname)
            assert PAGE_BREAK_MARKER in content, f"{fname} marked as trap but has no page-break marker"
            assert "### Step 4" in content, f"{fname} trap case must land in step 4"
    assert len(trap_files) == 1, f"expected exactly 1 trap runbook, found {len(trap_files)}"

    for fname in rb_files:
        with open(os.path.join(RUNBOOKS_DIR, fname), encoding="utf-8") as f:
            content = f.read()
        assert "declared_human_step_count:" in content
        assert "## Prerequisites" in content

    print(f"\nSELF-TEST PASSED: {len(rb_files)} runbooks (18-22 band), {len(pm_files)} postmortems (8-10 band), exactly 1 trap case ({trap_files[0]}).")
