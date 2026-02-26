#!/usr/bin/env python3
"""
Plan Generator - Creates Plan.md files for tasks in Needs_Action/
"""

import os
import re
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_plan_for_task(task_file_path, vault_path):
    """
    Create a Plan.md file for a task in Needs_Action/

    Args:
        task_file_path: Path to the task file in Needs_Action/
        vault_path: Path to the AI Employee vault
    """
    task_path = Path(task_file_path)
    vault_path = Path(vault_path)

    # Read the task file
    with open(task_path, 'r', encoding='utf-8') as f:
        task_content = f.read()

    # Extract information from the task file
    task_name = task_path.stem.replace(' ', '_').replace('-', '_')

    # Determine task type from frontmatter if present
    task_type = "general"
    if task_content.startswith('---'):
        # Extract frontmatter
        parts = task_content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            # Look for type in frontmatter
            type_match = re.search(r'type:\s*(.+)', frontmatter)
            if type_match:
                task_type = type_match.group(1).strip()

    # Create Plans directory if it doesn't exist
    plans_dir = vault_path / 'Plans'
    plans_dir.mkdir(exist_ok=True)

    # Generate plan content based on task type
    objective = f"Process the {task_type} task from {task_path.name}"
    steps = []

    if task_type == "email":
        # Extract email details
        from_match = re.search(r'from:\s*(.+)', frontmatter) if 'frontmatter' in locals() else None
        subject_match = re.search(r'subject:\s*(.+)', frontmatter) if 'frontmatter' in locals() else None

        sender = from_match.group(1).strip() if from_match else "Unknown"
        subject = subject_match.group(1).strip() if subject_match else "No Subject"

        objective = f"Process email from {sender} regarding '{subject}'"
        steps = [
            f"- [ ] Review email content from {sender}",
            f"- [ ] Determine appropriate response/action",
            f"- [ ] Draft response if needed",
            f"- [ ] Process through approval workflow if sensitive",
            f"- [ ] Update status and move to Done"
        ]

    elif task_type == "whatsapp_message":
        objective = "Process WhatsApp message requiring attention"
        steps = [
            "- [ ] Review WhatsApp message content",
            "- [ ] Identify urgency level and keywords",
            "- [ ] Determine appropriate response",
            "- [ ] Respond appropriately or escalate",
            "- [ ] Update status and move to Done"
        ]

    else:
        steps = [
            "- [ ] Review task content",
            "- [ ] Determine appropriate action",
            "- [ ] Execute required steps",
            "- [ ] Process through approval workflow if needed",
            "- [ ] Update status and move to Done"
        ]

    # Create approval requirements
    approval_reqs = "Any sensitive actions require human approval"

    # Create plan content
    plan_content = f"""---
created: {datetime.now().isoformat()}
objective: {objective}
status: pending
estimated_completion: 1-2 hours
---

# Plan: {task_name}

## Objective
{objective}

## Step-by-step Checklist
{chr(10).join(steps)}

## Approval Requirements
{approval_reqs}

## Estimated Completion
1-2 hours depending on complexity

## Notes
- Review Company_Handbook.md for guidelines
- Follow Business_Goals.md priorities
- Ensure all sensitive actions go through approval workflow
"""

    # Create plan file name
    plan_filename = f"Plan_{task_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    plan_path = plans_dir / plan_filename

    # Write the plan file
    with open(plan_path, 'w', encoding='utf-8') as f:
        f.write(plan_content)

    logger.info(f"Created plan file: {plan_path}")
    return plan_path

def monitor_needs_action_for_plans(vault_path):
    """
    Monitor Needs_Action/ folder and create plans for new files
    """
    vault_path = Path(vault_path)
    needs_action_dir = vault_path / 'Needs_Action'

    # Create plan for each file in Needs_Action that doesn't have a corresponding plan
    for task_file in needs_action_dir.glob('*.md'):
        # Check if a plan already exists for this task
        task_name = task_file.stem.replace(' ', '_').replace('-', '_')

        # Look for existing plans with similar names
        existing_plans = list((vault_path / 'Plans').glob(f'*{task_name}*'))

        if not existing_plans:
            try:
                create_plan_for_task(task_file, vault_path)
            except Exception as e:
                logger.error(f"Error creating plan for {task_file}: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Plan Generator for AI Employee')
    parser.add_argument('--vault-path', default='./AI_Employee_Vault', help='Path to AI Employee vault')
    parser.add_argument('--task-file', help='Specific task file to create plan for')

    args = parser.parse_args()

    if args.task_file:
        # Create plan for specific file
        create_plan_for_task(args.task_file, args.vault_path)
    else:
        # Monitor entire Needs_Action folder
        monitor_needs_action_for_plans(args.vault_path)