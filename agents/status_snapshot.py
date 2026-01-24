"""
Status Snapshot Agent
Generates a read-only snapshot of the current system state for observability.
Part of the AI Employee system - visibility layer.

This agent does NOT modify or move any files.
It only reads folder contents and produces a status report.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


# Configuration
BASE_DIR = Path(__file__).parent.parent
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
PLANS_DIR = BASE_DIR / "Plans"
APPROVALS_DIR = BASE_DIR / "Approvals"
APPROVED_DIR = BASE_DIR / "Approved"
IN_PROGRESS_DIR = BASE_DIR / "In_Progress"
COMPLETED_DIR = BASE_DIR / "Completed"
FAILED_DIR = BASE_DIR / "Failed"
STATUS_DIR = BASE_DIR / "Status"
SNAPSHOT_FILE = STATUS_DIR / "status_snapshot.json"


def ensure_directories():
    """Create Status directory if missing."""
    STATUS_DIR.mkdir(parents=True, exist_ok=True)


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
    Find tasks in Needs_Action that have a plan but no approval.
    These are waiting for human approval.
    """
    waiting = []
    
    needs_action_files = list_files(NEEDS_ACTION_DIR)
    
    for filename in needs_action_files:
        task_name = get_task_name(filename)
        
        # Check if plan exists
        plan_path = PLANS_DIR / f"{task_name}.plan.md"
        has_plan = plan_path.exists()
        
        # Check if approval exists
        approval_path = APPROVALS_DIR / f"{task_name}.approved"
        has_approval = approval_path.exists()
        
        # Waiting for approval = has plan but no approval
        if has_plan and not has_approval:
            waiting.append(filename)
    
    return waiting


def generate_snapshot() -> dict:
    """
    Generate a complete status snapshot of the system.
    Returns a dictionary with all state information.
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "needs_action": list_files(NEEDS_ACTION_DIR),
        "waiting_for_approval": get_waiting_for_approval(),
        "approved": list_files(APPROVED_DIR),
        "in_progress": list_files(IN_PROGRESS_DIR),
        "completed": list_files(COMPLETED_DIR),
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


def run_status_snapshot():
    """Main function to generate and save the status snapshot."""
    print("\n" + "=" * 50)
    print("📊 Status Snapshot Agent")
    print("=" * 50 + "\n")
    
    # Ensure Status directory exists
    try:
        ensure_directories()
    except Exception as e:
        print(f"❌ Failed to create Status directory: {e}")
        return
    
    # Generate snapshot
    snapshot = generate_snapshot()
    
    # Write snapshot file
    if write_snapshot(snapshot):
        print(f"✅ Snapshot saved to: {SNAPSHOT_FILE.name}")
    else:
        return
    
    # Display summary
    print("\n" + "-" * 50)
    print("📋 Current System State:")
    print("-" * 50)
    print(f"  Needs Action:          {len(snapshot['needs_action'])} task(s)")
    print(f"  Waiting for Approval:  {len(snapshot['waiting_for_approval'])} task(s)")
    print(f"  Approved:              {len(snapshot['approved'])} task(s)")
    print(f"  In Progress:           {len(snapshot['in_progress'])} task(s)")
    print(f"  Completed:             {len(snapshot['completed'])} task(s)")
    print(f"  Failed:                {len(snapshot['failed'])} task(s)")
    print("-" * 50)
    
    # Show details if any tasks exist
    if any([
        snapshot['needs_action'],
        snapshot['waiting_for_approval'],
        snapshot['approved'],
        snapshot['in_progress'],
        snapshot['completed'],
        snapshot['failed'],
    ]):
        print("\n📝 Details:")
        
        if snapshot['needs_action']:
            print("\n  Needs Action:")
            for f in snapshot['needs_action']:
                print(f"    - {f}")
        
        if snapshot['waiting_for_approval']:
            print("\n  Waiting for Approval:")
            for f in snapshot['waiting_for_approval']:
                print(f"    - {f}")
        
        if snapshot['approved']:
            print("\n  Approved:")
            for f in snapshot['approved']:
                print(f"    - {f}")
        
        if snapshot['in_progress']:
            print("\n  In Progress:")
            for f in snapshot['in_progress']:
                print(f"    - {f}")
        
        if snapshot['completed']:
            print("\n  Completed:")
            for f in snapshot['completed']:
                print(f"    - {f}")
        
        if snapshot['failed']:
            print("\n  Failed:")
            for f in snapshot['failed']:
                print(f"    - {f}")
    
    print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    run_status_snapshot()
