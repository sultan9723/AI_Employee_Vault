import os
import re
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

BASE_DIR = Path(__file__).parent.parent
IN_PROGRESS_DIR = BASE_DIR / "In_Progress"
DONE_DIR = BASE_DIR / "Done"
FAILED_DIR = BASE_DIR / "Failed"
LOG_FILE = BASE_DIR / "Logs" / "webhook_dispatcher.log"
DEBUG_MODE = True


def debug_log(message):
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")


def setup_logging():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("webhook_dispatcher")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    ch = logging.StreamHandler()
    fh = logging.FileHandler(LOG_FILE)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger


def extract_frontmatter(content):
    match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL | re.MULTILINE)
    data = {}
    if not match:
        return data

    for line in match.group(1).split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()

    return data


def clean_message(text):
    text = re.sub(r'^(Subject|Body):', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_email_task_for_webhook(content, logger):
    fm = extract_frontmatter(content)

    if fm.get("action", "").lower() != "webhook":
        return None, None

    url = fm.get("url")
    if not url:
        raise ValueError("Missing URL for email_task webhook action")

    body_match = re.search(r'Body:\s*(.*)', content, re.DOTALL | re.IGNORECASE)
    raw = body_match.group(1) if body_match else content

    cleaned = clean_message(raw)
    debug_log(f"Extracted URL: {url}")
    debug_log(f"Extracted message: {cleaned}")

    payload = {"message": cleaned}

    logger.info(f"Converted email_task → webhook")
    logger.info(f"Message: {cleaned}")

    return url, payload


def execute_webhook(task_file: Path, logger):
    name = task_file.stem
    print(f"[WEBHOOK] Processing: {task_file.name}")
    debug_log(f"File being processed: {task_file.name}")
    logger.info(f"Processing: {name}")

    try:
        content = task_file.read_text()

        fm = extract_frontmatter(content)
        task_type = fm.get("type", "").lower()

        if task_type == "email_task":
            url, payload = extract_email_task_for_webhook(content, logger)
            if not url:
                return False, False

        elif task_type == "webhook":
            url = fm.get("url")
            if not url:
                raise ValueError("Missing URL for webhook task")

            debug_log(f"Extracted URL: {url}")

            payload = {"message": "default message"}
            debug_log(f"Extracted message: {payload.get('message', '')}")

        else:
            print(f"[WARN] Unrecognized task type: {task_type}")
            return False, False

        logger.info(f"Sending POST → {url}")
        logger.info(f"Payload → {payload}")
        print(f"[WEBHOOK] URL: {url}")
        print(f"[WEBHOOK] Payload: {payload}")

        response = requests.post(url, json=payload, timeout=10)
        debug_log(f"HTTP response status: {response.status_code}")
        print(f"[WEBHOOK] Status: {response.status_code}")

        if response.status_code == 200:
            logger.info("✅ SUCCESS: HTTP 200")
            print("✅ Webhook sent successfully")
            return True, True
        else:
            logger.error(f"❌ FAILED: HTTP {response.status_code}")
            print(f"❌ Webhook failed: {response.status_code}")
            print(f"ERROR: HTTP failed with status {response.status_code}")
            return True, False

    except Exception as e:
        logger.error(f"ERROR: {e}")
        print(f"ERROR: {e}")
        return True, False


def run_webhook_dispatcher():
    logger = setup_logging()

    files = list(IN_PROGRESS_DIR.glob("*.md"))

    if not files:
        print("ERROR: No files in In_Progress")
        return

    for f in files:
        executed, success = execute_webhook(f, logger)

        if not executed:
            continue

        if success:
            shutil.move(str(f), DONE_DIR / f.name)
            if not (DONE_DIR / f.name).exists():
                print("ERROR: File not moved to Done")
        else:
            print(f"ERROR: Keeping {f.name} in In_Progress")


if __name__ == "__main__":
    run_webhook_dispatcher()