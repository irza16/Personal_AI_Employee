#!/usr/bin/env python3
"""
Instagram Poster - Uses Playwright to post content to Instagram with human approval
"""

import os
import time
import logging
from pathlib import Path
from datetime import datetime
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
        logging.FileHandler('instagram_poster.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class InstagramPoster:
    def __init__(self, vault_path=None, session_path=None):
        """
        Initialize Instagram Poster

        Args:
            vault_path: Path to the AI Employee vault
            session_path: Path to store Instagram session data
        """
        self.vault_path = Path(vault_path) if vault_path else Path(os.getenv('VAULT_PATH', './AI_Employee_Vault'))
        self.pending_posts_path = self.vault_path / 'Needs_Action' / 'INSTAGRAM_pending_posts.md'
        self.pending_approval_path = self.vault_path / 'Pending_Approval'
        self.done_path = self.vault_path / 'Done'
        self.logs_path = self.vault_path / 'Logs'
        self.session_path = Path(session_path) if session_path else self.vault_path / 'instagram_session'

        # Create directories if they don't exist
        self.pending_approval_path.mkdir(parents=True, exist_ok=True)
        self.done_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.session_path.mkdir(parents=True, exist_ok=True)

        # Get credentials from environment
        self.email = os.getenv('INSTAGRAM_EMAIL')
        self.password = os.getenv('INSTAGRAM_PASSWORD')

        if not self.email or not self.password:
            raise ValueError("INSTAGRAM_EMAIL and INSTAGRAM_PASSWORD must be set in .env file")

        # DRY_RUN mode
        self.dry_run = os.getenv('DRY_RUN', 'true').lower() == 'true'
        if self.dry_run:
            logger.info("DRY_RUN mode enabled - actions will be logged but not executed")

    def create_approval_request(self, post_content):
        """Create an approval request file before posting."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"INSTAGRAM_POST_APPROVAL_{timestamp}.md"
        filepath = self.pending_approval_path / filename

        content = f"""---
type: approval_request
action: instagram_post
created: {datetime.now().isoformat()}
expires: {datetime.now().replace(day=datetime.now().day + 7).isoformat()}
status: pending
---

## Instagram Post Content
{post_content}

## Action Required
Move this file to /Approved folder to post this content to Instagram.
"""

        if not self.dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Created approval request: {filepath}")
        else:
            logger.info(f"[DRY RUN] Would create approval request: {filepath}")

        return filepath

    def read_pending_posts(self):
        """Read pending posts from the INSTAGRAM_pending_posts.md file."""
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
        filename = f"INSTAGRAM_POST_DONE_{timestamp}.md"
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

    def post_to_instagram(self, post_content):
        """Post content to Instagram using Playwright."""
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

                # Navigate to Instagram
                page.goto('https://www.instagram.com/', wait_until='networkidle')

                # Check if already logged in by looking for navigation elements
                try:
                    page.wait_for_selector('input[aria-label="Username"]', timeout=5000)
                    # Need to log in
                    logger.info("Logging in to Instagram...")

                    # Fill in login credentials
                    page.fill('input[aria-label="Username"]', self.email)
                    page.fill('input[aria-label="Password"]', self.password)

                    # Click login button
                    login_button = page.get_by_role('button', name='Log in').first
                    login_button.click()

                    # Wait for login to complete
                    page.wait_for_selector('div[aria-label="Home"]', timeout=10000)
                    logger.info("Successfully logged in to Instagram")

                except:
                    # Already logged in, check for the home icon
                    try:
                        page.wait_for_selector('div[aria-label="Home"]', timeout=5000)
                        logger.info("Already logged in to Instagram")
                    except:
                        # If neither input nor home icon exists, we may be in a different state
                        logger.warning("Instagram login state uncertain, proceeding...")

                # Wait for the new post button to appear
                new_post_button = page.locator('svg[aria-label="New Post"]').first
                new_post_button.wait_for(state='visible', timeout=10000)

                # Click the new post button
                new_post_button.click()

                # Wait for the post upload modal to appear
                upload_button = page.locator('button:has-text("Select from computer")').first
                upload_button.wait_for(state='visible', timeout=5000)

                # For now, we'll simulate creating a text post instead of uploading media
                # Click to create a text post
                try:
                    text_post_button = page.locator('button:has-text("Create a text post")').first
                    text_post_button.wait_for(state='visible', timeout=3000)
                    text_post_button.click()
                except:
                    # If no text post button, just continue with regular post creation
                    pass

                # Fill in the caption
                caption_field = page.locator('textarea[aria-label="Write a caption..."]').first
                caption_field.wait_for(state='visible', timeout=5000)
                caption_field.fill(post_content)

                # Wait a moment for the content to be processed
                page.wait_for_timeout(2000)

                # Find and click the share button
                share_button = page.get_by_role('button', name='Share').first
                share_button.wait_for(state='visible', timeout=5000)

                if not self.dry_run:
                    share_button.click()
                    logger.info(f"Successfully posted to Instagram: {post_content[:100]}...")

                    # Wait for post to be submitted
                    page.wait_for_selector('div[aria-label="Home"]', timeout=10000)  # Wait to return to home
                else:
                    logger.info(f"[DRY RUN] Would post to Instagram: {post_content[:100]}...")

                # Wait for post to be submitted
                page.wait_for_timeout(3000)

                # Close browser
                browser.close()

                return True

            except Exception as e:
                logger.error(f"Error posting to Instagram: {e}")
                try:
                    browser.close()
                except:
                    pass
                return False

    def process_approved_posts(self):
        """Check for approved posts and publish them."""
        approved_dir = self.vault_path / 'Approved'
        approved_dir.mkdir(parents=True, exist_ok=True)

        # Look for approved Instagram post files
        for file_path in approved_dir.glob('INSTAGRAM_POST_APPROVAL_*.md'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract post content from the approval file
                lines = content.split('\n')
                post_content = ""
                capturing = False

                for line in lines:
                    if '## Instagram Post Content' in line:
                        capturing = True
                        continue
                    elif capturing and line.startswith('## ') and 'Instagram Post Content' not in line:
                        # Found next section header, stop capturing
                        break
                    elif capturing:
                        post_content += line + '\n'

                post_content = post_content.strip()

                if post_content:
                    logger.info(f"Processing approved post: {post_content[:100]}...")

                    # Post to Instagram
                    success = self.post_to_instagram(post_content)

                    if success:
                        # Move the approval file to Done after successful posting
                        done_file = self.vault_path / 'Done' / f"APPROVED_{file_path.name}"
                        if not self.dry_run:
                            file_path.rename(done_file)
                        else:
                            logger.info(f"[DRY RUN] Would move {file_path} to {done_file}")

                        # Move the original post to Done
                        self.move_post_to_done(post_content)

                        # Log engagement summary
                        self.log_engagement_summary(post_content, "instagram")

                        logger.info("Successfully processed approved post")
                    else:
                        logger.error("Failed to post to Instagram")
                else:
                    logger.warning(f"No post content found in approval file: {file_path}")

            except Exception as e:
                logger.error(f"Error processing approved post {file_path}: {e}")

    def log_engagement_summary(self, post_content, platform):
        """Log engagement summary for the post."""
        engagement_log = self.logs_path / f"social_engagement_{datetime.now().strftime('%Y-%m-%d')}.md"

        summary = f"""---
date: {datetime.now().isoformat()}
platform: {platform}
---

## Post Content
{post_content}

## Engagement Metrics
- Likes: 0
- Comments: 0
- Shares: 0
- Reach: 0

## Status
- Posted: Success
- Timestamp: {datetime.now().isoformat()}

"""

        if not self.dry_run:
            with open(engagement_log, 'a', encoding='utf-8') as f:
                f.write(summary + "\n")
            logger.info(f"Logged engagement summary for {platform} post")
        else:
            logger.info(f"[DRY RUN] Would log engagement summary for {platform} post")

    def generate_content_from_goals(self):
        """Generate Instagram post variations based on Business_Goals.md."""
        business_goals_path = self.vault_path / 'Business_Goals.md'

        if not business_goals_path.exists():
            logger.warning(f"Business_Goals.md not found at {business_goals_path}")
            return []

        try:
            with open(business_goals_path, 'r', encoding='utf-8') as f:
                goals_content = f.read()

            # Extract key business information from goals
            objectives = []
            metrics = []
            projects = []
            value_props = []

            lines = goals_content.split('\n')
            current_section = ''

            for line in lines:
                line_lower = line.lower()

                if '# objective' in line_lower or 'objective' in line_lower:
                    current_section = 'objectives'
                elif '# metric' in line_lower or 'metric' in line_lower:
                    current_section = 'metrics'
                elif '# project' in line_lower or 'project' in line_lower:
                    current_section = 'projects'
                elif '# value' in line_lower or 'value' in line_lower:
                    current_section = 'value_props'

                if line.strip().startswith('- ') or line.strip().startswith('* '):
                    if current_section == 'objectives':
                        objectives.append(line.strip()[2:])
                    elif current_section == 'metrics':
                        metrics.append(line.strip()[2:])
                    elif current_section == 'projects':
                        projects.append(line.strip()[2:])
                    elif current_section == 'value_props':
                        value_props.append(line.strip()[2:])

            # Generate 3 post variations
            posts = []

            # Post variation 1: Achievement/Fact based
            obj = objectives[0] if objectives else "key objectives"
            metric = metrics[0] if metrics else "Our metrics show"
            proj = projects[0] if projects else "our projects"

            post1 = f"We've reached a major milestone! 🚀 Our team has achieved {obj} and we're excited to share this journey with our network. {metric} - This drives home the importance of focusing on what truly matters."
            posts.append(post1)

            # Post variation 2: Educational/Insight based
            val_prop = value_props[0] if value_props else "focus on customer value"
            obj2 = objectives[0] if objectives else "achieving objectives"

            post2 = f"Key insight: Based on our experience with {proj}, we've learned that {val_prop} is crucial for success. Industry tip: When it comes to {obj2}, remember that consistency and adaptability go hand in hand."
            posts.append(post2)

            # Post variation 3: Call-to-action/Engagement based
            obj3 = objectives[0] if objectives else "strategic objectives"
            val_prop2 = value_props[0] if value_props else "customer-centric approaches"

            post3 = f"Thoughts? We're always looking to learn from industry experts. How do you approach {obj3} in your organization? Looking for insights! As we continue to evolve {proj}, what strategies have worked best for you? Join the conversation! We believe {val_prop2} is the future. What's your take?"
            posts.append(post3)

            return posts

        except Exception as e:
            logger.error(f"Error generating content from goals: {e}")
            return []

    def run_once(self):
        """Run one cycle of checking for posts and processing them."""
        logger.info("Checking for pending Instagram posts...")

        # Check for approved posts first
        self.process_approved_posts()

        # Read pending posts
        pending_posts = self.read_pending_posts()

        for post in pending_posts:
            if post.strip():  # Skip empty posts
                logger.info(f"Creating approval request for post: {post[:100]}...")
                self.create_approval_request(post)

def main():
    """Main function to run the Instagram Poster."""
    import argparse

    parser = argparse.ArgumentParser(description='Instagram Poster for AI Employee')
    parser.add_argument('--vault-path', default='./AI_Employee_Vault', help='Path to AI Employee vault')
    parser.add_argument('--session-path', help='Path to store Instagram session data')
    parser.add_argument('--dry-run', action='store_true', help='Enable dry run mode')
    parser.add_argument('--generate', action='store_true', help='Generate post variations from Business_Goals.md')
    parser.add_argument('--run-once', action='store_true', help='Run once and exit')

    args = parser.parse_args()

    # Override DRY_RUN from command line if specified
    if args.dry_run:
        os.environ['DRY_RUN'] = 'true'

    poster = InstagramPoster(
        vault_path=args.vault_path,
        session_path=args.session_path
    )

    if args.generate:
        # Generate content variations and save to pending posts
        posts = poster.generate_content_from_goals()
        if posts:
            pending_posts_path = poster.vault_path / 'Needs_Action' / 'INSTAGRAM_pending_posts.md'
            content = f"""---
generated: {datetime.now().isoformat()}
source: Business_Goals.md
status: pending_approval
---

# Instagram Post Ideas

Based on our business goals and objectives, here are some Instagram post suggestions:

---

## Post Variation 1
{posts[0]}

---

## Post Variation 2
{posts[1]}

---

## Post Variation 3
{posts[2]}

---

**Note:** These posts require human approval before publishing. Move to approval workflow for review.
"""
            with open(pending_posts_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Generated {len(posts)} Instagram post variations and saved to pending posts")
        return

    if args.run_once:
        poster.run_once()
    else:
        # Run continuously, checking for new posts periodically
        logger.info("Starting Instagram Poster (continuous mode)...")
        logger.info(f"Dry run mode: {poster.dry_run}")

        while True:
            try:
                poster.run_once()
                # Wait 5 minutes before checking again
                time.sleep(300)
            except KeyboardInterrupt:
                logger.info("Instagram Poster stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

if __name__ == '__main__':
    main()