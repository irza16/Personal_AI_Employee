"""
File System Watcher for AI Employee

This script monitors the AI Employee vault for new files in the Needs_Action folder
and processes them accordingly.
"""

import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_employee_watcher.log'),
        logging.StreamHandler()
    ]
)

class FileWatcherHandler(FileSystemEventHandler):
    """Handles file system events in the vault"""

    def __init__(self, vault_path):
        self.vault_path = Path(vault_path)
        self.needs_action_path = self.vault_path / 'Needs_Action'
        self.inbox_path = self.vault_path / 'Inbox'
        self.done_path = self.vault_path / 'Done'

        # Create directories if they don't exist
        self.needs_action_path.mkdir(exist_ok=True)
        self.inbox_path.mkdir(exist_ok=True)
        self.done_path.mkdir(exist_ok=True)

        logging.info(f"Initialized watcher for vault: {self.vault_path}")
        logging.info(f"Monitoring: {self.needs_action_path}")

    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check if it's in the Needs_Action folder
        if file_path.parent == self.needs_action_path:
            logging.info(f"New action item detected: {file_path.name}")
            self.process_needs_action_file(file_path)

    def on_moved(self, event):
        """Handle file move events"""
        if event.is_directory:
            return

        dest_path = Path(event.dest_path)

        # Check if it was moved to the Done folder
        if dest_path.parent == self.done_path:
            logging.info(f"Completed task: {dest_path.name}")

    def process_needs_action_file(self, file_path):
        """Process a file that requires action"""
        logging.info(f"Processing action file: {file_path.name}")

        # Read the file content
        try:
            content = file_path.read_text(encoding='utf-8')
            logging.info(f"File content preview: {content[:200]}...")

            # Log the action
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"[{timestamp}] Processing file: {file_path.name}"
            logging.info(log_message)

            # In a real implementation, this would trigger Claude Code to process the file
            # For now, we'll just log that it was detected

        except Exception as e:
            logging.error(f"Error processing file {file_path}: {str(e)}")

def main():
    """Main function to start the file watcher"""
    vault_path = Path("AI_Employee_Vault")

    # Create vault directory if it doesn't exist
    vault_path.mkdir(exist_ok=True)

    # Initialize the event handler
    event_handler = FileWatcherHandler(vault_path)

    # Initialize the observer
    observer = Observer()
    observer.schedule(event_handler, str(vault_path), recursive=True)

    # Start the observer
    observer.start()
    logging.info("File watcher started. Monitoring for changes...")

    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("File watcher stopped by user.")

    observer.join()

if __name__ == "__main__":
    main()