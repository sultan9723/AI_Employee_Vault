"""
Decision Maker Agent
Analyzes tasks and routes them to appropriate folders.
Part of the AI Employee system - the reasoning layer.

FIX: result["status"] was checked for "created" but never set to "created".
     Now correctly checks for "pending_approval".
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

# Valid decision states
VALID_DECISIONS = {
    "NEEDS_INPUT",
    "READY_FOR_APPROVAL",
    "READY_FOR_EXECUTION",
    "BLOCKED",
}

DECISION_TO_ACTION = {
    "NEEDS_INPUT":          "WAIT_FOR_HUMAN_INPUT",
    "READY_FOR_APPROVAL":   "WAIT_FOR_APPROVAL",
    "READY_FOR_EXECUTION":  "QUEUE_FOR_EXECUTION",
    "BLOCKED":              "NONE",
}


def setup_logging() -> logging.Logger:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("decision_maker")
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


def ensure_directories():
    for directory in [NEEDS_ACTION_DIR, PLANS_DIR, PENDING_APPROVAL_DIR, APPROVED_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def get_task_name(filename: str) -> str:
    return Path(filename).stem


def load_file_content(file_path: Path, logger: logging.Logger) -> str:
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
    Deterministic rule-based logic — no LLM calls.
    """
    content_stripped = task_content.strip()

    if not content_stripped:
        return "NEEDS_INPUT", "Task file is empty"

    if len(content_stripped) < 20:
        return "NEEDS_INPUT", "Task content too brief to be actionable"

    # Check for blocking keywords
    content_upper = content_stripped.upper()
    for keyword in ["BLOCKED", "CANCELLED", "INVALID", "REJECTED"]:
        if keyword in content_upper:
            return "BLOCKED", f"Task contains blocking keyword: {keyword}"

    # Check if plan exists
    plan_path = PLANS_DIR / f"{task_name}.plan.md"
    has_plan = plan_path.exists() and plan_path.stat().st_size > 0

    # Check if approval exists
    approved_path = APPROVED_DIR / f"{task_name}.md"
    has_approval = approved_path.exists()

    if has_plan and has_approval:
        return "READY_FOR_EXECUTION", "Task has plan and approval"

    if has_plan and not has_approval:
        return "READY_FOR_APPROVAL", "Task has plan, awaiting human approval"

    # Check completeness indicators
    completeness_indicators = [
        "objective" in content_stripped.lower(),
        "goal" in content_stripped.lower(),
        "requirement" in content_stripped.lower(),
        "action" in content_stripped.lower(),
        "#" in content_stripped,
        len(content_stripped) > 100,
    ]

    if sum(completeness_indicators) >= 2:
        return "READY_FOR_APPROVAL", "Task appears complete, awaiting plan and approval"

    return "NEEDS_INPUT", "Task requires additional details or clarification"


def move_to_pending_approval(task_path: Path, logger: logging.Logger) -> bool:
    destination = PENDING_APPROVAL_DIR / task_path.name
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
    task_filename = task_path.name
    task_name = get_task_name(task_filename)

    result = {
        "task_name": task_name,
        "filename": task_filename,
        "decision": None,
        "status": None,
    }

    # Skip if already processed
    pending_path = PENDING_APPROVAL_DIR / task_filename
    approved_path = APPROVED_DIR / task_filename
    if pending_path.exists() or approved_path.exists():
        result["status"] = "skipped"
        result["decision"] = "already processed"
        return result

    task_content = load_file_content(task_path, logger)
    decision, reason = analyze_task(task_name, task_content, logger)

    if decision in ("READY_FOR_APPROVAL", "READY_FOR_EXECUTION"):
        if move_to_pending_approval(task_path, logger):
            result["status"] = "pending_approval"  # FIX: was never "created"
            result["decision"] = decision
        else:
            result["status"] = "skipped"
            result["decision"] = "already in pending"
    else:
        result["status"] = "waiting"
        result["decision"] = decision
        logger.info(f"WAITING: {task_name} - {reason}")

    return result


def run_decision_maker():
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("Decision Maker Agent started")
    logger.info("=" * 60)

    print("\n" + "=" * 50)
    print("🧠 Decision Maker Agent")
    print("=" * 50 + "\n")

    try:
        ensure_directories()
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        return

    try:
        task_files = list(NEEDS_ACTION_DIR.glob("*.md"))
    except Exception as e:
        logger.error(f"Failed to scan Needs_Action: {e}")
        return

    if not task_files:
        print("📭 No task files found in Needs_Action directory")
        return

    print(f"📋 Found {len(task_files)} task file(s)\n")

    routed_count  = 0
    skipped_count = 0
    waiting_count = 0
    error_count   = 0

    for task_path in sorted(task_files):
        try:
            result = process_task(task_path, logger)

            # FIX: check "pending_approval" not "created"
            if result["status"] == "pending_approval":
                print(f"➡️  {result['task_name']}: routed → Pending_Approval ({result['decision']})")
                routed_count += 1
            elif result["status"] == "skipped":
                print(f"⏭️  {result['task_name']}: already processed")
                skipped_count += 1
            elif result["status"] == "waiting":
                print(f"⏳ {result['task_name']}: waiting ({result['decision']})")
                waiting_count += 1
            else:
                print(f"❌ {result['task_name']}: {result['decision']}")
                error_count += 1

        except Exception as e:
            logger.error(f"Exception processing {task_path.name}: {e}")
            print(f"❌ ERROR: {task_path.name} ({e})")
            error_count += 1

    print("\n" + "-" * 50)
    print(
        f"📊 Summary: {routed_count} routed, "
        f"{skipped_count} skipped, "
        f"{waiting_count} waiting, "
        f"{error_count} errors"
    )
    print("-" * 50 + "\n")

    logger.info(
        f"Decision Maker completed: {routed_count} routed, "
        f"{skipped_count} skipped, {waiting_count} waiting, {error_count} errors"
    )


if __name__ == "__main__":
    run_decision_maker()