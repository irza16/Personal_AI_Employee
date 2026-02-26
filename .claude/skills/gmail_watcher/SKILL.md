# Gmail Watcher Skill

## Description
Monitors Gmail account for unread and important messages every 120 seconds, saving each new email as a markdown file in the Needs_Action folder with appropriate metadata.

## Inputs
- Gmail OAuth credentials (credentials.json, token.json)
- Check interval configuration (default: 120 seconds)
- DRY_RUN mode flag (default: true)

## Outputs
- Creates markdown files in Needs_Action/ with the following frontmatter:
  - type: email
  - from: sender email address
  - subject: email subject
  - received: timestamp
  - priority: high/medium/low
  - status: pending

## Hard Limits
- Must never autonomously reply to or delete emails
- Must never process emails without proper OAuth authentication
- Must never store email credentials in plain text
- Must always respect DRY_RUN mode until manually changed
- Must never exceed Gmail API rate limits
- Must always track processed message IDs to avoid duplicates