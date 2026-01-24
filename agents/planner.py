"""
Planner Agent
Automatically generates structured execution plans for tasks in the Needs_Action directory.
Part of the AI Employee system.
"""

import os
import re
import logging
from datetime import datetime
from pathlib import Path


# Configuration
BASE_DIR = Path(__file__).parent.parent
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
PLANS_DIR = BASE_DIR / "Plans"
LOG_FILE = BASE_DIR / "Logs" / "activity.log"


def setup_logging() -> logging.Logger:
    """Configure and return the logger instance."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("planner_agent")
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # File handler
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def extract_task_name(filename: str, content: str) -> str:
    """Extract task name from content or derive from filename."""
    # Try to find a markdown heading
    heading_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if heading_match:
        return heading_match.group(1).strip()
    
    # Fall back to filename without extension
    name = Path(filename).stem
    # Convert task_something_here to "Something Here"
    name = name.replace("task_", "").replace("_", " ").title()
    return name


def extract_objective(content: str, task_name: str) -> str:
    """Extract or generate objective from task content."""
    # Look for objective/goal/purpose section
    objective_patterns = [
        r'##?\s*(?:Objective|Goal|Purpose)\s*\n+(.+?)(?:\n#|\n\n|\Z)',
        r'##?\s*(?:Summary|Overview|Description)\s*\n+(.+?)(?:\n#|\n\n|\Z)',
    ]
    
    for pattern in objective_patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            objective = match.group(1).strip()
            # Clean up and take first sentence/paragraph
            objective = objective.split('\n')[0].strip()
            if objective:
                return objective
    
    # Try to get first paragraph after heading
    first_para_match = re.search(r'^#.+\n+(.+?)(?:\n\n|\n#|\Z)', content, re.MULTILINE | re.DOTALL)
    if first_para_match:
        para = first_para_match.group(1).strip()
        if para and not para.startswith('#') and not para.startswith('-'):
            return para.split('\n')[0].strip()
    
    # Default objective
    return f"Complete the {task_name} task as specified in the requirements."


def extract_required_information(content: str) -> list:
    """Extract or infer required information from task content."""
    required_info = []
    
    # Look for explicit requirements section
    req_match = re.search(
        r'##?\s*(?:Requirements?|Required|Needs|Prerequisites?)\s*\n+((?:[-*]\s*.+\n?)+)',
        content,
        re.IGNORECASE
    )
    if req_match:
        items = re.findall(r'[-*]\s*(.+)', req_match.group(1))
        required_info.extend([item.strip() for item in items[:5]])
    
    # Look for questions or missing info indicators
    question_patterns = [
        r'\?(?:\s|$)',  # Questions
        r'(?:need|require|missing|unclear|TBD|TODO)',  # Keywords
    ]
    
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if any(re.search(p, line, re.IGNORECASE) for p in question_patterns):
            if line and len(line) > 10 and line not in required_info:
                # Clean up the line
                clean_line = re.sub(r'^[-*#>\s]+', '', line).strip()
                if clean_line and len(required_info) < 5:
                    required_info.append(clean_line)
    
    # Add default items if none found
    if not required_info:
        required_info = [
            "Stakeholder confirmation on scope",
            "Access to required resources/systems",
            "Timeline and deadline constraints",
            "Budget or resource limitations (if applicable)",
        ]
    
    return required_info


def generate_plan_content(filename: str, content: str) -> str:
    """Generate the structured execution plan markdown content."""
    task_name = extract_task_name(filename, content)
    objective = extract_objective(content, task_name)
    required_info = extract_required_information(content)
    generated_on = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Format required information as bullet points
    required_info_formatted = "\n".join(f"- {item}" for item in required_info)
    
    plan_content = f"""# Execution Plan: {task_name}

## Task Reference
- Task File: {filename}
- Generated On: {generated_on}

## Objective
{objective}

## Required Information
{required_info_formatted}

## Execution Steps
### Phase 1: Understanding
- Review task requirements
- Identify ambiguities

### Phase 2: Preparation
- Gather required data
- Validate assumptions

### Phase 3: Human Approval
- Pause and wait for approval before external action

### Phase 4: Execution
- Perform approved actions
- Confirm completion

## Success Criteria
- Task completed correctly
- Approval recorded
- Task ready to move to Done
"""
    
    return plan_content


def get_plan_filename(task_filename: str) -> str:
    """Generate plan filename from task filename."""
    stem = Path(task_filename).stem
    return f"{stem}.plan.md"


def process_task_file(task_path: Path, logger: logging.Logger) -> bool:
    """Process a single task file and generate its plan."""
    task_filename = task_path.name
    plan_filename = get_plan_filename(task_filename)
    plan_path = PLANS_DIR / plan_filename
    
    # Check if plan already exists
    if plan_path.exists():
        logger.info(f"Plan already exists, skipping: {plan_filename}")
        print(f"⏭️  Skipped (plan exists): {task_filename}")
        return False
    
    # Read task content
    try:
        content = task_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to read task file {task_filename}: {e}")
        print(f"❌ Error reading: {task_filename}")
        return False
    
    # Generate plan content
    plan_content = generate_plan_content(task_filename, content)
    
    # Save plan file
    try:
        PLANS_DIR.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(plan_content, encoding="utf-8")
        logger.info(f"Generated plan: {plan_filename} from {task_filename}")
        print(f"✅ Generated plan: {plan_filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to write plan file {plan_filename}: {e}")
        print(f"❌ Error writing plan: {plan_filename}")
        return False


def run_planner():
    """Main function to process all tasks and generate plans."""
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("Planner Agent started")
    logger.info(f"Scanning: {NEEDS_ACTION_DIR}")
    logger.info(f"Output: {PLANS_DIR}")
    logger.info("=" * 60)
    
    print("\n" + "=" * 50)
    print("🤖 Planner Agent - Execution Plan Generator")
    print("=" * 50 + "\n")
    
    # Ensure directories exist
    NEEDS_ACTION_DIR.mkdir(parents=True, exist_ok=True)
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find all .md files in Needs_Action
    task_files = list(NEEDS_ACTION_DIR.glob("*.md"))
    
    if not task_files:
        logger.info("No task files found in Needs_Action directory")
        print("📭 No task files found in Needs_Action directory")
        return
    
    logger.info(f"Found {len(task_files)} task file(s) to process")
    print(f"📋 Found {len(task_files)} task file(s)\n")
    
    # Process each task file
    generated_count = 0
    skipped_count = 0
    error_count = 0
    
    for task_path in sorted(task_files):
        result = process_task_file(task_path, logger)
        if result:
            generated_count += 1
        elif result is False and (PLANS_DIR / get_plan_filename(task_path.name)).exists():
            skipped_count += 1
        else:
            error_count += 1
    
    # Summary
    print("\n" + "-" * 50)
    print(f"📊 Summary: {generated_count} generated, {skipped_count} skipped, {error_count} errors")
    print("-" * 50 + "\n")
    
    logger.info(f"Planner Agent completed: {generated_count} generated, {skipped_count} skipped, {error_count} errors")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_planner()
