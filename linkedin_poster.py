#!/usr/bin/env python3
"""
LinkedIn Poster - Uses Playwright to post content to LinkedIn with human approval
"""

import os
import time
import logging
from pathlib import Path
from datetime import datetime
import asyncio
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('linkedin_poster.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LinkedInPoster:
    def __init__(self, vault_path=None, session_path=None):
        """
        Initialize LinkedIn Poster

        Args:
            vault_path: Path to the AI Employee vault
            session_path: Path to store LinkedIn session data
        """
        self.vault_path = Path(vault_path) if vault_path else Path(os.getenv('VAULT_PATH', './AI_Employee_Vault'))
        self.pending_posts_path = self.vault_path / 'Needs_Action' / 'LINKEDIN_pending_posts.md'
        self.done_path = self.vault_path / 'Done'
        self.pending_approval_path = self.vault_path / 'Pending_Approval'
        self.session_path = Path(session_path) if session_path else self.vault_path / 'linkedin_session'

        # Create directories if they don't exist
        self.done_path.mkdir(parents=True, exist_ok=True)
        self.pending_approval_path.mkdir(parents=True, exist_ok=True)

        # Get credentials from environment
        self.username = os.getenv('LINKEDIN_USERNAME')
        self.password = os.getenv('LINKEDIN_PASSWORD')

        if not self.username or not self.password:
            raise ValueError("LINKEDIN_USERNAME and LINKEDIN_PASSWORD must be set in .env file")

        # DRY_RUN mode
        self.dry_run = os.getenv('DRY_RUN', 'true').lower() == 'true'
        if self.dry_run:
            logger.info("DRY_RUN mode enabled - actions will be logged but not executed")

    def create_approval_request(self, post_content):
        """Create an approval request file before posting."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"LINKEDIN_POST_APPROVAL_{timestamp}.md"
        filepath = self.pending_approval_path / filename

        content = f"""---
type: approval_request
action: linkedin_post
created: {datetime.now().isoformat()}
expires: {datetime.now().replace(day=datetime.now().day + 7).isoformat()}
status: pending
---

## LinkedIn Post Content
{post_content}

## Action Required
Move this file to /Approved folder to post this content to LinkedIn.
"""

        if not self.dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Created approval request: {filepath}")
        else:
            logger.info(f"[DRY RUN] Would create approval request: {filepath}")

        return filepath

    def read_pending_posts(self):
        """Read pending posts from the LINKEDIN_pending_posts.md file."""
        if not self.pending_posts_path.exists():
            logger.info("No pending posts file found")
            return []

        try:
            with open(self.pending_posts_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse the content - assume each post is separated by a marker or by newlines
            # For now, split by double newlines which typically separates posts
            posts = [post.strip() for post in content.split('\n\n') if post.strip()]

            # Filter out frontmatter if present
            filtered_posts = []
            for post in posts:
                if post.startswith('---'):
                    # Skip frontmatter sections
                    parts = post.split('---', 2)
                    if len(parts) >= 3:
                        filtered_posts.append(parts[2].strip())
                    else:
                        filtered_posts.append(post)
                else:
                    filtered_posts.append(post)

            logger.info(f"Found {len(filtered_posts)} pending posts")
            return filtered_posts

        except Exception as e:
            logger.error(f"Error reading pending posts: {e}")
            return []

    def move_post_to_done(self, post_content):
        """Move processed post to Done folder."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"LINKEDIN_POST_DONE_{timestamp}.md"
        filepath = self.done_path / filename

        content = f"""---
type: posted_content
posted: {datetime.now().isoformat()}
---

{post_content}
"""

        if not self.dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Moved post to Done: {filepath}")
        else:
            logger.info(f"[DRY RUN] Would move post to Done: {filepath}")

    def post_to_linkedin(self, post_content):
        """Post content to LinkedIn using Playwright."""
        with sync_playwright() as p:
            try:
                # Launch browser with persistent context to maintain session
                browser = p.chromium.launch_persistent_context(
                    str(self.session_path),
                    headless=False,  # Set to True for production
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                    timezone_id='America/New_York'
                )

                page = browser.new_page()

                # Navigate to LinkedIn
                page.goto('https://www.linkedin.com/feed/')

                # Check if already logged in by looking for nav elements
                try:
                    page.wait_for_selector('nav.global-nav', timeout=5000)
                    logger.info("Already logged in to LinkedIn")
                except:
                    # Need to log in
                    logger.info("Logging in to LinkedIn...")
                    page.goto('https://www.linkedin.com/login')

                    # Fill in login credentials
                    page.fill('#username', self.username)
                    page.fill('#password', self.password)

                    # Click login button
                    login_button = page.get_by_text('Sign in').first
                    login_button.click()

                    # Wait for login to complete
                    page.wait_for_url('https://www.linkedin.com/feed/**', timeout=10000)
                    logger.info("Successfully logged in to LinkedIn")

                # Wait for the share box to appear
                share_box = page.locator('div[contenteditable="true"][data-test-id="share-content-textarea"]').first
                share_box.wait_for(state='visible', timeout=10000)

                # Click the share box to activate it
                share_box.click()

                # Fill in the post content
                share_box.fill(post_content)

                # Wait a moment for the content to be processed
                page.wait_for_timeout(2000)

                # Find and click the post button
                post_button = page.get_by_role('button', name='Post').first
                post_button.wait_for(state='visible', timeout=5000)

                if not self.dry_run:
                    post_button.click()
                    logger.info(f"Successfully posted to LinkedIn: {post_content[:100]}...")
                else:
                    logger.info(f"[DRY RUN] Would post to LinkedIn: {post_content[:100]}...")

                # Wait for post to be submitted
                page.wait_for_timeout(3000)

                # Close browser
                browser.close()

                return True

            except Exception as e:
                logger.error(f"Error posting to LinkedIn: {e}")
                try:
                    browser.close()
                except:
                    pass
                return False

    def process_approved_posts(self):
        """Check for approved posts and publish them."""
        approved_dir = self.vault_path / 'Approved'
        approved_dir.mkdir(parents=True, exist_ok=True)

        # Look for approved LinkedIn post files
        for file_path in approved_dir.glob('LINKEDIN_POST_APPROVAL_*.md'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract post content from the approval file
                lines = content.split('\n')
                post_content = ""
                capturing = False

                for line in lines:
                    if '## LinkedIn Post Content' in line:
                        capturing = True
                        continue
                    elif capturing and line.startswith('## ') and 'LinkedIn Post Content' not in line:
                        # Found next section header, stop capturing
                        break
                    elif capturing:
                        post_content += line + '\n'

                post_content = post_content.strip()

                if post_content:
                    logger.info(f"Processing approved post: {post_content[:100]}...")

                    # Post to LinkedIn
                    success = self.post_to_linkedin(post_content)

                    if success:
                        # Move the approval file to Done after successful posting
                        done_file = self.vault_path / 'Done' / f"APPROVED_{file_path.name}"
                        if not self.dry_run:
                            file_path.rename(done_file)
                        else:
                            logger.info(f"[DRY RUN] Would move {file_path} to {done_file}")

                        # Move the original post to Done
                        self.move_post_to_done(post_content)
                        logger.info("Successfully processed approved post")
                    else:
                        logger.error("Failed to post to LinkedIn")
                else:
                    logger.warning(f"No post content found in approval file: {file_path}")

            except Exception as e:
                logger.error(f"Error processing approved post {file_path}: {e}")

    def run_once(self):
        """Run one cycle of checking for posts and processing them."""
        logger.info("Checking for pending LinkedIn posts...")

        # Check for approved posts first
        self.process_approved_posts()

        # Read pending posts
        pending_posts = self.read_pending_posts()

        for post in pending_posts:
            if post.strip():  # Skip empty posts
                logger.info(f"Creating approval request for post: {post[:100]}...")
                self.create_approval_request(post)

def main():
    """Main function to run the LinkedIn Poster."""
    import argparse

    parser = argparse.ArgumentParser(description='LinkedIn Poster for AI Employee')
    parser.add_argument('--vault-path', default='./AI_Employee_Vault', help='Path to AI Employee vault')
    parser.add_argument('--session-path', help='Path to store LinkedIn session data')
    parser.add_argument('--dry-run', action='store_true', help='Enable dry run mode')
    parser.add_argument('--run-once', action='store_true', help='Run once and exit')

    args = parser.parse_args()

    # Override DRY_RUN from command line if specified
    if args.dry_run:
        os.environ['DRY_RUN'] = 'true'

    poster = LinkedInPoster(
        vault_path=args.vault_path,
        session_path=args.session_path
    )

    if args.run_once:
        poster.run_once()
    else:
        # Run continuously, checking for new posts periodically
        logger.info("Starting LinkedIn Poster (continuous mode)...")
        logger.info(f"Dry run mode: {poster.dry_run}")

        while True:
            try:
                poster.run_once()
                # Wait 5 minutes before checking again
                time.sleep(300)
            except KeyboardInterrupt:
                logger.info("LinkedIn Poster stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

if __name__ == '__main__':
    main()