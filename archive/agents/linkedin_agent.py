"""
LinkedIn Auto-Poster Agent (Simple - Write-Only)
Reads approved posts from /Approved/ and publishes them on LinkedIn
Uses LinkedIn API v2 with only w_member_social permission (no read required)

Setup:
1. Register app at https://www.linkedin.com/developers/apps
2. Generate Access Token with w_member_social permission
3. Get your LinkedIn Person URN from https://www.linkedin.com/in/YOUR-PROFILE/
4. Set these in .env:
   - LINKEDIN_ACCESS_TOKEN
   - LINKEDIN_PERSON_URN (format: urn:li:person:XXXXXXXX)

Approved file format:
---
type: linkedin_post
title: Post title (optional)
---

Your post content goes here.
Can include links, hashtags, mentions.

TO FIND YOUR PERSON URN:
- Go to your LinkedIn profile: https://www.linkedin.com/in/yourprofile/
- Open browser DevTools (F12)
- Network tab, search for "me" or "profile"
- Look for: "urn:li:person:XXXXXXXX" (9-10 digits)
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
    logger = logging.getLogger("linkedin_agent")
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


class LinkedInAgent:
    """LinkedIn poster with API v2 (write-only, no read permissions needed)"""
    
    def __init__(self, access_token: str, person_urn: str):
        self.access_token = access_token
        self.person_urn = person_urn  # Must be in format: urn:li:person:XXXXXXXX
        self.api_base = "https://api.linkedin.com/rest"
        self.logger = setup_logging()
        
    def post_to_linkedin(self, content: str) -> bool:
        """
        Post content to LinkedIn (text-only, no media)
        
        Args:
            content: Post text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "LinkedIn-Version": "202604"
            }
            
            # Minimal payload - text post only
            payload = {
                "author": self.person_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            response = requests.post(
                f"{self.api_base}/ugcPosts",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.logger.info(f"✅ LinkedIn post successful: {content[:50]}...")
                return True
            else:
                self.logger.error(f"LinkedIn API error {response.status_code}: {response.text}")
                return False
                
        except ImportError:
            self.logger.warning("requests library not installed. Run: pip install requests")
            return False
        except Exception as e:
            self.logger.error(f"❌ LinkedIn posting failed: {e}")
            return False


def process_linkedin_approvals():
    """Check /Approved for LinkedIn posts and execute them"""
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    
    logger = setup_logging()
    
    token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    person_urn = os.getenv("LINKEDIN_PERSON_URN")
    
    if not token or not person_urn:
        missing = []
        if not token:
            missing.append("LINKEDIN_ACCESS_TOKEN")
        if not person_urn:
            missing.append("LINKEDIN_PERSON_URN")
        logger.info(f"⏭️  Missing credentials ({', '.join(missing)}), skipping LinkedIn posts")
        return
    
    agent = LinkedInAgent(token, person_urn)
    
    # Process all markdown files tagged with 'linkedin'
    for filepath in sorted(APPROVED_DIR.glob("*.md")):
        # Skip non-LinkedIn files
        if "linkedin" not in filepath.name.lower():
            continue
        
        try:
            content = filepath.read_text(encoding="utf-8")
            
            # Parse frontmatter and extract post content
            parts = content.split("---")
            if len(parts) < 3:
                logger.warning(f"Invalid format in {filepath.name}, skipping")
                continue
            
            post_content = parts[2].strip()
            
            if not post_content:
                logger.warning(f"Empty post content in {filepath.name}, skipping")
                continue
            
            # Post to LinkedIn
            logger.info(f"📤 Posting to LinkedIn: {filepath.name}")
            if agent.post_to_linkedin(post_content):
                # Move to Done folder
                done_path = DONE_DIR / filepath.name
                filepath.rename(done_path)
                logger.info(f"✅ Moved to Done: {filepath.name}")
                
                # Log the action
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "action": "linkedin_post",
                    "file": filepath.name,
                    "status": "success",
                    "content_preview": post_content[:100]
                }
                logger.info(json.dumps(log_entry))
            else:
                logger.error(f"❌ Failed to post {filepath.name}")
                
        except Exception as e:
            logger.error(f"Error processing {filepath.name}: {e}")


def main():
    """Main entry point"""
    logger = setup_logging()
    logger.info("Starting LinkedIn Agent...")
    process_linkedin_approvals()
    logger.info("LinkedIn Agent completed")


if __name__ == "__main__":
    main()
