# Testing Guide for Silver Tier Components

This guide explains how to test each component of the Personal AI Employee Silver Tier implementation.

## Prerequisites

Before testing, ensure you have:

- Python 3.8+ installed
- Node.js installed (for MCP servers)
- Playwright installed (`playwright install`)
- Gmail OAuth credentials (credentials.json and token.json)
- LinkedIn credentials (for testing LinkedIn features)
- DRY_RUN mode enabled in your .env file

## Component Testing

### 1. Gmail Watcher

**Test Purpose**: Verify that the Gmail watcher monitors emails and creates action files.

**Steps**:
1. Ensure you have Gmail credentials in `AI_Employee_Vault/credentials.json` and `token.json`
2. Run the Gmail watcher: `python gmail_watcher.py --dry-run`
3. Send a test email to your account with "urgent" or "important" in the subject
4. Verify that a markdown file is created in `AI_Employee_Vault/Needs_Action/`
5. Check that the file contains proper frontmatter with type, from, subject, etc.

**Expected Results**:
- No actual email processing occurs in dry-run mode
- Log messages indicate what would have happened
- No duplicate processing of the same email

### 2. WhatsApp Watcher

**Test Purpose**: Verify that the WhatsApp watcher monitors messages and flags keywords.

**Steps**:
1. Run the WhatsApp watcher: `python whatsapp_watcher.py --dry-run`
2. Have someone send you a WhatsApp message containing keywords like "urgent", "asap", "invoice", "payment", "help", "pricing", or "quote"
3. Verify that a markdown file is created in `AI_Employee_Vault/Needs_Action/`
4. Check that the file contains proper frontmatter with type, from, and matched keywords

**Expected Results**:
- No actual message processing occurs in dry-run mode
- Log messages indicate what would have happened
- Session is maintained between checks

### 3. LinkedIn Poster

**Test Purpose**: Verify that the LinkedIn poster creates approval requests and posts content.

**Steps**:
1. Set up LinkedIn credentials in your `.env` file
2. Create a test post in `AI_Employee_Vault/Needs_Action/LINKEDIN_pending_posts.md`
3. Run the LinkedIn poster: `python linkedin_poster.py --dry-run --run-once`
4. Verify that an approval request is created in `AI_Employee_Vault/Pending_Approval/`
5. Move the approval file to `AI_Employee_Vault/Approved/`
6. Run the poster again to process the approved post

**Expected Results**:
- Approval request file is created in Pending_Approval/
- When approved, post is processed and moved to Done/
- No actual posting occurs in dry-run mode

### 4. LinkedIn Content Generator

**Test Purpose**: Verify that the LinkedIn content generator creates posts based on business goals.

**Steps**:
1. Ensure `Business_Goals.md` exists in your vault with some content
2. Run the generator: `python linkedin_content_generator.py --dry-run`
3. Check that `LINKEDIN_pending_posts.md` is created in `AI_Employee_Vault/Needs_Action/`
4. Verify the file contains 3 post variations

**Expected Results**:
- 3 LinkedIn post variations are generated
- Posts are based on content from Business_Goals.md
- Posts are saved to the pending posts file

### 5. Email MCP Server

**Test Purpose**: Verify that the email MCP server handles email operations.

**Steps**:
1. Ensure Gmail credentials are properly set up
2. Start the MCP server: `node mcp_servers/email_mcp/index.js`
3. In Claude Code, try using the email tools (send_email, draft_email, search_emails)
4. Verify that emails require approval files in `AI_Employee_Vault/Approved/`

**Expected Results**:
- Email MCP tools are available in Claude Code
- Emails are not sent without approval files
- Actions are logged to `AI_Employee_Vault/Logs/`

### 6. Orchestrator

**Test Purpose**: Verify that the orchestrator coordinates all components.

**Steps**:
1. Run the orchestrator: `python orchestrator.py --vault-path ./AI_Employee_Vault`
2. Verify that it starts the filesystem watcher
3. Verify that it starts the Gmail watcher
4. Verify that it starts the WhatsApp watcher
5. Place an approval file in `AI_Employee_Vault/Approved/`
6. Check that the orchestrator processes it

**Expected Results**:
- All watchers are started successfully
- Approval files are processed correctly
- Actions are logged to the logs directory

### 7. Plan Generator

**Test Purpose**: Verify that plans are created for tasks in Needs_Action.

**Steps**:
1. Create a test file in `AI_Employee_Vault/Needs_Action/`
2. Run the plan generator: `python plan_generator.py --vault-path ./AI_Employee_Vault`
3. Verify that a plan file is created in `AI_Employee_Vault/Plans/`
4. Check that the plan contains objective, steps, and approval requirements

**Expected Results**:
- Plan file is created for each task in Needs_Action
- Plan contains appropriate content based on task type
- Step-by-step checklist is provided

### 8. Windows Task Scheduler Setup

**Test Purpose**: Verify that the PowerShell script sets up scheduled tasks.

**Steps**:
1. Run the setup script as Administrator: `powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1`
2. Open Task Scheduler and verify that the tasks are created:
   - AI_Employee_Orchestrator (runs every 5 minutes)
   - AI_Employee_Gmail_Watcher (starts at startup)
   - AI_Employee_CEO_Briefing (runs Sunday at 9 PM)

**Expected Results**:
- All three tasks are created in Windows Task Scheduler
- Tasks have the correct triggers and actions

## Integration Testing

### End-to-End Email Flow
1. Send an important email to your Gmail account
2. Verify that the Gmail watcher creates a file in Needs_Action
3. Claude processes the file and creates a Plan.md
4. An approval request is created for any email response
5. After approval, email is sent and logged

### End-to-End LinkedIn Flow
1. LinkedIn content generator creates posts based on Business_Goals.md
2. Posts go to Pending_Approval/
3. Human approves by moving to Approved/
4. Orchestrator processes the approval
5. LinkedIn poster publishes the content (in non-dry-run mode)

## Troubleshooting

### Common Issues

1. **Gmail API Authentication Errors**:
   - Ensure credentials.json and token.json are properly set up
   - Check that the Gmail API is enabled in Google Cloud Console
   - Regenerate credentials if token is expired

2. **WhatsApp Session Issues**:
   - First run requires manual QR code scan
   - Session files are stored in whatsapp_session/ folder
   - Clear session files if authentication fails repeatedly

3. **LinkedIn Login Issues**:
   - Ensure credentials are correct
   - LinkedIn may require additional authentication steps
   - Check for CAPTCHA or security challenges

4. **MCP Server Connection Issues**:
   - Verify that the MCP server is running
   - Check that claude_mcp_config.json is properly configured
   - Ensure Node.js modules are installed

### Debugging Tips

- Enable detailed logging by adding `--debug` flags where available
- Check log files in the respective directories
- Use `--dry-run` mode extensively during initial testing
- Monitor the vault directories for expected file creation/movement
- Review the logs in `AI_Employee_Vault/Logs/` for audit trails