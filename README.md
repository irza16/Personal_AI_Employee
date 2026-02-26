# Personal AI Employee - Silver Tier Implementation

This project implements a Personal AI Employee using Claude Code as the reasoning engine, with Obsidian as the knowledge base and dashboard.

## Silver Tier Features

### 1. Multi-Channel Monitoring (Watchers)
- **Gmail Watcher**: Monitors Gmail for unread + important messages every 120 seconds
- **WhatsApp Watcher**: Monitors WhatsApp Web for messages with keywords (urgent, asap, invoice, payment, help, pricing, quote) every 30 seconds
- **LinkedIn Poster**: Automated LinkedIn posting with human approval workflow
- **File System Watcher**: Monitors local file system changes

### 2. Human-in-the-Loop (HITL) Approval System
- **Approval Workflow**: All sensitive actions require approval files in `/Approved/` folder
- **Pending Approval**: Requests are placed in `/Pending_Approval/` for review
- **Audit Logging**: All actions logged to `/Logs/` in JSON format
- **Rejected Handling**: Rejected actions moved to `/Done/` with rejection noted

### 3. MCP (Model Context Protocol) Servers
- **Email MCP**: Send, draft, and search emails via Gmail API
- **LinkedIn MCP**: Post content to LinkedIn (with approval required)

### 4. Automated Scheduling
- **Windows Task Scheduler**: Orchestrator runs every 5 minutes
- **Startup Jobs**: Gmail watcher starts automatically
- **Weekly Reports**: Sunday 9PM CEO briefing generation

### 5. Planning System
- **Plan Generation**: Creates Plan.md files for each task in `/Needs_Action/`
- **Step-by-step Checklists**: Detailed action items for each task
- **Approval Requirements**: Noted in all generated plans

## Architecture

The system follows a perception-reasoning-action loop:

- **Perception**: Python watcher scripts monitor external sources (Gmail, WhatsApp, File System)
- **Reasoning**: Claude Code processes information, creates plans, and makes decisions
- **Action**: MCP servers perform external actions (send emails, post to LinkedIn)
- **HITL**: Human approval required for sensitive actions

## Components

- `gmail_watcher.py`: Monitors Gmail using OAuth, saves emails to `/Needs_Action/`
- `whatsapp_watcher.py`: Monitors WhatsApp Web for keyword-triggered messages
- `linkedin_poster.py`: Automated LinkedIn posting with approval workflow
- `linkedin_content_generator.py`: Creates LinkedIn posts based on Business_Goals.md
- `filesystem_watcher.py`: Monitors file system changes
- `orchestrator.py`: Coordinates system components and processes approvals
- `plan_generator.py`: Creates Plan.md files for tasks
- `mcp_servers/email_mcp/index.js`: MCP server for email operations
- `setup_scheduler.ps1`: Windows Task Scheduler configuration
- `.claude/skills/`: Skill definitions for various capabilities
- `AI_Employee_Vault/`: Obsidian vault with dashboard and handbook

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Install Node.js dependencies: `npm install googleapis dotenv`
3. Set up your Obsidian vault in `AI_Employee_Vault/`
4. Configure OAuth for Gmail (credentials.json and token.json in vault)
5. Set up LinkedIn credentials in `.env` file
6. Run the orchestrator: `python orchestrator.py`

### Environment Variables (.env file in AI_Employee_Vault/)
```
LINKEDIN_USERNAME=your_linkedin_username
LINKEDIN_PASSWORD=your_linkedin_password
DRY_RUN=true  # Set to false when ready to execute actions
VAULT_PATH=./AI_Employee_Vault
```

### Running the System
1. Install Playwright browsers: `playwright install`
2. Set up Gmail OAuth: Visit Gmail API quickstart to get credentials.json
3. Run orchestrator: `python orchestrator.py`
4. For Windows scheduling: Run `setup_scheduler.ps1` as Administrator

## Security & Privacy

- All credentials stored in `.env` file (not committed to git)
- Gmail API uses OAuth 2.0 with proper scopes
- All sensitive actions require explicit approval files
- Session data stored locally in vault
- Comprehensive audit logging for all actions

## Folder Structure
- `/Needs_Action/`: Incoming tasks from watchers
- `/Pending_Approval/`: Actions requiring human approval
- `/Approved/`: Approved actions to execute
- `/Rejected/`: Rejected actions
- `/Done/`: Completed tasks
- `/Plans/`: Generated plans for tasks
- `/Logs/`: Audit logs in JSON format
- `/Briefings/`: CEO briefing reports
- `/Accounting/`: Financial records