"""
AI Employee Orchestrator v3 (Optimized)
- Fast dev mode
- Smart sleep (no idle waste)
- Run-once mode
- Skip empty cycles
"""

import os
import sys
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# ── ENV SETUP ────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "Logs"
LOG_FILE = LOGS_DIR / "orchestrator.log"
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
PENDING_APPROVAL_DIR = BASE_DIR / "Pending_Approval"
DASHBOARD_FILE = BASE_DIR / "Dashboard.md"

# ⚡ CONFIG
CYCLE_INTERVAL_SECONDS = int(os.getenv("CYCLE_INTERVAL_SECONDS", "10"))
DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"
RUN_ONCE = "--once" in sys.argv
AGENT_TIMEOUT_SECONDS = 60

AGENT_PIPELINE = [
    ("planner", "agents/planner.py"),
    ("decision_maker", "agents/decision_maker.py"),
    ("approval_gate", "agents/approval_gate.py"),
    ("approved_watcher", "agents/approved_watcher.py"),
    ("linkedin_agent", "agents/linkedin_agent.py"),
    ("facebook_agent", "agents/facebook_agent.py"),
    ("odoo_agent", "agents/odoo_agent.py"),
    ("execution_handler", "agents/execution_handler.py"),
    ("email_dispatcher", "agents/email_dispatcher.py"),
    ("webhook_dispatcher", "agents/webhook_dispatcher.py"),
    ("status_snapshot", "agents/status_snapshot.py"),
]

# ── LOGGING ─────────────────────────────────────────────────
def setup_logging():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("orchestrator")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    ch = logging.StreamHandler()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )

    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ── AGENT RUNNER ─────────────────────────────────────────────
def run_agent(name, path, logger):
    full_path = BASE_DIR / path
    if not full_path.exists():
        logger.warning(f"SKIP: {name} not found")
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(full_path)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=AGENT_TIMEOUT_SECONDS
        )

        if result.returncode == 0:
            logger.info(f"✔ {name} completed")
            return True
        else:
            logger.error(f"✖ {name} failed: {result.stderr[:200]}")
            return False

    except Exception as e:
        logger.error(f"✖ {name} error: {e}")
        return False


def run_pipeline(logger):
    success, failed = 0, 0
    for name, path in AGENT_PIPELINE:
        if run_agent(name, path, logger):
            success += 1
        else:
            failed += 1
    return {"success": success, "failed": failed}


# ── DASHBOARD ───────────────────────────────────────────────
def update_dashboard(cycle, results):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    needs = list(NEEDS_ACTION_DIR.glob("*.md"))
    pending = list(PENDING_APPROVAL_DIR.glob("*.md"))

    needs = [f for f in needs if f.name != ".gitkeep"]
    pending = [f for f in pending if f.name != ".gitkeep"]

    DASHBOARD_FILE.write_text(f"""
# 🤖 AI Employee Dashboard

Last Updated: {now}

Cycle: {cycle}
Agents OK: {results['success']}/{len(AGENT_PIPELINE)}

Needs Action: {len(needs)}
Pending Approval: {len(pending)}
""", encoding="utf-8")


# ── MAIN LOOP ───────────────────────────────────────────────
def main():
    logger = setup_logging()

    print("\n🚀 AI EMPLOYEE ORCHESTRATOR v3")
    print(f"Cycle: {CYCLE_INTERVAL_SECONDS}s | DEV_MODE={DEV_MODE} | RUN_ONCE={RUN_ONCE}\n")

    cycle = 0

    while True:
        cycle += 1
        start = datetime.now()

        # 🔍 Check tasks
        tasks = list(NEEDS_ACTION_DIR.glob("*.md"))
        tasks = [f for f in tasks if f.name != ".gitkeep"]

        if not tasks:
            print("😴 No tasks found")

            if RUN_ONCE:
                break

            time.sleep(5)
            continue

        print(f"\n🔄 Cycle {cycle} | Tasks: {len(tasks)}")

        results = run_pipeline(logger)
        update_dashboard(cycle, results)

        duration = (datetime.now() - start).seconds

        print(f"✅ Done in {duration}s | {results['success']} ok / {results['failed']} failed")

        if RUN_ONCE:
            break

        # ⚡ Smart sleep
        if DEV_MODE:
            time.sleep(1)
        else:
            time.sleep(CYCLE_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()