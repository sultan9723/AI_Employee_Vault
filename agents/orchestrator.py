"""
AI Employee Orchestrator
Master process that coordinates all agents in the correct sequence.
Runs the full perception → reasoning → action pipeline.
"""

import os
import sys
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "Logs"
LOG_FILE = LOGS_DIR / "orchestrator.log"

# Agent pipeline (in execution order)
AGENT_PIPELINE = [
    ("planner", "agents/planner.py"),           # Create plans for tasks
    ("decision_maker", "agents/decision_maker.py"),  # Route tasks to Pending_Approval
    ("approval_gate", "agents/approval_gate.py"),    # Check for approved tasks
    ("approved_watcher", "agents/approved_watcher.py"),  # Move approved → In_Progress
    ("webhook_dispatcher", "agents/webhook_dispatcher.py"),  # Execute via webhook
    ("status_snapshot", "agents/status_snapshot.py"),  # Update system status
]

# Timing
CYCLE_INTERVAL_SECONDS = 30
AGENT_TIMEOUT_SECONDS = 60


def setup_logging() -> logging.Logger:
    """Configure orchestrator logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("orchestrator")
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        return logger
    
    # File handler
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def run_agent(agent_name: str, agent_path: str, logger: logging.Logger) -> bool:
    """
    Run a single agent script.
    Returns True if successful, False otherwise.
    """
    full_path = BASE_DIR / agent_path
    
    if not full_path.exists():
        logger.warning(f"SKIP: {agent_name} - file not found: {agent_path}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(full_path)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=AGENT_TIMEOUT_SECONDS
        )
        
        if result.returncode == 0:
            logger.info(f"✔ {agent_name} completed")
            return True
        else:
            logger.error(f"✖ {agent_name} failed: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"✖ {agent_name} timed out after {AGENT_TIMEOUT_SECONDS}s")
        return False
    except Exception as e:
        logger.error(f"✖ {agent_name} error: {e}")
        return False


def run_pipeline(logger: logging.Logger) -> dict:
    """
    Run all agents in sequence.
    Returns summary of results.
    """
    results = {"success": 0, "failed": 0, "skipped": 0}
    
    for agent_name, agent_path in AGENT_PIPELINE:
        success = run_agent(agent_name, agent_path, logger)
        if success:
            results["success"] += 1
        else:
            results["failed"] += 1
    
    return results


def main():
    """Main orchestrator loop."""
    logger = setup_logging()
    
    print("\n" + "=" * 60)
    print("🧠 AI EMPLOYEE ORCHESTRATOR")
    print("=" * 60)
    print(f"📁 Vault: {BASE_DIR}")
    print(f"⏱️  Cycle: Every {CYCLE_INTERVAL_SECONDS} seconds")
    print(f"📝 Log: {LOG_FILE}")
    print("=" * 60 + "\n")
    
    logger.info("=" * 60)
    logger.info("Orchestrator started")
    logger.info(f"Pipeline: {len(AGENT_PIPELINE)} agents")
    logger.info("=" * 60)
    
    cycle_count = 0
    
    while True:
        cycle_count += 1
        logger.info(f"--- Cycle {cycle_count} started ---")
        
        try:
            results = run_pipeline(logger)
            logger.info(
                f"--- Cycle {cycle_count} complete: "
                f"{results['success']} ok, {results['failed']} failed ---"
            )
        except KeyboardInterrupt:
            logger.info("Orchestrator stopped by user")
            print("\n👋 Orchestrator stopped")
            break
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
        
        time.sleep(CYCLE_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()