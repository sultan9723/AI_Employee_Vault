"""
Execution Handler Agent
Universal task executor for the AI Employee system.
Detects task type and routes to appropriate handler.
Part of the action layer - moves tasks from In_Progress → Done/Failed

Task Types:
- email: Send via SMTP
- email_task: Email-style task with action field (webhook, email, etc)
- social: Post to LinkedIn, Facebook, etc (delegates to specific agents)
- generic: Log completion and move to Done

Minimal approach: No complex routing, just detect and execute.
"""

import os
import re
import json
import shutil
import logging
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Try to import requests for webhook execution
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Configuration
BASE_DIR = Path(__file__).parent.parent
IN_PROGRESS_DIR = BASE_DIR / "In_Progress"
DONE_DIR = BASE_DIR / "Done"
FAILED_DIR = BASE_DIR / "Failed"
PLANS_DIR = BASE_DIR / "Plans"
LOG_FILE = BASE_DIR / "Logs" / "execution_handler.log"
MAX_RETRIES = 3
DEBUG_MODE = True


def debug_log(message: str) -> None:
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")


def setup_logging() -> logging.Logger:
    """Configure logging"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("execution_handler")
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


def detect_task_type(task_content: str, task_name: str) -> str:
    """
    Detect task type from content.
    Returns: 'email_task', 'email', 'social', 'generic'
    """
    lower_content = task_content.lower()
    
    # Email-task detection (FIXED)
    if re.search(r'type:\s*email_task', task_content, re.IGNORECASE):
        return 'email_task'
    
    # Email detection
    if 'email' in task_name.lower() or 'type:.*email' in lower_content:
        return 'email'
    
    if re.search(r'to:|recipient:|send.*email', lower_content):
        return 'email'
    
    # Social detection
    if any(x in lower_content for x in ['linkedin', 'facebook', 'twitter', 'instagram', 'social']):
        return 'social'
    
    if 'type:.*social' in lower_content or 'type:.*post' in lower_content:
        return 'social'
    
    # Default to generic (log only)
    return 'generic'


def extract_task_details(task_content: str) -> dict:
    """Extract key information from task file"""
    details = {
        'title': 'Untitled Task',
        'type': 'generic',
        'priority': 'normal',
        'recipient': None,
    }
    
    # Extract title (first # heading)
    title_match = re.search(r'^#\s+(.+)$', task_content, re.MULTILINE)
    if title_match:
        details['title'] = title_match.group(1).strip()
    
    # Extract recipient if email
    recipient_match = re.search(r'(?:to:|recipient:|email to:)\s*([^\n]+)', task_content, re.IGNORECASE)
    if recipient_match:
        details['recipient'] = recipient_match.group(1).strip()
    
    return details


def extract_email_task_metadata(task_content: str) -> dict:
    """
    Extract metadata from email_task frontmatter.
    Returns dict with: action, url, payload, intent, etc.
    """
    metadata = {
        'action': 'generic',  # Default action
        'url': None,
        'payload': None,
        'intent': None,
    }
    
    # Extract frontmatter (--- ... ---)
    match = re.search(r'^---\n(.*?)\n---', task_content, re.MULTILINE | re.DOTALL)
    if not match:
        return metadata
    
    fm_text = match.group(1)
    
    # Parse key: value pairs
    for line in fm_text.split('\n'):
        line = line.strip()
        if not line or ':' not in line:
            continue
        
        key, value = line.split(':', 1)
        key = key.strip().lower()
        value = value.strip()
        
        if key == 'action':
            metadata['action'] = value.lower()
        elif key == 'url':
            metadata['url'] = value
        elif key == 'intent':
            metadata['intent'] = value
        elif key == 'payload':
            # Try to parse as JSON
            try:
                metadata['payload'] = json.loads(value)
            except:
                metadata['payload'] = value
    
    # Extract intent from body if not in frontmatter
    if not metadata['intent']:
        # Look for "Intent:" or similar in body
        intent_match = re.search(r'(?:intent|goal):\s*([^\n]+)', task_content, re.IGNORECASE)
        if intent_match:
            metadata['intent'] = intent_match.group(1).strip()
    
    # Extract payload from JSON block if not in frontmatter
    if not metadata['payload']:
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', task_content, re.DOTALL)
        if json_match:
            try:
                metadata['payload'] = json.loads(json_match.group(1).strip())
            except:
                metadata['payload'] = json_match.group(1).strip()
    
    return metadata


def extract_retry_count(task_content: str) -> int:
    """Extract retry_count from frontmatter. Defaults to 0."""
    match = re.search(r'^---\n(.*?)\n---', task_content, re.MULTILINE | re.DOTALL)
    if not match:
        return 0

    retry_match = re.search(r'^\s*retry_count\s*:\s*(\d+)\s*$', match.group(1), re.MULTILINE | re.IGNORECASE)
    if not retry_match:
        return 0

    try:
        return int(retry_match.group(1))
    except ValueError:
        return 0


def set_retry_count(task_content: str, retry_count: int) -> str:
    """Upsert retry_count in markdown frontmatter."""
    frontmatter_match = re.search(r'^---\n(.*?)\n---\s*', task_content, re.MULTILINE | re.DOTALL)

    if frontmatter_match:
        frontmatter_body = frontmatter_match.group(1)
        if re.search(r'^\s*retry_count\s*:', frontmatter_body, re.MULTILINE | re.IGNORECASE):
            updated_frontmatter = re.sub(
                r'^\s*retry_count\s*:\s*\d+\s*$',
                f'retry_count: {retry_count}',
                frontmatter_body,
                flags=re.MULTILINE | re.IGNORECASE,
            )
        else:
            updated_frontmatter = frontmatter_body.rstrip() + f"\nretry_count: {retry_count}"

        start, end = frontmatter_match.span()
        return task_content[:start] + f"---\n{updated_frontmatter}\n---\n\n" + task_content[end:]

    # No frontmatter exists, create one.
    return f"---\nretry_count: {retry_count}\n---\n\n{task_content}"


def handle_execution_failure(task_file: Path, task_content: str, logger: logging.Logger) -> None:
    """Apply retry policy: keep in In_Progress until retries exceed MAX_RETRIES."""
    current_retry = extract_retry_count(task_content)
    next_retry = current_retry + 1

    logger.warning(f"Retry attempt {next_retry}")

    if next_retry > MAX_RETRIES:
        FAILED_DIR.mkdir(parents=True, exist_ok=True)
        dest_path = FAILED_DIR / task_file.name
        if dest_path.exists():
            suffix = datetime.now().strftime("%Y%m%d%H%M%S")
            dest_path = FAILED_DIR / f"{task_file.stem}_{suffix}{task_file.suffix}"
        shutil.move(str(task_file), str(dest_path))
        logger.error("Moved to Failed")
        return

    updated_content = set_retry_count(task_content, next_retry)
    task_file.write_text(updated_content, encoding="utf-8")


def execute_email_task(task_file: Path, task_content: str, logger: logging.Logger) -> bool:
    """
    Execute email task.
    Uses email dispatcher if credentials present, otherwise logs + skips.
    """
    logger.info(f"  Type: EMAIL")
    
    # Check if email dispatcher can run
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    sender_email = os.getenv("SMTP_USER")
    app_password = os.getenv("SMTP_PASSWORD")
    recipient_email = os.getenv("SMTP_RECIPIENT")
    
    if not all([smtp_host, sender_email, app_password, recipient_email]):
        logger.warning("  ⏭️  Email credentials not set, skipping (SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_RECIPIENT)")
        return True  # Don't fail, just skip
    
    try:
        import smtplib
        from email.message import EmailMessage
        
        details = extract_task_details(task_content)
        subject = f"AI Employee - {details['title']}"
        
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg.set_content(task_content)
        
        with smtplib.SMTP(smtp_host, int(smtp_port), timeout=10) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(msg)
        
        logger.info(f"  ✅ Email sent to {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Email failed: {e}")
        return False


def execute_email_task_action(task_file: Path, task_content: str, logger: logging.Logger) -> bool:
    """
    Execute email-style task with action routing.
    Parses email_task metadata and routes to appropriate handler.
    
    Supported actions:
    - webhook: Send HTTP POST with payload
    - email: Send via SMTP
    - generic: Log only
    """
    logger.info(f"  Type: EMAIL_TASK")
    
    # Extract metadata
    metadata = extract_email_task_metadata(task_content)
    action = metadata.get('action', 'generic').lower()
    debug_log(f"Action: {action}")
    
    logger.info(f"  Action: {action}")
    
    if action == 'webhook':
        return execute_email_task_webhook_action(task_file, metadata, task_content, logger)
    if action == 'email':
        return execute_email_task_email_action(task_file, metadata, task_content, logger)

    logger.warning(f"Unknown action: {action}")
    return False


def execute_email_task_webhook_action(task_file: Path, metadata: dict, task_content: str, logger: logging.Logger) -> bool:
    """
    Execute email_task with action: webhook
    Sends HTTP POST to the specified URL with payload.
    """
    try:
        from agents import webhook_dispatcher
    except Exception:
        import webhook_dispatcher

    debug_log("Passing to webhook_dispatcher for email_task")
    logger.info("Calling webhook_dispatcher for email_task")
    executed, success = webhook_dispatcher.execute_webhook(task_file, logger)
    if not executed:
        logger.warning("Unknown action: webhook")
        return False
    return success


def execute_email_task_email_action(task_file: Path, metadata: dict, task_content: str, logger: logging.Logger) -> bool:
    """
    Execute email_task with action: email
    Sends email via SMTP.
    """
    try:
        from agents import email_dispatcher
    except Exception:
        import email_dispatcher

    config = email_dispatcher.load_config(logger)
    if not config:
        smtp_host = os.getenv("SMTP_HOST")
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_recipient = os.getenv("SMTP_RECIPIENT")
        if not all([smtp_host, smtp_user, smtp_password, smtp_recipient]):
            logger.warning("  ⏭️  Email credentials not set, skipping email dispatch")
            return True
        config = {
            "smtp_host": smtp_host,
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "sender_email": smtp_user,
            "app_password": smtp_password,
            "recipient_email": smtp_recipient,
            "username": smtp_user,
        }

    return email_dispatcher.process_task(task_file, config, logger)


def execute_social_task(task_file: Path, task_content: str, logger: logging.Logger) -> bool:
    """
    Execute social media task.
    Delegates to LinkedIn/Facebook agents.
    For now, just logs completion (actual posting done by those agents).
    """
    logger.info(f"  Type: SOCIAL")
    
    details = extract_task_details(task_content)
    
    # Check what platform
    if 'linkedin' in task_content.lower():
        logger.info(f"  🔗 LinkedIn post: {details['title']}")
    elif 'facebook' in task_content.lower():
        logger.info(f"  📘 Facebook post: {details['title']}")
    else:
        logger.info(f"  📱 Social post: {details['title']}")
    
    # Social agents handle the actual posting
    # This execution handler just confirms receipt
    return True


def execute_generic_task(task_file: Path, task_content: str, logger: logging.Logger) -> bool:
    """
    Execute generic task.
    Just log completion - no external action needed.
    """
    logger.info(f"  Type: GENERIC")
    
    details = extract_task_details(task_content)
    logger.info(f"  ✅ Task complete: {details['title']}")
    
    return True


def execute_task(task_file: Path, logger: logging.Logger) -> bool:
    """
    Main execution function.
    Detects task type and routes to appropriate handler.
    Returns True if successful.
    """
    task_name = task_file.stem
    logger.info(f"\n📋 Executing: {task_name}")
    
    try:
        # Load task content
        task_content = task_file.read_text(encoding="utf-8")
        
        # Detect type
        task_type = detect_task_type(task_content, task_name)
        debug_log(f"Detected task type: {task_type}")

        if task_type == 'email_task':
            logger.info("Skipping execution_handler for email_task (handled by webhook_dispatcher)")
            return True
        
        # Route to handler
        success = False
        if task_type == 'email_task':
            logger.info("Routing email_task → webhook_dispatcher")
            return True
        elif task_type == 'email':
            success = execute_email_task(task_file, task_content, logger)
        elif task_type == 'social':
            success = execute_social_task(task_file, task_content, logger)
        else:
            success = execute_generic_task(task_file, task_content, logger)
        
        # File may already be moved by delegated dispatcher (e.g., email_dispatcher).
        if not task_file.exists():
            return success

        # Pass successful task to downstream dispatcher flow
        if success:
            logger.info("➡️ Passing task to webhook_dispatcher (not moving to Done)")
            return True

        handle_execution_failure(task_file, task_content, logger)
        return False
        
    except Exception as e:
        logger.error(f"  ❌ Execution error: {e}")
        if task_file.exists():
            try:
                current_content = task_file.read_text(encoding="utf-8")
            except Exception:
                current_content = ""
            handle_execution_failure(task_file, current_content, logger)
        return False


def run_execution_handler():
    """Main execution loop"""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Execution Handler started")
    logger.info("=" * 60)
    
    # Ensure directories exist
    for directory in [IN_PROGRESS_DIR, DONE_DIR, FAILED_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Get all tasks in In_Progress
    task_files = sorted([f for f in IN_PROGRESS_DIR.glob("*.md") if f.name != ".gitkeep"])
    
    if not task_files:
        logger.info("No tasks in In_Progress/ to execute")
        return
    
    logger.info(f"Found {len(task_files)} task(s) to execute\n")
    
    # Execute each task
    success_count = 0
    for task_file in task_files:
        if not task_file.exists():
            continue

        content = task_file.read_text(encoding="utf-8")
        if re.search(r"type:\s*email_task", content, re.IGNORECASE):
            logger.info("Routing email_task → webhook_dispatcher")
            script = BASE_DIR / "agents" / "webhook_dispatcher.py"
            subprocess.run([sys.executable, str(script)])
            continue

        if execute_task(task_file, logger):
            success_count += 1
    
    logger.info("\n" + "=" * 60)
    logger.info(f"Execution complete: {success_count}/{len(task_files)} succeeded")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_execution_handler()
