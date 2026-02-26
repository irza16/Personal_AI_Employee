# Email MCP Skill

## Description
Exposes tools for sending, drafting, and searching emails via Gmail API. Never sends emails without approval files in Approved/ folder. Logs all actions to Logs/ in JSON format.

## Inputs
- Gmail OAuth credentials (credentials.json)
- Email content and recipient information
- Approval file in Approved/ folder (for sending)
- DRY_RUN mode flag (default: true)

## Outputs
- send_email: Sends email via Gmail API (requires approval)
- draft_email: Creates email draft in Gmail
- search_emails: Searches Gmail inbox based on criteria
- JSON logs in Logs/ folder with timestamp, action_type, actor, target, approval_status, result

## Hard Limits
- Must never send an email without corresponding approval file in Approved/
- Must never bypass approval workflow
- Must never store email credentials in plain text
- Must always respect DRY_RUN mode until manually changed
- Must always log every action to Logs/ folder
- Must never exceed Gmail API rate limits