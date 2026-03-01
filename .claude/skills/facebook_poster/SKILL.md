# Facebook Poster Skill

## Description
Uses Playwright to log into Facebook and post content to the feed after human approval. Reads pending posts from Needs_Action/FACEBOOK_pending_posts.md and moves them to Done/ after successful posting. Writes approval request to Pending_Approval/ before posting (HITL - never posts without human approval).

## Inputs
- Facebook credentials from .env file (FACEBOOK_EMAIL, FACEBOOK_PASSWORD)
- Facebook post content from Needs_Action/FACEBOOK_pending_posts.md
- DRY_RUN mode flag (default: true)

## Outputs
- Posts content to Facebook feed (with human approval)
- Moves processed posts from Needs_Action/ to Done/
- Creates approval request files in Pending_Approval/ before posting
- Logs engagement summary (likes, comments, shares) to Logs/social_engagement_{date}.md

## Hard Limits
- Must never post content without explicit human approval
- Must never interact with Facebook without proper authentication
- Must never store Facebook credentials in plain text
- Must always respect DRY_RUN mode until manually changed
- Must never bypass the approval workflow
- Must never post more than 1 post per hour to avoid rate limiting
- Must always save session to facebook_session/ folder for reuse