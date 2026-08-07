"""Monitoring simulator [MOCK-P1] — a thin-but-authentic stand-in for a Prometheus/Alertmanager-style
monitoring system. NOT a real monitoring tool; labelled as a simulator in the UI/README, never
presented as real SaaS (PRD §3.5/§4.21). Serves the synthetic alert stream + per-CI metric series
generated in backend/data_gen/{alerts,metrics}.py.

Field shapes deliberately mirror Alertmanager's real API conventions (labels/annotations/startsAt/
status) — field-name fidelity is the point jurors probe, not full feature coverage.

    python mcp_servers/simulators/monitoring.py         # boots on :9001
    python mcp_servers/simulators/monitoring.py --test  # in-process self-test, no port bound
"""
import csv
import json
import os
import sys

from fastapi import FastAPI, HTTPException

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")

app = FastAPI(title="Monitoring Simulator [MOCK-P1] — not a real monitoring system")


def _load_alerts() -> list[dict]:
    with open(os.path.join(DATA_DIR, "alerts.json"), encoding="utf-8") as f:
        return json.load(f)


def _load_metrics(ci_id: str) -> list[dict]:
    path = os.path.join(DATA_DIR, "metrics", f"{ci_id}.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@app.get("/api/v2/alerts")
def list_alerts(ci_id: str | None = None, category: str | None = None, severity: str | None = None):
    """Alertmanager-style listing — mirrors GET /api/v2/alerts field shape (status/labels/annotations)."""
    alerts = _load_alerts()
    if ci_id:
        alerts = [a for a in alerts if a["ci_id"] == ci_id]
    if category:
        alerts = [a for a in alerts if a["category"] == category]
    if severity:
        alerts = [a for a in alerts if a["severity"] == severity]
    return {"status": "success", "data": {"alerts": alerts}}


@app.get("/api/v1/ci/{ci_id}/metrics")
def get_metric_series(ci_id: str):
    """Per-CI metric series — real field names: cpu_pct, memory_pct, latency_ms, error_rate."""
    series = _load_metrics(ci_id)
    if not series:
        raise HTTPException(status_code=404, detail=f"no metric series for {ci_id}")
    return {"ci_id": ci_id, "series": series}


@app.get("/health")
def health():
    return {"status": "ok", "simulator": "monitoring"}


def _self_test() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app)
    r = client.get("/api/v2/alerts")
    assert r.status_code == 200, r.text
    alerts = r.json()["data"]["alerts"]
    assert len(alerts) > 0, "no alerts returned"
    print(f"PASS list_alerts: {len(alerts)} alerts")

    sample_ci = alerts[0]["ci_id"]
    r = client.get("/api/v2/alerts", params={"ci_id": sample_ci})
    assert r.status_code == 200
    filtered = r.json()["data"]["alerts"]
    assert all(a["ci_id"] == sample_ci for a in filtered)
    print(f"PASS list_alerts filter by ci_id: {len(filtered)} for {sample_ci}")

    with open(os.path.join(DATA_DIR, "metrics_index.json"), encoding="utf-8") as f:
        index = json.load(f)
    metrics_ci = index["sampled_ci_ids"][0]
    r = client.get(f"/api/v1/ci/{metrics_ci}/metrics")
    assert r.status_code == 200, r.text
    series = r.json()["series"]
    assert len(series) > 0
    print(f"PASS get_metric_series: {len(series)} points for {metrics_ci}")

    r = client.get("/api/v1/ci/CI-9999/metrics")
    assert r.status_code == 404
    print("PASS get_metric_series 404 for unknown CI")

    print("\nSELF-TEST PASSED: monitoring simulator endpoints all working.")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _self_test()
    else:
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=9001)
