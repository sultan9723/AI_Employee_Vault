from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
NEEDS_ACTION = BASE_DIR / "Needs_Action"

def create_task(message: str):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"task_{timestamp}.md"

    content = f"""---
type: email_task
action: webhook
url: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
---

Subject: Auto Task

Body:
{message}
"""

    file_path = NEEDS_ACTION / filename
    file_path.write_text(content, encoding="utf-8")

    print(f"Created task: {filename}")

if __name__ == "__main__":
    import sys
    msg = " ".join(sys.argv[1:])
    create_task(msg)