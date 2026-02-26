"""
Orchestrator for AI Employee

This script manages the various components of the AI Employee system,
including starting the file watcher and coordinating tasks.
"""

import subprocess
import sys
import os
import signal
import time
from pathlib import Path
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_employee_orchestrator.log'),
        logging.StreamHandler()
    ]
)

class AIEmployeeOrchestrator:
    """Manages the AI Employee system components"""

    def __init__(self, vault_path=None):
        self.processes = []
        self.running = False
        self.vault_path = Path(vault_path) if vault_path else Path('./AI_Employee_Vault')
        self.approved_path = self.vault_path / 'Approved'
        self.rejected_path = self.vault_path / 'Rejected'
        self.done_path = self.vault_path / 'Done'
        self.logs_path = self.vault_path / 'Logs'

        # Create directories if they don't exist
        self.approved_path.mkdir(parents=True, exist_ok=True)
        self.rejected_path.mkdir(parents=True, exist_ok=True)
        self.done_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)

    def start_filesystem_watcher(self):
        """Start the filesystem watcher process"""
        try:
            # Start the filesystem watcher as a subprocess
            watcher_process = subprocess.Popen([
                sys.executable, 'filesystem_watcher.py'
            ])

            self.processes.append(watcher_process)
            logging.info("Filesystem watcher started with PID: {}".format(watcher_process.pid))
            return watcher_process

        except Exception as e:
            logging.error(f"Failed to start filesystem watcher: {str(e)}")
            return None

    def start_gmail_watcher(self):
        """Start the Gmail watcher process"""
        try:
            # Start the Gmail watcher as a subprocess
            gmail_process = subprocess.Popen([
                sys.executable, 'gmail_watcher.py'
            ])

            self.processes.append(gmail_process)
            logging.info("Gmail watcher started with PID: {}".format(gmail_process.pid))
            return gmail_process

        except Exception as e:
            logging.error(f"Failed to start Gmail watcher: {str(e)}")
            return None

    def start_whatsapp_watcher(self):
        """Start the WhatsApp watcher process"""
        try:
            # Start the WhatsApp watcher as a subprocess
            whatsapp_process = subprocess.Popen([
                sys.executable, 'whatsapp_watcher.py'
            ])

            self.processes.append(whatsapp_process)
            logging.info("WhatsApp watcher started with PID: {}".format(whatsapp_process.pid))
            return whatsapp_process

        except Exception as e:
            logging.error(f"Failed to start WhatsApp watcher: {str(e)}")
            return None

    def log_action(self, action_type, actor, target, approval_status, result, parameters=None):
        """Log actions to JSON file"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "actor": actor,
            "target": target,
            "approval_status": approval_status,
            "result": result,
            "parameters": parameters or {}
        }

        log_file = self.logs_path / f"{datetime.now().strftime('%Y-%m-%d')}.json"

        existing_logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    existing_logs = json.load(f)
            except:
                existing_logs = []

        existing_logs.append(log_entry)

        with open(log_file, 'w') as f:
            json.dump(existing_logs, f, indent=2)

    def process_approval_files(self):
        """Process files in the Approved folder"""
        for file_path in self.approved_path.glob('*.md'):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()

                # Determine what type of action this is based on the file content
                if 'send_email' in content.lower():
                    self.handle_email_approval(file_path, content)
                elif 'linkedin_post' in content.lower():
                    self.handle_linkedin_approval(file_path, content)
                else:
                    # Generic approval handler
                    self.handle_generic_approval(file_path, content)

            except Exception as e:
                logging.error(f"Error processing approval file {file_path}: {str(e)}")

    def handle_email_approval(self, file_path, content):
        """Handle email approval by calling the email MCP server"""
        try:
            # Extract email details from the approval file
            import re

            # This is a simplified extraction - in a real implementation, you'd parse the content more thoroughly
            to_match = re.search(r'to:\s*(.+)', content)
            subject_match = re.search(r'subject:\s*(.+)', content)

            if to_match and subject_match:
                to = to_match.group(1).strip()
                subject = subject_match.group(1).strip()

                # In a real implementation, you would call the email MCP server here
                # For now, we'll simulate the action
                logging.info(f"Would send email to: {to}, subject: {subject}")

                # Move the approval file to Done
                done_file = self.done_path / f"APPROVED_EMAIL_{file_path.name}"
                file_path.rename(done_file)

                self.log_action(
                    action_type="email_send",
                    actor="orchestrator",
                    target=to,
                    approval_status="approved",
                    result="completed",
                    parameters={"subject": subject}
                )

                logging.info(f"Email approval processed: {file_path.name}")
            else:
                logging.warning(f"Could not extract email details from: {file_path.name}")

        except Exception as e:
            logging.error(f"Error handling email approval: {str(e)}")
            self.log_action(
                action_type="email_send",
                actor="orchestrator",
                target="unknown",
                approval_status="approved",
                result=f"error: {str(e)}",
                parameters={}
            )

    def handle_linkedin_approval(self, file_path, content):
        """Handle LinkedIn post approval by calling the LinkedIn MCP server"""
        try:
            # In a real implementation, you would call the LinkedIn MCP server here
            # For now, we'll simulate the action
            logging.info(f"Would post to LinkedIn based on: {file_path.name}")

            # Move the approval file to Done
            done_file = self.done_path / f"APPROVED_LINKEDIN_{file_path.name}"
            file_path.rename(done_file)

            self.log_action(
                action_type="linkedin_post",
                actor="orchestrator",
                target="linkedin",
                approval_status="approved",
                result="completed",
                parameters={}
            )

            logging.info(f"LinkedIn approval processed: {file_path.name}")

        except Exception as e:
            logging.error(f"Error handling LinkedIn approval: {str(e)}")
            self.log_action(
                action_type="linkedin_post",
                actor="orchestrator",
                target="linkedin",
                approval_status="approved",
                result=f"error: {str(e)}",
                parameters={}
            )

    def handle_generic_approval(self, file_path, content):
        """Handle generic approval"""
        try:
            # Move the approval file to Done
            done_file = self.done_path / f"APPROVED_{file_path.name}"
            file_path.rename(done_file)

            self.log_action(
                action_type="generic_approval",
                actor="orchestrator",
                target=file_path.name,
                approval_status="approved",
                result="completed",
                parameters={}
            )

            logging.info(f"Generic approval processed: {file_path.name}")

        except Exception as e:
            logging.error(f"Error handling generic approval: {str(e)}")

    def process_rejected_files(self):
        """Process files in the Rejected folder"""
        for file_path in self.rejected_path.glob('*.md'):
            try:
                # Log the rejection
                self.log_action(
                    action_type="rejection",
                    actor="orchestrator",
                    target=file_path.name,
                    approval_status="rejected",
                    result="moved_to_done",
                    parameters={}
                )

                # Move the rejected file to Done
                done_file = self.done_path / f"REJECTED_{file_path.name}"
                file_path.rename(done_file)

                logging.info(f"Rejected file processed: {file_path.name}")

            except Exception as e:
                logging.error(f"Error processing rejected file {file_path}: {str(e)}")

    def check_and_process_folders(self):
        """Check Approved and Rejected folders and process files"""
        self.process_approval_files()
        self.process_rejected_files()

    def check_processes(self):
        """Check if managed processes are still running"""
        for i, process in enumerate(self.processes[:]):
            if process.poll() is not None:
                logging.warning(f"Process {process.pid} has terminated unexpectedly")
                # In a real implementation, we might want to restart the process
                del self.processes[i]

    def run(self):
        """Main run loop for the orchestrator"""
        logging.info("Starting AI Employee Orchestrator...")
        logging.info(f"Monitoring vault: {self.vault_path}")

        # Start the filesystem watcher
        watcher = self.start_filesystem_watcher()
        if not watcher:
            logging.error("Failed to start orchestrator - required processes could not start")
            return

        # Start the Gmail watcher
        gmail_watcher = self.start_gmail_watcher()
        if not gmail_watcher:
            logging.warning("Failed to start Gmail watcher, continuing anyway")

        # Start the WhatsApp watcher
        whatsapp_watcher = self.start_whatsapp_watcher()
        if not whatsapp_watcher:
            logging.warning("Failed to start WhatsApp watcher, continuing anyway")

        self.running = True
        logging.info("AI Employee Orchestrator is now running")

        try:
            while self.running:
                # Check if processes are still running
                self.check_processes()

                # Check for approval and rejection files
                self.check_and_process_folders()

                # Sleep briefly before checking again
                time.sleep(5)

        except KeyboardInterrupt:
            logging.info("Received interrupt signal, shutting down...")
            self.shutdown()

    def shutdown(self):
        """Gracefully shut down all processes"""
        logging.info("Shutting down AI Employee Orchestrator...")

        for process in self.processes:
            if process.poll() is None:  # Process is still running
                logging.info(f"Terminating process {process.pid}")
                process.terminate()

        # Wait a bit for processes to terminate
        time.sleep(2)

        # Force kill if still running
        for process in self.processes:
            if process.poll() is None:
                logging.info(f"Force killing process {process.pid}")
                process.kill()

        self.running = False
        logging.info("All processes terminated")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='AI Employee Orchestrator')
    parser.add_argument('--vault-path', default='./AI_Employee_Vault', help='Path to AI Employee vault')

    args = parser.parse_args()

    orchestrator = AIEmployeeOrchestrator(vault_path=args.vault_path)

    try:
        orchestrator.run()
    except Exception as e:
        logging.error(f"Orchestrator failed with error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()