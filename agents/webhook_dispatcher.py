"""
Webhook Dispatcher Agent
Sends tasks to external webhook and handles response routing.
Part of the AI Employee system - action layer of Digital FTE.
"""

import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# Configuration
BASE_DIR = Path(__file__).parent.parent
IN_PROGRESS_DIR = BASE_DIR / "In_Progress"
PLANS_DIR = BASE_DIR / "Plans"
DONE_DIR = BASE_DIR / "Done"
FAILED_DIR = BASE_DIR / "Failed"
LOG_FILE = BASE_DIR / "Logs" / "webhook_dispatcher.log"

WEBHOOK_URL = "http://localhost:8000/webhook"
TIMEOUT_SECONDS = 30


def setup_logging() -> logging.Logger:
    """Configure and return the logger instance."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("webhook_dispatcher")
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
    for directory in [IN_PROGRESS_DIR, PLANS_DIR, DONE_DIR, FAILED_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def get_task_name(filename: str) -> str:
    """Extract task name from filename (e.g., task_001.md → task_001)."""
    return Path(filename).stem


def load_file_content(file_path: Path, logger: logging.Logger = None) -> str:
    """Load and return file content, or empty string if not found."""
    try:
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
        return ""
    except Exception as e:
        if logger:
            logger.error(f"READ FAILED: {file_path} - {e}")
        return ""


def build_payload(task_name: str, task_content: str, plan_content: str) -> dict:
    """Construct the JSON payload for the webhook."""
    return {
        "task_name": task_name,
        "task_content": task_content,
        "plan": plan_content,
        "timestamp": datetime.now().isoformat(),
    }


def send_webhook(payload: dict, logger: logging.Logger) -> tuple:
    """
    Send HTTP POST to webhook endpoint.
    Returns (success: bool, status_code: int, error_message: str).
    """
    try:
        data = json.dumps(payload).encode("utf-8")
        
        request = Request(
            WEBHOOK_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "WebhookDispatcher/1.0",
            },
            method="POST",
        )
        
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status_code = response.getcode()
            # Success if 2xx status code
            if 200 <= status_code < 300:
                return True, status_code, ""
            else:
                return False, status_code, f"Unexpected status: {status_code}"
                
    except HTTPError as e:
        return False, e.code, str(e.reason)
    except URLError as e:
        return False, 0, f"Connection error: {e.reason}"
    except Exception as e:
        return False, 0, f"Unexpected error: {e}"


def move_task(task_path: Path, destination_dir: Path, logger: logging.Logger) -> bool:
    """
    Move a task file to the destination directory.
    Returns True if successful, False otherwise.
    """
    task_filename = task_path.name
    destination = destination_dir / task_filename
    
    # Never overwrite existing files
    if destination.exists():
        logger.warning(f"SKIPPED: {task_filename} already exists in {destination_dir.name}/")
        return False
    
    try:
        shutil.move(str(task_path), str(destination))
        return True
    except Exception as e:
        logger.error(f"MOVE FAILED: Could not move {task_filename}: {e}")
        return False


def process_task(task_path: Path, logger: logging.Logger) -> dict:
    """
    Process a single task through the webhook dispatcher.
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
    
    # Load task content
    task_content = load_file_content(task_path, logger)
    if not task_content:
        result["status"] = "error"
        result["reason"] = "could not read task file"
        logger.error(f"ERROR: {task_name} - could not read task file")
        return result
    
    # Load plan content
    plan_path = PLANS_DIR / f"{task_name}.plan.md"
    plan_content = load_file_content(plan_path, logger)
    if not plan_path.exists() or not plan_content:
        logger.error(f"BLOCKED: {task_name} has no plan")
        move_task(task_path, FAILED_DIR, logger)
        result["status"] = "failed"
        result["reason"] = "missing plan"
        return result
    
    # Build payload
    payload = build_payload(task_name, task_content, plan_content)
    
    # Send webhook
    logger.info(f"SENDING: {task_name} to {WEBHOOK_URL}")
    success, status_code, error_msg = send_webhook(payload, logger)
    
    if success:
        # Move to Done
        if move_task(task_path, DONE_DIR, logger):
            result["status"] = "success"
            result["reason"] = f"status {status_code}"
            logger.info(f"SUCCESS: {task_name} sent to webhook")
        else:
            result["status"] = "error"
            result["reason"] = "webhook succeeded but move failed"
    else:
        # Move to Failed
        if move_task(task_path, FAILED_DIR, logger):
            result["status"] = "failed"
            result["reason"] = error_msg or f"status {status_code}"
            logger.error(f"FAILED: {task_name} webhook error {status_code}")
        else:
            result["status"] = "error"
            result["reason"] = "webhook failed and move also failed"
            logger.error(f"FAILED: {task_name} webhook error {status_code} (move also failed)")
    
    return result


def run_webhook_dispatcher():
    """Main function to process all in-progress tasks through webhooks."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Webhook Dispatcher Agent started")
    logger.info(f"Input: {IN_PROGRESS_DIR}")
    logger.info(f"Plans: {PLANS_DIR}")
    logger.info(f"Webhook: {WEBHOOK_URL}")
    logger.info(f"Done: {DONE_DIR}")
    logger.info(f"Failed: {FAILED_DIR}")
    logger.info("=" * 60)
    
    print("\n" + "=" * 50)
    print("🚀 Webhook Dispatcher Agent - Action Layer")
    print("=" * 50 + "\n")
    
    # Ensure all directories exist
    try:
        ensure_directories()
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        print(f"❌ Failed to create directories: {e}")
        return
    
    # Find all .md files in In_Progress
    try:
        task_files = list(IN_PROGRESS_DIR.glob("*.md"))
    except Exception as e:
        logger.error(f"Failed to scan In_Progress directory: {e}")
        print(f"❌ Failed to scan directory: {e}")
        return
    
    if not task_files:
        logger.info("No tasks found in In_Progress directory")
        print("📭 No tasks found in In_Progress directory")
        return
    
    logger.info(f"Found {len(task_files)} task(s) to dispatch")
    print(f"📋 Found {len(task_files)} task(s)\n")
    
    # Process each task file
    success_count = 0
    failed_count = 0
    error_count = 0
    
    for task_path in sorted(task_files):
        task_name = get_task_name(task_path.name)
        
        try:
            result = process_task(task_path, logger)
            
            if result["status"] == "success":
                print(f"✅ SUCCESS: {task_name} → Completed/")
                success_count += 1
            elif result["status"] == "failed":
                print(f"❌ FAILED: {task_name} → Failed/ ({result['reason']})")
                failed_count += 1
            else:
                print(f"⚠️  ERROR: {task_name} ({result['reason']})")
                error_count += 1
                
        except Exception as e:
            logger.error(f"Exception processing {task_path.name}: {e}")
            print(f"⚠️  ERROR: {task_name} (exception: {e})")
            error_count += 1
    
    # Summary
    print("\n" + "-" * 50)
    print(f"📊 Summary: {success_count} success, {failed_count} failed, {error_count} errors")
    print("-" * 50 + "\n")
    
    logger.info(f"Webhook Dispatcher completed: {success_count} success, {failed_count} failed, {error_count} errors")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_webhook_dispatcher()
