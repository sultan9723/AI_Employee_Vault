import os
import shutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NEEDS_ACTION = os.path.join(BASE_DIR, "Needs_Action")
APPROVED = os.path.join(BASE_DIR, "Approved")
PENDING = os.path.join(BASE_DIR, "Pending_Approval")
LOG_FILE = os.path.join(BASE_DIR, "Logs", "activity.log")

def log(message):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {message}\n")
    print(message)

def classify_tasks():
    for filename in os.listdir(NEEDS_ACTION):
        task_path = os.path.join(NEEDS_ACTION, filename)

        if not os.path.isfile(task_path):
            continue

        with open(task_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if content == "":
            log(f"Task {filename} missing info → staying in Needs_Action")
            continue

        if "APPROVE" in content.upper():
            shutil.move(task_path, os.path.join(APPROVED, filename))
            log(f"Task {filename} → Approved")
        else:
            shutil.move(task_path, os.path.join(PENDING, filename))
            log(f"Task {filename} → Pending_Approval")

if __name__ == "__main__":
    classify_tasks()
