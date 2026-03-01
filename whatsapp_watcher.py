#!/usr/bin/env python3
"""
WhatsApp Watcher - Uses Playwright to monitor WhatsApp Web for unread messages
"""

import os
import sys
import time
import logging
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from playwright._impl._errors import TargetClosedError
from dotenv import load_dotenv
import re

import io

# Force UTF-8 encoding for all log output on Windows
handler = logging.StreamHandler(
    io.TextIOWrapper(
        sys.stdout.buffer,
        encoding='utf-8',
        errors='replace'
    )
)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logging.basicConfig(handlers=[handler], level=logging.DEBUG)

# Add file handler separately with UTF-8 encoding
file_handler = logging.FileHandler('whatsapp_watcher.log', encoding='utf-8')
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logging.getLogger().addHandler(file_handler)

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)

import hashlib
import json
import re
from datetime import datetime, timedelta

class WhatsAppWatcher:
    def __init__(self, vault_path=None, session_path=None, check_interval=30):
        """
        Initialize WhatsApp Watcher

        Args:
            vault_path: Path to the AI Employee vault
            session_path: Path to store WhatsApp session data
            check_interval: Interval in seconds between checks (default: 30)
        """
        self.vault_path = Path(vault_path) if vault_path else Path(os.getenv('VAULT_PATH', './AI_Employee_Vault'))
        self.needs_action_path = self.vault_path / 'Needs_Action'
        self.logs_path = self.vault_path / 'Logs'
        self.check_interval = check_interval

        # Use provided session path or default to whatsapp_session in vault
        self.session_path = Path(session_path) if session_path else self.vault_path / 'whatsapp_session'

        # Create directories if they don't exist
        self.needs_action_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.session_path.mkdir(parents=True, exist_ok=True)

        # Keywords to filter messages
        self.keywords = ['urgent', 'asap', 'invoice', 'payment', 'help', 'pricing', 'quote']

        # DRY_RUN mode
        self.dry_run = os.getenv('DRY_RUN', 'true').lower() == 'true'
        if self.dry_run:
            logger.info("DRY_RUN mode enabled - actions will be logged but not executed")

        # Set to keep track of processed chat previews to avoid duplicates
        self.processed_chat_previews = set()
        self.last_clear_time = datetime.now()

        # Load previously processed chats from file
        self.load_processed_chats()

    def filter_messages_by_keywords(self, message_text):
        """Check if message contains any of the monitored keywords."""
        message_lower = message_text.lower()
        return any(keyword in message_lower for keyword in self.keywords)

    def create_action_file(self, contact_name, message_text):
        """Create markdown file in Needs_Action folder for flagged messages."""
        # Final guard: check if a file for this contact+message hash already exists in Needs_Action/
        # Normalize the text for consistent hashing
        normalized_text = self.normalize_for_hash(message_text)
        normalized_contact = self.normalize_for_hash(contact_name)
        preview_hash = hashlib.md5(f"{normalized_contact}{normalized_text}".encode()).hexdigest()
        existing_files = list(self.needs_action_path.glob(f"WHATSAPP_{self.sanitize_contact_name(contact_name)}_*.md"))

        # Check if any existing file contains similar message content
        for existing_file in existing_files:
            try:
                with open(existing_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                if message_text[:20] in content:  # Check if first 20 chars of message are in the file
                    logger.warning(f"Duplicate action file would be created for {contact_name}: {message_text[:50]}..., skipping")
                    return None
            except:
                continue

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize contact name to create valid filename
        sanitized_contact_name = self.sanitize_contact_name(contact_name)
        filename = f"WHATSAPP_{sanitized_contact_name}_{timestamp}.md"
        filepath = self.needs_action_path / filename

        content = f"""---
type: whatsapp_message
from: {contact_name}
received: {datetime.now().isoformat()}
priority: high
status: pending
keywords_matched: {', '.join([kw for kw in self.keywords if kw.lower() in message_text.lower()])}
---

## WhatsApp Message
Contact: {contact_name}

Message: {message_text}

## Suggested Actions
- [ ] Review the message content
- [ ] Respond appropriately
- [ ] Take necessary action based on keywords

## Keywords Matched
{', '.join([kw for kw in self.keywords if kw.lower() in message_text.lower()])}

## Suggested Reply
{(self.generate_suggested_reply(contact_name, message_text))}
"""

        if not self.dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Created action file: {filepath}")
        else:
            logger.info(f"[DRY RUN] Would create action file: {filepath}")

        return filepath

    def generate_suggested_reply(self, contact_name, message_text):
        """Generate a suggested reply based on the message content."""
        message_lower = message_text.lower()

        if 'urgent' in message_lower or 'asap' in message_lower:
            return f"Hi {contact_name}, thanks for reaching out. I've noted this as urgent and will prioritize addressing your request. I'll get back to you shortly."
        elif 'quote' in message_lower or 'pricing' in message_lower:
            return f"Hi {contact_name}, thank you for your inquiry about pricing. I'll prepare a detailed quote for you and send it over soon."
        elif 'invoice' in message_lower:
            return f"Hi {contact_name}, I've received your invoice request. I'll review the details and process it according to our standard procedure."
        elif 'payment' in message_lower:
            return f"Hi {contact_name}, regarding the payment inquiry, I'll check the status and provide you with an update shortly."
        elif 'help' in message_lower:
            return f"Hi {contact_name}, I'm here to help. Could you please provide more details about what you need assistance with?"
        else:
            return f"Hi {contact_name}, thanks for your message. I'll review your request and get back to you as soon as possible."

    def sanitize_contact_name(self, contact_name):
        """Sanitize contact name to create a valid Windows filename."""
        if not contact_name:
            return "Unknown_Contact"

        # Strip any URL (anything starting with http:// or https://) and replace with "Group_Chat"
        if 'http://' in contact_name or 'https://' in contact_name:
            contact_name = "Group_Chat"

        # Remove ALL characters that are invalid in Windows filenames: \ / : * ? " < > |
        invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            contact_name = contact_name.replace(char, '_')

        # Replace spaces with underscores
        contact_name = contact_name.replace(' ', '_')

        # Truncate contact name to max 30 characters
        contact_name = contact_name[:30]

        # If result is empty after sanitization, use "Unknown_Contact"
        if not contact_name or contact_name.isspace():
            contact_name = "Unknown_Contact"

        return contact_name

    def normalize_for_hash(self, text):
        """Normalize text for consistent hashing - strip trailing digits, whitespace, lowercase, and truncate."""
        if not text:
            return ""
        # Strip trailing digits (the unread count badge from WhatsApp UI)
        normalized = re.sub(r'\d+$', '', text)
        # Strip whitespace and lowercase
        normalized = normalized.strip().lower()
        # Take only first 50 characters
        return normalized[:50]

    def should_clear_processed_chats(self):
        """Check if it's time to clear the processed chats set (every 24 hours)."""
        time_diff = datetime.now() - self.last_clear_time
        return time_diff.total_seconds() >= 24 * 3600  # 24 hours in seconds

    def clear_processed_chats_if_needed(self):
        """Clear the processed chats set if 24 hours have passed."""
        if self.should_clear_processed_chats():
            logger.info("Clearing processed chats set (24 hour cycle)")
            self.processed_chat_previews.clear()
            self.last_clear_time = datetime.now()

    def load_processed_chats(self):
        """Load previously processed chats from file."""
        processed_chats_file = self.logs_path / 'processed_chats.json'
        try:
            if processed_chats_file.exists():
                with open(processed_chats_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_chat_previews = set(data.get('processed_chats', []))
                logger.info(f"Loaded {len(self.processed_chat_previews)} previously processed chats from file")
        except Exception as e:
            logger.error(f"Error loading processed chats from file: {e}")

    def save_processed_chats(self):
        """Save processed chats to file."""
        processed_chats_file = self.logs_path / 'processed_chats.json'
        try:
            data = {'processed_chats': list(self.processed_chat_previews)}
            with open(processed_chats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving processed chats to file: {e}")

    def is_logged_in(self, page):
        """Check if WhatsApp is logged in by looking for elements that appear only when logged in."""
        logged_in_indicators = [
            'div[aria-label="Chat list"]',
            '[data-testid="chat-list"]',
            '#side',
            'div[role="grid"]',
            '[data-testid="default-user"]',
            '[data-testid="chat"]'
        ]

        for indicator in logged_in_indicators:
            try:
                if page.query_selector(indicator):
                    logger.info(f"Logged in indicator found: {indicator}")
                    return True
            except:
                continue

        return False

    def check_whatsapp_web(self):
        """Check WhatsApp Web for unread messages."""
        flagged_messages = []

        try:
            with sync_playwright() as p:
                # Launch browser with persistent context to maintain WhatsApp session
                browser = p.chromium.launch_persistent_context(
                    str(self.session_path),
                    headless=False,  # Set to True for production
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                    timezone_id='America/New_York'
                )

                page = browser.new_page()
                page.goto('https://web.whatsapp.com/', wait_until='networkidle')

                # Add 5 second sleep after page.goto() before waiting for any selector
                time.sleep(5)
                logger.info("Navigated to WhatsApp Web, waiting for page to load...")

                # Check if already logged in first
                if self.is_logged_in(page):
                    logger.info("Already logged in to WhatsApp Web")
                else:
                    logger.info("Not logged in, checking for QR code or login screen...")

                    # Wait for WhatsApp to load with improved selector logic
                    chat_list_loaded = False
                    selectors_to_try = [
                        'div[aria-label="Chat list"]',
                        '[data-testid="chat-list"]',
                        '#side',
                        'div[role="grid"]'
                    ]

                    for selector in selectors_to_try:
                        try:
                            logger.info(f"Trying selector: {selector}")
                            page.wait_for_selector(selector, timeout=60000)  # Updated timeout to 60000ms
                            logger.info(f"WhatsApp Web loaded successfully with selector: {selector}")
                            chat_list_loaded = True
                            break
                        except Exception as e:
                            logger.info(f"Selector '{selector}' failed: {str(e)}")
                            continue

                    if not chat_list_loaded:
                        # If none of the main selectors worked, check if we're still on the QR code screen
                        qr_selectors = ['canvas[data-ref]', '[data-testid="qr-tab"]', '[data-testid="f7nni5sa"]', '._3quh._30yy._2t_']
                        qr_detected = False
                        for qr_selector in qr_selectors:
                            try:
                                if page.is_visible(qr_selector):
                                    logger.warning(f"QR code detected with selector: {qr_selector} - scan to log in to WhatsApp Web")
                                    qr_detected = True
                                    break
                            except:
                                continue

                        if qr_detected:
                            browser.close()
                            return flagged_messages
                        else:
                            logger.error("WhatsApp Web did not load properly with any of the expected selectors")
                            logger.info("Available elements on page: ")
                            try:
                                # Log some general page info to help debug
                                title = page.title()
                                logger.info(f"Page title: {title}")

                                # Get more detailed page information
                                html_content = page.inner_html('body')
                                logger.debug(f"Body HTML length: {len(html_content)}")

                                # Look for common WhatsApp Web elements
                                possible_indicators = [
                                    '[data-testid*="login"]',
                                    '.landing-window',
                                    '._3quh._30yy._2t_',
                                    '[data-testid="default-user"]',
                                    '[data-testid="f7nni5sa"]',  # Another possible QR code selector
                                    '[data-testid="chat"]',
                                    'canvas',
                                    'img[alt*="QR"]',
                                    '[data-icon="qr-outline"]'
                                ]
                                for indicator in possible_indicators:
                                    try:
                                        elements = page.query_selector_all(indicator)
                                        if elements:
                                            logger.info(f"Found {len(elements)} elements with selector: {indicator}")
                                            # Get text content of first few elements
                                            for i, elem in enumerate(elements[:3]):
                                                try:
                                                    text = elem.text_content()[:100]  # First 100 chars
                                                    logger.debug(f"  Element {i+1} text: {text}")
                                                except:
                                                    continue
                                        else:
                                            logger.debug(f"No elements found with selector: {indicator}")
                                    except Exception as e:
                                        logger.debug(f"Error querying selector '{indicator}': {str(e)}")
                            except Exception as e:
                                logger.error(f"Error getting page info: {str(e)}")

                            browser.close()
                            return flagged_messages

                # Get all chats from the chat list and check for keywords in their content
                logger.info("Looking for chats containing keywords...")

                # First, get all chat elements
                all_chats = []
                chat_list_selectors = [
                    'div[aria-label="Chat list"] > div > div',
                    'div[aria-label="Chat list"] [role="row"]',
                    '[data-testid="chat-list"] [role="row"]',
                    '#pane-side [role="row"]',
                    'div[role="navigation"] [role="row"]'
                ]

                for selector in chat_list_selectors:
                    try:
                        logger.info(f"Trying chat list selector: {selector}")
                        temp_chats = page.query_selector_all(selector)
                        if temp_chats:
                            all_chats = temp_chats
                            logger.info(f"Found {len(temp_chats)} chats with selector: {selector}")

                            # Debug mode: print HTML of first 3 chat items
                            if logger.level <= logging.DEBUG:
                                for i, chat in enumerate(all_chats[:3]):
                                    try:
                                        chat_html = chat.inner_html()[:500]  # First 500 chars
                                        logger.debug(f"Chat {i+1} HTML: {chat_html}...")

                                        # Also get aria-label and text content
                                        aria_label = chat.get_attribute('aria-label')
                                        text_content = chat.text_content()[:200]  # First 200 chars
                                        # Safely log with Unicode handling
                                        try:
                                            safe_aria_label = aria_label.encode('utf-8', errors='replace').decode('utf-8') if aria_label else ""
                                            safe_text_content = text_content.encode('utf-8', errors='replace').decode('utf-8')
                                            logger.debug(f"  aria-label: {safe_aria_label}")
                                            logger.debug(f"  text_content: {safe_text_content}...")
                                        except:
                                            logger.debug(f"  aria-label: {aria_label}" if aria_label else "  aria-label: None")
                                            logger.debug(f"  text_content: {text_content[:100]}...")
                                    except Exception as e_debug:
                                        logger.debug(f"  Could not get debug info for chat {i+1}: {str(e_debug)}")

                            break
                        else:
                            logger.info(f"No chats found with selector: {selector}")
                    except Exception as e:
                        logger.info(f"Chat list selector '{selector}' failed: {str(e)}")
                        continue

                if not all_chats:
                    logger.warning("No chats found in the chat list")
                    # Still close the browser and return empty list
                    browser.close()
                    return flagged_messages

                # Filter chats that contain keywords in their text content
                keyword_chats = []
                for chat in all_chats:
                    try:
                        # Get the text content of the chat element
                        chat_text = chat.text_content().lower()

                        # Check if the chat text contains any of our keywords
                        if any(keyword in chat_text for keyword in self.keywords):
                            keyword_chats.append(chat)
                            # Safely log chat text with Unicode handling
                            try:
                                safe_chat_text = chat_text.encode('utf-8', errors='replace').decode('utf-8')
                                logger.info(f"Found keyword '{next(k for k in self.keywords if k in chat_text)}' in chat: {safe_chat_text[:100]}...")
                            except:
                                logger.info(f"Found keyword '{next(k for k in self.keywords if k in chat_text)}' in chat")
                        else:
                            # Also check for unread message badges with numbers
                            # Look for elements that might contain unread counts
                            badge_selectors = ['[aria-label*="unread"]', 'span:has(> div:where(:not([style*="hidden"])))']
                            has_unread_badge = False

                            for badge_selector in badge_selectors:
                                try:
                                    badge_elements = chat.query_selector_all(badge_selector)
                                    if badge_elements:
                                        for badge_elem in badge_elements:
                                            badge_text = badge_elem.text_content().strip()
                                            # Check if it contains a number (likely an unread count)
                                            if badge_text.isdigit() and int(badge_text) > 0:
                                                has_unread_badge = True
                                                break
                                except:
                                    continue

                            if has_unread_badge:
                                keyword_chats.append(chat)
                                # Safely log chat text with Unicode handling
                                try:
                                    safe_chat_text = chat_text.encode('utf-8', errors='replace').decode('utf-8')
                                    logger.info(f"Found chat with unread badge: {safe_chat_text[:100]}...")
                                except:
                                    logger.info(f"Found chat with unread badge")

                    except Exception as e:
                        logger.debug(f"Error checking chat for keywords: {str(e)}")
                        continue

                # If no chats were found with keywords or unread badges, use all chats as fallback
                if not keyword_chats:
                    logger.info(f"No chats contained keywords or unread badges, checking all {len(all_chats)} chats for keyword messages")
                    chats_to_check = all_chats
                else:
                    logger.info(f"Found {len(keyword_chats)} chats with keywords or unread badges")
                    chats_to_check = keyword_chats

                # Instead of clicking into each chat, try to get recent message previews from the chat list
                for chat in chats_to_check:
                    try:
                        # Get the chat text content to extract contact name and preview messages
                        chat_text = chat.text_content()

                        # Check if the raw chat text_content contains "(You)" anywhere - skip entire chat if outgoing message
                        if "(you)" in chat_text.lower():
                            logger.debug(f"Skipping outgoing message from {chat_text[:50]}...")
                            continue

                        # Extract contact name from the chat element using regex
                        contact_name = "Unknown Contact"

                        # Define time patterns to look for
                        import re
                        time_patterns = [
                            r'Yesterday',
                            r'Today',
                            r'\d{1,2}:\d{2}',  # HH:MM format
                            r'\d{1,2}/\d{1,2}/\d{4}'  # MM/DD/YYYY format
                        ]

                        # Combine all time patterns into one regex
                        combined_pattern = '(' + '|'.join(time_patterns) + ')'

                        # Search for the first occurrence of any time pattern
                        match = re.search(combined_pattern, chat_text)

                        if match:
                            # Extract everything before the first time pattern
                            contact_part = chat_text[:match.start()].strip()

                            # Handle "default-contact-refreshed+92 307 3929690" style names
                            if 'default-contact-refreshed' in contact_part or 'default-group-refreshed' in contact_part:
                                # Extract phone number part (starts with +)
                                phone_match = re.search(r'\+\d+(?:\s\d+)*', contact_part)
                                if phone_match:
                                    contact_name = phone_match.group(0)
                                else:
                                    # If no phone number found, use whatever comes after the default pattern
                                    after_default = re.sub(r'^default-[^+]*', '', contact_part)
                                    contact_name = after_default.strip() if after_default.strip() else "Unknown Contact"
                            else:
                                contact_name = contact_part
                        else:
                            # If no time pattern found, use the first part of the text
                            # Split by common separators and take the first meaningful part
                            parts = re.split(r'[Yy]esterday|[Tt]oday|\d{1,2}:\d{2}|\d{1,2}/\d{1,2}/\d{4}', chat_text)
                            if parts and parts[0]:
                                contact_part = parts[0].strip()

                                # Handle "default-contact-refreshed+92 307 3929690" style names
                                if 'default-contact-refreshed' in contact_part or 'default-group-refreshed' in contact_part:
                                    # Extract phone number part (starts with +)
                                    phone_match = re.search(r'\+\d+(?:\s\d+)*', contact_part)
                                    if phone_match:
                                        contact_name = phone_match.group(0)
                                    else:
                                        after_default = re.sub(r'^default-[^+]*', '', contact_part)
                                        contact_name = after_default.strip() if after_default.strip() else "Unknown Contact"
                                else:
                                    contact_name = contact_part

                        # Clean up the contact name by stripping extra whitespace
                        contact_name = contact_name.strip()

                        # If contact name is empty, use default
                        if not contact_name:
                            contact_name = "Unknown Contact"

                        # Now try to find message previews in the chat element
                        # Look for text that might be recent messages
                        message_preview_selectors = [
                            'div[aria-label*="message"]',
                            '[data-testid="conversation-snippet"]',
                            'span[dir="auto"]:last-child',
                            'div:last-child',
                            'div[dir="auto"]'
                        ]

                        message_found = False
                        for preview_selector in message_preview_selectors:
                            try:
                                preview_elements = chat.query_selector_all(preview_selector)
                                for preview_elem in preview_elements:
                                    preview_text = preview_elem.text_content().strip()
                                    if preview_text and len(preview_text) > 2:  # Meaningful text
                                        # Check if the preview text contains any of our keywords
                                        if self.filter_messages_by_keywords(preview_text):
                                            # Filter out junk WhatsApp UI artifacts
                                            clean_preview_text = preview_text.strip()
                                            junk_patterns = [
                                                "status-dblcheck", "status-ciphertext", "wds-ic-", "ic-",
                                                "default-contact-refreshed", "default-group-refreshed"
                                            ]

                                            # Check if message contains only junk artifacts
                                            is_junk = any(junk in clean_preview_text.lower() for junk in junk_patterns)
                                            if is_junk:
                                                # Add hash to processed set to prevent future processing of same junk
                                                normalized_text = self.normalize_for_hash(clean_preview_text)
                                                normalized_contact = self.normalize_for_hash(contact_name)
                                                preview_hash = hashlib.md5(f"{normalized_contact}{normalized_text}".encode()).hexdigest()
                                                self.processed_chat_previews.add(preview_hash)
                                                logger.debug(f"Skipping junk artifact from {contact_name}: {clean_preview_text[:50]}...")
                                                continue

                                            # Check if message is outgoing (contains "(You)" or "(you)")
                                            if "(you)" in clean_preview_text.lower():
                                                logger.debug(f"Skipping outgoing message from {contact_name}: {clean_preview_text[:50]}...")
                                                continue

                                            # Normalize the text for consistent hashing
                                            normalized_text = self.normalize_for_hash(clean_preview_text)
                                            normalized_contact = self.normalize_for_hash(contact_name)

                                            # Create a hash of contact_name + normalized message to check for duplicates
                                            preview_hash = hashlib.md5(f"{normalized_contact}{normalized_text}".encode()).hexdigest()

                                            # Check if this combination was already processed - BEFORE adding to list
                                            if preview_hash in self.processed_chat_previews:
                                                logger.debug(f"Skipping duplicate message from {contact_name}: {clean_preview_text[:50]}...")
                                                continue

                                            # Add to processed set and create action file
                                            self.processed_chat_previews.add(preview_hash)
                                            flagged_messages.append({
                                                'contact': contact_name,
                                                'message': clean_preview_text
                                            })
                                            # Safely log with Unicode handling
                                            try:
                                                safe_preview_text = preview_text.encode('utf-8', errors='replace').decode('utf-8')
                                                safe_contact_name = contact_name.encode('utf-8', errors='replace').decode('utf-8')
                                                logger.info(f"Flagged message preview from {safe_contact_name}: {safe_preview_text[:50]}...")
                                            except:
                                                logger.info(f"Flagged message preview from {contact_name}: {preview_text[:50]}...")
                                            message_found = True
                                            break
                                if message_found:
                                    break
                            except:
                                continue

                        # If no message preview was found in the chat list, we could optionally click into the chat
                        # But for now, let's try to avoid clicking and just use previews from the chat list
                        if not message_found:
                            # As a fallback, we can still click into important chats to read full messages
                            # But let's try other selectors first without clicking

                            # Look for any elements in the chat that might contain message content
                            try:
                                # Try to get any text content from the chat element that might be message previews
                                all_text_elements = chat.query_selector_all('div, span, p')
                                for text_elem in all_text_elements:
                                    element_text = text_elem.text_content().strip()
                                    if element_text and len(element_text) > 5:  # At least some meaningful text
                                        if self.filter_messages_by_keywords(element_text):
                                            # Filter out junk WhatsApp UI artifacts
                                            clean_element_text = element_text.strip()
                                            junk_patterns = [
                                                "status-dblcheck", "status-ciphertext", "wds-ic-", "ic-",
                                                "default-contact-refreshed", "default-group-refreshed"
                                            ]

                                            # Check if message contains only junk artifacts
                                            is_junk = any(junk in clean_element_text.lower() for junk in junk_patterns)
                                            if is_junk:
                                                # Add hash to processed set to prevent future processing of same junk
                                                normalized_text = self.normalize_for_hash(clean_element_text)
                                                normalized_contact = self.normalize_for_hash(contact_name)
                                                preview_hash = hashlib.md5(f"{normalized_contact}{normalized_text}".encode()).hexdigest()
                                                self.processed_chat_previews.add(preview_hash)
                                                logger.debug(f"Skipping junk artifact from {contact_name} (preview): {clean_element_text[:50]}...")
                                                continue

                                            # Check if message is outgoing (contains "(You)" or "(you)")
                                            if "(you)" in clean_element_text.lower():
                                                logger.debug(f"Skipping outgoing message from {contact_name} (preview): {clean_element_text[:50]}...")
                                                continue

                                            # Normalize the text for consistent hashing
                                            normalized_text = self.normalize_for_hash(clean_element_text)
                                            normalized_contact = self.normalize_for_hash(contact_name)

                                            # Create a hash of contact_name + normalized message to check for duplicates
                                            preview_hash = hashlib.md5(f"{normalized_contact}{normalized_text}".encode()).hexdigest()

                                            # Check if this combination was already processed - BEFORE adding to list
                                            if preview_hash in self.processed_chat_previews:
                                                logger.debug(f"Skipping duplicate message from {contact_name} (preview): {clean_element_text[:50]}...")
                                                continue

                                            # Add to processed set and create action file
                                            self.processed_chat_previews.add(preview_hash)
                                            flagged_messages.append({
                                                'contact': contact_name,
                                                'message': clean_element_text
                                            })
                                            # Safely log with Unicode handling
                                            try:
                                                safe_element_text = element_text.encode('utf-8', errors='replace').decode('utf-8')
                                                safe_contact_name = contact_name.encode('utf-8', errors='replace').decode('utf-8')
                                                logger.info(f"Flagged message from {safe_contact_name} (preview): {safe_element_text[:50]}...")
                                            except:
                                                logger.info(f"Flagged message from {contact_name} (preview): {element_text[:50]}...")
                                            message_found = True
                                            break
                            except:
                                continue

                    except Exception as e:
                        logger.error(f"Error processing chat preview: {e}", exc_info=True)
                        continue

                # Close browser
                try:
                    browser.close()
                except TargetClosedError:
                    # Silently handle TargetClosedError - this is expected when user stops the watcher
                    pass
                except:
                    # Silently handle other browser close errors - this is expected when user stops the watcher
                    pass

        except TargetClosedError:
            # Silently handle TargetClosedError - this is expected when user stops the watcher
            return flagged_messages
        except Exception as e:
            logger.error(f"Error checking WhatsApp Web: {e}", exc_info=True)  # Added exc_info for full traceback
            # Don't close browser here as it might not exist

            # Handle session expiry gracefully
            if "session" in str(e).lower() or "authentication" in str(e).lower():
                logger.warning("WhatsApp session may have expired. Please log in again by scanning the QR code.")

            return flagged_messages

        # Safety net deduplication filter - catches anything that slipped through
        seen = set()
        deduped = []
        for msg in flagged_messages:
            h = self.normalize_for_hash(msg['contact'] + msg['message'])
            hash_combined = hashlib.md5(h.encode()).hexdigest()
            if h not in seen and hash_combined not in self.processed_chat_previews:
                seen.add(h)
                self.processed_chat_previews.add(hash_combined)  # Add to processed set
                deduped.append(msg)

        return deduped

    def run(self):
        """Main run loop for the WhatsApp Watcher."""
        logger.info("Starting WhatsApp Watcher...")
        logger.info(f"Checking every {self.check_interval} seconds")
        logger.info(f"Dry run mode: {self.dry_run}")
        logger.info(f"Monitoring keywords: {', '.join(self.keywords)}")

        while True:
            try:
                # Clear processed chats if needed (every 24 hours)
                self.clear_processed_chats_if_needed()

                flagged_messages = self.check_whatsapp_web()

                for msg in flagged_messages:
                    self.create_action_file(msg['contact'], msg['message'])

                if flagged_messages:
                    logger.info(f"Flagged {len(flagged_messages)} messages for action")

                # Save processed chats to file after each cycle
                self.save_processed_chats()

                # Wait before next check
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("WhatsApp Watcher stopped by user")
                # Save processed chats before exiting
                self.save_processed_chats()
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")

                # Log session expiry gracefully
                if "session" in str(e).lower() or "auth" in str(e).lower():
                    logger.warning("Session may have expired - please log in again by scanning QR code when prompted")

                logger.info(f"Waiting {self.check_interval} seconds before retrying...")
                time.sleep(self.check_interval)

def main():
    """Main function to run the WhatsApp Watcher."""
    import argparse

    parser = argparse.ArgumentParser(description='WhatsApp Watcher for AI Employee')
    parser.add_argument('--vault-path', default='./AI_Employee_Vault', help='Path to AI Employee vault')
    parser.add_argument('--session-path', help='Path to store WhatsApp session data')
    parser.add_argument('--check-interval', type=int, default=30, help='Check interval in seconds (default: 30)')
    parser.add_argument('--dry-run', action='store_true', help='Enable dry run mode')

    args = parser.parse_args()

    # Override DRY_RUN from command line if specified
    if args.dry_run:
        os.environ['DRY_RUN'] = 'true'

    watcher = WhatsAppWatcher(
        vault_path=args.vault_path,
        session_path=args.session_path,
        check_interval=args.check_interval
    )

    watcher.run()

if __name__ == '__main__':
    main()