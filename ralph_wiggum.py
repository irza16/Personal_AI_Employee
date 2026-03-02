#!/usr/bin/env python3
"""
Ralph Wiggum Autonomous Loop - Continuous execution until task completion
"""

import os
import json
import logging
import subprocess
import sys
import shutil
import platform
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ralph_wiggum.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RalphWiggum:
    def __init__(self, task_description, vault_path=None, max_iterations=10):
        """
        Initialize Ralph Wiggum Autonomous Loop

        Args:
            task_description: Description of the task to be completed
            vault_path: Path to the AI Employee vault
            max_iterations: Maximum number of iterations before stopping
        """
        self.task_description = task_description
        self.vault_path = Path(vault_path) if vault_path else Path(os.getenv('VAULT_PATH', './AI_Employee_Vault'))
        self.max_iterations = max_iterations
        self.plans_path = self.vault_path / 'Plans'
        self.logs_path = self.vault_path / 'Logs'
        self.done_path = self.vault_path / 'Done'

        # Create directories if they don't exist
        self.plans_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.done_path.mkdir(parents=True, exist_ok=True)

    def create_state_file(self):
        """Create a state file in Plans/ tracking current iteration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"RALPH_WIGGUM_STATE_{timestamp}.json"
        filepath = self.plans_path / filename

        state = {
            "task_description": self.task_description,
            "created_at": datetime.now().isoformat(),
            "current_iteration": 0,
            "max_iterations": self.max_iterations,
            "status": "initialized",
            "history": []
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)

        logger.info(f"Created Ralph Wiggum state file: {filepath}")
        return filepath

    def run_claude_iteration(self, context=""):
        """Run Claude Code in a loop using direct HTTP call to local router."""
        try:
            # Prepare the prompt for Claude
            prompt = f"""
            Task: {self.task_description}

            Context from previous iteration:
            {context}

            Please continue working on this task. If you believe the task is complete, please respond with:
            <promise>TASK_COMPLETE</promise>

            Otherwise, continue working on the task and provide updates.
            """

            # Initialize OpenAI client pointing to local Claude Code Router
            client = OpenAI(
                api_key="k7dMEzvLfFSAoBJpDp2e0ayX2ps21E8K2WmysqTdOEYzPvV644BWjAI6jZIqECIDn2qhZQ6fjIa95lUJdSHr1g",
                base_url="http://127.0.0.1:3456/v1"
            )

            # Create messages for the API call
            messages = [
                {
                    "role": "system",
                    "content": f"You are an AI Employee managing an Obsidian vault at {self.vault_path}. Complete the task and end with <promise>TASK_COMPLETE</promise> when fully done."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            # Call the Claude Code Router API
            response = client.chat.completions.create(
                model="claude-3-5-sonnet-20241022",
                messages=messages,
                max_tokens=2000
            )

            output = response.choices[0].message.content

            logger.info(f"Claude iteration completed successfully")
            logger.debug(f"Claude response: {output[:500]}...")  # Log first 500 chars for debugging

            return output

        except Exception as e:
            logger.error(f"Claude iteration failed: {e}")
            return f"Error: {str(e)}"

    def check_completion_condition(self, claude_output, completion_file=None):
        """Check if completion condition is met."""
        # Check for promise-based completion
        if "<promise>TASK_COMPLETE</promise>" in claude_output or "TASK_COMPLETE" in claude_output:
            logger.info("Task completion promise found in Claude output")
            return True

        # Check for file-based completion
        if completion_file:
            completion_path = self.done_path / completion_file
            if completion_path.exists():
                logger.info(f"Completion file found: {completion_path}")
                return True

        return False

    def update_state_file(self, state_file, iteration, claude_output, status):
        """Update the state file with the current iteration."""
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            state['current_iteration'] = iteration
            state['status'] = status
            state['history'].append({
                'iteration': iteration,
                'timestamp': datetime.now().isoformat(),
                'output': claude_output[:500] + "..." if len(claude_output) > 500 else claude_output  # Truncate long outputs
            })

            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)

            logger.info(f"Updated state file: {state_file}")
        except Exception as e:
            logger.error(f"Error updating state file: {e}")

    def log_iteration(self, iteration, claude_output):
        """Log each iteration to Logs/ralph_wiggum_{task}_{date}.json."""
        log_filename = f"ralph_wiggum_{self.task_description.replace(' ', '_')[:50]}_{datetime.now().strftime('%Y-%m-%d')}.json"
        log_path = self.logs_path / log_filename

        log_entry = {
            "iteration": iteration,
            "timestamp": datetime.now().isoformat(),
            "task_description": self.task_description,
            "claude_output": claude_output,
            "status": "completed"
        }

        # Load existing logs or create new list
        existing_logs = []
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    existing_logs = json.load(f)
            except:
                existing_logs = []

        existing_logs.append(log_entry)

        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(existing_logs, f, indent=2)

        logger.info(f"Logged iteration {iteration} to: {log_path}")

    def run_loop(self, completion_file=None):
        """Run the Ralph Wiggum autonomous loop."""
        logger.info(f"Starting Ralph Wiggum loop for task: {self.task_description}")
        logger.info(f"Max iterations: {self.max_iterations}")

        # Create state file
        state_file = self.create_state_file()

        # Initialize context for Claude
        context = f"Starting new task: {self.task_description}\n\nThis is an autonomous loop that will continue until the task is complete."

        # Run the loop
        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"Iteration {iteration}/{self.max_iterations}")

            # Run Claude iteration
            claude_output = self.run_claude_iteration(context)

            # Log the iteration
            self.log_iteration(iteration, claude_output)

            # Check completion condition
            if self.check_completion_condition(claude_output, completion_file):
                logger.info(f"Task completed successfully at iteration {iteration}")
                self.update_state_file(state_file, iteration, claude_output, "completed_successfully")
                return True

            # Update state file
            self.update_state_file(state_file, iteration, claude_output, "continuing")

            # Prepare context for next iteration
            context = f"""
Previous iteration output:
{claude_output}

Continue working on the task: {self.task_description}
"""

            # Small delay between iterations to prevent overwhelming Claude
            import time
            time.sleep(2)

        # If we reach here, max iterations were exceeded
        logger.warning(f"Max iterations ({self.max_iterations}) exceeded without task completion")
        self.update_state_file(state_file, self.max_iterations, "Max iterations exceeded", "completed_max_iterations")
        return False

def main():
    """Main function to run the Ralph Wiggum loop."""
    import argparse

    parser = argparse.ArgumentParser(description='Ralph Wiggum Autonomous Loop for AI Employee')
    parser.add_argument('task_description', nargs='?', help='Description of the task to be completed')
    parser.add_argument('--vault-path', default='./AI_Employee_Vault', help='Path to AI Employee vault')
    parser.add_argument('--completion-file', help='File name to monitor for completion (file-based completion)')
    parser.add_argument('--max-iterations', type=int, default=10, help='Maximum number of iterations (default: 10)')
    parser.add_argument('--task', help='Alternative way to specify task description')

    args = parser.parse_args()

    # Use either the positional argument or the --task option for task description
    task_description = args.task_description or args.task

    if not task_description:
        print("Error: Task description is required. Use either positional argument or --task option.")
        print("Usage: python ralph_wiggum.py \"Task description here\"")
        print("   or: python ralph_wiggum.py --task \"Task description here\"")
        sys.exit(1)

    wiggum = RalphWiggum(
        task_description=task_description,
        vault_path=args.vault_path,
        max_iterations=args.max_iterations
    )

    success = wiggum.run_loop(completion_file=args.completion_file)

    if success:
        logger.info("Ralph Wiggum loop completed successfully")
        sys.exit(0)
    else:
        logger.warning("Ralph Wiggum loop completed without task completion")
        sys.exit(1)

if __name__ == '__main__':
    main()