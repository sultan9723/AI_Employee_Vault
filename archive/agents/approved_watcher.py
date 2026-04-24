"""
Approved Watcher Agent
Moves approved tasks to the execution queue (In_Progress).
Part of the AI Employee system - execution handoff stage.
Guarantees: Every approved task reaches execution.
"""

import sys
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
    """Create all required directories if they don't exist.
    
    Raises:
        Exception: If directories cannot be created
    """
    for directory in [APPROVED_DIR, IN_PROGRESS_DIR]:
        try:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
            
            # Verify we can read/write to the directory
            if not directory.is_dir():
                raise Exception(f"{directory} exists but is not a directory")
                
        except Exception as e:
            raise Exception(f"Cannot access/create {directory}: {e}")


def get_task_name(filename: str) -> str:
    """Extract task name from filename (e.g., task_001.md → task_001)."""
    return Path(filename).stem


def move_to_in_progress(task_path: Path, logger: logging.Logger) -> bool:
    """
    Move a task file to the In_Progress directory.
    
    Args:
        task_path: Path to the task file in Approved/
        logger: Logger instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    task_filename = task_path.name
    task_name = get_task_name(task_filename)
    destination = IN_PROGRESS_DIR / task_filename
    
    # Never overwrite existing files
    if destination.exists():
        logger.warning(f"SKIP: {task_name} already exists in In_Progress/")
        return False
    
    try:
        # Perform the move
        shutil.move(str(task_path), str(destination))
        
        # Verify the file was actually moved
        if not destination.exists():
            logger.error(f"FAIL: {task_name} - Move appeared successful but file not found at destination")
            return False
        
        if task_path.exists():
            logger.error(f"FAIL: {task_name} - File still exists in Approved/ after move")
            return False
        
        logger.info(f"SUCCESS: {task_name} moved to In_Progress/")
        logger.info(f"Sent to execution: {task_filename}")
        return True
        
    except FileNotFoundError as e:
        logger.error(f"FAIL: {task_name} - File not found: {e}")
        return False
    except PermissionError as e:
        logger.error(f"FAIL: {task_name} - Permission denied: {e}")
        return False
    except Exception as e:
        logger.error(f"FAIL: {task_name} - Could not move: {e}")
        return False


def run_approved_watcher():
    """Main function to process all approved tasks for execution.
    
    Returns:
        bool: True if operation successful, False if errors occurred
    """
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
        logger.info("Directories verified")
    except Exception as e:
        logger.error(f"CRITICAL: Failed to create directories: {e}")
        print(f"❌ CRITICAL: Failed to create directories: {e}\n")
        return False
    
    # Find all .md files in Approved (ignore .gitkeep)
    try:
        task_files = [f for f in APPROVED_DIR.glob("*.md") if f.name != ".gitkeep"]
        task_files = sorted(task_files)
    except Exception as e:
        logger.error(f"CRITICAL: Failed to scan Approved directory: {e}")
        print(f"❌ CRITICAL: Failed to scan directory: {e}\n")
        return False
    
    # Log what we found
    if not task_files:
        logger.info("No approved tasks found in Approved/")
        print("📭 No approved tasks found in Approved/\n")
        print("=" * 50 + "\n")
        return True  # Success: nothing to do
    
    logger.info(f"Found {len(task_files)} approved task file(s)")
    print(f"📋 Found {len(task_files)} approved task file(s)\n")
    
    # Process each task file
    queued_count = 0
    skipped_count = 0
    failed_count = 0
    
    for task_path in task_files:
        task_name = get_task_name(task_path.name)
        
        try:
            # Check if already in In_Progress
            destination = IN_PROGRESS_DIR / task_path.name
            
            if destination.exists():
                # Already queued, skip
                print(f"⏭️  SKIP: {task_name} (already in In_Progress/)")
                logger.warning(f"SKIP: {task_name} already exists in In_Progress/")
                skipped_count += 1
            else:
                # Move to In_Progress
                if move_to_in_progress(task_path, logger):
                    print(f"⚡ QUEUED: {task_name} → In_Progress/")
                    queued_count += 1
                else:
                    print(f"❌ FAILED: {task_name} (move error)")
                    failed_count += 1
                    
        except Exception as e:
            logger.error(f"EXCEPTION: Processing {task_path.name}: {e}")
            print(f"❌ ERROR: {task_name} - {e}")
            failed_count += 1
    
    # Verify that files actually moved
    try:
        verify_moved = [f for f in IN_PROGRESS_DIR.glob("*.md") if f.name != ".gitkeep"]
        logger.info(f"Verification: {len(verify_moved)} tasks now in In_Progress/")
    except Exception as e:
        logger.warning(f"Could not verify: {e}")
    
    # Summary
    print("\n" + "-" * 50)
    print(f"📊 Summary")
    print(f"  Queued:  {queued_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Failed:  {failed_count}")
    print("-" * 50 + "\n")
    
    logger.info(f"Summary: {queued_count} queued, {skipped_count} skipped, {failed_count} failed")
    logger.info("=" * 60)
    
    # Return success only if no failures
    return failed_count == 0


if __name__ == "__main__":
    success = run_approved_watcher()
    sys.exit(0 if success else 1)
