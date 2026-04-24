"""Simulated email action for the AI Email Agent."""

from __future__ import annotations


def send_email_simulated(message: str) -> tuple[str, bool]:
    """Simulate sending an email with the given message."""
    print("📧 Simulated email sent")
    print(f"Message: {message}")
    return "simulated", True
