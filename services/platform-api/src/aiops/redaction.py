from __future__ import annotations

import re
from typing import Any, Dict, Tuple

SENSITIVE_KEYS = [
    "token",
    "secret",
    "password",
    "authorization",
    "bearer",
    "apikey",
    "kubeconfig",
]

TOKEN_PATTERN = re.compile(r"(bearer\s+[A-Za-z0-9\-_.]+|token=\S+|password=\S+)", re.IGNORECASE)


def _is_sensitive_key(key: str) -> bool:
    key_lower = key.lower()
    return any(token in key_lower for token in SENSITIVE_KEYS)


def redact_value(value: Any) -> Tuple[Any, int]:
    if isinstance(value, str):
        if TOKEN_PATTERN.search(value):
            return "[REDACTED]", 1
        return value, 0
    return value, 0


def _redact(payload: Any) -> Tuple[Any, int]:
    redacted_count = 0
    if isinstance(payload, dict):
        redacted = {}
        for key, value in payload.items():
            if _is_sensitive_key(key):
                redacted[key] = "[REDACTED]"
                redacted_count += 1
            else:
                new_value, count = _redact(value)
                redacted[key] = new_value
                redacted_count += count
        return redacted, redacted_count
    if isinstance(payload, list):
        items = []
        for item in payload:
            new_item, count = _redact(item)
            items.append(new_item)
            redacted_count += count
        return items, redacted_count
    value, count = redact_value(payload)
    return value, count


def redact_payload(payload: Any) -> Tuple[Any, Dict[str, int]]:
    redacted, count = _redact(payload)
    return redacted, {"redacted_fields": count}
