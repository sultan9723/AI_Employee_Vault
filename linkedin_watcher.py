"""
LinkedIn Lead Watcher
Simulates receiving LinkedIn business leads and creates task files in the Inbox.
"""

import os
import random
import logging
import time
from datetime import datetime
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).parent
INBOX_DIR = BASE_DIR / "Inbox"
LOG_FILE = BASE_DIR / "Logs" / "activity.log"
CHECK_INTERVAL_SECONDS = 30

# Sample data for realistic lead generation
FIRST_NAMES = [
    "Sarah", "Michael", "Jennifer", "David", "Emily", "James", "Jessica", "Robert",
    "Amanda", "Christopher", "Ashley", "Matthew", "Stephanie", "Daniel", "Nicole",
    "Andrew", "Elizabeth", "Joshua", "Megan", "Ryan", "Lauren", "Justin", "Rachel"
]

LAST_NAMES = [
    "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez",
    "Martinez", "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin", "Lee",
    "Thompson", "White", "Harris", "Clark", "Lewis", "Robinson", "Walker", "Young"
]

COMPANIES = [
    "TechVenture Solutions", "Quantum Dynamics Inc", "Apex Digital Group",
    "Horizon Analytics", "BlueSky Innovations", "NextGen Systems",
    "Pinnacle Consulting", "Velocity Partners", "Summit Technologies",
    "Forge Industries", "Catalyst Software", "Evergreen Enterprises",
    "Mosaic Marketing Co", "Sterling Financial", "Nova Health Systems",
    "Brightpath Education", "Urban Development Corp", "Pacific Trade Group"
]

JOB_TITLES = [
    "CEO", "CTO", "VP of Sales", "Director of Operations", "Head of Marketing",
    "Business Development Manager", "Chief Revenue Officer", "Founder",
    "Managing Director", "VP of Engineering", "Head of Partnerships",
    "Director of Strategy", "Chief Growth Officer", "VP of Product"
]

INDUSTRIES = [
    "SaaS", "FinTech", "HealthTech", "E-commerce", "Consulting", "Manufacturing",
    "Real Estate", "Education Technology", "Logistics", "Renewable Energy",
    "Cybersecurity", "AI/Machine Learning", "Digital Marketing", "HR Tech"
]

INQUIRY_TYPES = [
    ("consulting", "Interested in your consulting services for our upcoming digital transformation initiative."),
    ("partnership", "Looking to explore a potential strategic partnership opportunity."),
    ("demo_request", "Would love to schedule a demo of your platform for our leadership team."),
    ("pricing", "Requesting pricing information for enterprise-level engagement."),
    ("referral", "Was referred by a colleague and interested in learning more about your offerings."),
    ("rfp", "Preparing an RFP and your company came highly recommended."),
    ("expansion", "We're expanding operations and need a trusted partner to support our growth."),
    ("audit", "Seeking an external audit of our current processes and systems."),
]

COMPANY_SIZES = [
    "10-50 employees", "50-200 employees", "200-500 employees",
    "500-1000 employees", "1000-5000 employees", "5000+ employees"
]

URGENCY_LEVELS = ["Low", "Medium", "High", "Critical"]


def setup_logging() -> logging.Logger:
    """Configure and return the logger instance."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("linkedin_watcher")
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


def generate_lead_id() -> str:
    """Generate a unique lead identifier."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = random.randint(1000, 9999)
    return f"LI-{timestamp}-{random_suffix}"


def generate_lead() -> dict:
    """Generate a realistic LinkedIn business lead."""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    inquiry_type, inquiry_message = random.choice(INQUIRY_TYPES)
    
    return {
        "lead_id": generate_lead_id(),
        "first_name": first_name,
        "last_name": last_name,
        "full_name": f"{first_name} {last_name}",
        "email": f"{first_name.lower()}.{last_name.lower()}@{random.choice(COMPANIES).lower().replace(' ', '')}.com",
        "company": random.choice(COMPANIES),
        "job_title": random.choice(JOB_TITLES),
        "industry": random.choice(INDUSTRIES),
        "company_size": random.choice(COMPANY_SIZES),
        "inquiry_type": inquiry_type,
        "inquiry_message": inquiry_message,
        "urgency": random.choice(URGENCY_LEVELS),
        "linkedin_url": f"https://linkedin.com/in/{first_name.lower()}{last_name.lower()}{random.randint(100, 999)}",
        "received_at": datetime.now().isoformat(),
    }


def create_task_content(lead: dict) -> str:
    """Create markdown content for the task file."""
    return f"""# LinkedIn Lead: {lead['full_name']}

## Lead Information
| Field | Value |
|-------|-------|
| **Lead ID** | `{lead['lead_id']}` |
| **Name** | {lead['full_name']} |
| **Email** | {lead['email']} |
| **Job Title** | {lead['job_title']} |
| **Company** | {lead['company']} |
| **Industry** | {lead['industry']} |
| **Company Size** | {lead['company_size']} |
| **LinkedIn** | [{lead['linkedin_url']}]({lead['linkedin_url']}) |

## Inquiry Details
- **Type**: {lead['inquiry_type'].replace('_', ' ').title()}
- **Urgency**: {lead['urgency']}
- **Received**: {lead['received_at']}

## Message
> {lead['inquiry_message']}

## Required Actions
- [ ] Review lead information
- [ ] Research company background
- [ ] Prepare personalized response
- [ ] Schedule follow-up if appropriate
- [ ] Update CRM with lead details

## Notes
_Add any relevant notes or context here._

---
*Generated by LinkedIn Watcher*
"""


def save_task_file(lead: dict, logger: logging.Logger) -> Path:
    """Save the lead as a markdown task file in the Inbox directory."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create filename from lead info
    safe_name = lead['full_name'].lower().replace(' ', '_')
    filename = f"task_linkedin_{safe_name}_{lead['lead_id']}.md"
    filepath = INBOX_DIR / filename
    
    content = create_task_content(lead)
    
    filepath.write_text(content, encoding="utf-8")
    logger.info(f"Created task file: {filename}")
    
    return filepath


def run_watcher():
    """Main loop that continuously monitors for new leads."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("LinkedIn Lead Watcher started")
    logger.info(f"Inbox directory: {INBOX_DIR}")
    logger.info(f"Check interval: {CHECK_INTERVAL_SECONDS} seconds")
    logger.info("=" * 60)
    
    lead_count = 0
    
    try:
        while True:
            # Simulate receiving a new lead
            lead = generate_lead()
            lead_count += 1
            
            logger.info(f"Received lead #{lead_count}: {lead['full_name']} ({lead['job_title']} at {lead['company']})")
            
            # Save the task file
            filepath = save_task_file(lead, logger)
            
            logger.info(f"Lead #{lead_count} processed successfully | Type: {lead['inquiry_type']} | Urgency: {lead['urgency']}")
            
            # Wait before next check
            logger.info(f"Waiting {CHECK_INTERVAL_SECONDS} seconds for next lead...")
            time.sleep(CHECK_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        logger.info("=" * 60)
        logger.info(f"LinkedIn Lead Watcher stopped by user")
        logger.info(f"Total leads processed: {lead_count}")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run_watcher()
