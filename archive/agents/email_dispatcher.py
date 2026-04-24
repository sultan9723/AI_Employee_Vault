"""
Email Dispatcher Agent
Sends approved tasks via email as an external action.
Part of the AI Employee system - email action layer.
"""

import os
import re
import json
import shutil
import logging
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# Configuration
BASE_DIR = Path(__file__).parent.parent
IN_PROGRESS_DIR = BASE_DIR / "In_Progress"
PLANS_DIR = BASE_DIR / "Plans"
DONE_DIR = BASE_DIR / "Done"
FAILED_DIR = BASE_DIR / "Failed"
CONFIGS_DIR = BASE_DIR / "Configs"
CONFIG_FILE = CONFIGS_DIR / "email_config.json"
LOG_FILE = BASE_DIR / "Logs" / "email_dispatcher.log"


def setup_logging() -> logging.Logger:
    """Configure and return the logger instance."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("email_dispatcher")
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
    """Create all required directories if they don't exist."""
    for directory in [IN_PROGRESS_DIR, PLANS_DIR, DONE_DIR, FAILED_DIR, CONFIGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def load_config(logger: logging.Logger) -> dict:
    """Load email configuration from file."""
    if not CONFIG_FILE.exists():
        logger.error(f"Config file not found: {CONFIG_FILE}")
        return None
    
    try:
        content = CONFIG_FILE.read_text(encoding="utf-8")
        config = json.loads(content)
        
        required_fields = ["smtp_host", "smtp_port", "sender_email", "recipient_email", "app_password"]
        for field in required_fields:
            if field not in config:
                logger.error(f"Missing required config field: {field}")
                return None
        
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return None


def load_file_content(file_path: Path, logger: logging.Logger) -> str:
    """Load and return file content."""
    try:
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
        return ""
    except Exception as e:
        logger.error(f"READ FAILED: {file_path} - {e}")
        return ""


def extract_subject(task_content: str, plan_content: str, task_name: str) -> str:
    """Extract email subject from task or plan content."""
    heading_match = re.search(r'^#\s+(.+)$', task_content, re.MULTILINE)
    if heading_match:
        return f"AI Employee - {heading_match.group(1).strip()}"
    
    clean_name = task_name.replace('_', ' ').replace('task ', '').title()
    return f"AI Employee - Task Completed: {clean_name}"


def build_email_body(task_content: str, plan_content: str, task_name: str) -> str:
    """Construct a clean, professional email body."""
    timestamp = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    
    body = f"""AI Employee - Task Execution Report

Task Reference: {task_name}
Completed: {timestamp}

------------------------------------------------------------------------
TASK DETAILS
------------------------------------------------------------------------

{task_content.strip() if task_content else 'No task content available.'}

------------------------------------------------------------------------
EXECUTION PLAN
------------------------------------------------------------------------

{plan_content.strip() if plan_content else 'No execution plan was generated for this task.'}

------------------------------------------------------------------------

This is an automated message from your AI Employee system.
Do not reply directly to this email.
"""
    return body


def send_email(config: dict, subject: str, body: str, logger: logging.Logger) -> tuple:
    """Send email via SMTP. Returns (success, error_message)."""
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = config["sender_email"]
        msg["To"] = config["recipient_email"]
        msg.set_content(body)
        
        smtp_host = config["smtp_host"]
        smtp_port = config.get("smtp_port", 587)
        username = config.get("username", config["sender_email"])
        password = config["app_password"].replace(" ", "")  # Remove spaces from app password
        
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
        
        return True, ""
    
    except smtplib.SMTPAuthenticationError as e:
        return False, f"Authentication failed: {e}"
    except Exception as e:
        return False, f"Email failed: {e}"


def process_task(task_file: Path, config: dict, logger: logging.Logger) -> bool:
    """Process a single task file and send email."""
    task_name = task_file.stem
    logger.info(f"Processing: {task_name}")
    
    # Load content
    task_content = load_file_content(task_file, logger)
    plan_file = PLANS_DIR / f"{task_name}.plan.md"
    plan_content = load_file_content(plan_file, logger)
    
    # Build email
    subject = extract_subject(task_content, plan_content, task_name)
    body = build_email_body(task_content, plan_content, task_name)
    
    # Send email
    success, error = send_email(config, subject, body, logger)
    
    if success:
        logger.info(f"✔ Email sent for: {task_name}")
        # Move to Done
        dest = DONE_DIR / task_file.name
        shutil.move(str(task_file), str(dest))
        logger.info(f"  Moved to Done/")
        return True
    else:
        logger.error(f"✖ Email failed for {task_name}: {error}")
        # Move to Failed
        dest = FAILED_DIR / task_file.name
        shutil.move(str(task_file), str(dest))
        logger.info(f"  Moved to Failed/")
        return False


def run_dispatcher():
    """Main function to process all tasks in In_Progress."""
    logger = setup_logging()
    ensure_directories()
    
    logger.info("=" * 50)
    logger.info("Email Dispatcher started")
    logger.info("=" * 50)
    
    # Check for credentials
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_recipient = os.getenv("SMTP_RECIPIENT")
    
    if not all([smtp_host, smtp_user, smtp_password, smtp_recipient]):
        logger.info("⏭️  SMTP credentials not set, skipping email dispatcher")
        logger.info("   Set these in .env to enable: SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SMTP_RECIPIENT")
        return
    
    # Load config (or use env vars directly)
    config = load_config(logger)
    if not config:
        # Try to use env vars directly
        config = {
            "smtp_host": smtp_host,
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "sender_email": smtp_user,
            "app_password": smtp_password,
            "recipient_email": smtp_recipient,
            "username": smtp_user
        }
    
    # Get tasks to process
    task_files = list(IN_PROGRESS_DIR.glob("*.md"))
    task_files = [f for f in task_files if f.name != ".gitkeep"]
    
    if not task_files:
        logger.info("No tasks in In_Progress/")
        return
    
    logger.info(f"Found {len(task_files)} task(s) to process")
    
    success_count = 0
    for task_file in task_files:
        if process_task(task_file, config, logger):
            success_count += 1
    
    logger.info("=" * 50)
    logger.info(f"Complete: {success_count}/{len(task_files)} emails sent")
    logger.info("=" * 50)


if __name__ == "__main__":
    run_dispatcher()