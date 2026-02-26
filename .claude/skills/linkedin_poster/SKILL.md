# LinkedIn Poster Skill

## Description
Uses Playwright to log into LinkedIn and post content to the feed after human approval. Reads pending posts from Needs_Action/LINKEDIN_pending_posts.md and moves them to Done/ after successful posting.

## Inputs
- LinkedIn credentials from .env file
- LinkedIn post content from Needs_Action/LINKEDIN_pending_posts.md
- DRY_RUN mode flag (default: true)

## Outputs
- Posts content to LinkedIn feed (with human approval)
- Moves processed posts from Needs_Action/ to Done/
- Creates approval request files in Pending_Approval/ before posting

## Hard Limits
- Must never post content without explicit human approval
- Must never interact with LinkedIn without proper authentication
- Must never store LinkedIn credentials in plain text
- Must always respect DRY_RUN mode until manually changed
- Must never bypass the approval workflow
- Must never post more than 1 post per hour to avoid rate limiting