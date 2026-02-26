# LinkedIn Content Skill

## Description
Reads Business_Goals.md to understand business context and generates professional LinkedIn posts about the business. Creates 3 variations saved to Needs_Action/LINKEDIN_pending_posts.md for human approval. Never posts directly - always goes through HITL approval process.

## Inputs
- Business_Goals.md content for context
- Current business goals and objectives
- DRY_RUN mode flag (default: true)

## Outputs
- Generates 3 LinkedIn post variations
- Saves posts to Needs_Action/LINKEDIN_pending_posts.md
- Each post goes through approval workflow before posting

## Hard Limits
- Must never post directly to LinkedIn without human approval
- Must always read Business_Goals.md for context before generating content
- Must always respect DRY_RUN mode until manually changed
- Must never bypass the approval workflow
- Must generate professional, brand-appropriate content only
- Must never create controversial or inappropriate content