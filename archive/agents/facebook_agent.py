"""
Facebook Auto-Poster Agent
Reads approved posts from /Approved/ and publishes them to Facebook Pages
Uses Facebook Graph API v18.0

Setup:
1. Create Facebook App at https://developers.facebook.com
2. Generate Page Access Token for your page
3. Set FACEBOOK_PAGE_ACCESS_TOKEN and FACEBOOK_PAGE_ID in .env

Approved file format:
---
type: facebook_post
page_id: your_page_id (optional, uses env var if not specified)
---

Your post content goes here.
Can include links, hashtags, emojis.
"""

import os
import logging
from pathlib import Path
from datetime import datetime
import json

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system env vars

# Configuration
BASE_DIR = Path(__file__).parent.parent
APPROVED_DIR = BASE_DIR / "Approved"
DONE_DIR = BASE_DIR / "Done"
LOGS_DIR = BASE_DIR / "Logs"
LOG_FILE = LOGS_DIR / "activity.log"


def setup_logging() -> logging.Logger:
    """Configure logging"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("facebook_agent")
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


class FacebookAgent:
    """Facebook page poster using Graph API"""
    
    def __init__(self, page_token: str, page_id: str):
        self.page_token = page_token
        self.page_id = page_id
        self.api_base = "https://graph.facebook.com/v18.0"
        self.logger = setup_logging()
        
    def post_to_page(self, message: str, image_url: str = None) -> bool:
        """
        Post to Facebook page
        
        Args:
            message: Post text content
            image_url: Optional image URL to attach
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import requests
            
            # Build the payload
            payload = {
                "message": message,
                "access_token": self.page_token
            }
            
            # Add image if provided
            if image_url:
                payload["picture"] = image_url
            
            # Make the API call
            response = requests.post(
                f"{self.api_base}/{self.page_id}/feed",
                data=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                post_data = response.json()
                post_id = post_data.get("id", "unknown")
                self.logger.info(f"✅ Facebook post successful (ID: {post_id}): {message[:50]}...")
                return True
            else:
                self.logger.error(f"Facebook API error {response.status_code}: {response.text}")
                return False
                
        except ImportError:
            self.logger.warning("requests library not installed. Run: pip install requests")
            return False
        except Exception as e:
            self.logger.error(f"❌ Facebook posting failed: {e}")
            return False


def process_facebook_approvals():
    """Check /Approved for Facebook posts and execute them"""
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    
    logger = setup_logging()
    
    # Get credentials from environment
    page_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID")
    
    if not (page_token and page_id):
        logger.info("⏭️  Facebook credentials not set (FACEBOOK_PAGE_ACCESS_TOKEN, FACEBOOK_PAGE_ID), skipping")
        return
    
    agent = FacebookAgent(page_token, page_id)
    
    # Process all markdown files tagged with 'facebook'
    for filepath in sorted(APPROVED_DIR.glob("*.md")):
        # Skip non-Facebook files
        if "facebook" not in filepath.name.lower():
            continue
        
        try:
            content = filepath.read_text(encoding="utf-8")
            
            # Parse frontmatter and extract post content
            parts = content.split("---")
            if len(parts) < 3:
                logger.warning(f"Invalid format in {filepath.name}, skipping")
                continue
            
            message = parts[2].strip()
            
            if not message:
                logger.warning(f"Empty message in {filepath.name}, skipping")
                continue
            
            # Post to Facebook
            logger.info(f"📤 Posting to Facebook: {filepath.name}")
            if agent.post_to_page(message):
                # Move to Done folder
                done_path = DONE_DIR / filepath.name
                filepath.rename(done_path)
                logger.info(f"✅ Moved to Done: {filepath.name}")
                
                # Log the action
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "action": "facebook_post",
                    "file": filepath.name,
                    "status": "success",
                    "content_preview": message[:100]
                }
                logger.info(json.dumps(log_entry))
            else:
                logger.error(f"❌ Failed to post {filepath.name}")
                
        except Exception as e:
            logger.error(f"Error processing {filepath.name}: {e}")


def main():
    """Main entry point"""
    logger = setup_logging()
    logger.info("Starting Facebook Agent...")
    process_facebook_approvals()
    logger.info("Facebook Agent completed")


if __name__ == "__main__":
    main()
