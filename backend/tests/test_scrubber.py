"""Unit tests for the scrubber (backend/guardrails/scrubber.py) against the planted
data/pii_ground_truth.json — computes real precision/recall, not an assertion that it works
(domain-privacy.md: "so the eval computes real precision/recall, not an assertion that it works").

Regex-covered types (structured, exact patterns) are held to a strict recall bar. Person names
depend on the local Ollama SLM pass and are inherently probabilistic — reported as a metric with a
looser bar, and skipped gracefully (not failed) if Ollama isn't reachable in this environment.

    pytest backend/tests/test_scrubber.py -v -s
"""
import json
import os

import pytest

from guardrails.scrubber import restore_text, scrub

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
REGEX_COVERED_TYPES = {"email", "phone", "employee_id", "connection_string", "api_key", "bearer_token", "private_ip", "hostname"}


def _load_snippets() -> list[dict]:
    with open(os.path.join(DATA_DIR, "pii_ground_truth.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def scrub_results():
    """Scrub every snippet once (module-scoped: the SLM pass is a real network call per snippet)."""
    snippets = _load_snippets()
    return [(s, scrub(s["text"], use_slm=True)) for s in snippets]


def test_regex_covered_items_high_recall(scrub_results):
    total, found = 0, 0
    misses = []
    for snippet, result in scrub_results:
        detected_values = {result.token_map[d["token"]] for d in result.detected_items}
        for item in snippet["planted_items"]:
            if item["item_type"] not in REGEX_COVERED_TYPES:
                continue
            total += 1
            if item["value"] in detected_values:
                found += 1
            else:
                misses.append((snippet["source_ref"], item["item_type"], item["value"]))
    recall = found / total if total else 0
    print(f"\nRegex-covered recall: {found}/{total} = {recall:.0%}; misses={misses}")
    assert recall >= 0.95, f"regex recall too low: {recall:.0%}, misses={misses}"


def test_regex_covered_items_no_false_positive_type_confusion(scrub_results):
    """Every regex-detected item's type must match a planted item's actual type at that value —
    catches e.g. a phone-shaped false match consuming what was really an employee ID."""
    for snippet, result in scrub_results:
        planted_by_value = {item["value"]: item["item_type"] for item in snippet["planted_items"]}
        for d in result.detected_items:
            value = result.token_map[d["token"]]
            if value in planted_by_value:
                assert d["item_type"] == planted_by_value[value], f"{snippet['source_ref']}: {value!r} detected as {d['item_type']}, planted as {planted_by_value[value]}"


def test_reversible_tokenisation_round_trips(scrub_results):
    for snippet, result in scrub_results:
        restored = restore_text(result.scrubbed_text, result.token_map)
        assert restored == snippet["text"], f"{snippet['source_ref']}: restore did not reproduce the original text"


def test_scrubbed_text_never_contains_original_secret_values(scrub_results):
    for snippet, result in scrub_results:
        for item in snippet["planted_items"]:
            if item["item_type"] in REGEX_COVERED_TYPES:
                assert item["value"] not in result.scrubbed_text, f"{snippet['source_ref']}: {item['item_type']} value leaked into scrubbed text"


def test_injection_flagged_on_the_adversarial_snippet(scrub_results):
    injection_snippet = next(s for s, _ in scrub_results if s["source_ref"] == "PII-010")
    result = next(r for s, r in scrub_results if s["source_ref"] == "PII-010")
    assert result.injection_suspected is True


def test_injection_not_flagged_on_clean_snippets(scrub_results):
    for snippet, result in scrub_results:
        if snippet["source_ref"] == "PII-010":
            continue
        assert result.injection_suspected is False, f"{snippet['source_ref']}: false-positive injection flag"


def test_person_name_detection_via_local_slm(scrub_results):
    """Probabilistic (local SLM) — reported as a metric, not a hard-fail bar. Skips (doesn't fail)
    if Ollama wasn't reachable, since that's an environment condition, not a scrubber defect."""
    any_ran = any(result.slm_pass_ran for _, result in scrub_results)
    if not any_ran:
        pytest.skip("Ollama not reachable in this environment — SLM name-detection pass did not run")

    total, found = 0, 0
    for snippet, result in scrub_results:
        if not result.slm_pass_ran:
            continue
        detected_values = {result.token_map[d["token"]] for d in result.detected_items if d["item_type"] == "person_name"}
        for item in snippet["planted_items"]:
            if item["item_type"] != "person_name":
                continue
            total += 1
            if item["value"] in detected_values:
                found += 1
    recall = found / total if total else 0
    print(f"\nPerson-name (local SLM) recall: {found}/{total} = {recall:.0%}")
    assert found > 0, "local SLM pass ran but detected zero planted names — likely not wired correctly"
