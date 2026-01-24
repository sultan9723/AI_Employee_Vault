"""
Decision Resolver Agent
Translates decision artifacts into safe filesystem state transitions.
Part of the AI Employee system - bridge between reasoning and execution.

This agent does NOT reason and does NOT execute external actions.
It only applies explicit, pre-authorized state transitions.
"""

import json
import shutil
import logging
from pathlib import Path


# Configuration
BASE_DIR = Path(__file__).parent.parent
DECISIONS_DIR = BASE_DIR / "Decisions"
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
APPROVALS_DIR = BASE_DIR / "Approvals"
APPROVED_DIR = BASE_DIR / "Approved"
FAILED_DIR = BASE_DIR / "Failed"
LOG_FILE = BASE_DIR / "Logs" / "decision_resolver.log"

# Supported decision states
DECISION_NEEDS_INPUT = "NEEDS_INPUT"
DECISION_READY_FOR_APPROVAL = "READY_FOR_APPROVAL"
DECISION_READY_FOR_EXECUTION = "READY_FOR_EXECUTION"
DECISION_BLOCKED = "BLOCKED"

VALID_DECISIONS = {
    DECISION_NEEDS_INPUT,
    DECISION_READY_FOR_APPROVAL,
    DECISION_READY_FOR_EXECUTION,
    DECISION_BLOCKED,
}


def setup_logging() -> logging.Logger:
    """Configure and return the logger instance."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("decision_resolver")
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
    for directory in [DECISIONS_DIR, NEEDS_ACTION_DIR, APPROVALS_DIR, APPROVED_DIR, FAILED_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def load_decision_file(decision_path: Path, logger: logging.Logger) -> dict:
    """
    Load and parse a decision JSON file.
    Returns the parsed dict or None if invalid.
    """
    try:
        content = decision_path.read_text(encoding="utf-8")
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"INVALID JSON: {decision_path.name} - {e}")
        return None
    except Exception as e:
        logger.error(f"READ FAILED: {decision_path.name} - {e}")
        return None


def validate_decision(decision: dict, logger: logging.Logger) -> bool:
    """
    Validate that a decision dict has required fields.
    Returns True if valid, False otherwise.
    """
    required_fields = ["task_name", "decision"]
    
    for field in required_fields:
        if field not in decision:
            logger.error(f"INVALID DECISION: missing required field '{field}'")
            return False
    
    if decision["decision"] not in VALID_DECISIONS:
        logger.error(f"INVALID DECISION: unknown decision state '{decision['decision']}'")
        return False
    
    return True


def find_task_file(task_name: str) -> Path:
    """Find the task file in Needs_Action directory."""
    # Try common extensions
    for ext in [".md", ".txt", ""]:
        task_path = NEEDS_ACTION_DIR / f"{task_name}{ext}"
        if task_path.exists():
            return task_path
    
    # Fallback: search for any file starting with task_name
    for file_path in NEEDS_ACTION_DIR.iterdir():
        if file_path.stem == task_name:
            return file_path
    
    return None


def move_task(task_path: Path, destination_dir: Path, logger: logging.Logger) -> bool:
    """
    Move a task file to the destination directory.
    Returns True if successful, False otherwise.
    Never overwrites existing files.
    """
    if not task_path.exists():
        logger.warning(f"SKIPPED: Task file not found: {task_path.name}")
        return False
    
    destination = destination_dir / task_path.name
    
    # Never overwrite existing files
    if destination.exists():
        logger.warning(f"SKIPPED: {task_path.name} already exists in {destination_dir.name}/")
        return False
    
    try:
        shutil.move(str(task_path), str(destination))
        return True
    except Exception as e:
        logger.error(f"MOVE FAILED: Could not move {task_path.name}: {e}")
        return False


def process_decision(decision_path: Path, logger: logging.Logger) -> dict:
    """
    Process a single decision file and apply the appropriate state transition.
    Returns a status dictionary.
    """
    decision_filename = decision_path.name
    
    result = {
        "decision_file": decision_filename,
        "task_name": None,
        "decision": None,
        "action": None,
        "status": None,
    }
    
    # Load decision file
    decision = load_decision_file(decision_path, logger)
    if decision is None:
        result["status"] = "error"
        result["action"] = "could not load decision file"
        return result
    
    # Validate decision structure
    if not validate_decision(decision, logger):
        result["status"] = "error"
        result["action"] = "invalid decision format"
        return result
    
    task_name = decision["task_name"]
    decision_state = decision["decision"]
    
    result["task_name"] = task_name
    result["decision"] = decision_state
    
    logger.info(f"PROCESSING: {task_name} - decision: {decision_state}")
    
    # Apply decision based on state
    if decision_state == DECISION_NEEDS_INPUT:
        # Do nothing - wait for human input
        logger.info(f"WAITING: {task_name} needs human input")
        result["action"] = "no action (waiting for input)"
        result["status"] = "waiting"
        
    elif decision_state == DECISION_READY_FOR_APPROVAL:
        # Do nothing - wait for approval file
        logger.info(f"WAITING: {task_name} ready for approval")
        result["action"] = "no action (waiting for approval)"
        result["status"] = "waiting"
        
    elif decision_state == DECISION_READY_FOR_EXECUTION:
        # Check for human approval file first
        approval_path = APPROVALS_DIR / f"{task_name}.approved"
        
        if not approval_path.exists():
            # Human approval required but not present
            logger.info(f"WAITING: {task_name} missing human approval")
            result["action"] = "no action (missing human approval)"
            result["status"] = "waiting"
        else:
            # Approval exists - proceed with transition
            task_path = find_task_file(task_name)
            
            if task_path is None:
                logger.warning(f"NOT FOUND: {task_name} not in Needs_Action/")
                result["action"] = "task file not found"
                result["status"] = "skipped"
            elif move_task(task_path, APPROVED_DIR, logger):
                logger.info(f"APPROVED: {task_name} moved to Approved/")
                result["action"] = "moved to Approved/"
                result["status"] = "transitioned"
            else:
                result["action"] = "move failed"
                result["status"] = "error"
            
    elif decision_state == DECISION_BLOCKED:
        # Move task to Failed/
        task_path = find_task_file(task_name)
        
        if task_path is None:
            logger.warning(f"NOT FOUND: {task_name} not in Needs_Action/")
            result["action"] = "task file not found"
            result["status"] = "skipped"
        elif move_task(task_path, FAILED_DIR, logger):
            reason = decision.get("reason", "no reason provided")
            logger.info(f"BLOCKED: {task_name} moved to Failed/ - {reason}")
            result["action"] = f"moved to Failed/ ({reason})"
            result["status"] = "transitioned"
        else:
            result["action"] = "move failed"
            result["status"] = "error"
    
    return result


def run_decision_resolver():
    """Main function to process all decision files."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Decision Resolver Agent started")
    logger.info(f"Decisions: {DECISIONS_DIR}")
    logger.info(f"Needs_Action: {NEEDS_ACTION_DIR}")
    logger.info(f"Approved: {APPROVED_DIR}")
    logger.info(f"Failed: {FAILED_DIR}")
    logger.info("=" * 60)
    
    print("\n" + "=" * 50)
    print("🔀 Decision Resolver Agent")
    print("=" * 50 + "\n")
    
    # Ensure all directories exist
    try:
        ensure_directories()
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        print(f"❌ Failed to create directories: {e}")
        return
    
    # Find all decision files
    try:
        decision_files = list(DECISIONS_DIR.glob("*.decision.json"))
    except Exception as e:
        logger.error(f"Failed to scan Decisions directory: {e}")
        print(f"❌ Failed to scan directory: {e}")
        return
    
    if not decision_files:
        logger.info("No decision files found")
        print("📭 No decision files found in Decisions/")
        return
    
    logger.info(f"Found {len(decision_files)} decision file(s)")
    print(f"📋 Found {len(decision_files)} decision file(s)\n")
    
    # Process each decision file
    transitioned_count = 0
    waiting_count = 0
    skipped_count = 0
    error_count = 0
    
    for decision_path in sorted(decision_files):
        try:
            result = process_decision(decision_path, logger)
            
            task_display = result["task_name"] or decision_path.name
            
            if result["status"] == "transitioned":
                print(f"✅ {task_display}: {result['action']}")
                transitioned_count += 1
            elif result["status"] == "waiting":
                print(f"⏳ {task_display}: {result['action']}")
                waiting_count += 1
            elif result["status"] == "skipped":
                print(f"⏭️  {task_display}: {result['action']}")
                skipped_count += 1
            else:
                print(f"❌ {task_display}: {result['action']}")
                error_count += 1
                
        except Exception as e:
            logger.error(f"Exception processing {decision_path.name}: {e}")
            print(f"❌ ERROR: {decision_path.name} ({e})")
            error_count += 1
    
    # Summary
    print("\n" + "-" * 50)
    print(f"📊 Summary: {transitioned_count} transitioned, {waiting_count} waiting, {skipped_count} skipped, {error_count} errors")
    print("-" * 50 + "\n")
    
    logger.info(f"Decision Resolver completed: {transitioned_count} transitioned, {waiting_count} waiting, {skipped_count} skipped, {error_count} errors")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_decision_resolver()
