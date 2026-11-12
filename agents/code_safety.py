"""Safety checks for code before any model sees it.

Two jobs:
1. Blank out secrets (API keys, tokens, private keys, passwords), so pasting a
   repo never leaks a credential to a model provider.
2. Spot prompt-injection phrases hidden in code or comments, so the dashboard
   can warn that a file tried to give the AI orders.

Both are pattern checks: they catch the common shapes, not every possible
secret. They are a safety net on top of "never commit secrets", not a
replacement for it.
"""

import re

REDACTED = "[REDACTED]"

# Well-known key formats. Each pattern matches the secret itself.
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}"),       # OpenAI / Anthropic
    re.compile(r"\bsk_[A-Za-z0-9]{32,}"),                         # ElevenLabs, Stripe-style
    re.compile(r"\bnvapi-[A-Za-z0-9_-]{20,}"),                     # NVIDIA
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}"),                        # Google
    re.compile(r"\b(?:ghp|gho|ghs|ghu|ghr)_[A-Za-z0-9]{36,}"),     # GitHub tokens
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),                  # AWS access key id
    re.compile(r"\bxox[abpors]-[A-Za-z0-9-]{10,}"),                # Slack
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),  # JWT
]

# NAME = "value" where the name sounds secret. Keeps the name, blanks the value.
ASSIGNMENT = re.compile(
    r"""(?ix)
    \b([A-Z0-9_]*(?:API_?KEY|SECRET|TOKEN|PASSWORD|PASSWD|PRIVATE_KEY|ACCESS_KEY)[A-Z0-9_]*)
    (\s*[:=]\s*)
    (["']?)([^\s"'#,;]{8,})(\3)
    """
)

# An unquoted value that is a CONSTANT, an attribute or a function call: a reference to
# where a secret is kept, not the secret itself. (A bare lowercase word still counts as a
# possible secret, e.g. PASSWORD=hunter2hunter2.)
CODE_REFERENCE = re.compile(
    r"(?:[A-Z][A-Z0-9_]*"                                    # a CONSTANT_NAME
    r"|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+(?:\(.*)?"  # settings.api_key, os.environ.get(
    r"|[A-Za-z_][A-Za-z0-9_]*\(.*"                            # get_secret(
    r")\)*"
)

INJECTION_PATTERNS = [
    ("ignore earlier instructions", re.compile(r"\b(?:ignore|disregard|forget)\b[^\n]{0,30}\b(?:previous|prior|above|earlier|all|your)\b[^\n]{0,20}\b(?:instructions|rules|prompts?)\b", re.I)),
    ("tries to change the AI's role", re.compile(r"\byou are now\b|\bact as (?:a|an|the)\b|\bnew instructions\s*:", re.I)),
    ("asks for the system prompt", re.compile(r"\b(?:reveal|print|show|repeat)\b[^\n]{0,30}\bsystem prompt\b", re.I)),
    ("fake chat markers", re.compile(r"<\|im_start\|>|<\|system\|>|\[INST\]|^\s*(?:system|assistant)\s*:", re.I | re.M)),
    ("asks the AI to send data out", re.compile(r"\b(?:send|post|upload|exfiltrate)\b[^\n]{0,40}\b(?:https?://|webhook|api key|secret|token)", re.I)),
]


def scrub_secrets(text: str) -> tuple[str, int]:
    """Return the text with secrets blanked out, and how many were found."""
    count = 0

    def blank(_m: re.Match) -> str:
        nonlocal count
        count += 1
        return REDACTED

    for pattern in SECRET_PATTERNS:
        text = pattern.sub(blank, text)

    def blank_value(m: re.Match) -> str:
        nonlocal count
        value, quoted = m.group(4), bool(m.group(3))
        if value == REDACTED:
            return m.group(0)
        if not quoted and CODE_REFERENCE.fullmatch(value):
            # `max_tokens=MAX_OUTPUT_TOKENS` or `token = os.environ.get(` names where a
            # secret is kept; it isn't the secret itself, so leave it readable.
            return m.group(0)
        count += 1
        return f"{m.group(1)}{m.group(2)}{m.group(3)}{REDACTED}{m.group(5)}"

    text = ASSIGNMENT.sub(blank_value, text)
    return text, count


def injection_flags(text: str) -> list[str]:
    """Names of the injection tricks found in the text (empty list = clean)."""
    return [name for name, pattern in INJECTION_PATTERNS if pattern.search(text)]
