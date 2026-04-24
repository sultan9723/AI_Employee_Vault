"""Simple rule-based decision engine for email-like task content."""

from __future__ import annotations

import re


KEYWORDS_WEBHOOK = ("alert", "notify", "system down")
KEYWORDS_EMAIL = ("reply", "respond", "email")


def extract_body_section(email_content: str) -> str:
    """Extract the Body section from a markdown task file."""
    if not email_content:
        return ""

    body_match = re.search(
        r"^\s*Body:\s*(.*?)(?=^\s*[A-Za-z][A-Za-z ]*:\s*|\Z)",
        email_content,
        flags=re.IGNORECASE | re.DOTALL | re.MULTILINE,
    )
    if body_match:
        return body_match.group(1).strip()

    # Fallback: remove frontmatter and return remaining text.
    content_after_frontmatter = re.split(
        r"^---\s*$.*?^---\s*$",
        email_content,
        maxsplit=1,
        flags=re.IGNORECASE | re.DOTALL | re.MULTILINE,
    )
    if len(content_after_frontmatter) > 1:
        return content_after_frontmatter[1].strip()

    return email_content.strip()


def clean_message(text: str) -> str:
    """Remove labels, markdown artifacts, and extra whitespace."""
    if not text:
        return ""

    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.fullmatch(r"`{3,}.*", line):
            continue
        line = re.sub(r"^(Subject|Body):\s*", "", line, flags=re.IGNORECASE)
        line = re.sub(r"^#+\s*", "", line)
        if line:
            lines.append(line)

    message = " ".join(lines)
    message = re.sub(r"\s+", " ", message)
    return message.strip()


def decide_action(email_content: str) -> dict:
    """Decide an action for email-like content using simple rules."""
    message = clean_message(extract_body_section(email_content))
    lowered = f"{email_content}\n{message}".lower()

    if any(keyword in lowered for keyword in KEYWORDS_WEBHOOK):
        action = "webhook"
    elif any(keyword in lowered for keyword in KEYWORDS_EMAIL):
        action = "email"
    else:
        action = "ignore"

    return {
        "action": action,
        "message": message,
    }


if __name__ == "__main__":
    sample = """---
    type: email_task
    ---

    Subject: Test

    Body:
    System down, notify the team.
    """
    print(decide_action(sample))
