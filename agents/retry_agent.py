"""
Retry Agent
Performs policy-driven, human-authorized retries for failed tasks.
Part of the AI Employee system - controlled recovery layer.

This agent does NOT retry automatically.
It requires explicit human approval via .retry files.
"""

import json
import shutil
import logging
from datetime import datetime, timezone
from pathlib import Path


# Configuration
BASE_DIR = Path(__file__).parent.parent
FAILED_DIR = BASE_DIR / "Failed"
IN_PROGRESS_DIR = BASE_DIR / "In_Progress"
APPROVALS_DIR = BASE_DIR / "Approvals"
POLICIES_DIR = BASE_DIR / "Policies"
POLICY_FILE = POLICIES_DIR / "retry_policy.json"
LOG_FILE = BASE_DIR / "Logs" / "retry_agent.log"

# Default policy (used if policy file doesn't exist)
DEFAULT_POLICY = {
    "max_retries": 3,
    "enabled": True,
}


def setup_logging() -> logging.Logger:
    """Configure and return the logger instance."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("retry_agent")
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
    """Create required directories if missing."""
    for directory in [FAILED_DIR, IN_PROGRESS_DIR, APPROVALS_DIR, POLICIES_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def get_task_name(filename: str) -> str:
    """Extract task name from filename (e.g., task_100.md → task_100)."""
    return Path(filename).stem


def load_policy(logger: logging.Logger) -> dict:
    """
    Load retry policy from file.
    Returns default policy if file doesn't exist.
    """
    if not POLICY_FILE.exists():
        logger.info(f"Policy file not found, using defaults: max_retries={DEFAULT_POLICY['max_retries']}")
        return DEFAULT_POLICY.copy()
    
    try:
        content = POLICY_FILE.read_text(encoding="utf-8")
        policy = json.loads(content)
        logger.info(f"Loaded policy: max_retries={policy.get('max_retries', DEFAULT_POLICY['max_retries'])}")
        return policy
    except Exception as e:
        logger.error(f"Failed to load policy: {e}, using defaults")
        return DEFAULT_POLICY.copy()


def get_retry_count_file(task_name: str) -> Path:
    """Get the path to the retry count sidecar file."""
    return FAILED_DIR / f"{task_name}.retries.json"


def get_retry_count(task_name: str, logger: logging.Logger) -> int:
    """
    Get the current retry count for a task.
    Returns 0 if no retry file exists.
    """
    retry_file = get_retry_count_file(task_name)
    
    if not retry_file.exists():
        return 0
    
    try:
        content = retry_file.read_text(encoding="utf-8")
        data = json.loads(content)
        return data.get("retry_count", 0)
    except Exception as e:
        logger.error(f"Failed to read retry count for {task_name}: {e}")
        return 0


def increment_retry_count(task_name: str, logger: logging.Logger) -> bool:
    """
    Increment the retry count for a task.
    Creates the file if it doesn't exist.
    Returns True if successful.
    """
    retry_file = get_retry_count_file(task_name)
    current_count = get_retry_count(task_name, logger)
    
    data = {
        "task_name": task_name,
        "retry_count": current_count + 1,
        "last_retry": datetime.now(timezone.utc).isoformat(),
    }
    
    try:
        content = json.dumps(data, indent=2)
        retry_file.write_text(content, encoding="utf-8")
        logger.info(f"Retry count for {task_name}: {current_count} → {current_count + 1}")
        return True
    except Exception as e:
        logger.error(f"Failed to update retry count for {task_name}: {e}")
        return False


def has_retry_approval(task_name: str) -> bool:
    """Check if a retry approval file exists for the task."""
    approval_file = APPROVALS_DIR / f"{task_name}.retry"
    return approval_file.exists()


def move_to_in_progress(task_path: Path, logger: logging.Logger) -> bool:
    """
    Move a task file to In_Progress directory.
    Never overwrites existing files.
    Returns True if successful.
    """
    destination = IN_PROGRESS_DIR / task_path.name
    
    if destination.exists():
        logger.warning(f"SKIPPED: {task_path.name} already exists in In_Progress/")
        return False
    
    try:
        shutil.move(str(task_path), str(destination))
        return True
    except Exception as e:
        logger.error(f"MOVE FAILED: {task_path.name} - {e}")
        return False


def remove_retry_approval(task_name: str, logger: logging.Logger):
    """Remove the retry approval file after successful retry."""
    approval_file = APPROVALS_DIR / f"{task_name}.retry"
    
    try:
        if approval_file.exists():
            approval_file.unlink()
            logger.info(f"Removed retry approval: {task_name}.retry")
    except Exception as e:
        logger.warning(f"Failed to remove retry approval for {task_name}: {e}")


def process_failed_task(task_path: Path, policy: dict, logger: logging.Logger) -> dict:
    """
    Process a single failed task for potential retry.
    Returns a status dictionary.
    """
    task_filename = task_path.name
    task_name = get_task_name(task_filename)
    max_retries = policy.get("max_retries", DEFAULT_POLICY["max_retries"])
    
    result = {
        "task_name": task_name,
        "filename": task_filename,
        "action": None,
        "status": None,
    }
    
    # Check if retries are enabled
    if not policy.get("enabled", True):
        logger.info(f"SKIPPED: {task_name} - retries disabled by policy")
        result["action"] = "retries disabled"
        result["status"] = "skipped"
        return result
    
    # Check for retry approval
    if not has_retry_approval(task_name):
        logger.info(f"WAITING: {task_name} - no retry approval")
        result["action"] = "no retry approval"
        result["status"] = "waiting"
        return result
    
    # Check retry count
    current_count = get_retry_count(task_name, logger)
    
    if current_count >= max_retries:
        logger.warning(f"EXHAUSTED: {task_name} - max retries reached ({current_count}/{max_retries})")
        result["action"] = f"max retries exhausted ({current_count}/{max_retries})"
        result["status"] = "exhausted"
        return result
    
    # Attempt retry
    logger.info(f"RETRYING: {task_name} (attempt {current_count + 1}/{max_retries})")
    
    # Increment retry count first
    if not increment_retry_count(task_name, logger):
        result["action"] = "failed to update retry count"
        result["status"] = "error"
        return result
    
    # Move task to In_Progress
    if move_to_in_progress(task_path, logger):
        logger.info(f"RETRY QUEUED: {task_name} moved to In_Progress/")
        remove_retry_approval(task_name, logger)
        result["action"] = f"moved to In_Progress (attempt {current_count + 1})"
        result["status"] = "retried"
    else:
        result["action"] = "move failed"
        result["status"] = "error"
    
    return result


def run_retry_agent():
    """Main function to process failed tasks for retry."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Retry Agent started")
    logger.info(f"Failed: {FAILED_DIR}")
    logger.info(f"Policy: {POLICY_FILE}")
    logger.info(f"Output: {IN_PROGRESS_DIR}")
    logger.info("=" * 60)
    
    print("\n" + "=" * 50)
    print("🔄 Retry Agent - Controlled Recovery")
    print("=" * 50 + "\n")
    
    # Ensure directories exist
    try:
        ensure_directories()
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        print(f"❌ Failed to create directories: {e}")
        return
    
    # Load policy
    policy = load_policy(logger)
    
    # Find all task files in Failed (exclude .retries.json sidecar files)
    try:
        failed_tasks = [
            f for f in FAILED_DIR.iterdir()
            if f.is_file() and not f.name.endswith(".retries.json")
        ]
        failed_tasks = sorted(failed_tasks, key=lambda x: x.name)
    except Exception as e:
        logger.error(f"Failed to scan Failed directory: {e}")
        print(f"❌ Failed to scan directory: {e}")
        return
    
    if not failed_tasks:
        logger.info("No failed tasks found")
        print("📭 No failed tasks found in Failed/")
        return
    
    logger.info(f"Found {len(failed_tasks)} failed task(s)")
    print(f"📋 Found {len(failed_tasks)} failed task(s)\n")
    
    # Process each failed task
    retried_count = 0
    waiting_count = 0
    exhausted_count = 0
    error_count = 0
    
    for task_path in failed_tasks:
        try:
            result = process_failed_task(task_path, policy, logger)
            
            if result["status"] == "retried":
                print(f"🔄 RETRIED: {result['task_name']} → In_Progress/")
                retried_count += 1
            elif result["status"] == "waiting":
                print(f"⏳ WAITING: {result['task_name']} (needs .retry approval)")
                waiting_count += 1
            elif result["status"] == "exhausted":
                print(f"🚫 EXHAUSTED: {result['task_name']} ({result['action']})")
                exhausted_count += 1
            elif result["status"] == "skipped":
                print(f"⏭️  SKIPPED: {result['task_name']} ({result['action']})")
            else:
                print(f"❌ ERROR: {result['task_name']} ({result['action']})")
                error_count += 1
                
        except Exception as e:
            logger.error(f"Exception processing {task_path.name}: {e}")
            print(f"❌ ERROR: {task_path.name} ({e})")
            error_count += 1
    
    # Summary
    print("\n" + "-" * 50)
    print(f"📊 Summary: {retried_count} retried, {waiting_count} waiting, {exhausted_count} exhausted, {error_count} errors")
    print("-" * 50 + "\n")
    
    logger.info(f"Retry Agent completed: {retried_count} retried, {waiting_count} waiting, {exhausted_count} exhausted, {error_count} errors")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_retry_agent()
