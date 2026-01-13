import os
import shutil
from datetime import datetime

# Feature flag (AI OFF by default)
USE_AI_REASONING = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NEEDS_ACTION = os.path.join(BASE_DIR, "Needs_Action")
APPROVED = os.path.join(BASE_DIR, "Approved")
PENDING = os.path.join(BASE_DIR, "Pending_Approval")
LOG_FILE = os.path.join(BASE_DIR, "Logs", "activity.log")
REASONING_DIR = os.path.join(BASE_DIR, "Logs", "Reasoning")

os.makedirs(REASONING_DIR, exist_ok=True)


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


def decide_task_state(content: str) -> str:
    """
    Rule-based decision logic (Iteration 2).
    Returns: NEEDS_ACTION | APPROVED | PENDING
    """

    if content.strip() == "":
        return "NEEDS_ACTION"

    if "APPROVE" in content.upper():
        return "APPROVED"

    return "PENDING"


def decide_task_state_ai(content: str) -> str:
    """
    AI-assisted decision stub (Iteration 3).
    Will call OpenAI in a later iteration.
    """
    # Fallback to rule-based logic for now
    return decide_task_state(content)


def classify_tasks():
    for filename in os.listdir(NEEDS_ACTION):
        task_path = os.path.join(NEEDS_ACTION, filename)

        if not os.path.isfile(task_path):
            continue

        with open(task_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Safe decision switch
        if USE_AI_REASONING:
            decision = decide_task_state_ai(content)
        else:
            decision = decide_task_state(content)

        if decision == "NEEDS_ACTION":
            reason = "Task content was empty or missing required information."
            write_reasoning(filename, "NEEDS_ACTION", reason)
            log(f"Task {filename} missing info → staying in Needs_Action")
            continue

        if decision == "APPROVED":
            reason = "Task content contained an approval intent keyword."
            write_reasoning(filename, "APPROVED", reason)
            shutil.move(task_path, os.path.join(APPROVED, filename))
            log(f"Task {filename} → Approved")
        else:
            reason = "Task contained content but no explicit approval signal."
            write_reasoning(filename, "PENDING_APPROVAL", reason)
            shutil.move(task_path, os.path.join(PENDING, filename))
            log(f"Task {filename} → Pending_Approval")


if __name__ == "__main__":
    classify_tasks()
