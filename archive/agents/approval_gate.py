"""
Approval Gate Agent
Validates that tasks have a plan and auto-approves them by moving to Approved.
Part of the AI Employee system - hackathon-safe autonomous agent.
"""

import os
import shutil
import logging
from datetime import datetime
from pathlib import Path


# Configuration
BASE_DIR = Path(__file__).parent.parent
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
PLANS_DIR = BASE_DIR / "Plans"
PENDING_APPROVAL_DIR = BASE_DIR / "Pending_Approval"
APPROVED_DIR = BASE_DIR / "Approved"
LOG_FILE = BASE_DIR / "Logs" / "approval_gate.log"


def setup_logging() -> logging.Logger:
    """Configure and return the logger instance."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("approval_gate")
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate handlers
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


def ensure_directories():
    """Create all required directories if they don't exist."""
    for directory in [NEEDS_ACTION_DIR, PLANS_DIR, PENDING_APPROVAL_DIR, APPROVED_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def get_task_name(filename: str) -> str:
    """Extract task name from filename (e.g., task_001.md → task_001)."""
    return Path(filename).stem


def check_plan_exists(task_name: str) -> bool:
    """Check if a plan file exists for the given task."""
    plan_file = PLANS_DIR / f"{task_name}.plan.md"
    return plan_file.exists()


def move_task_to_approved(task_path: Path, logger: logging.Logger) -> bool:
    """
    Move a task file to the Approved directory.
    Returns True if successful, False otherwise.
    """
    task_filename = task_path.name
    destination = APPROVED_DIR / task_filename
    
    # Never overwrite existing files
    if destination.exists():
        logger.warning(f"SKIPPED: {task_filename} already exists in Approved/")
        return False
    
    try:
        shutil.move(str(task_path), str(destination))
        return True
    except Exception as e:
        logger.error(f"FAILED: Could not move {task_filename}: {e}")
        return False


def drain_pending_approval(logger: logging.Logger) -> int:
    """Move legacy Pending_Approval tasks directly into Approved."""
    moved_count = 0
    pending_files = sorted(PENDING_APPROVAL_DIR.glob("*.md"))

    for pending_task in pending_files:
        task_filename = pending_task.name
        destination = APPROVED_DIR / task_filename

        # If a name conflict exists, keep both files by adding a suffix.
        if destination.exists():
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            destination = APPROVED_DIR / f"{pending_task.stem}_auto_{timestamp}{pending_task.suffix}"

        try:
            shutil.move(str(pending_task), str(destination))
            moved_count += 1
            logger.info(f"Auto-approved: {destination.name}")
        except Exception as e:
            logger.error(f"FAILED: Could not auto-approve pending task {task_filename}: {e}")

    return moved_count


def process_task(task_path: Path, logger: logging.Logger) -> dict:
    """
    Process a single task file through the approval gate.
    Returns a status dictionary.
    """
    task_filename = task_path.name
    task_name = get_task_name(task_filename)
    
    result = {
        "task_name": task_name,
        "filename": task_filename,
        "status": None,
        "reason": None,
    }
    
    # Check for plan
    has_plan = check_plan_exists(task_name)
    
    # Determine status
    if not has_plan:
        result["status"] = "blocked"
        result["reason"] = "missing plan"
        logger.info(f"BLOCKED: {task_name} (missing plan)")

    else:
        # Plan exists - auto-approve and move directly to Approved
        if move_task_to_approved(task_path, logger):
            result["status"] = "approved"
            result["reason"] = "auto-approved and moved to Approved"
            logger.info(f"Auto-approved task: {task_name}")
        else:
            result["status"] = "error"
            result["reason"] = "move failed"
    
    return result


def run_approval_gate():
    """Main function to process all tasks through the approval gate."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Approval Gate Agent started")
    logger.info(f"Input: {NEEDS_ACTION_DIR}")
    logger.info(f"Plans: {PLANS_DIR}")
    logger.info(f"Legacy pending queue: {PENDING_APPROVAL_DIR}")
    logger.info(f"Output: {APPROVED_DIR}")
    logger.info("=" * 60)
    
    print("\n" + "=" * 50)
    print("🚦 Approval Gate Agent")
    print("=" * 50 + "\n")
    
    # Ensure all directories exist
    try:
        ensure_directories()
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        print(f"❌ Failed to create directories: {e}")
        return

    # Drain legacy pending queue so no tasks remain waiting for manual approval.
    moved_from_pending = drain_pending_approval(logger)
    if moved_from_pending:
        print(f"✅ Auto-approved {moved_from_pending} task(s) from Pending_Approval/")
    
    # Find all .md files in Needs_Action
    try:
        task_files = list(NEEDS_ACTION_DIR.glob("*.md"))
    except Exception as e:
        logger.error(f"Failed to scan Needs_Action directory: {e}")
        print(f"❌ Failed to scan directory: {e}")
        return
    
    if not task_files:
        logger.info("No task files found in Needs_Action directory")
        print("📭 No task files found in Needs_Action directory")
        return
    
    logger.info(f"Found {len(task_files)} task file(s) to process")
    print(f"📋 Found {len(task_files)} task file(s)\n")
    
    # Process each task file
    approved_count = 0
    blocked_count = 0
    error_count = 0
    
    for task_path in sorted(task_files):
        try:
            result = process_task(task_path, logger)
            
            # Display status
            if result["status"] == "approved":
                print(f"✅ APPROVED: {result['task_name']} → Approved/")
                approved_count += 1
            elif result["status"] == "blocked":
                print(f"🚫 BLOCKED: {result['task_name']} ({result['reason']})")
                blocked_count += 1
            else:
                print(f"❌ ERROR: {result['task_name']} ({result['reason']})")
                error_count += 1
                
        except Exception as e:
            logger.error(f"Exception processing {task_path.name}: {e}")
            print(f"❌ ERROR: {task_path.name} (exception: {e})")
            error_count += 1
    
    # Summary
    print("\n" + "-" * 50)
    print(f"📊 Summary: {approved_count} approved, {blocked_count} blocked, {error_count} errors")
    print("-" * 50 + "\n")
    
    logger.info(f"Approval Gate completed: {approved_count} approved, {blocked_count} blocked, {error_count} errors")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_approval_gate()
