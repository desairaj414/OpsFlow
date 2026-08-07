"""PII/secret scrubber — domain-privacy.md "Scrub-before-send at every model boundary". Two passes:
  1. Regex, for structured secrets/identifiers (emails, phones, employee IDs, connection strings,
     API keys, bearer tokens, private IPs, internal hostnames).
  2. Local SLM (Ollama), for free-text person names regex can't reliably catch — "highest-sensitivity
     content never leaves the machine" (arch-overview.md), a privacy *architecture* choice, not cost.
Reversible tokenisation: `svc-payments-prd` -> `[HOST_7]`, restorable for an authorised viewer,
never restored to a model. A separate prompt-injection FLAG (not a redaction) is raised for
adversarial input — containment is an architectural (typed-contract) concern downstream, this
module's job is only to surface the signal, not to claim it neutralises the attack by itself.
"""
import json
import os
import re
from dataclasses import dataclass, field

import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_NAME_MODEL = os.getenv("OLLAMA_NAME_MODEL", "llama-3.2-3b-it")

_REGEX_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    # (item_type, token_prefix, pattern) — order matters: longer/more-specific patterns first,
    # so e.g. a connection string is redacted whole before a bare IP pattern could partially match inside it.
    ("connection_string", "CONNSTR", re.compile(r"\b\w+://[\w.]+:[^@\s]+@[\w.]+:\d+/\w+\b")),
    ("api_key", "APIKEY", re.compile(r"\bsk-[A-Za-z0-9]{16,}\b")),
    ("bearer_token", "TOKEN", re.compile(r"\bBearer\s+[A-Za-z0-9]{20,}\b")),
    ("email", "EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("employee_id", "EMPID", re.compile(r"\bEMP-\d{4,6}\b")),
    ("private_ip", "IP", re.compile(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b")),
    ("hostname", "HOST", re.compile(r"\bsvc-[a-z0-9]+(?:-[a-z0-9]+)*\b")),
    ("phone", "PHONE", re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?:\s?x\d+)?")),
]

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(prior|previous)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+(developer|debug)\s+mode", re.IGNORECASE),
]


@dataclass
class ScrubResult:
    scrubbed_text: str
    token_map: dict[str, str] = field(default_factory=dict)  # token -> original value, never sent to a model
    detected_items: list[dict] = field(default_factory=list)  # [{item_type, token}]
    injection_suspected: bool = False
    slm_pass_ran: bool = False


def _next_token(token_map: dict[str, str], prefix: str) -> str:
    n = sum(1 for t in token_map if t.startswith(f"[{prefix}_")) + 1
    return f"[{prefix}_{n}]"


def _scrub_regex(text: str, token_map: dict[str, str], detected: list[dict]) -> str:
    for item_type, prefix, pattern in _REGEX_PATTERNS:
        def _replace(m: re.Match, item_type=item_type, prefix=prefix) -> str:
            token = _next_token(token_map, prefix)
            token_map[token] = m.group(0)
            detected.append({"item_type": item_type, "token": token})
            return token

        text = pattern.sub(_replace, text)
    return text


def _detect_injection(text: str) -> bool:
    return any(p.search(text) for p in _INJECTION_PATTERNS)


def _scrub_names_via_slm(text: str, token_map: dict[str, str], detected: list[dict]) -> tuple[str, bool]:
    """Local-only: calls Ollama on localhost, text never leaves the machine. Returns (text, ran)."""
    prompt = (
        "Extract every person's full name mentioned in the text below. "
        "Respond with ONLY a JSON array of the exact name strings as they appear, nothing else. "
        "If there are none, respond with [].\n\nText:\n" + text
    )
    try:
        resp = httpx.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={"model": OLLAMA_NAME_MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False},
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"].strip()
        if content.startswith("```"):
            content = content.strip("`").removeprefix("json").strip()
        names = json.loads(content)
        if not isinstance(names, list):
            return text, False
    except Exception:
        # Ollama unreachable/misbehaving: fail closed on this pass only — regex pass already ran,
        # caller sees slm_pass_ran=False and knows name coverage is not guaranteed for this call.
        return text, False

    for name in names:
        if not isinstance(name, str) or not name or name not in text:
            continue
        token = _next_token(token_map, "NAME")
        token_map[token] = name
        detected.append({"item_type": "person_name", "token": token})
        text = text.replace(name, token)
    return text, True


def scrub(text: str, use_slm: bool = True) -> ScrubResult:
    token_map: dict[str, str] = {}
    detected: list[dict] = []

    injection_suspected = _detect_injection(text)
    scrubbed = _scrub_regex(text, token_map, detected)

    slm_ran = False
    if use_slm:
        scrubbed, slm_ran = _scrub_names_via_slm(scrubbed, token_map, detected)

    return ScrubResult(
        scrubbed_text=scrubbed, token_map=token_map, detected_items=detected,
        injection_suspected=injection_suspected, slm_pass_ran=slm_ran,
    )


def restore_text(scrubbed_text: str, token_map: dict[str, str]) -> str:
    """For an authorised human viewer only — never call this to reconstruct text sent to a model."""
    restored = scrubbed_text
    for token, original in token_map.items():
        restored = restored.replace(token, original)
    return restored
