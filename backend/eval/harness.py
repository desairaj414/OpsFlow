"""Scenario Library eval harness (Phase 5 step 4) — runs every scenario seeded in the `scenarios`
table (data/scenarios/*.json) through the real supervisor.run_workflow(), same call this project's
own Scenario Launcher UI panel and scripts/pregenerate_demo_outputs.py already use (not a fourth
reimplementation of "how to run a scenario"). Grades each run's outcome against the fixture's
`expected` block, and reports:
  - pass/fail per scenario
  - verified_resolved vs symptom_suppressed counts (Fake Fix Detector outcomes)
  - citation coverage (fraction of runs whose diagnosis step produced at least one cited hypothesis)
  - cache-hit counts (confirms a replayed scenario doesn't re-hit the gateway — Phase 5 step 5/6)

Writes data/eval_report.json, which main.py's GET /metrics/summary reads for the
`scenario_eval_status` field instead of the honest "not_run" placeholder it shipped with.

Run from backend/:
    python -m eval.harness
"""
import asyncio
import json
import os
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import sqlite3  # noqa: E402

import providers  # noqa: E402
from intake.voice_path import run_voice_intake  # noqa: E402
from orchestrator.mcp_wiring import wire_all_in_process  # noqa: E402
from orchestrator.supervisor import run_workflow  # noqa: E402

DATA_DIR = os.path.join(REPO_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")
SCENARIOS_DIR = os.path.join(DATA_DIR, "scenarios")
VOICE_SAMPLES_DIR = os.path.join(DATA_DIR, "voice_samples")
REPORT_PATH = os.path.join(DATA_DIR, "eval_report.json")


def _load_cis() -> dict:
    with open(os.path.join(DATA_DIR, "cmdb.json"), encoding="utf-8") as f:
        return {c["id"]: c for c in json.load(f)["cis"]}


def _load_alerts() -> list[dict]:
    with open(os.path.join(DATA_DIR, "alerts.json"), encoding="utf-8") as f:
        return json.load(f)


def _load_seeded_scenarios() -> list[dict]:
    """Reads the `scenarios` table (not just os.listdir) so the harness only grades what's actually
    seeded into the running app — the same set the Scenario Launcher panel and GET /scenarios show."""
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT id, name, workflow_type, is_edge_case, fixture_path FROM scenarios ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    scenarios = []
    for sid, name, workflow_type, is_edge_case, fixture_path in rows:
        with open(os.path.join(DATA_DIR, fixture_path), encoding="utf-8") as f:
            fixture = json.load(f)
        scenarios.append(fixture)
    return scenarios


def _check_expected(outcome: dict, expected: dict) -> tuple[bool, list[str]]:
    """Only asserts on keys the fixture actually declares — `status`/`verification_status` may be
    a single string (exact match) or a list (any-of). Fixture keys ending in `_note` are
    informational context for a human reading the report, never asserted (see the edge_* fixtures'
    own docstrings for why: conflicting-evidence/no-strong-precedent outcomes are LLM-dependent,
    not something a fixture can force deterministically)."""
    failures = []
    for key in ("status", "verification_status"):
        if key not in expected:
            continue
        want = expected[key]
        got = outcome.get(key)
        ok = (got in want) if isinstance(want, list) else (got == want)
        if not ok:
            failures.append(f"{key}: expected {want!r}, got {got!r}")
    return (len(failures) == 0, failures)


async def _run_one(scenario: dict, cis: dict, alerts: list[dict], run_label: str) -> dict:
    ci = cis.get(scenario["ci_id"])
    if ci is None:
        return {"id": scenario["id"], "passed": False, "error": f"CI {scenario['ci_id']} not found in CMDB"}

    scenario_alerts = [
        a for a in alerts if a["ci_id"] == scenario["ci_id"] and a["category"] == scenario.get("alert_category", "fault")
    ]
    incident_id = f"EVAL-{scenario['id']}-{run_label}"
    start = time.perf_counter()
    outcome = await run_workflow(
        incident_id=incident_id, ci=ci, alerts=scenario_alerts, workflow_type=scenario["workflow_type"],
        actor_role="operator", auto_approve=scenario.get("auto_approve", False),
    )
    elapsed_s = time.perf_counter() - start

    passed, failures = _check_expected(outcome, scenario.get("expected", {}))
    diagnosis_entries = [r for r in outcome["trace"] if r.agent_name == "diagnosis"]
    planner_entries = [r for r in outcome["trace"] if r.agent_name == "planner"]
    has_citation = bool(diagnosis_entries and diagnosis_entries[0].cited_artifact_ids)
    cache_hits = [r.cache_hit for r in (diagnosis_entries + planner_entries) if r.cache_hit is not None]

    return {
        "id": scenario["id"],
        "name": scenario["name"],
        "workflow_type": scenario["workflow_type"],
        "is_edge_case": scenario.get("is_edge_case", False),
        "passed": passed,
        "failures": failures,
        "status": outcome.get("status"),
        "verification_status": outcome.get("verification_status"),
        "has_citation": has_citation,
        "cache_hits": cache_hits,
        "elapsed_s": round(elapsed_s, 2),
    }


def _check_voice_fixtures() -> str:
    """Runs every data/voice_samples/*.wav through the real run_voice_intake() (Whisper
    transcription -> scrub -> intent parse) and reports what actually happened, instead of a
    hardcoded string. These are synthetic (Windows SAPI TTS, some noise-mixed/accented-voice) —
    a labeled placeholder, not the real human-recorded samples PRD §6.1/§6.3 actually require (see
    data/voice_samples/README.md). Skips gracefully, same as tests/test_voice_path.py's real-Whisper
    test, if the active provider doesn't support transcription."""
    if not providers.PROVIDERS[providers.DEFAULT_PROVIDER]["supports_transcription"]:
        return (f"skipped — DEFAULT_PROVIDER={providers.DEFAULT_PROVIDER!r} has no transcription "
                f"endpoint; synthetic placeholder samples exist in data/voice_samples/ but weren't run")
    if not os.path.isdir(VOICE_SAMPLES_DIR):
        return "0 samples found — data/voice_samples/ missing"
    wav_files = sorted(f for f in os.listdir(VOICE_SAMPLES_DIR) if f.endswith(".wav"))
    if not wav_files:
        return "0 samples found — pending real recorded samples, see data/voice_samples/README.md"
    outcomes = []
    for fname in wav_files:
        with open(os.path.join(VOICE_SAMPLES_DIR, fname), "rb") as f:
            audio_bytes = f.read()
        try:
            signal = run_voice_intake(audio_bytes, filename=fname)
            outcomes.append(f"{fname}: intent={signal.parsed_intent}, confirm_required={signal.requires_human_confirmation}")
        except Exception as e:
            outcomes.append(f"{fname}: ERROR {e}")
    return f"{len(wav_files)} synthetic sample(s) run (SYNTHETIC, not real recordings — see README): " + "; ".join(outcomes)


async def run_all(run_label: str = "1") -> dict:
    wire_all_in_process()
    cis = _load_cis()
    alerts = _load_alerts()
    scenarios = _load_seeded_scenarios()

    results = [await _run_one(s, cis, alerts, run_label) for s in scenarios]

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    verified_resolved = sum(1 for r in results if r.get("verification_status") == "verified_resolved")
    symptom_suppressed = sum(1 for r in results if r.get("verification_status") == "symptom_suppressed")
    with_citation = sum(1 for r in results if r.get("has_citation"))
    citation_coverage = round(with_citation / total, 3) if total else 0.0
    total_cache_checks = sum(len(r.get("cache_hits", [])) for r in results)
    total_cache_hits = sum(sum(1 for h in r.get("cache_hits", []) if h) for r in results)

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_label": run_label,
        "total_scenarios": total,
        "passed": passed,
        "failed": total - passed,
        "verified_resolved": verified_resolved,
        "symptom_suppressed": symptom_suppressed,
        "citation_coverage": citation_coverage,
        "cache_checks": total_cache_checks,
        "cache_hits": total_cache_hits,
        "voice_fixtures": _check_voice_fixtures(),
        "results": results,
    }


def _print_report(report: dict) -> None:
    print(f"\n=== Eval Harness — run {report['run_label']} ({report['generated_at']}) ===")
    print(f"{report['passed']}/{report['total_scenarios']} passed | "
          f"verified_resolved={report['verified_resolved']} symptom_suppressed={report['symptom_suppressed']} | "
          f"citation_coverage={report['citation_coverage']:.0%} | "
          f"cache_hits={report['cache_hits']}/{report['cache_checks']}")
    for r in report["results"]:
        mark = "PASS" if r["passed"] else "FAIL"
        edge = " [edge]" if r.get("is_edge_case") else ""
        print(f"  [{mark}] {r['id']}{edge} — status={r.get('status')} verification={r.get('verification_status')}"
              + (f" — {r['failures']}" if r.get("failures") else ""))


async def _main() -> None:
    run_label = sys.argv[1] if len(sys.argv) > 1 else "1"
    report = await run_all(run_label)
    _print_report(report)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {REPORT_PATH}")


if __name__ == "__main__":
    asyncio.run(_main())
