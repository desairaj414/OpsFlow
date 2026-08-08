"""Generates the synthetic alert stream — heterogeneous raw shapes (Prometheus-like, SNMP-terse,
APM-verbose) so downstream normalisation into MaintenanceSignal has real variety to handle, not
one convenient shape. Fully synthetic, fixed seed (PRD §6.3).

    python data_gen/alerts.py

Writes:
    data/alerts.json   ~500 alerts, each {id, source, ci_id, category, severity, received_at, raw_payload}
"""
import json
import os
import random
import uuid

from faker import Faker

SEED = 20260807
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")

ALERT_COUNT = 500
DEGRADATION_RATE = 0.30  # performance-tuning-triggering alerts vs. fault (incident-triggering)

FAULT_SUMMARIES = [
    "access denied - permission error", "sync client crash-looped", "storage quota critical", "connection refused",
    "health check failing", "5xx error rate spike", "flow run failed - throttled", "certificate expired",
]
DEGRADATION_SUMMARIES = [
    "latency creeping upward over past hour", "sync queue backlog trending up, no recovery",
    "API call duration p95 rising steadily", "throttling rate higher than baseline for 3 days",
    "connection pool utilization trending toward saturation",
]
SEVERITIES = ["critical", "warning", "info"]


def _load_cis() -> list[dict]:
    with open(os.path.join(DATA_DIR, "cmdb.json"), encoding="utf-8") as f:
        return json.load(f)["cis"]


def _prometheus_alert(ci: dict, category: str, severity: str, summary: str, ts: str) -> dict:
    return {
        "labels": {"alertname": summary.replace(" ", "_"), "severity": severity, "instance": ci["name"], "job": ci["type"]},
        "annotations": {"summary": summary, "description": f"{ci['name']} ({ci['id']}): {summary}"},
        "startsAt": ts,
        "status": "firing",
    }


def _snmp_alert(ci: dict, category: str, severity: str, summary: str, ts: str) -> str:
    sev_num = {"critical": 1, "warning": 4, "info": 6}[severity]
    code = "IF-DOWN" if category == "fault" else "PERF-DEGRADE"
    return f"TRAP 1.3.6.1.4.1.9 {code} {ci['id']} sev={sev_num} ts={ts} msg=\"{summary}\""


def _apm_alert(ci: dict, category: str, severity: str, summary: str, ts: str) -> dict:
    return {
        "trace_id": str(uuid.uuid4()),
        "service": ci["name"],
        "span": {"operation": random.choice(["GET /api", "db.query", "cache.get", "queue.publish"])},
        "latency_p99_ms": random.randint(200, 8000) if category == "degradation" else random.randint(50, 400),
        "error_rate_pct": round(random.uniform(0.1, 15.0), 2) if category == "fault" else round(random.uniform(0.0, 2.0), 2),
        "message": summary,
        "timestamp": ts,
    }


def generate_alerts(cis: list[dict]) -> list[dict]:
    alerts = []
    for i in range(1, ALERT_COUNT + 1):
        ci = random.choice(cis)
        category = "degradation" if random.random() < DEGRADATION_RATE else "fault"
        summary = random.choice(DEGRADATION_SUMMARIES if category == "degradation" else FAULT_SUMMARIES)
        severity = random.choice(SEVERITIES)
        ts = fake.date_time_between(start_date="-14d", end_date="now").isoformat()
        source = random.choice(["prometheus", "snmp", "apm"])
        if source == "prometheus":
            raw = _prometheus_alert(ci, category, severity, summary, ts)
        elif source == "snmp":
            raw = _snmp_alert(ci, category, severity, summary, ts)
        else:
            raw = _apm_alert(ci, category, severity, summary, ts)
        alerts.append({
            "id": f"ALERT-{i:04d}",
            "source": source,
            "ci_id": ci["id"],
            "category": category,
            "severity": severity,
            "received_at": ts,
            "summary": summary,
            "raw_payload": raw,
        })
    return alerts


def main() -> None:
    cis = _load_cis()
    alerts = generate_alerts(cis)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "alerts.json"), "w", encoding="utf-8") as f:
        json.dump(alerts, f, indent=2)
    by_source = {s: sum(1 for a in alerts if a["source"] == s) for s in ("prometheus", "snmp", "apm")}
    by_category = {c: sum(1 for a in alerts if a["category"] == c) for c in ("fault", "degradation")}
    print(f"alerts.json: {len(alerts)} alerts, by source={by_source}, by category={by_category}")


if __name__ == "__main__":
    main()

    with open(os.path.join(DATA_DIR, "alerts.json"), encoding="utf-8") as f:
        alerts = json.load(f)
    assert len(alerts) == ALERT_COUNT, f"expected {ALERT_COUNT} alerts, got {len(alerts)}"
    sources = {a["source"] for a in alerts}
    assert sources == {"prometheus", "snmp", "apm"}, f"missing a shape: {sources}"
    ci_ids = {ci["id"] for ci in _load_cis()}
    assert all(a["ci_id"] in ci_ids for a in alerts), "alert references a CI not in cmdb.json"
    assert all(a.get("summary") for a in alerts), "alert missing a human-readable summary"
    print("\nSELF-TEST PASSED: volume, shape variety, and CI references all valid.")
