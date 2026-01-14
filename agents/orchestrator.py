import time
import subprocess
from datetime import datetime

def log(msg):
    print(f"[{datetime.now()}] {msg}")

log("🧠 AI Employee Orchestrator started")

while True:
    try:
        # Run classifier periodically
        subprocess.run(
            ["python", "agents/task_classifier.py"],
            check=True
        )
        log("✔ Task classification cycle complete")

    except Exception as e:
        log(f"❌ Orchestrator error: {e}")

    time.sleep(10)  # simple heartbeat
