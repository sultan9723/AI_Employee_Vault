"""
Gmail Watcher - REAL Gmail API Integration
Monitors Gmail for unread important emails and creates task files in Needs_Action.
Part of the AI Employee system - perception layer.
"""

import os
import logging
import time
import pickle
from datetime import datetime
from pathlib import Path
from base64 import urlsafe_b64decode

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Configuration
BASE_DIR = Path(__file__).parent
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
CONFIGS_DIR = BASE_DIR / "Configs"
LOG_FILE = BASE_DIR / "Logs" / "gmail_watcher.log"

CREDENTIALS_FILE = CONFIGS_DIR / "gmail_credentials.json"
TOKEN_FILE = CONFIGS_DIR / "gmail_token.pickle"

CHECK_INTERVAL_SECONDS = 120  # Check every 2 minutes
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Keywords that indicate high priority
PRIORITY_KEYWORDS = ["urgent", "asap", "invoice", "payment", "contract", "deadline", "important"]


def setup_logging() -> logging.Logger:
    """Configure and return the logger instance."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("gmail_watcher")
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


def get_gmail_service(logger: logging.Logger):
    """Authenticate and return Gmail API service."""
    creds = None
    
    # Load existing token
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                logger.error(f"Credentials file not found: {CREDENTIALS_FILE}")
                raise FileNotFoundError(f"Missing {CREDENTIALS_FILE}")
            
            logger.info("Starting OAuth flow - check your browser...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save token for next run
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)
        logger.info("Credentials saved.")
    
    return build("gmail", "v1", credentials=creds)


def get_email_body(payload: dict) -> str:
    """Extract email body from payload."""
    body = ""
    
    if "body" in payload and payload["body"].get("data"):
        body = urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    elif "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and part["body"].get("data"):
                body = urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                break
            elif part["mimeType"] == "text/html" and part["body"].get("data") and not body:
                body = urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
    
    # Truncate if too long
    if len(body) > 1000:
        body = body[:1000] + "\n\n... [truncated]"
    
    return body.strip()


def determine_priority(subject: str, body: str) -> str:
    """Determine email priority based on keywords."""
    text = (subject + " " + body).lower()
    
    for keyword in PRIORITY_KEYWORDS:
        if keyword in text:
            return "High"
    
    return "Normal"


def create_task_content(email_data: dict) -> str:
    """Create markdown content for the task file."""
    return f"""# {email_data['subject']}

## Source
- **Platform**: Gmail
- **From**: {email_data['from']}
- **To**: {email_data['to']}
- **Date**: {email_data['date']}
- **Message ID**: {email_data['id']}

## Priority
**{email_data['priority']}**

## Email Content
{email_data['body']}

## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Archive after processing

---
*Detected by Gmail Watcher at {datetime.now().isoformat()}*
"""


def save_task_file(email_data: dict, logger: logging.Logger) -> Path:
    """Save the email as a markdown task file in Needs_Action."""
    NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    # Clean subject for filename
    safe_subject = "".join(c if c.isalnum() else "_" for c in email_data['subject'][:30])
    filename = f"task_{timestamp}_gmail_{safe_subject}.md"
    filepath = NEEDS_ACTION_DIR / filename
    
    content = create_task_content(email_data)
    filepath.write_text(content, encoding="utf-8")
    
    logger.info(f"Created task: {filename}")
    return filepath


def fetch_unread_emails(service, logger: logging.Logger, processed_ids: set) -> list:
    """Fetch unread emails from Gmail."""
    emails = []
    
    try:
        # Query for unread emails (you can add 'is:important' if desired)
        results = service.users().messages().list(
            userId="me",
            q="is:unread",
            maxResults=10
        ).execute()
        
        messages = results.get("messages", [])
        
        for msg in messages:
            if msg["id"] in processed_ids:
                continue
            
            # Get full message
            full_msg = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="full"
            ).execute()
            
            # Extract headers
            headers = {h["name"]: h["value"] for h in full_msg["payload"]["headers"]}
            
            subject = headers.get("Subject", "(No Subject)")
            from_addr = headers.get("From", "Unknown")
            to_addr = headers.get("To", "Unknown")
            date = headers.get("Date", "Unknown")
            
            # Get body
            body = get_email_body(full_msg["payload"])
            
            # Determine priority
            priority = determine_priority(subject, body)
            
            email_data = {
                "id": msg["id"],
                "subject": subject,
                "from": from_addr,
                "to": to_addr,
                "date": date,
                "body": body,
                "priority": priority,
            }
            
            emails.append(email_data)
            processed_ids.add(msg["id"])
            
            logger.info(f"Found: {subject[:50]} from {from_addr}")
    
    except HttpError as e:
        logger.error(f"Gmail API error: {e}")
    
    return emails


def run_watcher():
    """Main loop that continuously watches Gmail."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Gmail Watcher started (REAL API)")
    logger.info(f"Output: {NEEDS_ACTION_DIR}")
    logger.info(f"Interval: {CHECK_INTERVAL_SECONDS} seconds")
    logger.info("=" * 60)
    
    print("\n" + "=" * 50)
    print("📧 Gmail Watcher - Real Gmail API")
    print("=" * 50 + "\n")
    
    # Authenticate
    try:
        service = get_gmail_service(logger)
        logger.info("Gmail API authenticated successfully!")
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        print(f"❌ Authentication failed: {e}")
        return
    
    processed_ids = set()
    task_count = 0
    
    try:
        while True:
            logger.info("Checking for new emails...")
            print("🔍 Checking Gmail...")
            
            emails = fetch_unread_emails(service, logger, processed_ids)
            
            for email_data in emails:
                save_task_file(email_data, logger)
                task_count += 1
                print(f"📨 New task: {email_data['subject'][:40]}")
            
            if not emails:
                print("   No new unread emails.")
            
            logger.info(f"Waiting {CHECK_INTERVAL_SECONDS} seconds...")
            time.sleep(CHECK_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        logger.info("=" * 60)
        logger.info(f"Gmail Watcher stopped. Total tasks created: {task_count}")
        logger.info("=" * 60)
        print(f"\n👋 Stopped. Total tasks created: {task_count}")


if __name__ == "__main__":
    run_watcher()