import re
from typing import Tuple, Optional

# Signatures for prompt injection, jailbreaking, and system extraction
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|directives|prompts)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(DAN|unrestricted|jailbroken|godmode|root)", re.IGNORECASE),
    re.compile(r"system\s+prompt\s*(leak|reveal|show|display|print)", re.IGNORECASE),
    re.compile(r"reveal\s+(your\s+)?(secret|internal|hidden)\s+(prompt|instructions|rules|api\s*key)", re.IGNORECASE),
    re.compile(r"what\s+(is|are)\s+your\s+(initial|system)\s+(prompt|instructions)", re.IGNORECASE),
    re.compile(r"<\s*script\b[^>]*>", re.IGNORECASE),
    re.compile(r"union\s+select\b", re.IGNORECASE),
    re.compile(r"drop\s+table\b", re.IGNORECASE),
    re.compile(r"(exec|eval|system)\s*\(", re.IGNORECASE),
    re.compile(r"base64\s+decode", re.IGNORECASE),
]

# Sensitive information exfiltration detection
DATA_LEAKAGE_PATTERNS = [
    re.compile(r"\b(password_hash|secret_key|jwt_secret|private_key)\b", re.IGNORECASE),
    re.compile(r"\b(admin_password|database_url)\b", re.IGNORECASE),
]

EDUCATIONAL_DISCLAIMER = (
    "DISCLAIMER: This analysis is provided for educational and illustrative purposes only. "
    "Calculations represent estimates based on assumed rates and parameters. It does not constitute "
    "fiduciary, tax, or legal financial advice. Consult a certified financial planner for individual advisory services."
)


def detect_prompt_injection(prompt: str) -> Tuple[bool, Optional[str]]:
    """Scan prompt for injection attempts, jailbreaks, or exfiltration patterns."""
    if not prompt:
        return False, None

    for pattern in INJECTION_PATTERNS:
        match = pattern.search(prompt)
        if match:
            return True, f"Security violation detected: prohibited injection pattern '{match.group(0)}'."

    for pattern in DATA_LEAKAGE_PATTERNS:
        match = pattern.search(prompt)
        if match:
            return True, f"Security violation detected: sensitive system keyword '{match.group(0)}'."

    return False, None


def sanitize_chat_input(prompt: str, max_length: int = 500) -> str:
    """Normalize and enforce length limits on chatbot user prompts."""
    if not prompt:
        return ""
    # Strip dangerous characters
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", prompt)
    return cleaned.strip()[:max_length]
