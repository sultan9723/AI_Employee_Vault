"""One-command end-to-end debug execution for the agent pipeline."""

from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
NEEDS_ACTION = BASE_DIR / "Needs_Action"
IN_PROGRESS = BASE_DIR / "In_Progress"
DONE = BASE_DIR / "Done"
LOG_EXEC = BASE_DIR / "Logs" / "execution_handler.log"
LOG_WEBHOOK = BASE_DIR / "Logs" / "webhook_dispatcher.log"


def clear_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for item in path.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def create_test_task() -> tuple[Path, str]:
    task_name = "debug_task"
    task_content = """---
type: email_task
action: webhook
url: https://webhook.site/4b9d9d64-5dff-4183-a9d5-760bd2d63c21
---

Subject: Debug

Body:
System end-to-end test
"""

    task_file = NEEDS_ACTION / "debug_task.md"
    task_file.write_text(task_content)

    print("Task Created: OK")
    return task_file, task_name


def run_orchestrator_once() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", "orchestrator.py", "--once"],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def extract_http_status(log_text: str) -> str:
    statuses = re.findall(r"HTTP Status:\s*(\d+)", log_text)
    if statuses:
        return statuses[-1]

    statuses = re.findall(r"HTTP\s*(\d+)", log_text)
    if statuses:
        return statuses[-1]

    return "N/A"


def main() -> int:
    clear_folder(NEEDS_ACTION)
    clear_folder(IN_PROGRESS)
    clear_folder(DONE)

    task_file, task_name = create_test_task()

    result = run_orchestrator_once()

    exec_log = read_text_if_exists(LOG_EXEC)
    webhook_log = read_text_if_exists(LOG_WEBHOOK)

    task_created = "OK" if task_file.exists() else "FAILED"
    execution_status = "SKIPPED email_task" if "Skipping execution_handler for email_task" in exec_log else "FAILED"
    webhook_status = "CALLED" if task_name in webhook_log else "FAILED"
    http_status = extract_http_status(webhook_log)
    moved_to_done = "YES" if (DONE / f"{task_name}.md").exists() else "NO"

    print("=== DEBUG RESULT ===")
    print(f"Task Created: {task_created}")
    print(f"Execution Handler: {execution_status}")
    print(f"Webhook Dispatcher: {webhook_status}")
    print(f"HTTP Status: {http_status}")
    print(f"File Moved to Done: {moved_to_done}")

    if not list(IN_PROGRESS.glob("*.md")) and moved_to_done == "NO":
        print("ERROR: No files in In_Progress")
        return 1

    if webhook_status != "CALLED":
        print("ERROR: Webhook dispatcher was not called")
        return 1

    if http_status in {"N/A", ""}:
        print("ERROR: HTTP failed or no status captured")
        return 1

    if moved_to_done != "YES":
        print("ERROR: File not moved to Done")
        return 1

    if result.returncode != 0:
        return result.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
