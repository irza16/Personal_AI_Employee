#!/usr/bin/env python3
"""
LinkedIn Content Generator - Creates LinkedIn posts based on Business Goals
"""

import os
from pathlib import Path
from datetime import datetime
import logging
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinkedInContentGenerator:
    def __init__(self, vault_path=None):
        """
        Initialize LinkedIn Content Generator

        Args:
            vault_path: Path to the AI Employee vault
        """
        self.vault_path = Path(vault_path) if vault_path else Path(os.getenv('VAULT_PATH', './AI_Employee_Vault'))
        self.business_goals_path = self.vault_path / 'Business_Goals.md'
        self.needs_action_path = self.vault_path / 'Needs_Action'
        self.pending_posts_path = self.needs_action_path / 'LINKEDIN_pending_posts.md'

        # Create directories if they don't exist
        self.needs_action_path.mkdir(parents=True, exist_ok=True)

        # DRY_RUN mode
        self.dry_run = os.getenv('DRY_RUN', 'true').lower() == 'true'
        if self.dry_run:
            logger.info("DRY_RUN mode enabled - actions will be logged but not executed")

    def read_business_goals(self):
        """Read Business_Goals.md to understand business context."""
        if not self.business_goals_path.exists():
            logger.warning(f"Business_Goals.md not found at {self.business_goals_path}")
            return ""

        try:
            with open(self.business_goals_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error(f"Error reading Business_Goals.md: {e}")
            return ""

    def extract_key_info_from_goals(self, goals_content):
        """Extract key business information from goals."""
        key_info = {
            'objectives': [],
            'metrics': [],
            'projects': [],
            'target_audience': [],
            'value_propositions': []
        }

        # Simple extraction based on headings
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
            elif '# target' in line_lower or 'audience' in line_lower:
                current_section = 'target_audience'
            elif '# value' in line_lower or 'value' in line_lower:
                current_section = 'value_propositions'

            if line.strip().startswith('- ') or line.strip().startswith('* '):
                if current_section in key_info:
                    key_info[current_section].append(line.strip()[2:])  # Remove '- ' or '* '

        return key_info

    def generate_post_variations(self, business_info):
        """Generate 3 LinkedIn post variations based on business info."""
        posts = []

        # Helper function to safely choose from a list
        def safe_choice(items, default_items):
            """Safely choose an item from a list, with fallback to default items if the list is empty."""
            if not items:
                items = default_items
            if not items:
                # If even default items are empty, return a generic fallback
                return "business success"
            return random.choice(items)

        # Get all the info with defaults
        objectives = business_info.get('objectives', ['business growth', 'innovation', 'customer satisfaction'])
        metrics = business_info.get('metrics', ['positive metrics', 'growth indicators', 'performance measures'])
        projects = business_info.get('projects', ['current projects', 'recent initiatives', 'ongoing efforts'])
        value_props = business_info.get('value_propositions', ['customer value', 'quality service', 'expertise'])
        target_audience = business_info.get('target_audience', ['industry professionals', 'potential clients', 'partners'])

        # Log warnings if no metrics were found
        if not business_info.get('metrics'):
            logger.warning("No metrics found in Business_Goals.md, using default metrics")

        # Post variation 1: Achievement/Fact based
        achievement_posts = [
            f"We've reached a major milestone! 🚀 Our team has achieved {safe_choice(objectives, ['key objectives'])} and we're excited to share this journey with our network.",
            f"Did you know? {safe_choice(metrics, ['Our metrics show'])} - This drives home the importance of focusing on what truly matters.",
            f"Innovation at its finest! We're proud to announce progress on {safe_choice(projects, ['our projects'])} that aligns with our strategic vision."
        ]
        posts.append(random.choice(achievement_posts))

        # Post variation 2: Educational/Insight based
        insight_posts = [
            f"Key insight: Based on our experience with {safe_choice(projects, ['recent projects'])}, we've learned that {safe_choice(value_props, ['focus on customer value'])} is crucial for success.",
            f"Industry tip: When it comes to {safe_choice(objectives, ['achieving objectives'])}, remember that consistency and adaptability go hand in hand.",
            f"What we've discovered: {safe_choice(metrics, ['Our data shows'])} highlights the importance of continuous improvement in today's market."
        ]
        posts.append(random.choice(insight_posts))

        # Post variation 3: Call-to-action/Engagement based
        engagement_posts = [
            f"Thoughts? We're always looking to learn from industry experts. How do you approach {safe_choice(objectives, ['strategic objectives'])} in your organization?",
            f"Looking for insights! As we continue to evolve {safe_choice(projects, ['our initiatives'])}, what strategies have worked best for you?",
            f"Join the conversation! We believe {safe_choice(value_props, ['customer-centric approaches'])} is the future. What's your take?"
        ]
        posts.append(random.choice(engagement_posts))

        return posts

    def save_posts_to_pending(self, posts):
        """Save generated posts to LINKEDIN_pending_posts.md."""
        content = f"""---
generated: {datetime.now().isoformat()}
source: Business_Goals.md
status: pending_approval
---

# LinkedIn Post Ideas

Based on our business goals and objectives, here are some LinkedIn post suggestions:

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

        if not self.dry_run:
            with open(self.pending_posts_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Saved {len(posts)} post variations to {self.pending_posts_path}")
        else:
            logger.info(f"[DRY RUN] Would save {len(posts)} post variations to {self.pending_posts_path}")
            print(content)

        return self.pending_posts_path

    def generate_content(self):
        """Generate LinkedIn content based on business goals."""
        logger.info("Reading business goals...")
        goals_content = self.read_business_goals()

        if not goals_content.strip():
            logger.warning("No business goals found, using generic content")
            business_info = {
                'objectives': ['business growth', 'innovation', 'customer satisfaction'],
                'metrics': ['positive metrics', 'growth indicators', 'performance measures'],
                'projects': ['current projects', 'recent initiatives', 'ongoing efforts'],
                'value_propositions': ['customer value', 'quality service', 'expertise'],
                'target_audience': ['industry professionals', 'potential clients', 'partners']
            }
        else:
            business_info = self.extract_key_info_from_goals(goals_content)

        logger.info("Generating LinkedIn post variations...")
        posts = self.generate_post_variations(business_info)

        logger.info("Saving posts to pending file...")
        saved_file = self.save_posts_to_pending(posts)

        logger.info(f"LinkedIn content generation complete. Created {len(posts)} variations in {saved_file}")
        return saved_file

def main():
    """Main function to run the LinkedIn Content Generator."""
    import argparse

    parser = argparse.ArgumentParser(description='LinkedIn Content Generator for AI Employee')
    parser.add_argument('--vault-path', default='./AI_Employee_Vault', help='Path to AI Employee vault')
    parser.add_argument('--dry-run', action='store_true', help='Enable dry run mode')

    args = parser.parse_args()

    # Override DRY_RUN from command line if specified
    if args.dry_run:
        os.environ['DRY_RUN'] = 'true'

    generator = LinkedInContentGenerator(vault_path=args.vault_path)
    generator.generate_content()

if __name__ == '__main__':
    main()