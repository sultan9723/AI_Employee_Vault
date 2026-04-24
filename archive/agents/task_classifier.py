import os
import shutil
import requests
from datetime import datetime

# ==============================
# Feature flag (Silver control)
# ==============================
USE_AI_REASONING = False   # turn ON for Silver demo, OFF after

# ==============================
# Paths
# ==============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NEEDS_ACTION = os.path.join(BASE_DIR, "Needs_Action")
APPROVED = os.path.join(BASE_DIR, "Approved")
PENDING = os.path.join(BASE_DIR, "Pending_Approval")
LOG_FILE = os.path.join(BASE_DIR, "Logs", "activity.log")
REASONING_DIR = os.path.join(BASE_DIR, "Logs", "Reasoning")

os.makedirs(REASONING_DIR, exist_ok=True)

# ==============================
# DeepSeek config
# ==============================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


# ==============================
# Logging
# ==============================
def log(message: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {message}\n")
    print(message)


def write_reasoning(task_name: str, decision: str, reason: str):
    path = os.path.join(REASONING_DIR, f"{task_name}.reasoning.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Task Reasoning\n\n")
        f.write(f"**Task:** {task_name}\n\n")
        f.write(f"**Decision:** {decision}\n\n")
        f.write(f"**Reason:** {reason}\n")


# ==============================
# Bronze rules (SAFE FALLBACK)
# ==============================
def decide_task_state(content: str) -> str:
    if content.strip() == "":
        return "NEEDS_ACTION"
    if "APPROVE" in content.upper():
        return "APPROVED"
    return "PENDING"


# ==============================
# Silver AI reasoning (DeepSeek)
# ==============================
def decide_task_state_ai(content: str) -> str:
    if not DEEPSEEK_API_KEY:
        log("DeepSeek key missing → fallback to rules")
        return decide_task_state(content)

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": f"""
Classify the task below.

Respond with ONLY ONE word:
NEEDS_ACTION or PENDING

Task:
{content}
"""
            }
        ],
        "temperature": 0
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            DEEPSEEK_URL,
            json=payload,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()

        decision = response.json()["choices"][0]["message"]["content"].strip().upper()
        return decision if decision in ("NEEDS_ACTION", "PENDING") else "PENDING"

    except Exception as e:
        log(f"DeepSeek failed → fallback to rules: {e}")
        return decide_task_state(content)


# ==============================
# Main loop
# ==============================
def classify_tasks():
    for filename in os.listdir(NEEDS_ACTION):
        task_path = os.path.join(NEEDS_ACTION, filename)

        if not os.path.isfile(task_path):
            continue

        try:
            with open(task_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            log(f"Skipping non-text file: {filename}")
            continue

        if USE_AI_REASONING and content.strip() and "APPROVE" not in content.upper():
            decision = decide_task_state_ai(content)
        else:
            decision = decide_task_state(content)

        if decision == "NEEDS_ACTION":
            write_reasoning(filename, decision, "Missing or unclear information.")
            log(f"{filename} → Needs_Action")
            continue

        if decision == "APPROVED":
            write_reasoning(filename, decision, "Approval keyword detected.")
            shutil.move(task_path, os.path.join(APPROVED, filename))
            log(f"{filename} → Approved")
        else:
            write_reasoning(filename, decision, "Pending human approval.")
            shutil.move(task_path, os.path.join(PENDING, filename))
            log(f"{filename} → Pending_Approval")


if __name__ == "__main__":
    classify_tasks()
