"""Unit tests for the closed-vocabulary voice intent parser. Covers all 6 supported intents plus
explicit rejection of out-of-vocabulary phrases (never a silent guess)."""
from intake.voice_intent import (
    INTENT_APPROVE,
    INTENT_REJECT,
    INTENT_SHOW_INCIDENT,
    INTENT_SHOW_OPEN_INCIDENTS,
    INTENT_START_SCENARIO,
    INTENT_UNRECOGNIZED,
    INTENT_WHAT_CHANGED,
    parse_voice_intent,
)


def test_show_open_incidents():
    for phrase in ["show open incidents", "show p1s", "show p1 incidents", "show incidents"]:
        result = parse_voice_intent(phrase)
        assert result.intent == INTENT_SHOW_OPEN_INCIDENTS, phrase
        assert result.requires_human_confirmation is False


def test_show_incident_extracts_target_id():
    result = parse_voice_intent("show incident INC-0042")
    assert result.intent == INTENT_SHOW_INCIDENT
    assert result.params["target_id"] == "INC-0042"
    assert result.requires_human_confirmation is False


def test_approve_extracts_target_id_and_requires_confirmation():
    result = parse_voice_intent("approve INC-0042")
    assert result.intent == INTENT_APPROVE
    assert result.params["target_id"] == "INC-0042"
    assert result.requires_human_confirmation is True


def test_reject_extracts_target_id_and_reason():
    result = parse_voice_intent("reject INC-0042 with reason insufficient evidence")
    assert result.intent == INTENT_REJECT
    assert result.params["target_id"] == "INC-0042"
    assert result.params["reason"] == "insufficient evidence"
    assert result.requires_human_confirmation is True


def test_what_changed_on_ci_extracts_ci_id():
    result = parse_voice_intent("what changed on CI CI-0087")
    assert result.intent == INTENT_WHAT_CHANGED
    assert result.params["ci_id"] == "CI-0087"


def test_start_scenario_extracts_scenario_name():
    result = parse_voice_intent("start scenario alert storm")
    assert result.intent == INTENT_START_SCENARIO
    assert result.params["scenario_name"] == "alert storm"
    assert result.requires_human_confirmation is True


def test_out_of_vocabulary_phrase_is_unrecognized_not_guessed():
    result = parse_voice_intent("please restart the database server right now")
    assert result.intent == INTENT_UNRECOGNIZED
    assert result.params == {}
    assert result.requires_human_confirmation is True


def test_near_miss_phrase_does_not_silently_match_wrong_intent():
    # "approve" without a target must NOT fuzzy-match INTENT_APPROVE.
    result = parse_voice_intent("approve")
    assert result.intent == INTENT_UNRECOGNIZED


def test_misheard_fragment_does_not_trigger_approval():
    # A plausible ASR misfire near "approve" but not an exact closed-vocabulary match.
    result = parse_voice_intent("a prove it")
    assert result.intent == INTENT_UNRECOGNIZED
    assert result.requires_human_confirmation is True


def test_case_insensitive_matching():
    result = parse_voice_intent("APPROVE inc-0042")
    assert result.intent == INTENT_APPROVE
    assert result.params["target_id"] == "inc-0042"


def test_extra_whitespace_is_tolerated():
    result = parse_voice_intent("  show   incident   INC-0042  ")
    assert result.intent == INTENT_SHOW_INCIDENT
    assert result.params["target_id"] == "INC-0042"
