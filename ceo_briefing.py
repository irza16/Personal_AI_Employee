#!/usr/bin/env python3
"""
CEO Briefing Generator - Creates comprehensive Monday Morning CEO Briefing
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
import re
import subprocess
import sys

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ceo_briefing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CEOBriefingGenerator:
    def __init__(self, vault_path=None):
        """
        Initialize CEO Briefing Generator

        Args:
            vault_path: Path to the AI Employee vault
        """
        self.vault_path = Path(vault_path) if vault_path else Path(os.getenv('VAULT_PATH', './AI_Employee_Vault'))
        self.business_goals_path = self.vault_path / 'Business_Goals.md'
        self.done_path = self.vault_path / 'Done'
        self.accounting_path = self.vault_path / 'Accounting'
        self.logs_path = self.vault_path / 'Logs'
        self.briefings_path = self.vault_path / 'Briefings'

        # Create directories if they don't exist
        self.done_path.mkdir(parents=True, exist_ok=True)
        self.accounting_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.briefings_path.mkdir(parents=True, exist_ok=True)

    def read_business_goals(self):
        """Read Business_Goals.md for targets and KPIs."""
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

    def read_completed_tasks(self, days_back=7):
        """Read all files in Done/ folder from the past X days."""
        completed_tasks = []
        cutoff_date = datetime.now() - timedelta(days=days_back)

        for file_path in self.done_path.glob('*.md'):
            try:
                # Get file modification time
                mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)

                if mod_time >= cutoff_date:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    completed_tasks.append({
                        'filename': file_path.name,
                        'content': content,
                        'modified': mod_time
                    })
            except Exception as e:
                logger.error(f"Error reading completed task {file_path}: {e}")

        return completed_tasks

    def read_accounting_data(self):
        """Read Accounting/Current_Month.md for financial data."""
        current_month_file = self.accounting_path / f"{datetime.now().strftime('%Y-%m')}_Current_Month.md"

        if not current_month_file.exists():
            logger.warning(f"Current month accounting file not found: {current_month_file}")
            return ""

        try:
            with open(current_month_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error(f"Error reading accounting data: {e}")
            return ""

    def read_social_engagement(self):
        """Read social media engagement logs."""
        engagement_data = []
        today = datetime.now()

        # Look for engagement logs from the past 7 days
        for i in range(7):
            date_str = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            engagement_file = self.logs_path / f"social_engagement_{date_str}.md"

            if engagement_file.exists():
                try:
                    with open(engagement_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    engagement_data.append({
                        'date': date_str,
                        'content': content
                    })
                except Exception as e:
                    logger.error(f"Error reading engagement log {engagement_file}: {e}")

        return engagement_data

    def extract_kpis_from_goals(self, goals_content):
        """Extract KPIs and targets from Business_Goals.md."""
        kpis = {
            'revenue_target': 0,
            'monthly_targets': [],
            'key_metrics': [],
            'upcoming_deadlines': []
        }

        lines = goals_content.split('\n')
        for line in lines:
            line_lower = line.lower()

            if 'revenue' in line_lower and ('target' in line_lower or '$' in line):
                # Extract revenue target
                revenue_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', line)
                if revenue_match:
                    try:
                        kpis['revenue_target'] = float(revenue_match.group(1).replace(',', ''))
                    except:
                        pass

            if 'target' in line_lower:
                kpis['monthly_targets'].append(line.strip())

            if 'metric' in line_lower:
                kpis['key_metrics'].append(line.strip())

            if 'deadline' in line_lower or 'due' in line_lower:
                kpis['upcoming_deadlines'].append(line.strip())

        return kpis

    def calculate_revenue_summary(self, accounting_content):
        """Calculate revenue summary from accounting data."""
        revenue_info = {
            'this_week': 0,
            'month_to_date': 0,
            'trend': 'stable'
        }

        # Look for monetary values in accounting data
        money_matches = re.findall(r'\$?([\d,]+(?:\.\d{2})?)', accounting_content)
        amounts = []

        for match in money_matches:
            try:
                amount = float(match.replace(',', ''))
                amounts.append(amount)
            except:
                continue

        if amounts:
            revenue_info['month_to_date'] = sum(amounts)
            # Simplified calculation - in a real system you'd need more sophisticated date tracking
            revenue_info['this_week'] = sum(amounts[-3:]) if len(amounts) >= 3 else sum(amounts)

        return revenue_info

    def analyze_completed_tasks(self, tasks):
        """Analyze completed tasks for bottlenecks and insights."""
        analysis = {
            'total_completed': len(tasks),
            'task_types': [],
            'potential_bottlenecks': [],
            'efficiency_insights': []
        }

        for task in tasks:
            content = task['content'].lower()

            # Look for common task types
            if 'email' in content:
                analysis['task_types'].append('Email Processing')
            elif 'linkedin' in content:
                analysis['task_types'].append('LinkedIn Operations')
            elif 'whatsapp' in content:
                analysis['task_types'].append('WhatsApp Communications')
            elif 'payment' in content:
                analysis['task_types'].append('Payment Processing')
            elif 'invoice' in content:
                analysis['task_types'].append('Invoice Management')
            else:
                analysis['task_types'].append('General Task')

            # Look for potential bottlenecks (mentions of delays, issues, etc.)
            if any(word in content for word in ['delay', 'issue', 'problem', 'stuck', 'blocked']):
                analysis['potential_bottlenecks'].append(task['filename'])

        return analysis

    def analyze_social_performance(self, engagement_data):
        """Analyze social media engagement performance."""
        performance = {
            'total_likes': 0,
            'total_comments': 0,
            'total_shares': 0,
            'top_performing_platforms': [],
            'engagement_trends': []
        }

        for data in engagement_data:
            content = data['content'].lower()

            # Extract engagement metrics
            likes_match = re.search(r'likes:\s*(\d+)', content)
            if likes_match:
                performance['total_likes'] += int(likes_match.group(1))

            comments_match = re.search(r'comments:\s*(\d+)', content)
            if comments_match:
                performance['total_comments'] += int(comments_match.group(1))

            shares_match = re.search(r'shares:\s*(\d+)', content)
            if shares_match:
                performance['total_shares'] += int(shares_match.group(1))

        return performance

    def generate_proactive_suggestions(self, goals_content, accounting_content):
        """Generate proactive suggestions for cost savings and automation."""
        suggestions = []

        # Look for opportunities in goals and accounting data
        goals_lower = goals_content.lower()
        accounting_lower = accounting_content.lower()

        if 'subscription' in goals_lower or 'monthly' in accounting_lower:
            suggestions.append("Consider reviewing subscription services for potential cost savings")

        if 'manual' in goals_lower:
            suggestions.append("Opportunity to automate manual processes identified in goals")

        if 'expense' in accounting_lower:
            suggestions.append("Review expense categories for optimization opportunities")

        if 'time' in goals_lower:
            suggestions.append("Time-intensive tasks identified - consider automation solutions")

        if not suggestions:
            suggestions.append("No specific cost-saving opportunities identified in current data")

        return suggestions

    def generate_briefing(self):
        """Generate the comprehensive CEO briefing."""
        logger.info("Generating Monday Morning CEO Briefing...")

        # Read all required data
        goals_content = self.read_business_goals()
        completed_tasks = self.read_completed_tasks(days_back=7)
        accounting_content = self.read_accounting_data()
        engagement_data = self.read_social_engagement()

        # Extract KPIs from goals
        kpis = self.extract_kpis_from_goals(goals_content)

        # Calculate revenue summary
        revenue_summary = self.calculate_revenue_summary(accounting_content)

        # Analyze completed tasks
        task_analysis = self.analyze_completed_tasks(completed_tasks)

        # Analyze social performance
        social_performance = self.analyze_social_performance(engagement_data)

        # Generate proactive suggestions
        suggestions = self.generate_proactive_suggestions(goals_content, accounting_content)

        # Create the briefing content
        briefing_content = f"""---
generated: {datetime.now().isoformat()}
period: {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}
---

# Monday Morning CEO Briefing
## {datetime.now().strftime('%A, %B %d, %Y')}

### Executive Summary
This week we processed {len(completed_tasks)} tasks with strong performance in various areas. Revenue is tracking at ${revenue_summary.get('this_week', 0):,.2f} for the week with ${revenue_summary.get('month_to_date', 0):,.2f} month-to-date.

### Revenue Analysis
- **This Week**: ${revenue_summary.get('this_week', 0):,.2f}
- **Month-to-Date**: ${revenue_summary.get('month_to_date', 0):,.2f}
- **Target**: ${kpis['revenue_target']:,.2f}
- **Trend**: {revenue_summary.get('trend', 'unknown')}

### Completed Tasks ({len(completed_tasks)} Total)
{chr(10).join([f"- {task['filename']} ({task['modified'].strftime('%m/%d %H:%M')})" for task in completed_tasks[:10]]) if completed_tasks else "- No tasks completed this week"}
{f"... and {len(completed_tasks) - 10} more" if len(completed_tasks) > 10 else ""}

### Bottlenecks & Issues
{chr(10).join([f"- {bottleneck}" for bottleneck in task_analysis['potential_bottlenecks']]) if task_analysis['potential_bottlenecks'] else "- No bottlenecks identified this week"}

### Social Media Performance
- **Total Likes**: {social_performance['total_likes']}
- **Total Comments**: {social_performance['total_comments']}
- **Total Shares**: {social_performance['total_shares']}
- **Top Platforms**: {', '.join(social_performance['top_performing_platforms']) if social_performance['top_performing_platforms'] else 'Data pending'}

### Proactive Suggestions
{chr(10).join([f"- {suggestion}" for suggestion in suggestions]) if suggestions else "- No specific suggestions at this time"}

### Upcoming Deadlines
{chr(10).join([f"- {deadline}" for deadline in kpis['upcoming_deadlines']]) if kpis['upcoming_deadlines'] else "- No upcoming deadlines in goals"}

### Key Metrics Tracking
{chr(10).join([f"- {metric}" for metric in kpis['key_metrics']]) if kpis['key_metrics'] else "- No specific metrics defined in goals"}

---

*Generated by AI Employee CEO Briefing System*
*Total tasks processed: {len(completed_tasks)}*
*Revenue tracking: {(revenue_summary.get('month_to_date', 0)/max(kpis['revenue_target'], 1)*100):.1f}% of monthly target*
"""

        # Save the briefing
        briefing_filename = f"{datetime.now().strftime('%Y-%m-%d')}_Monday_Briefing.md"
        briefing_path = self.briefings_path / briefing_filename

        with open(briefing_path, 'w', encoding='utf-8') as f:
            f.write(briefing_content)

        logger.info(f"CEO Briefing generated: {briefing_path}")
        return briefing_path

    def schedule_briefing(self):
        """Schedule the CEO briefing to run every Sunday at 9 PM using Windows Task Scheduler."""
        try:
            # Create the task scheduler command
            script_path = Path(__file__).resolve()
            task_name = "AI_Employee_CEO_Briefing"

            # PowerShell command to create scheduled task
            ps_command = f'''
            $Action = New-ScheduledTaskAction -Execute "python" -Argument "{script_path} --generate"
            $Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 9PM
            $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
            $Principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive

            # Remove existing task if it exists
            try {{
                Unregister-ScheduledTask -TaskName "{task_name}" -Confirm:$false -ErrorAction SilentlyContinue
            }} catch {{}}

            # Register the new task
            Register-ScheduledTask -TaskName "{task_name}" -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "Generates weekly CEO briefing every Sunday at 9 PM"
            '''

            # Execute the PowerShell command
            result = subprocess.run([
                'powershell', '-Command', ps_command
            ], capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("CEO Briefing scheduled successfully for every Sunday at 9 PM")
                return True
            else:
                logger.error(f"Failed to schedule CEO Briefing: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error scheduling CEO Briefing: {e}")
            return False

def main():
    """Main function to run the CEO Briefing Generator."""
    import argparse

    parser = argparse.ArgumentParser(description='CEO Briefing Generator for AI Employee')
    parser.add_argument('--vault-path', default='./AI_Employee_Vault', help='Path to AI Employee vault')
    parser.add_argument('--generate', action='store_true', help='Generate the CEO briefing')
    parser.add_argument('--schedule', action='store_true', help='Schedule the CEO briefing to run weekly')

    args = parser.parse_args()

    generator = CEOBriefingGenerator(vault_path=args.vault_path)

    if args.schedule:
        generator.schedule_briefing()
    elif args.generate or True:  # Default to generate if no specific action is requested
        generator.generate_briefing()

if __name__ == '__main__':
    main()