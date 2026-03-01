# Twitter Poster Skill

## Description
Uses Playwright to log into Twitter/X and post content to the feed after human approval. Reads pending posts from Needs_Action/TWITTER_pending_posts.md and moves them to Done/ after successful posting. Writes approval request to Pending_Approval/ before posting (HITL - never posts without human approval).

## Inputs
- Twitter credentials from .env file (TWITTER_EMAIL, TWITTER_PASSWORD)
- Twitter post content from Needs_Action/TWITTER_pending_posts.md
- DRY_RUN mode flag (default: true)

## Outputs
- Posts content to Twitter/X feed (with human approval)
- Moves processed posts from Needs_Action/ to Done/
- Creates approval request files in Pending_Approval/ before posting
- Logs engagement summary (likes, retweets, comments) to Logs/social_engagement_{date}.md

## Hard Limits
- Must never post content without explicit human approval
- Must never interact with Twitter/X without proper authentication
- Must never store Twitter credentials in plain text
- Must always respect DRY_RUN mode until manually changed
- Must never bypass the approval workflow
- Must never post more than 1 post per hour to avoid rate limiting
- Must always save session to twitter_session/ folder for reuse