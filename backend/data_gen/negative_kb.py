"""Generates the Negative Knowledge Base seed — remediations that were tried and failed, scoped to
(ci_class, failure_signature) per the bias-mitigation rule in domain-guardrails.md (never a blanket
filter). Fully synthetic, fixed seed, combinatorial over the same CI_TYPES vocabulary cmdb.py uses
so ci_class values line up with real generated CIs.

    python data_gen/negative_kb.py

Writes:
    data/failed_remediations.json   ~500 entries: id, ci_class, failure_signature, attempted_fix,
                                     reason_failed, source_incident_id
"""
import json
import os
import random

SEED = 20260807
random.seed(SEED)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")

ENTRY_COUNT = 500

# Same 9 CI types data_gen/cmdb.py generates real CIs against — keeps ci_class values meaningful
# rather than inventing a parallel vocabulary the rest of the dataset never uses.
CI_TYPES = [
    "sharepoint-site", "power-platform-environment", "dataverse-instance", "exchange-online-connector",
    "power-automate-gateway", "onedrive-sync-cache", "teams-notification-queue",
    "sharepoint-document-library", "azure-ad-connect-sync",
]

FAILURE_SIGNATURES = [
    "access denied on SharePoint site collection", "Conditional Access policy blocking sign-in",
    "Dataverse API throttling (429)", "Power BI dataset refresh failure",
    "Azure AD Connect sync interruption", "Teams meeting audio/video degraded",
    "SharePoint document library storage quota exceeded", "Exchange Online mail delivery delayed",
    "OneDrive sync stuck / not syncing", "Power Automate flow run failures (throttled)",
    "Dataverse plugin execution timeout", "SharePoint search index stale",
    "Teams channel message delivery delayed", "Power Apps canvas app failing to load",
]

ATTEMPTED_FIXES = [
    "restarted the OneDrive sync client", "cleared the Teams client cache",
    "requested additional SharePoint storage quota", "increased the connector throttling limit",
    "added the user to the Conditional Access exclusion group", "re-granted site permissions",
    "requested a Dataverse capacity add-on", "restarted the Exchange Online transport queue",
    "rebuilt the SharePoint search index", "recycled the Power Automate connection",
]

REASON_FAILED = [
    "root cause was a broken permission-inheritance chain, not a simple access grant",
    "the Conditional Access policy was reapplied by the next sync cycle",
    "the exclusion group itself was scoped incorrectly",
    "fix addressed a symptom, underlying license assignment was still missing",
    "the throttling limit increase did not address the actual API call volume spike",
    "the underlying quota policy was tenant-level, not site-level",
    "the timeout was caused by a downstream dependency, not the plugin itself",
    "the index rebuild completed but the crawl schedule was never re-enabled",
]


def generate_entries() -> list[dict]:
    entries = []
    for i in range(1, ENTRY_COUNT + 1):
        entries.append({
            "id": f"NEGKB-{i:03d}",
            "ci_class": random.choice(CI_TYPES),
            "failure_signature": random.choice(FAILURE_SIGNATURES),
            "attempted_fix": random.choice(ATTEMPTED_FIXES),
            "reason_failed": random.choice(REASON_FAILED),
            "source_incident_id": f"INC-{random.randint(1000, 9999)}",
        })
    return entries


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    entries = generate_entries()
    with open(os.path.join(DATA_DIR, "failed_remediations.json"), "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    print(f"failed_remediations.json: {len(entries)} entries")


if __name__ == "__main__":
    main()

    with open(os.path.join(DATA_DIR, "failed_remediations.json"), encoding="utf-8") as f:
        entries = json.load(f)
    assert len(entries) == ENTRY_COUNT
    ids = {e["id"] for e in entries}
    assert len(ids) == ENTRY_COUNT, "duplicate NEGKB ids"
    required_fields = {"id", "ci_class", "failure_signature", "attempted_fix", "reason_failed", "source_incident_id"}
    assert all(required_fields.issubset(e.keys()) for e in entries)
    assert {e["ci_class"] for e in entries} == set(CI_TYPES), "not every CI type represented"
    print(f"\nSELF-TEST PASSED: {len(entries)} unique entries, all fields present, full CI-type coverage.")
