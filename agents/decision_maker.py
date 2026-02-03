"""
Decision Maker Agent
Analyzes tasks and routes them to appropriate folders.
Part of the AI Employee system - the reasoning layer.

This agent THINKS and ROUTES task files based on analysis.
"""

import json
import shutil
import logging
from datetime import datetime, timezone
from pathlib import Path


# Configuration
BASE_DIR = Path(__file__).parent.parent
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
PLANS_DIR = BASE_DIR / "Plans"
PENDING_APPROVAL_DIR = BASE_DIR / "Pending_Approval"
APPROVED_DIR = BASE_DIR / "Approved"
LOG_FILE = BASE_DIR / "Logs" / "decision_maker.log"

# Valid decision states (canonical)
VALID_DECISIONS = {
    "NEEDS_INPUT",
    "READY_FOR_APPROVAL",
    "READY_FOR_EXECUTION",
    "BLOCKED",
}

# Valid next actions (canonical)
VALID_NEXT_ACTIONS = {
    "WAIT_FOR_HUMAN_INPUT",
    "WAIT_FOR_APPROVAL",
    "QUEUE_FOR_EXECUTION",
    "NONE",
}

# Decision to next action mapping
DECISION_TO_ACTION = {
    "NEEDS_INPUT": "WAIT_FOR_HUMAN_INPUT",
    "READY_FOR_APPROVAL": "WAIT_FOR_APPROVAL",
    "READY_FOR_EXECUTION": "QUEUE_FOR_EXECUTION",
    "BLOCKED": "NONE",
}


def setup_logging() -> logging.Logger:
    """Configure and return the logger instance."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("decision_maker")
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
    for directory in [NEEDS_ACTION_DIR, PLANS_DIR, PENDING_APPROVAL_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def get_task_name(filename: str) -> str:
    """Extract task name from filename (e.g., task_001.md → task_001)."""
    return Path(filename).stem


def load_file_content(file_path: Path, logger: logging.Logger) -> str:
    """Load and return file content, or empty string if not found."""
    try:
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
        return ""
    except Exception as e:
        logger.error(f"READ FAILED: {file_path} - {e}")
        return ""


def analyze_task(task_name: str, task_content: str, logger: logging.Logger) -> tuple:
    """
    Analyze a task and determine its decision state.
    Returns (decision, reason) tuple.
    
    This is deterministic rule-based logic. No LLM calls.
    """
    # Check if task content is empty or trivial
    content_stripped = task_content.strip()
    
    if not content_stripped:
        return "NEEDS_INPUT", "Task file is empty"
    
    if len(content_stripped) < 20:
        return "NEEDS_INPUT", "Task content too brief to be actionable"
    
    # Check for blocking keywords
    blocking_keywords = ["BLOCKED", "CANCELLED", "INVALID", "REJECTED"]
    content_upper = content_stripped.upper()
    
    for keyword in blocking_keywords:
        if keyword in content_upper:
            return "BLOCKED", f"Task contains blocking keyword: {keyword}"
    
    # Check if plan exists
    plan_path = PLANS_DIR / f"{task_name}.plan.md"
    has_plan = plan_path.exists() and plan_path.stat().st_size > 0
    
    # Check if approval exists (task was moved to Approved folder)
    approved_path = APPROVED_DIR / f"{task_name}.md"
    has_approval = approved_path.exists()
    
    # Decision logic based on state
    if has_plan and has_approval:
        return "READY_FOR_EXECUTION", "Task has plan and approval"
    
    if has_plan and not has_approval:
        return "READY_FOR_APPROVAL", "Task has plan, awaiting human approval"
    
    # Check if task appears complete enough for planning
    completeness_indicators = [
        "objective" in content_stripped.lower(),
        "goal" in content_stripped.lower(),
        "requirement" in content_stripped.lower(),
        "action" in content_stripped.lower(),
        "#" in content_stripped,  # Has markdown structure
        len(content_stripped) > 100,  # Substantial content
    ]
    
    if sum(completeness_indicators) >= 2:
        # Task seems ready but no plan yet - still needs plan generation
        return "READY_FOR_APPROVAL", "Task appears complete, awaiting plan and approval"
    
    # Default: needs more input
    return "NEEDS_INPUT", "Task requires additional details or clarification"


def create_decision(task_name: str, decision: str, reason: str) -> dict:
    """
    Create a canonical decision object.
    """
    if decision not in VALID_DECISIONS:
        raise ValueError(f"Invalid decision: {decision}")
    
    next_action = DECISION_TO_ACTION.get(decision, "NONE")
    
    return {
        "task_name": task_name,
        "decision": decision,
        "reason": reason,
        "next_action": next_action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def move_to_pending_approval(task_path: Path, logger: logging.Logger) -> bool:
    """
    Move a task file to Pending_Approval directory for human review.
    Never overwrites existing files.
    """
    destination = PENDING_APPROVAL_DIR / task_path.name
    
    # Never overwrite existing files
    if destination.exists():
        logger.info(f"SKIPPED: {task_path.name} already in Pending_Approval")
        return False
    
    try:
        shutil.move(str(task_path), str(destination))
        logger.info(f"MOVED: {task_path.name} → Pending_Approval/")
        return True
    except Exception as e:
        logger.error(f"MOVE FAILED: {task_path.name} - {e}")
        return False


def process_task(task_path: Path, logger: logging.Logger) -> dict:
    """
    Process a single task and route it appropriately.
    Returns a status dictionary.
    """
    task_filename = task_path.name
    task_name = get_task_name(task_filename)
    
    result = {
        "task_name": task_name,
        "filename": task_filename,
        "decision": None,
        "status": None,
    }
    
    # Check if already in Pending_Approval or Approved
    pending_path = PENDING_APPROVAL_DIR / task_filename
    approved_path = APPROVED_DIR / task_filename
    
    if pending_path.exists() or approved_path.exists():
        result["status"] = "skipped"
        result["decision"] = "already processed"
        return result
    
    # Load task content
    task_content = load_file_content(task_path, logger)
    
    # Analyze task and determine decision
    decision, reason = analyze_task(task_name, task_content, logger)
    
    # Route based on decision
    if decision == "READY_FOR_APPROVAL" or decision == "READY_FOR_EXECUTION":
        # Move to Pending_Approval for human review
        if move_to_pending_approval(task_path, logger):
            result["status"] = "pending_approval"
            result["decision"] = decision
        else:
            result["status"] = "error"
            result["decision"] = "move failed"
    else:
        # Keep in Needs_Action (needs more input or blocked)
        result["status"] = "waiting"
        result["decision"] = decision
        logger.info(f"WAITING: {task_name} - {reason}")
    
    return result


def run_decision_maker():
    """Main function to process all tasks and route them appropriately."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Decision Maker Agent started")
    logger.info(f"Input: {NEEDS_ACTION_DIR}")
    logger.info(f"Plans: {PLANS_DIR}")
    logger.info(f"Output: {PENDING_APPROVAL_DIR}")
    logger.info(f"Approved: {APPROVED_DIR}")
    logger.info("=" * 60)
    
    print("\n" + "=" * 50)
    print("🧠 Decision Maker Agent")
    print("=" * 50 + "\n")
    
    # Ensure all directories exist
    try:
        ensure_directories()
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        print(f"❌ Failed to create directories: {e}")
        return
    
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
    
    logger.info(f"Found {len(task_files)} task file(s)")
    print(f"📋 Found {len(task_files)} task file(s)\n")
    
    # Process each task file
    created_count = 0
    skipped_count = 0
    error_count = 0
    
    for task_path in sorted(task_files):
        try:
            result = process_task(task_path, logger)
            
            if result["status"] == "created":
                print(f"🧠 {result['task_name']}: {result['decision']}")
                created_count += 1
            elif result["status"] == "skipped":
                print(f"⏭️  {result['task_name']}: decision already exists")
                skipped_count += 1
            else:
                print(f"❌ {result['task_name']}: {result['decision']}")
                error_count += 1
                
        except Exception as e:
            logger.error(f"Exception processing {task_path.name}: {e}")
            print(f"❌ ERROR: {task_path.name} ({e})")
            error_count += 1
    
    # Summary
    print("\n" + "-" * 50)
    print(f"📊 Summary: {created_count} created, {skipped_count} skipped, {error_count} errors")
    print("-" * 50 + "\n")
    
    logger.info(f"Decision Maker completed: {created_count} created, {skipped_count} skipped, {error_count} errors")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_decision_maker()
