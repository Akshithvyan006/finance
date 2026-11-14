import re
import html
from typing import Tuple, Optional

# Username: alphanumeric, underscores, hyphens, 3-30 chars
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,30}$")
# Email: standard pattern
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def sanitize_text(text: Optional[str], max_length: int = 1000) -> str:
    """Strip dangerous characters, HTML-encode, and truncate."""
    if not text:
        return ""
    # Strip leading/trailing whitespaces and control characters
    cleaned = "".join(ch for ch in text if ch.isprintable() or ch in ("\n", "\r", "\t"))
    # Escape HTML entities to prevent stored/reflected XSS
    cleaned = html.escape(cleaned.strip())
    return cleaned[:max_length]


def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """Validate username format and length."""
    if not username:
        return False, "Username is required."
    if not USERNAME_REGEX.match(username):
        return False, "Username must be 3-30 characters and contain only letters, numbers, underscores, and hyphens."
    return True, None


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """Validate email format and length."""
    if not email:
        return False, "Email is required."
    if len(email) > 120 or not EMAIL_REGEX.match(email):
        return False, "Invalid email address format."
    return True, None


def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """Enforce NIST-aligned strong password policy."""
    if not password or len(password) < 10:
        return False, "Password must be at least 10 characters long."
    if len(password) > 128:
        return False, "Password must not exceed 128 characters."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_]", password):
        return False, "Password must contain at least one special character."
    return True, None


def validate_numeric_range(
    value,
    min_val: float,
    max_val: float,
    field_name: str
) -> Tuple[bool, Optional[float], Optional[str]]:
    """Validate that a value can be converted to float and lies within [min_val, max_val]."""
    try:
        val = float(value)
    except (ValueError, TypeError):
        return False, None, f"'{field_name}' must be a valid numeric value."

    if val < min_val or val > max_val:
        return False, None, f"'{field_name}' must be between {min_val:g} and {max_val:g}."

    return True, val, None
