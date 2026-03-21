"""
Security validation for file uploads and input sanitization.

REQ-S01: Validate all file uploads for malicious content
REQ-S02: Enforce strict content-type validation
REQ-S03: Rate-limiting for file upload endpoints
"""

import re
import time
from collections import defaultdict

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB (REQ-T02)
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX = 10  # requests per window per IP (REQ-S03)

_ALLOWED_CONTENT_TYPES = {
    "text/plain",
    "application/json",
    "text/csv",
}

# In-memory rate limit store: {ip: [(timestamp, ...), ...]}
_rate_store: dict[str, list[float]] = defaultdict(list)

# Patterns that suggest malicious content in text deck files
_MALICIOUS_TEXT_PATTERNS = [
    re.compile(r"<script", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"\x00"),  # null bytes
]


def validate_file_upload(file_content: bytes, content_type: str) -> tuple[bool, str]:
    """
    REQ-S01: Validate uploaded file content for malicious payloads.

    Returns (is_valid, reason).
    """
    if not check_file_size(file_content):
        return False, f"File exceeds maximum size of {_MAX_FILE_SIZE // (1024*1024)}MB"

    if not validate_content_type(content_type):
        return False, f"Content type {content_type!r} is not allowed"

    # Scan text content for obvious malicious patterns
    try:
        text = file_content.decode("utf-8", errors="replace")
        for pattern in _MALICIOUS_TEXT_PATTERNS:
            if pattern.search(text):
                return False, "File content contains disallowed patterns"
    except Exception:
        return False, "Could not decode file content"

    return True, ""


def check_file_size(content: bytes) -> bool:
    """REQ-T02: Reject files larger than 10MB."""
    return len(content) <= _MAX_FILE_SIZE


def validate_content_type(content_type: str) -> bool:
    """REQ-S02: Enforce strict content-type validation."""
    # Strip parameters like "; charset=utf-8"
    base_type = content_type.split(";")[0].strip().lower()
    return base_type in _ALLOWED_CONTENT_TYPES


def sanitize_input(text: str) -> str:
    """Strip characters that could be used for injection attacks."""
    # Allow alphanumeric, spaces, hyphens, apostrophes, commas, slashes (card names)
    return re.sub(r"[^\w\s\-',./()&]", "", text)


def check_rate_limit(ip: str) -> tuple[bool, str]:
    """
    REQ-S03: Max 10 imports per minute per IP.

    Returns (allowed, reason). Cleans up expired entries on each check.
    """
    now = time.monotonic()
    window_start = now - _RATE_LIMIT_WINDOW

    # Remove expired timestamps
    _rate_store[ip] = [t for t in _rate_store[ip] if t > window_start]

    if len(_rate_store[ip]) >= _RATE_LIMIT_MAX:
        return False, f"Rate limit exceeded: max {_RATE_LIMIT_MAX} imports per minute"

    _rate_store[ip].append(now)
    return True, ""
