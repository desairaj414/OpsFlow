"""Closed-vocabulary voice intent parser — NO LLM (domain-multimodal-intake.md, decisions-log.md:
"a misheard command reaching an approval action is unacceptable; command-scope + on-screen
confirmation is the safety choice"). Matches ONLY the 6 audited intents; anything else is
UNRECOGNIZED and flagged for human confirmation — never a silently-guessed best match.
Do not expand the intent list without the human's sign-off (domain-multimodal-intake.md).
"""
import re
from dataclasses import dataclass

INTENT_SHOW_OPEN_INCIDENTS = "show_open_incidents"
INTENT_SHOW_INCIDENT = "show_incident"
INTENT_APPROVE = "approve_x"
INTENT_REJECT = "reject_x"
INTENT_WHAT_CHANGED = "what_changed_on_ci"
INTENT_START_SCENARIO = "start_scenario"
INTENT_UNRECOGNIZED = "unrecognized"

# Side-effecting intents require on-screen confirmation before executing; read-only queries don't.
_REQUIRES_CONFIRMATION = {INTENT_APPROVE, INTENT_REJECT, INTENT_START_SCENARIO}

_ID_PATTERN = r"[A-Za-z]+-\d+|[\w-]+"

_PATTERNS: list[tuple[str, re.Pattern, tuple[str, ...]]] = [
    (INTENT_SHOW_OPEN_INCIDENTS, re.compile(r"^show\s+(open\s+)?(p1s?|p1\s+incidents|incidents)$", re.IGNORECASE), ()),
    (INTENT_SHOW_INCIDENT, re.compile(rf"^show\s+incident\s+({_ID_PATTERN})$", re.IGNORECASE), ("target_id",)),
    (INTENT_APPROVE, re.compile(rf"^approve\s+({_ID_PATTERN})$", re.IGNORECASE), ("target_id",)),
    (INTENT_REJECT, re.compile(rf"^reject\s+({_ID_PATTERN})\s+with\s+reason\s+(.+)$", re.IGNORECASE), ("target_id", "reason")),
    (INTENT_WHAT_CHANGED, re.compile(rf"^what\s+changed\s+on\s+ci\s+({_ID_PATTERN})$", re.IGNORECASE), ("ci_id",)),
    (INTENT_START_SCENARIO, re.compile(r"^start\s+scenario\s+(.+)$", re.IGNORECASE), ("scenario_name",)),
]


@dataclass
class ParsedIntent:
    intent: str
    params: dict
    requires_human_confirmation: bool
    raw_text: str


def parse_voice_intent(text: str) -> ParsedIntent:
    normalized = " ".join(text.strip().split())  # collapse whitespace, keep case for param extraction
    for intent, pattern, param_names in _PATTERNS:
        m = pattern.match(normalized)
        if m:
            params = dict(zip(param_names, m.groups()))
            return ParsedIntent(
                intent=intent, params=params,
                requires_human_confirmation=intent in _REQUIRES_CONFIRMATION,
                raw_text=text,
            )
    # No match: never guess. Flag for human confirmation, name nothing as the intent.
    return ParsedIntent(intent=INTENT_UNRECOGNIZED, params={}, requires_human_confirmation=True, raw_text=text)
