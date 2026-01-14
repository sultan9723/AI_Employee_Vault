import os
import time
import shutil
from datetime import datetime

# -------------------------------
# Base paths
# -------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INBOX = os.path.join(BASE_DIR, "Inbox")
NEEDS_ACTION = os.path.join(BASE_DIR, "Needs_Action")
LOGS_DIR = os.path.join(BASE_DIR, "Logs")
LOG_FILE = os.path.join(LOGS_DIR, "activity.log")

# Ensure required folders exist
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(NEEDS_ACTION, exist_ok=True)

# -------------------------------
# Logger
# -------------------------------
def log(message: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {message}\n")
    print(message)

# -------------------------------
# Watcher start
# -------------------------------
print("📡 File system watcher started. Monitoring Inbox...")

seen_files = set()

while True:
    try:
        current_files = set(os.listdir(INBOX))
    except FileNotFoundError:
        log("Inbox folder not found. Retrying...")
        time.sleep(2)
        continue

    new_files = current_files - seen_files

    for filename in new_files:
        src = os.path.join(INBOX, filename)

        if os.path.isfile(src):
            dst = os.path.join(NEEDS_ACTION, filename)
            shutil.move(src, dst)
            log(f"New task detected: {filename} -> moved to Needs_Action")

    seen_files = current_files
    time.sleep(2)
