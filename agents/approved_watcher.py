"""
Approved Watcher Agent
Moves approved tasks to the execution queue (In_Progress).
Part of the AI Employee system - execution handoff stage.
"""

import shutil
import logging
from datetime import datetime
from pathlib import Path


# Configuration
BASE_DIR = Path(__file__).parent.parent
APPROVED_DIR = BASE_DIR / "Approved"
IN_PROGRESS_DIR = BASE_DIR / "In_Progress"
LOG_FILE = BASE_DIR / "Logs" / "approved_watcher.log"


def setup_logging() -> logging.Logger:
    """Configure and return the logger instance."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("approved_watcher")
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
    for directory in [APPROVED_DIR, IN_PROGRESS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def get_task_name(filename: str) -> str:
    """Extract task name from filename (e.g., task_001.md → task_001)."""
    return Path(filename).stem


def move_to_in_progress(task_path: Path, logger: logging.Logger) -> bool:
    """
    Move a task file to the In_Progress directory.
    Returns True if successful, False otherwise.
    """
    task_filename = task_path.name
    task_name = get_task_name(task_filename)
    destination = IN_PROGRESS_DIR / task_filename
    
    # Never overwrite existing files
    if destination.exists():
        logger.warning(f"SKIPPED: {task_name} already exists in In_Progress/")
        return False
    
    try:
        shutil.move(str(task_path), str(destination))
        logger.info(f"EXECUTION QUEUED: {task_name}")
        return True
    except Exception as e:
        logger.error(f"FAILED: Could not move {task_name}: {e}")
        return False


def run_approved_watcher():
    """Main function to process all approved tasks for execution."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Approved Watcher Agent started")
    logger.info(f"Watch folder: {APPROVED_DIR}")
    logger.info(f"Output folder: {IN_PROGRESS_DIR}")
    logger.info("=" * 60)
    
    print("\n" + "=" * 50)
    print("⚡ Approved Watcher Agent - Execution Handoff")
    print("=" * 50 + "\n")
    
    # Ensure all directories exist
    try:
        ensure_directories()
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        print(f"❌ Failed to create directories: {e}")
        return
    
    # Find all .md files in Approved
    try:
        task_files = list(APPROVED_DIR.glob("*.md"))
    except Exception as e:
        logger.error(f"Failed to scan Approved directory: {e}")
        print(f"❌ Failed to scan directory: {e}")
        return
    
    if not task_files:
        logger.info("No approved tasks found")
        print("📭 No approved tasks found in Approved directory")
        return
    
    logger.info(f"Found {len(task_files)} approved task(s)")
    print(f"📋 Found {len(task_files)} approved task(s)\n")
    
    # Process each task file
    queued_count = 0
    skipped_count = 0
    error_count = 0
    
    for task_path in sorted(task_files):
        task_name = get_task_name(task_path.name)
        
        try:
            destination = IN_PROGRESS_DIR / task_path.name
            
            if destination.exists():
                print(f"⏭️  SKIPPED: {task_name} (already in queue)")
                skipped_count += 1
                logger.warning(f"SKIPPED: {task_name} already exists in In_Progress/")
            elif move_to_in_progress(task_path, logger):
                print(f"⚡ QUEUED: {task_name} → In_Progress/")
                queued_count += 1
            else:
                error_count += 1
                
        except Exception as e:
            logger.error(f"Exception processing {task_path.name}: {e}")
            print(f"❌ ERROR: {task_name} ({e})")
            error_count += 1
    
    # Summary
    print("\n" + "-" * 50)
    print(f"📊 Summary: {queued_count} queued, {skipped_count} skipped, {error_count} errors")
    print("-" * 50 + "\n")
    
    logger.info(f"Approved Watcher completed: {queued_count} queued, {skipped_count} skipped, {error_count} errors")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_approved_watcher()
