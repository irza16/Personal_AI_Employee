# HITL Approval Skill

## Description
Manages the Human-in-the-Loop approval workflow by monitoring Approved/ and Rejected/ folders, triggering corresponding MCP actions when approval files appear, and logging all approvals/rejections.

## Inputs
- Approval files in Approved/ folder
- Rejection files in Rejected/ folder
- Action parameters specified in approval files

## Outputs
- Triggers corresponding MCP actions when files appear in Approved/
- Moves approval files to Done/ after successful execution
- Moves rejected files to Done/ with rejection noted
- Logs all approvals and rejections to Logs/ folder

## Hard Limits
- Must never execute actions without proper approval files in Approved/ folder
- Must never bypass the approval workflow
- Must never modify or delete approval files without moving them to Done/
- Must always maintain audit trail in Logs/
- Must never execute rejected actions
- Must never auto-approve sensitive actions