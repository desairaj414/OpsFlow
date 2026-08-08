"""Patch-source simulator [MOCK-P1] — a thin-but-authentic stand-in for the vendor patch feeds /
patch-management systems (WSUS/SCCM-shaped) a real IT org would poll. NOT a real vendor site;
labelled as a simulator in the UI/README, never presented as real SaaS. Serves the synthetic
pending-patch inventory and change-calendar generated in backend/data_gen/patch_inventory.py.

    python mcp_servers/simulators/patch_source.py         # boots on :9005
    python mcp_servers/simulators/patch_source.py --test  # in-process self-test, no port bound
"""
import json
import os
import sys

from fastapi import FastAPI

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")

app = FastAPI(title="Patch Source Simulator [MOCK-P1] — not a real vendor patch feed")

_PATCHES_BY_CI: dict[str, list[dict]] = {}
_CALENDAR: list[dict] = []


def _load() -> None:
    if _PATCHES_BY_CI:
        return
    with open(os.path.join(DATA_DIR, "patch_inventory.json"), encoding="utf-8") as f:
        for patch in json.load(f):
            _PATCHES_BY_CI.setdefault(patch["ci_id"], []).append(patch)
    with open(os.path.join(DATA_DIR, "change_calendar.json"), encoding="utf-8") as f:
        _CALENDAR.extend(json.load(f))


@app.get("/patch_inventory/{ci_id}")
def get_pending_patches(ci_id: str):
    _load()
    return {"ci_id": ci_id, "patches": _PATCHES_BY_CI.get(ci_id, [])}


@app.get("/change_calendar")
def get_change_calendar(scope: str | None = None):
    """scope filters to windows matching 'global' OR the given scope exactly (an environment name
    or a specific ci_id) — callers pass the CI's environment or id to get the windows relevant to it."""
    _load()
    if scope is None:
        return {"blackouts": _CALENDAR}
    return {"blackouts": [w for w in _CALENDAR if w["scope"] in ("global", scope)]}


@app.get("/health")
def health():
    return {"status": "ok", "simulator": "patch_source"}


def _self_test() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app)

    r = client.get("/patch_inventory/CI-0059")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ci_id"] == "CI-0059"
    assert len(body["patches"]) >= 1, "CI-0059 is a guaranteed-coverage CI in data_gen/patch_inventory.py"
    print(f"PASS get_pending_patches: {len(body['patches'])} pending patch(es) for CI-0059")

    r = client.get("/patch_inventory/CI-9999")
    assert r.status_code == 200
    assert r.json()["patches"] == [], "unknown/uncovered CI should return an empty list, not 404"
    print("PASS get_pending_patches returns empty list for an uncovered CI")

    r = client.get("/change_calendar", params={"scope": "prod"})
    assert r.status_code == 200
    blackouts = r.json()["blackouts"]
    scopes = {w["scope"] for w in blackouts}
    assert scopes.issubset({"global", "prod"})
    assert "global" in scopes and "prod" in scopes, "expected at least one global and one prod-scoped window"
    print(f"PASS get_change_calendar(scope='prod'): {len(blackouts)} window(s), scopes={scopes}")

    r = client.get("/change_calendar", params={"scope": "CI-0059"})
    assert r.status_code == 200
    ci_scopes = {w["scope"] for w in r.json()["blackouts"]}
    assert "CI-0059" in ci_scopes, "CI-0059 has a guaranteed per-CI blackout window"
    print("PASS get_change_calendar(scope='CI-0059') includes its dedicated blackout window")

    print("\nSELF-TEST PASSED: Patch Source simulator endpoints all working.")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _self_test()
    else:
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=9005)
