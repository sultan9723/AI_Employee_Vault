"""
WhatsApp Watcher
Simulates detecting WhatsApp events and creates task files in Needs_Action.
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
LOG_FILE = BASE_DIR / "Logs" / "whatsapp_watcher.log"
CHECK_INTERVAL_SECONDS = 30

# Mock data for realistic WhatsApp simulation
CONTACTS = [
    ("Alex Kumar", "+1-555-0101"),
    ("Sophie Chen", "+1-555-0102"),
    ("Marcus Johnson", "+1-555-0103"),
    ("Priya Sharma", "+1-555-0104"),
    ("Daniel Kim", "+1-555-0105"),
    ("Emma Williams", "+1-555-0106"),
    ("Raj Patel", "+1-555-0107"),
    ("Olivia Brown", "+1-555-0108"),
]

GROUP_CHATS = [
    "Leadership Team",
    "Sales Updates",
    "Project Alpha",
    "Client Support",
    "Operations",
    "Partner Network",
]

MESSAGE_TYPES = [
    {
        "type": "urgent_request",
        "preview": "Need your approval ASAP on the proposal...",
        "summary": "Urgent request requiring immediate decision or approval.",
        "why_matters": "Time-sensitive matter that may block other team members.",
        "sensitivity": "High",
    },
    {
        "type": "client_escalation",
        "preview": "Client is asking about the delivery timeline...",
        "summary": "Client escalation requiring prompt attention and response.",
        "why_matters": "Customer satisfaction at risk. Delay may impact relationship.",
        "sensitivity": "High",
    },
    {
        "type": "meeting_request",
        "preview": "Can we schedule a quick call today?",
        "summary": "Request for synchronous communication to discuss important matter.",
        "why_matters": "Stakeholder needs alignment before proceeding.",
        "sensitivity": "Medium",
    },
    {
        "type": "status_update",
        "preview": "Just finished the deliverable, ready for review...",
        "summary": "Team member providing status update on assigned work.",
        "why_matters": "Unblocks next phase of work. May require acknowledgment.",
        "sensitivity": "Low",
    },
    {
        "type": "document_share",
        "preview": "Sharing the updated contract draft...",
        "summary": "Important document shared requiring review or action.",
        "why_matters": "Document may require signature, feedback, or distribution.",
        "sensitivity": "Medium",
    },
    {
        "type": "issue_report",
        "preview": "We have a problem with the system...",
        "summary": "Team member reporting an issue or blocker requiring attention.",
        "why_matters": "Operational issue that may escalate if not addressed.",
        "sensitivity": "High",
    },
    {
        "type": "follow_up",
        "preview": "Following up on our earlier discussion...",
        "summary": "Follow-up on previous conversation requiring response.",
        "why_matters": "Pending item that needs closure or next steps.",
        "sensitivity": "Medium",
    },
    {
        "type": "media_share",
        "preview": "[Photo] Check out this from the event...",
        "summary": "Media content shared that may require acknowledgment or action.",
        "why_matters": "May contain important visual information or require response.",
        "sensitivity": "Low",
    },
]


def setup_logging() -> logging.Logger:
    """Configure and return the logger instance."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("whatsapp_watcher")
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


def simulate_whatsapp_event() -> dict:
    """Simulate detecting a WhatsApp event with mock data."""
    is_group = random.choice([True, False])
    name, phone = random.choice(CONTACTS)
    message_type = random.choice(MESSAGE_TYPES)
    
    event = {
        "sender_name": name,
        "sender_phone": phone,
        "is_group": is_group,
        "group_name": random.choice(GROUP_CHATS) if is_group else None,
        "message_type": message_type["type"],
        "preview": message_type["preview"],
        "summary": message_type["summary"],
        "why_matters": message_type["why_matters"],
        "sensitivity": message_type["sensitivity"],
        "detected_at": datetime.now().isoformat(),
    }
    
    return event


def format_message_type(message_type: str) -> str:
    """Format message type for display."""
    return message_type.replace("_", " ").title()


def create_task_content(event: dict) -> str:
    """Create markdown content for the task file."""
    source_info = f"**Group**: {event['group_name']}" if event['is_group'] else "**Chat**: Direct Message"
    
    return f"""# WhatsApp: {format_message_type(event['message_type'])} from {event['sender_name']}

## Source
- **Platform**: WhatsApp
- **Sender**: {event['sender_name']} ({event['sender_phone']})
- {source_info}
- **Detected**: {event['detected_at']}

## Message Preview
> {event['preview']}

## Event Summary
{event['summary']}

## Why This Matters
{event['why_matters']}

## Sensitivity Level
**{event['sensitivity']}**

---
*Detected by WhatsApp Watcher*
"""


def save_task_file(event: dict, logger: logging.Logger) -> Path:
    """Save the event as a markdown task file in Needs_Action."""
    NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = generate_timestamp()
    filename = f"task_{timestamp}_whatsapp.md"
    filepath = NEEDS_ACTION_DIR / filename
    
    content = create_task_content(event)
    filepath.write_text(content, encoding="utf-8")
    
    logger.info(f"Created task: {filename}")
    return filepath


def run_watcher():
    """Main loop that continuously watches for WhatsApp events."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("WhatsApp Watcher started")
    logger.info(f"Output: {NEEDS_ACTION_DIR}")
    logger.info(f"Interval: {CHECK_INTERVAL_SECONDS} seconds")
    logger.info("=" * 60)
    
    print("\n" + "=" * 50)
    print("💬 WhatsApp Watcher - Event Detection")
    print("=" * 50 + "\n")
    
    event_count = 0
    
    try:
        while True:
            # Simulate detecting a WhatsApp event
            event = simulate_whatsapp_event()
            event_count += 1
            
            source = f"[{event['group_name']}]" if event['is_group'] else "[DM]"
            logger.info(f"Event #{event_count}: {source} {format_message_type(event['message_type'])} from {event['sender_name']}")
            print(f"💬 Detected: {source} {event['sender_name']} - {format_message_type(event['message_type'])}")
            
            # Create task file
            save_task_file(event, logger)
            
            # Wait before next check
            logger.info(f"Waiting {CHECK_INTERVAL_SECONDS} seconds...")
            time.sleep(CHECK_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        logger.info("=" * 60)
        logger.info(f"WhatsApp Watcher stopped. Total events: {event_count}")
        logger.info("=" * 60)
        print(f"\n👋 Stopped. Total events detected: {event_count}")


if __name__ == "__main__":
    run_watcher()
