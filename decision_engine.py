"""Decision logic for the AI Email Agent."""

from __future__ import annotations

import re


def clean_message(message: str) -> str:
    """Normalize user input into a clean single-line message."""
    text = re.sub(r"^(Subject|Body):\s*", "", message, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"`{3,}.*?`{3,}", "", text, flags=re.DOTALL)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    return re.sub(r"\s+", " ", text).strip()


def decide_action(message: str) -> str:
    """Choose action based on simple keyword rules."""
    lowered = message.lower()
    if any(k in lowered for k in ("alert", "notify", "system")):
        return "webhook"
    if any(k in lowered for k in ("reply", "email", "respond")):
        return "email"
    return "ignore"
