"""Simple AI Email -> Action MVP."""

from __future__ import annotations

import re
import sys
from datetime import datetime
from requests import post

URL = "https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21"


def clean_message(message: str) -> str:
    message = re.sub(r"^(Subject|Body):\s*", "", message, flags=re.I | re.M)
    message = re.sub(r"`{3,}.*?`{3,}", "", message, flags=re.S)
    message = re.sub(r"^#+\s*", "", message, flags=re.M)
    return re.sub(r"\s+", " ", message).strip()


def decide_action(message: str) -> str:
    lowered = message.lower()
    if any(word in lowered for word in ("alert", "notify", "system")):
        return "webhook"
    if any(word in lowered for word in ("reply", "email", "respond")):
        return "email"
    return "ignore"


def main() -> int:
    message = " ".join(sys.argv[1:]).strip()
    if not message:
        print("Usage: python run_ai_employee.py \"your message\"")
        return 1

    cleaned = clean_message(message)
    action = decide_action(cleaned)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "ignored"
    success = False
    execution = "ignored"

    if action == "webhook":
        response = post(URL, json={"message": cleaned}, timeout=15)
        status = str(response.status_code)
        success = response.status_code == 200
        execution = "webhook"
    elif action == "email":
        print("📧 Simulated email sent")
        print(f"Message: {cleaned}")
        status = "simulated"
        success = True
        execution = "email (simulated)"
    else:
        success = True

    print("====================================")
    print("🤖 AI EMPLOYEE EXECUTION")
    print("========================")
    print()
    print(f"🕒 Time: {timestamp}")
    print()
    print(f"📩 Input: {message}")
    print()
    print(f"🧠 Decision: {action}")
    print()
    print(f"⚡ Execution: {execution}")
    print()
    print("---")
    print()
    print("✅ Result:")
    print(f"Status: {status}")
    print(f"Success: {success}")
    print()
    print("====================================")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
