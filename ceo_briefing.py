"""
CEO Monday Morning Briefing Generator
Autonomously audits your business every week and generates a briefing.
Part of the AI Employee system - proactive intelligence layer.

Run manually or schedule via Task Scheduler every Monday at 8am.
Usage: py ceo_briefing.py
"""

import json
import re
import os
from datetime import datetime, timedelta
from pathlib import Path


# ── Configuration ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DONE_DIR = BASE_DIR / "Done"
FAILED_DIR = BASE_DIR / "Failed"
PENDING_DIR = BASE_DIR / "Pending_Approval"
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
PLANS_DIR = BASE_DIR / "Plans"
BRIEFINGS_DIR = BASE_DIR / "Briefings"
LOGS_DIR = BASE_DIR / "Logs"
BUSINESS_GOALS_FILE = BASE_DIR / "Business_Goals.md"
ACCOUNTING_FILE = BASE_DIR / "Accounting" / "Current_Month.md"
STATUS_FILE = BASE_DIR / "Status" / "status_snapshot.json"


# ── Data Collection ───────────────────────────────────────────────────────────
def get_tasks_completed_this_week() -> list:
    """Get all tasks completed in the last 7 days."""
    completed = []
    week_ago = datetime.now() - timedelta(days=7)

    if not DONE_DIR.exists():
        return completed

    for f in DONE_DIR.glob("*.md"):
        if f.name == ".gitkeep":
            continue
        try:
            modified = datetime.fromtimestamp(f.stat().st_mtime)
            if modified >= week_ago:
                completed.append({
                    "name": f.stem,
                    "file": f.name,
                    "completed_at": modified.strftime("%Y-%m-%d %H:%M")
                })
        except Exception:
            pass

    return completed


def get_failed_tasks_this_week() -> list:
    """Get all tasks that failed in the last 7 days."""
    failed = []
    week_ago = datetime.now() - timedelta(days=7)

    if not FAILED_DIR.exists():
        return failed

    for f in FAILED_DIR.glob("*.md"):
        if f.name == ".gitkeep":
            continue
        try:
            modified = datetime.fromtimestamp(f.stat().st_mtime)
            if modified >= week_ago:
                failed.append({
                    "name": f.stem,
                    "file": f.name,
                    "failed_at": modified.strftime("%Y-%m-%d %H:%M")
                })
        except Exception:
            pass

    return failed


def get_pending_approvals() -> list:
    """Get all tasks currently waiting for human approval."""
    pending = []
    if not PENDING_DIR.exists():
        return pending

    for f in PENDING_DIR.glob("*.md"):
        if f.name == ".gitkeep":
            continue
        try:
            age_hours = (datetime.now() - datetime.fromtimestamp(
                f.stat().st_mtime
            )).seconds // 3600
            pending.append({
                "name": f.stem,
                "file": f.name,
                "age_hours": age_hours
            })
        except Exception:
            pass

    return pending


def get_needs_action() -> list:
    """Get all tasks currently in Needs_Action."""
    tasks = []
    if not NEEDS_ACTION_DIR.exists():
        return tasks

    for f in NEEDS_ACTION_DIR.glob("*.md"):
        if f.name == ".gitkeep":
            continue
        tasks.append(f.stem)

    return tasks


def read_business_goals() -> str:
    """Read business goals from vault."""
    if BUSINESS_GOALS_FILE.exists():
        return BUSINESS_GOALS_FILE.read_text(encoding="utf-8")
    return "No business goals file found. Create Business_Goals.md in vault root."


def read_accounting() -> str:
    """Read current month accounting data."""
    if ACCOUNTING_FILE.exists():
        return ACCOUNTING_FILE.read_text(encoding="utf-8")
    return "No accounting data found."


def load_status_snapshot() -> dict:
    """Load latest status snapshot."""
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def analyze_bottlenecks(failed: list, pending: list) -> list:
    """Identify bottlenecks from failed and long-pending tasks."""
    bottlenecks = []

    for task in failed:
        bottlenecks.append({
            "type": "Failed Task",
            "task": task["name"],
            "detail": f"Task failed at {task['failed_at']}"
        })

    for task in pending:
        if task["age_hours"] > 24:
            bottlenecks.append({
                "type": "Stale Approval",
                "task": task["name"],
                "detail": f"Waiting {task['age_hours']} hours for approval"
            })

    return bottlenecks


def generate_suggestions(bottlenecks: list, pending: list, goals: str) -> list:
    """Generate proactive suggestions based on system state."""
    suggestions = []

    if len(pending) > 5:
        suggestions.append(
            f"You have {len(pending)} tasks waiting for approval. "
            f"Consider reviewing Pending_Approval/ to unblock the pipeline."
        )

    if len(bottlenecks) > 0:
        suggestions.append(
            f"{len(bottlenecks)} bottleneck(s) detected this week. "
            f"Review Failed/ folder and resolve stale approvals."
        )

    if "gmail" in goals.lower() or "email" in goals.lower():
        suggestions.append(
            "Gmail watcher is configured. Ensure credentials are refreshed monthly."
        )

    suggestions.append(
        "Run `py ralph_wiggum.py` to autonomously process all pending tasks."
    )

    return suggestions


# ── Briefing Generator ────────────────────────────────────────────────────────
def generate_briefing() -> str:
    """Generate the full CEO Monday Morning Briefing."""

    print("Generating CEO Monday Morning Briefing...")

    # Collect all data
    completed = get_tasks_completed_this_week()
    failed = get_failed_tasks_this_week()
    pending = get_pending_approvals()
    needs_action = get_needs_action()
    goals = read_business_goals()
    accounting = read_accounting()
    snapshot = load_status_snapshot()
    bottlenecks = analyze_bottlenecks(failed, pending)
    suggestions = generate_suggestions(bottlenecks, pending, goals)

    # Date range
    now = datetime.now()
    week_start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    week_end = now.strftime("%Y-%m-%d")

    # Performance score (simple metric)
    total_tasks = len(completed) + len(failed)
    success_rate = (len(completed) / total_tasks * 100) if total_tasks > 0 else 0

    # Format sections
    completed_list = "\n".join(
        f"- [x] {t['name']} (completed {t['completed_at']})"
        for t in completed
    ) if completed else "- No tasks completed this week"

    failed_list = "\n".join(
        f"- [!] {t['name']} (failed {t['failed_at']})"
        for t in failed
    ) if failed else "- No failed tasks this week"

    pending_list = "\n".join(
        f"- [ ] {t['name']} (waiting {t['age_hours']}h)"
        for t in pending
    ) if pending else "- No pending approvals"

    needs_action_list = "\n".join(
        f"- {t}" for t in needs_action
    ) if needs_action else "- Queue is clear"

    bottleneck_list = "\n".join(
        f"- **{b['type']}**: {b['task']} — {b['detail']}"
        for b in bottlenecks
    ) if bottlenecks else "- No bottlenecks detected"

    suggestions_list = "\n".join(
        f"{i+1}. {s}"
        for i, s in enumerate(suggestions)
    ) if suggestions else "1. System running smoothly. No action required."

    briefing = f"""# Monday Morning CEO Briefing
**Period:** {week_start} to {week_end}
**Generated:** {now.strftime("%Y-%m-%d %H:%M:%S")}
**AI Employee Version:** v1.0

---

## Executive Summary

Your AI Employee processed **{total_tasks} tasks** this week with a **{success_rate:.0f}% success rate**.
There are currently **{len(pending)} tasks awaiting your approval** and **{len(needs_action)} new items** in the queue.

---

## System Performance

| Metric | Value |
|--------|-------|
| Tasks Completed | {len(completed)} |
| Tasks Failed | {len(failed)} |
| Success Rate | {success_rate:.0f}% |
| Pending Approval | {len(pending)} |
| Needs Action | {len(needs_action)} |

---

## Completed This Week
{completed_list}

---

## Failed This Week
{failed_list}

---

## Awaiting Your Approval
{pending_list}

> **Action Required:** Review `Pending_Approval/` folder and move approved tasks to `Approved/`

---

## Current Queue (Needs Action)
{needs_action_list}

---

## Bottlenecks Identified
{bottleneck_list}

---

## Proactive Suggestions
{suggestions_list}

---

## Business Goals Reference
{goals[:500] + "..." if len(goals) > 500 else goals}

---

## Accounting Summary
{accounting[:300] + "..." if len(accounting) > 300 else accounting}

---

*Generated autonomously by AI Employee v1.0*
*Next briefing: {(now + timedelta(days=7)).strftime("%Y-%m-%d")} (Monday)*
"""

    return briefing


def save_briefing(briefing: str) -> Path:
    """Save briefing to Briefings folder."""
    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_Monday_Briefing")
    filepath = BRIEFINGS_DIR / f"{timestamp}.md"
    filepath.write_text(briefing, encoding="utf-8")
    return filepath


def main():
    print("\n" + "=" * 60)
    print("CEO MONDAY MORNING BRIEFING GENERATOR")
    print("=" * 60 + "\n")

    briefing = generate_briefing()
    filepath = save_briefing(briefing)

    print(f"Briefing saved: {filepath}")
    print(f"Open in Obsidian: Briefings/{filepath.name}")
    print("\n" + "=" * 60)
    print("BRIEFING PREVIEW")
    print("=" * 60)
    print(briefing[:500] + "...")


if __name__ == "__main__":
    main()