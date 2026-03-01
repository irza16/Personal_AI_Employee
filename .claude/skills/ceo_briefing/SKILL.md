# CEO Briefing Skill

## Description
Generates a comprehensive Monday Morning CEO Briefing by reading Business_Goals.md for targets and KPIs, scanning all files in Done/ folder from the past 7 days, analyzing Accounting/Current_Month.md for financial data, and reviewing social media engagement logs. Creates a structured briefing document in Briefings/ folder.

## Inputs
- Business_Goals.md for targets and KPIs
- Files in Done/ folder from the past 7 days
- Accounting/Current_Month.md for financial data
- Logs/social_engagement_{date}.md for social media performance
- --schedule flag to register Windows Task Scheduler job

## Outputs
- Creates comprehensive CEO briefing in Briefings/{date}_Monday_Briefing.md with:
  * Executive Summary (2-3 sentences)
  * Revenue (this week vs target, MTD, trend)
  * Completed Tasks (from Done/ folder)
  * Bottlenecks (tasks that took longer than expected)
  * Social Media Performance (engagement summary)
  * Proactive Suggestions (cost savings, automation opportunities)
  * Upcoming Deadlines (from Business_Goals.md)

## Hard Limits
- Must never generate briefings without proper data sources
- Must never modify source data files (Business_Goals.md, Done/ files, etc.)
- Must always respect the structured briefing format
- Must never run scheduled tasks without explicit approval
- Must always maintain data integrity in source files