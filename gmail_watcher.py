#!/usr/bin/env python3
"""
Gmail Watcher - Monitors Gmail for unread + important messages every 120 seconds
"""

import time
import logging
import os
import json
from pathlib import Path
from datetime import datetime
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import backoff
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Scopes for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gmail_watcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GmailWatcher:
    def __init__(self, vault_path=None, credentials_path=None, check_interval=120):
        """
        Initialize Gmail Watcher

        Args:
            vault_path: Path to the AI Employee vault
            credentials_path: Path to credentials.json
            check_interval: Interval in seconds between checks (default: 120)
        """
        self.vault_path = Path(vault_path) if vault_path else Path(os.getenv('VAULT_PATH', './AI_Employee_Vault'))
        self.needs_action_path = self.vault_path / 'Needs_Action'
        self.check_interval = check_interval
        self.processed_ids = set()

        # Load credentials
        self.credentials_path = Path(credentials_path) if credentials_path else self.vault_path / 'credentials.json'
        self.token_path = self.vault_path / 'token.json'

        # Load previously processed message IDs
        self.processed_ids_path = self.vault_path / '.gmail_processed_ids'
        self.load_processed_ids()

        # Initialize Gmail service
        self.service = self.get_gmail_service()

        # DRY_RUN mode
        self.dry_run = os.getenv('DRY_RUN', 'true').lower() == 'true'
        if self.dry_run:
            logger.info("DRY_RUN mode enabled - actions will be logged but not executed")

    def get_gmail_service(self):
        """Authenticate and return Gmail service object."""
        creds = None

        # Load existing token
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    # Remove invalid token file and re-authenticate
                    if self.token_path.exists():
                        self.token_path.unlink()

            if not creds or not creds.valid:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(f"Credentials file not found: {self.credentials_path}")

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)

    def load_processed_ids(self):
        """Load previously processed message IDs from file."""
        if self.processed_ids_path.exists():
            try:
                with open(self.processed_ids_path, 'r') as f:
                    data = json.load(f)
                    self.processed_ids = set(data.get('processed_ids', []))
                logger.info(f"Loaded {len(self.processed_ids)} previously processed message IDs")
            except Exception as e:
                logger.error(f"Failed to load processed IDs: {e}")
                self.processed_ids = set()

    def save_processed_ids(self):
        """Save processed message IDs to file."""
        try:
            with open(self.processed_ids_path, 'w') as f:
                json.dump({'processed_ids': list(self.processed_ids)}, f)
        except Exception as e:
            logger.error(f"Failed to save processed IDs: {e}")

    @backoff.on_exception(backoff.expo, Exception, max_tries=3, max_time=60)
    def check_for_updates(self):
        """Check Gmail for new unread important messages."""
        try:
            # Query for unread important messages
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread is:important',
                maxResults=100  # Limit to prevent overwhelming
            ).execute()

            messages = results.get('messages', [])
            new_messages = []

            for msg in messages:
                msg_id = msg['id']
                if msg_id not in self.processed_ids:
                    new_messages.append(msg)

            logger.info(f"Found {len(new_messages)} new unread important messages")
            return new_messages

        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            raise
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            raise

    def extract_message_headers(self, msg_data):
        """Extract headers from message data."""
        headers = {}
        payload = msg_data.get('payload', {})
        header_list = payload.get('headers', [])

        for header in header_list:
            name = header.get('name', '').lower()
            value = header.get('value', '')
            headers[name] = value

        return headers

    def create_action_file(self, message):
        """Create markdown file in Needs_Action folder for a new email."""
        try:
            # Get full message details
            msg = self.service.users().messages().get(
                userId='me',
                id=message['id'],
                format='full'
            ).execute()

            headers = self.extract_message_headers(msg)

            # Extract email information
            sender = headers.get('from', 'Unknown')
            subject = headers.get('subject', 'No Subject')
            received_time = headers.get('date', datetime.now().isoformat())

            # Extract snippet/content
            snippet = msg.get('snippet', '')

            # Determine priority based on certain factors
            priority = 'high'
            if any(word in subject.lower() for word in ['urgent', 'asap', 'critical']):
                priority = 'high'
            elif any(word in snippet.lower() for word in ['urgent', 'asap', 'critical']):
                priority = 'high'
            elif any(word in subject.lower() for word in ['meeting', 'call', 'follow', 'deadline']):
                priority = 'medium'

            # Create markdown content with frontmatter
            content = f"""---
type: email
from: {sender}
subject: {subject}
received: {datetime.now().isoformat()}
priority: {priority}
status: pending
---

## Email Content
{snippet}

## Suggested Actions
- [ ] Review and respond if necessary
- [ ] Forward to relevant party if needed
- [ ] Archive after processing

## Raw Headers
From: {sender}
Subject: {subject}
Date: {received_time}
"""

            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"EMAIL_{message['id']}_{timestamp}.md"
            filepath = self.needs_action_path / filename

            if not self.dry_run:
                # Ensure directory exists
                self.needs_action_path.mkdir(parents=True, exist_ok=True)

                # Write the file
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

                logger.info(f"Created action file: {filepath}")
            else:
                logger.info(f"[DRY RUN] Would create action file: {filepath}")

            # Add to processed IDs
            self.processed_ids.add(message['id'])
            self.save_processed_ids()

            return filepath

        except Exception as e:
            logger.error(f"Error creating action file: {e}")
            raise

    def run(self):
        """Main run loop for the Gmail Watcher."""
        logger.info("Starting Gmail Watcher...")
        logger.info(f"Checking every {self.check_interval} seconds")
        logger.info(f"Dry run mode: {self.dry_run}")

        while True:
            try:
                messages = self.check_for_updates()
                for message in messages:
                    self.create_action_file(message)

                # Wait before next check
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("Gmail Watcher stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                logger.info(f"Waiting {self.check_interval} seconds before retrying...")
                time.sleep(self.check_interval)

def main():
    """Main function to run the Gmail Watcher."""
    import argparse

    parser = argparse.ArgumentParser(description='Gmail Watcher for AI Employee')
    parser.add_argument('--vault-path', default='./AI_Employee_Vault', help='Path to AI Employee vault')
    parser.add_argument('--credentials-path', help='Path to credentials.json')
    parser.add_argument('--check-interval', type=int, default=120, help='Check interval in seconds (default: 120)')
    parser.add_argument('--dry-run', action='store_true', help='Enable dry run mode')

    args = parser.parse_args()

    # Override DRY_RUN from command line if specified
    if args.dry_run:
        os.environ['DRY_RUN'] = 'true'

    watcher = GmailWatcher(
        vault_path=args.vault_path,
        credentials_path=args.credentials_path,
        check_interval=args.check_interval
    )

    watcher.run()

if __name__ == '__main__':
    main()