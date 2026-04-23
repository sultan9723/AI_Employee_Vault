"""
Ralph Wiggum Loop
Autonomous multi-step task completion engine.
Keeps Claude working until a task is complete or max iterations reached.

Pattern: Task → Claude works → Check completion → Not done? → Loop again
Named after Ralph Wiggum's persistence: "I'm still here!"

Usage:
    py ralph_wiggum.py "Process all files in Needs_Action"
    py ralph_wiggum.py "Generate CEO briefing for this week"
"""

import os
import sys
import time
import subprocess
import logging
import json
from datetime import datetime
from pathlib import Path


# ── Configuration ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "Logs"
LOG_FILE = LOGS_DIR / "ralph_wiggum.log"
STATE_DIR = BASE_DIR / "Status"
STATE_FILE = STATE_DIR / "ralph_state.json"
DONE_DIR = BASE_DIR / "Done"
IN_PROGRESS_DIR = BASE_DIR / "In_Progress"

MAX_ITERATIONS = 10
ITERATION_DELAY = 5  # seconds between iterations
COMPLETION_TOKEN = "TASK_COMPLETE"


# ── Logging ───────────────────────────────────────────────────────────────────
def setup_logging() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ralph_wiggum")
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


# ── State Management ──────────────────────────────────────────────────────────
def save_state(task: str, iteration: int, status: str, history: list):
    """Save current loop state to disk."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "task": task,
        "iteration": iteration,
        "status": status,
        "history": history,
        "timestamp": datetime.now().isoformat()
    }
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def load_state() -> dict:
    """Load previous loop state from disk."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def clear_state():
    """Clear state after successful completion."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()


# ── Completion Checkers ───────────────────────────────────────────────────────
def check_output_for_completion(output: str) -> bool:
    """Check if Claude's output contains the completion token."""
    return COMPLETION_TOKEN in output


def check_needs_action_empty() -> bool:
    """Check if Needs_Action folder is empty (all tasks processed)."""
    if not BASE_DIR.joinpath("Needs_Action").exists():
        return True
    files = [
        f for f in BASE_DIR.joinpath("Needs_Action").glob("*.md")
        if f.name != ".gitkeep"
    ]
    return len(files) == 0


def check_task_file_in_done(task_filename: str) -> bool:
    """Check if a specific task file has been moved to Done."""
    done_path = DONE_DIR / task_filename
    return done_path.exists()


# ── Pipeline Runner ───────────────────────────────────────────────────────────
def run_full_pipeline(logger: logging.Logger) -> tuple:
    """
    Run the full agent pipeline once.
    Returns (success, output) tuple.
    """
    agents = [
        "agents/planner.py",
        "agents/decision_maker.py",
        "agents/approval_gate.py",
        "agents/approved_watcher.py",
        "agents/email_dispatcher.py",
        "agents/webhook_dispatcher.py",
        "agents/status_snapshot.py",
    ]

    all_output = []
    all_success = True

    for agent_path in agents:
        full_path = BASE_DIR / agent_path
        if not full_path.exists():
            continue
        try:
            result = subprocess.run(
                [sys.executable, str(full_path)],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=60
            )
            all_output.append(result.stdout)
            if result.returncode != 0:
                all_success = False
                logger.warning(f"Agent failed: {agent_path}")
        except Exception as e:
            logger.error(f"Agent error {agent_path}: {e}")
            all_success = False

    return all_success, "\n".join(all_output)


# ── Completion Strategy ───────────────────────────────────────────────────────
def is_task_complete(task: str, output: str, iteration: int) -> tuple:
    """
    Multi-strategy completion check.
    Returns (is_complete, reason).
    """
    # Strategy 1: Explicit completion token in output
    if check_output_for_completion(output):
        return True, f"Completion token found in output"

    # Strategy 2: Needs_Action is empty (all tasks processed)
    if check_needs_action_empty():
        return True, "All tasks processed - Needs_Action is empty"

    # Strategy 3: Task mentions specific file — check if it's in Done
    words = task.split()
    for word in words:
        if word.endswith(".md") and check_task_file_in_done(word):
            return True, f"Task file {word} found in Done/"

    # Strategy 4: Max iterations safety net
    if iteration >= MAX_ITERATIONS:
        return True, f"Max iterations ({MAX_ITERATIONS}) reached"

    return False, "Task not yet complete"


# ── Main Ralph Wiggum Loop ────────────────────────────────────────────────────
def ralph_loop(task: str, logger: logging.Logger):
    """
    Main autonomous loop.
    Keeps running until task is complete or max iterations reached.
    """
    print("\n" + "=" * 60)
    print("RALPH WIGGUM LOOP")
    print("=" * 60)
    print(f"Task: {task}")
    print(f"Max iterations: {MAX_ITERATIONS}")
    print(f"Completion token: {COMPLETION_TOKEN}")
    print("=" * 60 + "\n")

    logger.info("=" * 60)
    logger.info("Ralph Wiggum Loop started")
    logger.info(f"Task: {task}")
    logger.info("=" * 60)

    history = []
    start_time = datetime.now()

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n--- Iteration {iteration}/{MAX_ITERATIONS} ---")
        logger.info(f"Iteration {iteration} started")

        # Save state
        save_state(task, iteration, "running", history)

        # Run the full pipeline
        print(f"Running pipeline...")
        success, output = run_full_pipeline(logger)

        # Record this iteration
        history.append({
            "iteration": iteration,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "output_preview": output[:200] if output else ""
        })

        # Check completion
        complete, reason = is_task_complete(task, output, iteration)

        if complete:
            print(f"\nTASK COMPLETE after {iteration} iteration(s)")
            print(f"Reason: {reason}")
            print(f"Time taken: {(datetime.now() - start_time).seconds}s")

            logger.info(f"Task complete after {iteration} iterations: {reason}")
            save_state(task, iteration, "complete", history)

            # Write completion summary
            summary_path = BASE_DIR / "Briefings" / f"ralph_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary = f"""# Ralph Wiggum Loop - Task Complete

## Task
{task}

## Result
- Status: COMPLETE
- Iterations: {iteration}/{MAX_ITERATIONS}
- Reason: {reason}
- Duration: {(datetime.now() - start_time).seconds}s
- Completed: {datetime.now().isoformat()}

## Iteration History
{chr(10).join(f"- Iteration {h['iteration']}: {'OK' if h['success'] else 'FAILED'} at {h['timestamp']}" for h in history)}
"""
            summary_path.write_text(summary, encoding="utf-8")
            print(f"Summary saved: {summary_path.name}")
            clear_state()
            return True

        print(f"Not complete yet: {reason}")
        print(f"Waiting {ITERATION_DELAY}s before next iteration...")
        logger.info(f"Iteration {iteration} done — not complete: {reason}")
        time.sleep(ITERATION_DELAY)

    # Max iterations reached without completion
    print(f"\nMax iterations reached. Task may be incomplete.")
    logger.warning(f"Ralph loop ended at max iterations for task: {task}")
    save_state(task, MAX_ITERATIONS, "max_iterations", history)
    return False


# ── Entry Point ───────────────────────────────────────────────────────────────
def main():
    logger = setup_logging()

    # Get task from command line or use default
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = "Process all tasks in Needs_Action and move completed ones to Done"

    success = ralph_loop(task, logger)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()