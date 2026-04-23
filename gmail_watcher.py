"""
Gmail Watcher - REAL Gmail API Integration
Monitors Gmail for unread emails and creates task files in Needs_Action.
Part of the AI Employee system - perception layer.
Inherits from BaseWatcher for consistent behavior across all watchers.
"""

import os
import pickle
from datetime import datetime
from pathlib import Path
from base64 import urlsafe_b64decode

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from base_watcher import BaseWatcher


# Gmail config
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CHECK_INTERVAL_SECONDS = 120

PRIORITY_KEYWORDS = [
    "urgent", "asap", "invoice", "payment",
    "contract", "deadline", "important", "action required"
]


class GmailWatcher(BaseWatcher):
    def __init__(self, vault_path: str, credentials_path: str, token_path: str):
        super().__init__(vault_path, check_interval=CHECK_INTERVAL_SECONDS)
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.service = None

    def on_startup(self):
        """Authenticate Gmail API on startup."""
        self.logger.info("Authenticating Gmail API...")
        self.service = self._get_gmail_service()
        self.logger.info("✅ Gmail API authenticated successfully")

    def _get_gmail_service(self):
        """Authenticate and return Gmail API service."""
        creds = None

        if self.token_path.exists():
            with open(self.token_path, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                self.logger.info("Refreshing expired credentials...")
                creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"Missing credentials file: {self.credentials_path}\n"
                        f"Download from Google Cloud Console → APIs → Gmail API → Credentials"
                    )
                self.logger.info("Starting OAuth flow — check your browser...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save token
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, "wb") as token:
                pickle.dump(creds, token)
            self.logger.info("Credentials saved.")

        return build("gmail", "v1", credentials=creds)

    def _get_email_body(self, payload: dict) -> str:
        """Extract plain text body from email payload."""
        body = ""

        if "body" in payload and payload["body"].get("data"):
            body = urlsafe_b64decode(
                payload["body"]["data"]
            ).decode("utf-8", errors="ignore")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and part["body"].get("data"):
                    body = urlsafe_b64decode(
                        part["body"]["data"]
                    ).decode("utf-8", errors="ignore")
                    break
                elif part["mimeType"] == "text/html" and part["body"].get("data") and not body:
                    body = urlsafe_b64decode(
                        part["body"]["data"]
                    ).decode("utf-8", errors="ignore")

        # Truncate long bodies
        if len(body) > 1000:
            body = body[:1000] + "\n\n... [truncated]"

        return body.strip()

    def _determine_priority(self, subject: str, body: str) -> str:
        """Determine email priority based on keywords."""
        text = (subject + " " + body).lower()
        for keyword in PRIORITY_KEYWORDS:
            if keyword in text:
                return "High"
        return "Normal"

    def check_for_updates(self) -> list:
        """Fetch unread emails from Gmail. Returns list of email dicts."""
        if not self.service:
            self.logger.error("Gmail service not initialized")
            return []

        emails = []

        try:
            results = self.service.users().messages().list(
                userId="me",
                q="is:unread",
                maxResults=10
            ).execute()

            messages = results.get("messages", [])

            for msg in messages:
                if self._is_already_processed(msg["id"]):
                    continue

                full_msg = self.service.users().messages().get(
                    userId="me",
                    id=msg["id"],
                    format="full"
                ).execute()

                headers = {
                    h["name"]: h["value"]
                    for h in full_msg["payload"]["headers"]
                }

                subject  = headers.get("Subject", "(No Subject)")
                from_addr = headers.get("From", "Unknown")
                to_addr  = headers.get("To", "Unknown")
                date     = headers.get("Date", "Unknown")
                body     = self._get_email_body(full_msg["payload"])
                priority = self._determine_priority(subject, body)

                email_data = {
                    "id":       msg["id"],
                    "subject":  subject,
                    "from":     from_addr,
                    "to":       to_addr,
                    "date":     date,
                    "body":     body,
                    "priority": priority,
                }

                emails.append(email_data)
                self._mark_as_processed(msg["id"])
                self.logger.info(f"📧 Found: {subject[:50]} from {from_addr}")

        except HttpError as e:
            self.logger.error(f"Gmail API error: {e}")

        return emails

    def create_action_file(self, item: dict) -> Path:
        """Create a markdown task file for the email."""
        filename = self._generate_task_filename("gmail", item["subject"])

        content = f"""# {item['subject']}

## Source
- **Platform**: Gmail
- **From**: {item['from']}
- **To**: {item['to']}
- **Date**: {item['date']}
- **Message ID**: {item['id']}
- **Priority**: {item['priority']}

## Email Content
{item['body']}

## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Archive after processing

---
*Detected by Gmail Watcher at {datetime.now().isoformat()}*
"""
        return self._write_action_file(filename, content)


def main():
    """Entry point — configure paths and start watcher."""
    # Resolve vault path
    vault_path = os.getenv("VAULT_PATH", str(Path(__file__).parent))

    # Credentials paths
    configs_dir = Path(vault_path) / "Configs"
    credentials_path = os.getenv(
        "GMAIL_CREDENTIALS_PATH",
        str(configs_dir / "gmail_credentials.json")
    )
    token_path = os.getenv(
        "GMAIL_TOKEN_PATH",
        str(configs_dir / "gmail_token.pickle")
    )

    print("\n" + "=" * 50)
    print("📧 Gmail Watcher")
    print(f"📁 Vault: {vault_path}")
    print(f"🔑 Credentials: {credentials_path}")
    print("=" * 50 + "\n")

    watcher = GmailWatcher(
        vault_path=vault_path,
        credentials_path=credentials_path,
        token_path=token_path,
    )
    watcher.run()


if __name__ == "__main__":
    main()