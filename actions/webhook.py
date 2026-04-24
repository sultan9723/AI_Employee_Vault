"""Webhook action for the AI Email Agent."""

from __future__ import annotations

import requests

WEBHOOK_URL = "https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21"


def send_webhook(message: str) -> tuple[str, bool]:
    """Send message to webhook and return status code and success flag."""
    response = requests.post(WEBHOOK_URL, json={"message": message}, timeout=15)
    status = str(response.status_code)
    return status, response.status_code == 200
