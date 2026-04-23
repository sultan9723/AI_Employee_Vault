"""
Status Snapshot Agent
Generates a read-only snapshot of the current system state for observability.
Part of the AI Employee system - visibility layer.

This agent does NOT modify or move any files.
It only reads folder contents and produces a status report.

FIXED: KeyError 'completed' - snapshot uses 'done' key consistently throughout.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


# Configuration
BASE_DIR = Path(__file__).parent.parent
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
PLANS_DIR = BASE_DIR / "Plans"
PENDING_APPROVAL_DIR = BASE_DIR / "Pending_Approval"
APPROVED_DIR = BASE_DIR / "Approved"
IN_PROGRESS_DIR = BASE_DIR / "In_Progress"
DONE_DIR = BASE_DIR / "Done"
FAILED_DIR = BASE_DIR / "Failed"
STATUS_DIR = BASE_DIR / "Status"
SNAPSHOT_FILE = STATUS_DIR / "status_snapshot.json"


def ensure_directories():
    """Create required directories if missing."""
    for directory in [STATUS_DIR, APPROVED_DIR, IN_PROGRESS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def list_files(directory: Path) -> list:
    """
    List all filenames in a directory.
    Returns empty list if directory doesn't exist.
    """
    if not directory.exists():
        return []
    try:
        return sorted([f.name for f in directory.iterdir() if f.is_file()])
    except Exception:
        return []


def get_task_name(filename: str) -> str:
    """Extract task name from filename (e.g., task_100.md → task_100)."""
    return Path(filename).stem


def get_waiting_for_approval() -> list:
    """
    Find tasks in Pending_Approval that have not yet been moved to Approved.
    """
    waiting = []
    pending_files = list_files(PENDING_APPROVAL_DIR)

    for filename in pending_files:
        approved_path = APPROVED_DIR / filename
        if not approved_path.exists():
            waiting.append(filename)

    return waiting


def generate_snapshot() -> dict:
    """
    Generate a complete status snapshot of the system.
    Returns a dictionary with all state information.
    KEY FIX: Uses 'done' consistently — was previously mixed with 'completed'.
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "needs_action": list_files(NEEDS_ACTION_DIR),
        "pending_approval": list_files(PENDING_APPROVAL_DIR),
        "waiting_for_approval": get_waiting_for_approval(),
        "approved": list_files(APPROVED_DIR),
        "in_progress": list_files(IN_PROGRESS_DIR),
        "done": list_files(DONE_DIR),          # FIX: was 'completed' in display code
        "failed": list_files(FAILED_DIR),
    }


def write_snapshot(snapshot: dict) -> bool:
    """
    Write the snapshot to the status file.
    Overwrites existing file.
    Returns True if successful.
    """
    try:
        content = json.dumps(snapshot, indent=2)
        SNAPSHOT_FILE.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"❌ Failed to write snapshot: {e}")
        return False


def display_summary(snapshot: dict):
    """Display a clean summary of the current system state."""
    print("\n" + "-" * 50)
    print("📋 Current System State:")
    print("-" * 50)
    print(f"  Needs Action:          {len(snapshot['needs_action'])} task(s)")
    print(f"  Waiting for Approval:  {len(snapshot['waiting_for_approval'])} task(s)")
    print(f"  Approved:              {len(snapshot['approved'])} task(s)")
    print(f"  In Progress:           {len(snapshot['in_progress'])} task(s)")
    print(f"  Completed:             {len(snapshot['done'])} task(s)")   # FIX: snapshot['done']
    print(f"  Failed:                {len(snapshot['failed'])} task(s)")
    print("-" * 50)

    has_tasks = any([
        snapshot['needs_action'],
        snapshot['waiting_for_approval'],
        snapshot['approved'],
        snapshot['in_progress'],
        snapshot['done'],                      # FIX: was 'completed'
        snapshot['failed'],
    ])

    if has_tasks:
        print("\n📝 Details:")

        sections = [
            ("Needs Action",        snapshot['needs_action']),
            ("Waiting for Approval",snapshot['waiting_for_approval']),
            ("Approved",            snapshot['approved']),
            ("In Progress",         snapshot['in_progress']),
            ("Completed",           snapshot['done']),          # FIX: snapshot['done']
            ("Failed",              snapshot['failed']),
        ]

        for label, files in sections:
            if files:
                print(f"\n  {label}:")
                for f in files:
                    print(f"    - {f}")

    print("\n" + "=" * 50 + "\n")


def run_status_snapshot():
    """Main function to generate and save the status snapshot."""
    print("\n" + "=" * 50)
    print("📊 Status Snapshot Agent")
    print("=" * 50 + "\n")

    try:
        ensure_directories()
    except Exception as e:
        print(f"❌ Failed to create directories: {e}")
        return

    snapshot = generate_snapshot()

    if write_snapshot(snapshot):
        print(f"✅ Snapshot saved to: {SNAPSHOT_FILE.name}")
    else:
        return

    display_summary(snapshot)


if __name__ == "__main__":
    run_status_snapshot()