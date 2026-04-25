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
    if any(word in lowered for word in ("refund", "issue", "problem", "help", "support")):
        return "support"
    if any(word in lowered for word in ("alert", "notify", "system")):
        return "webhook"
    if any(word in lowered for word in ("reply", "email", "respond")):
        return "email"
    return "ignore"


def generate_support_response(message: str) -> str:
    lowered = message.lower()
    if "refund" in lowered:
        return "We understand your concern. Your refund request is being processed."
    if "problem" in lowered or "issue" in lowered:
        return "We're sorry for the inconvenience. Our team is looking into it."
    return "Thank you for reaching out. Our support team will assist you shortly."


def execute_task(message: str) -> dict:
    cleaned = clean_message(message)
    action = decide_action(cleaned)
    status = "ignored"
    success = False
    execution = "ignored"
    result_detail = ""

    if action == "support":
        result_detail = generate_support_response(cleaned)
        status = "handled"
        success = True
        execution = "support"
    elif action == "webhook":
        response = post(URL, json={"message": cleaned}, timeout=15)
        status = str(response.status_code)
        success = response.status_code == 200
        execution = "webhook"
        result_detail = f"Status code: {status}"
    elif action == "email":
        status = "simulated"
        success = True
        execution = "email (simulated)"
        result_detail = f"Simulated email sent for: {cleaned}"
    else:
        success = True
        result_detail = "No action taken"

    return {
        "action": action,
        "execution": execution,
        "status": status,
        "success": success,
        "result": result_detail,
        "cleaned_message": cleaned
    }


def main() -> int:
    message = " ".join(sys.argv[1:]).strip()
    if not message:
        print("Usage: python run_ai_employee.py \"your message\"")
        return 1

    res = execute_task(message)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if res["action"] == "support":
        print(f"Support Response: {res['result']}")
    elif res["action"] == "email":
        print("📧 Simulated email sent")
        print(f"Message: {res['cleaned_message']}")

    print("====================================")
    print("🤖 AI EMPLOYEE EXECUTION")
    print("========================")
    print()
    print(f"🕒 Time: {timestamp}")
    print()
    print(f"📩 Input: {message}")
    print()
    print(f"🧠 Decision: {res['action']}")
    print()
    print(f"⚡ Execution: {res['execution']}")
    print()
    print("---")
    print()
    print("✅ Result:")
    print(f"Status: {res['status']}")
    print(f"Success: {res['success']}")
    print()
    print("====================================")
    return 0 if res["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
