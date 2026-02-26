# WhatsApp Watcher Skill

## Description
Uses Playwright with persistent session to monitor WhatsApp Web for unread messages every 30 seconds, filtering for specific keywords and saving flagged messages to Needs_Action/ folder.

## Inputs
- WhatsApp session stored in whatsapp_session/ folder
- Check interval configuration (default: 30 seconds)
- Keyword filters (urgent, asap, invoice, payment, help, pricing, quote)
- DRY_RUN mode flag (default: true)

## Outputs
- Creates markdown files in Needs_Action/ as WHATSAPP_{contact}_{timestamp}.md
- Filters messages based on predefined keywords
- Handles session expiry gracefully

## Hard Limits
- Must never send messages without human approval
- Must never store WhatsApp credentials or session data insecurely
- Must always respect DRY_RUN mode until manually changed
- Must never violate WhatsApp Terms of Service
- Must never bypass session management
- Must never crash on session expiry - should log warning and continue