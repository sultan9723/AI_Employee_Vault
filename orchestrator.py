"""
AI Employee Orchestrator v2
Master process that coordinates all agents in the correct sequence.
Runs the full perception → reasoning → action pipeline.

Improvements over v1:
- Email dispatcher added to pipeline
- Dashboard.md auto-updated after every cycle
- Graceful shutdown handling
- Cycle stats tracking
- New task detection logging
- Environment variable support
"""

import os
import sys
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "Logs"
LOG_FILE = LOGS_DIR / "orchestrator.log"
DASHBOARD_FILE = BASE_DIR / "Dashboard.md"
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
PENDING_APPROVAL_DIR = BASE_DIR / "Pending_Approval"
STATUS_FILE = BASE_DIR / "Status" / "status_snapshot.json"

CYCLE_INTERVAL_SECONDS = int(os.getenv("CYCLE_INTERVAL_SECONDS", "30"))
AGENT_TIMEOUT_SECONDS = 60

# Agent pipeline (in execution order)
AGENT_PIPELINE = [
    ("planner",             "agents/planner.py"),
    ("decision_maker",      "agents/decision_maker.py"),
    ("approval_gate",       "agents/approval_gate.py"),
    ("approved_watcher",    "agents/approved_watcher.py"),
    ("email_dispatcher",    "agents/email_dispatcher.py"),
    ("webhook_dispatcher",  "agents/webhook_dispatcher.py"),
    ("status_snapshot",     "agents/status_snapshot.py"),
]


# ── Logging ───────────────────────────────────────────────────────────────────
def setup_logging() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("orchestrator")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


# ── Agent Runner ──────────────────────────────────────────────────────────────
def run_agent(agent_name: str, agent_path: str, logger: logging.Logger) -> bool:
    full_path = BASE_DIR / agent_path
    if not full_path.exists():
        logger.warning(f"SKIP: {agent_name} — file not found: {agent_path}")
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(full_path)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=AGENT_TIMEOUT_SECONDS
        )
        if result.returncode == 0:
            logger.info(f"✔ {agent_name} completed")
            return True
        else:
            logger.error(f"✖ {agent_name} failed: {result.stderr[:300]}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"✖ {agent_name} timed out after {AGENT_TIMEOUT_SECONDS}s")
        return False
    except Exception as e:
        logger.error(f"✖ {agent_name} error: {e}")
        return False


def run_pipeline(logger: logging.Logger) -> dict:
    results = {"success": 0, "failed": 0}
    for agent_name, agent_path in AGENT_PIPELINE:
        success = run_agent(agent_name, agent_path, logger)
        if success:
            results["success"] += 1
        else:
            results["failed"] += 1
    return results


# ── Dashboard Updater ─────────────────────────────────────────────────────────
def update_dashboard(cycle: int, results: dict, logger: logging.Logger):
    """Update Dashboard.md with current system status after every cycle."""
    try:
        needs_action = list(NEEDS_ACTION_DIR.glob("*.md")) if NEEDS_ACTION_DIR.exists() else []
        pending = list(PENDING_APPROVAL_DIR.glob("*.md")) if PENDING_APPROVAL_DIR.exists() else []

        # Filter out .gitkeep
        needs_action = [f for f in needs_action if f.name != ".gitkeep"]
        pending = [f for f in pending if f.name != ".gitkeep"]

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        dashboard = f"""# 🤖 AI Employee Dashboard

> Last updated: {now} | Cycle #{cycle}

## System Status
| Metric | Value |
|--------|-------|
| Status | 🟢 Running |
| Cycle | #{cycle} |
| Last Run | {now} |
| Agents OK | {results['success']}/{len(AGENT_PIPELINE)} |

## Task Queue
| Folder | Count |
|--------|-------|
| Needs Action | {len(needs_action)} |
| Pending Approval | {len(pending)} |

## Needs Action
{"".join(f"- {f.name}\\n" for f in needs_action) if needs_action else "- None"}

## Pending Approval
{"".join(f"- ⏳ {f.name}\\n" for f in pending) if pending else "- None"}

## How to Approve a Task
1. Open the task file in `Pending_Approval/`
2. Review the plan in `Plans/`
3. Copy the file to `Approved/` folder
4. Orchestrator will handle the rest automatically

---
*AI Employee v1.0 — Running autonomously*
"""
        DASHBOARD_FILE.write_text(dashboard, encoding="utf-8")
        logger.info("📊 Dashboard updated")
    except Exception as e:
        logger.error(f"Dashboard update failed: {e}")


# ── Main Loop ─────────────────────────────────────────────────────────────────
def main():
    logger = setup_logging()

    print("\n" + "=" * 60)
    print("🧠 AI EMPLOYEE ORCHESTRATOR v2")
    print("=" * 60)
    print(f"📁 Vault:    {BASE_DIR}")
    print(f"⏱️  Cycle:    Every {CYCLE_INTERVAL_SECONDS} seconds")
    print(f"🤖 Agents:   {len(AGENT_PIPELINE)}")
    print(f"📝 Log:      {LOG_FILE}")
    print("=" * 60)
    print("Press Ctrl+C to stop\n")

    logger.info("=" * 60)
    logger.info("AI Employee Orchestrator v2 started")
    logger.info(f"Pipeline: {len(AGENT_PIPELINE)} agents")
    logger.info(f"Cycle interval: {CYCLE_INTERVAL_SECONDS}s")
    logger.info("=" * 60)

    cycle_count = 0
    total_success = 0
    total_failed = 0

    while True:
        cycle_count += 1
        cycle_start = datetime.now()

        print(f"\n{'─'*60}")
        print(f"🔄 Cycle #{cycle_count} — {cycle_start.strftime('%H:%M:%S')}")
        print(f"{'─'*60}")
        logger.info(f"── Cycle {cycle_count} started ──")

        try:
            # Count tasks before cycle
            tasks_before = len(list(NEEDS_ACTION_DIR.glob("*.md"))) if NEEDS_ACTION_DIR.exists() else 0

            # Run all agents
            results = run_pipeline(logger)
            total_success += results["success"]
            total_failed += results["failed"]

            # Count tasks after cycle
            tasks_after = len(list(NEEDS_ACTION_DIR.glob("*.md"))) if NEEDS_ACTION_DIR.exists() else 0
            new_tasks = tasks_before - tasks_after

            # Update dashboard
            update_dashboard(cycle_count, results, logger)

            # Cycle summary
            duration = (datetime.now() - cycle_start).seconds
            print(f"\n✅ Cycle #{cycle_count} complete in {duration}s")
            print(f"   Agents: {results['success']} ok, {results['failed']} failed")
            if new_tasks > 0:
                print(f"   Tasks processed: {new_tasks}")

            logger.info(
                f"── Cycle {cycle_count} complete: "
                f"{results['success']} ok, {results['failed']} failed "
                f"({duration}s) ──"
            )

        except KeyboardInterrupt:
            print(f"\n\n{'='*60}")
            print("👋 Orchestrator stopped by user")
            print(f"   Total cycles: {cycle_count}")
            print(f"   Total agent runs: {total_success + total_failed}")
            print(f"   Success rate: {total_success}/{total_success+total_failed}")
            print(f"{'='*60}\n")
            logger.info(f"Orchestrator stopped. Cycles: {cycle_count}")
            break
        except Exception as e:
            logger.error(f"Pipeline error in cycle {cycle_count}: {e}")
            print(f"⚠️  Error in cycle {cycle_count}: {e}")

        # Wait for next cycle
        print(f"⏳ Next cycle in {CYCLE_INTERVAL_SECONDS}s...")
        time.sleep(CYCLE_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
