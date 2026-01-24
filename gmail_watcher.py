"""
Gmail Watcher
Simulates detecting email events and creates task files in Needs_Action.
Part of the FTES system - event detection layer.

This script only detects and reports events.
It does NOT call real APIs, reason, plan, or execute actions.
"""

import random
import logging
import time
from datetime import datetime
from pathlib import Path


# Configuration
BASE_DIR = Path(__file__).parent
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
LOG_FILE = BASE_DIR / "Logs" / "gmail_watcher.log"
CHECK_INTERVAL_SECONDS = 30

# Mock data for realistic email simulation
SENDERS = [
    ("John Smith", "john.smith@techcorp.com"),
    ("Sarah Johnson", "sarah.j@innovate.io"),
    ("Michael Chen", "m.chen@enterprise.net"),
    ("Emily Davis", "emily.davis@startup.co"),
    ("Robert Wilson", "r.wilson@consulting.biz"),
    ("Amanda Lee", "amanda.lee@partners.org"),
    ("David Brown", "david.b@investors.capital"),
    ("Lisa Martinez", "lisa.m@legal.firm"),
]

EMAIL_TYPES = [
    {
        "subject": "Urgent: Contract Review Required",
        "summary": "Legal team requesting immediate review of updated vendor contract terms before Friday deadline.",
        "why_matters": "Contract expires in 48 hours. Delay may result in service interruption.",
        "sensitivity": "High",
    },
    {
        "subject": "Meeting Request: Q1 Strategy Discussion",
        "summary": "Executive team proposing strategy alignment meeting for next quarter planning.",
        "why_matters": "Strategic decisions require input before budget allocation.",
        "sensitivity": "Medium",
    },
    {
        "subject": "Invoice #INV-2026-0142 - Payment Due",
        "summary": "Outstanding invoice from vendor requiring payment authorization.",
        "why_matters": "Payment terms expire in 15 days. Late fees may apply.",
        "sensitivity": "Medium",
    },
    {
        "subject": "New Lead: Enterprise Inquiry",
        "summary": "Potential enterprise client expressing interest in our services via website contact form.",
        "why_matters": "High-value lead requiring prompt follow-up within 24 hours.",
        "sensitivity": "High",
    },
    {
        "subject": "Employee Onboarding: New Hire Starting Monday",
        "summary": "HR notification about new team member requiring system access and equipment.",
        "why_matters": "Preparation needed before employee start date.",
        "sensitivity": "Low",
    },
    {
        "subject": "Security Alert: Unusual Login Detected",
        "summary": "IT security system flagged login attempt from unrecognized location.",
        "why_matters": "Potential security breach requiring immediate verification.",
        "sensitivity": "Critical",
    },
    {
        "subject": "Project Update: Milestone Completed",
        "summary": "Development team reporting completion of sprint deliverables.",
        "why_matters": "Triggers next phase approval and stakeholder notification.",
        "sensitivity": "Low",
    },
    {
        "subject": "Partnership Proposal from Industry Leader",
        "summary": "Major industry player proposing strategic partnership discussion.",
        "why_matters": "Significant business development opportunity requiring executive attention.",
        "sensitivity": "High",
    },
]


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


def generate_timestamp() -> str:
    """Generate a timestamp string for filenames."""
    return datetime.now().strftime("%Y%m%d%H%M%S")


def simulate_email_event() -> dict:
    """Simulate detecting an email event with mock data."""
    sender_name, sender_email = random.choice(SENDERS)
    email_type = random.choice(EMAIL_TYPES)
    
    return {
        "sender_name": sender_name,
        "sender_email": sender_email,
        "subject": email_type["subject"],
        "summary": email_type["summary"],
        "why_matters": email_type["why_matters"],
        "sensitivity": email_type["sensitivity"],
        "received_at": datetime.now().isoformat(),
    }


def create_task_content(event: dict) -> str:
    """Create markdown content for the task file."""
    return f"""# {event['subject']}

## Source
- **Platform**: Gmail
- **Sender**: {event['sender_name']} <{event['sender_email']}>
- **Received**: {event['received_at']}

## Event Summary
{event['summary']}

## Why This Matters
{event['why_matters']}

## Sensitivity Level
**{event['sensitivity']}**

---
*Detected by Gmail Watcher*
"""


def save_task_file(event: dict, logger: logging.Logger) -> Path:
    """Save the event as a markdown task file in Needs_Action."""
    NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = generate_timestamp()
    filename = f"task_{timestamp}_gmail.md"
    filepath = NEEDS_ACTION_DIR / filename
    
    content = create_task_content(event)
    filepath.write_text(content, encoding="utf-8")
    
    logger.info(f"Created task: {filename}")
    return filepath


def run_watcher():
    """Main loop that continuously watches for email events."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Gmail Watcher started")
    logger.info(f"Output: {NEEDS_ACTION_DIR}")
    logger.info(f"Interval: {CHECK_INTERVAL_SECONDS} seconds")
    logger.info("=" * 60)
    
    print("\n" + "=" * 50)
    print("📧 Gmail Watcher - Event Detection")
    print("=" * 50 + "\n")
    
    event_count = 0
    
    try:
        while True:
            # Simulate detecting an email event
            event = simulate_email_event()
            event_count += 1
            
            logger.info(f"Event #{event_count}: {event['subject']} from {event['sender_name']}")
            print(f"📨 Detected: {event['subject']}")
            
            # Create task file
            save_task_file(event, logger)
            
            # Wait before next check
            logger.info(f"Waiting {CHECK_INTERVAL_SECONDS} seconds...")
            time.sleep(CHECK_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        logger.info("=" * 60)
        logger.info(f"Gmail Watcher stopped. Total events: {event_count}")
        logger.info("=" * 60)
        print(f"\n👋 Stopped. Total events detected: {event_count}")


if __name__ == "__main__":
    run_watcher()
