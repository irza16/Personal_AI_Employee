const fs = require('fs').promises;
const path = require('path');
const { google } = require('googleapis');
require('dotenv').config();

// Configuration
const VAULT_PATH = process.env.VAULT_PATH || path.join(__dirname, '..', '..');
const LOGS_DIR = path.join(VAULT_PATH, 'Logs');
const APPROVED_DIR = path.join(VAULT_PATH, 'Approved');

// Ensure logs directory exists
async function ensureDirectoryExists(dirPath) {
  try {
    await fs.access(dirPath);
  } catch {
    await fs.mkdir(dirPath, { recursive: true });
  }
}

// Initialize Gmail API
let gmailService = null;

async function initializeGmailService() {
  try {
    const credentialsPath = path.join(__dirname, '..', '..', 'AI_Employee_Vault', 'credentials.json');
    const tokenPath = path.join(__dirname, '..', '..', 'AI_Employee_Vault', 'token.json');

    // Check if credentials exist
    await fs.access(credentialsPath);
    await fs.access(tokenPath);

    const credentials = JSON.parse(await fs.readFile(credentialsPath));
    const token = JSON.parse(await fs.readFile(tokenPath));

    const { client_secret, client_id, redirect_uris } = credentials.installed;
    const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);

    oAuth2Client.setCredentials(token);

    gmailService = google.gmail({ version: 'v1', auth: oAuth2Client });
    console.log('Gmail service initialized successfully');
  } catch (error) {
    console.error('Error initializing Gmail service:', error.message);
    throw error;
  }
}

// Log action to JSON file
async function logAction(actionType, actor, target, approvalStatus, result, parameters = {}) {
  try {
    await ensureDirectoryExists(LOGS_DIR);

    const logEntry = {
      timestamp: new Date().toISOString(),
      action_type: actionType,
      actor: actor,
      target: target,
      approval_status: approvalStatus,
      result: result,
      parameters: parameters
    };

    const logFileName = `${new Date().toISOString().split('T')[0]}.json`;
    const logFilePath = path.join(LOGS_DIR, logFileName);

    let existingLogs = [];
    try {
      const existingLogContent = await fs.readFile(logFilePath, 'utf8');
      existingLogs = JSON.parse(existingLogContent);
    } catch (readError) {
      // File doesn't exist yet, start with empty array
      existingLogs = [];
    }

    existingLogs.push(logEntry);

    await fs.writeFile(logFilePath, JSON.stringify(existingLogs, null, 2));
  } catch (error) {
    console.error('Error logging action:', error.message);
  }
}

// Check for approval file
async function checkApproval(requiredParams) {
  try {
    const files = await fs.readdir(APPROVED_DIR);

    for (const file of files) {
      if (file.endsWith('.md')) {
        const filePath = path.join(APPROVED_DIR, file);
        const content = await fs.readFile(filePath, 'utf8');

        // Check if this approval file matches the required parameters
        if (content.includes('send_email') &&
            content.includes(requiredParams.to) &&
            content.includes(requiredParams.subject)) {
          return { approved: true, file: filePath };
        }
      }
    }

    return { approved: false, file: null };
  } catch (error) {
    console.error('Error checking approval:', error.message);
    return { approved: false, file: null };
  }
}

// MCP Tools
const tools = [
  {
    name: 'send_email',
    description: 'Send an email via Gmail API. Requires approval file in Approved/ folder.',
    inputSchema: {
      type: 'object',
      properties: {
        to: { type: 'string', description: 'Recipient email address' },
        subject: { type: 'string', description: 'Email subject' },
        body: { type: 'string', description: 'Email body content' },
        cc: { type: 'string', description: 'CC recipients (optional)' },
        bcc: { type: 'string', description: 'BCC recipients (optional)' }
      },
      required: ['to', 'subject', 'body']
    }
  },
  {
    name: 'draft_email',
    description: 'Create a draft email in Gmail.',
    inputSchema: {
      type: 'object',
      properties: {
        to: { type: 'string', description: 'Recipient email address' },
        subject: { type: 'string', description: 'Email subject' },
        body: { type: 'string', description: 'Email body content' },
        cc: { type: 'string', description: 'CC recipients (optional)' },
        bcc: { type: 'string', description: 'BCC recipients (optional)' }
      },
      required: ['to', 'subject', 'body']
    }
  },
  {
    name: 'search_emails',
    description: 'Search emails in Gmail inbox.',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Search query (e.g., "from:example@email.com subject:urgent")' },
        maxResults: { type: 'number', description: 'Maximum number of results to return (default: 10)' }
      },
      required: ['query']
    }
  }
];

// MCP Handler
async function handleCall(toolName, parameters) {
  if (!gmailService) {
    await initializeGmailService();
  }

  switch (toolName) {
    case 'send_email':
      return await sendEmail(parameters);
    case 'draft_email':
      return await draftEmail(parameters);
    case 'search_emails':
      return await searchEmails(parameters);
    default:
      throw new Error(`Unknown tool: ${toolName}`);
  }
}

async function sendEmail(params) {
  // Check for approval
  const approval = await checkApproval({ to: params.to, subject: params.subject });

  if (!approval.approved) {
    await logAction(
      'send_email',
      'email_mcp',
      params.to,
      'denied',
      'No approval file found in Approved/ folder',
      params
    );
    throw new Error(`Cannot send email to ${params.to} without approval. Create approval file in Approved/ folder.`);
  }

  try {
    // Create email message
    const emailLines = [
      `To: ${params.to}`,
      `Subject: ${params.subject}`,
      '',
      params.body
    ];

    if (params.cc) {
      emailLines.splice(1, 0, `Cc: ${params.cc}`);
    }

    if (params.bcc) {
      emailLines.splice(1, 0, `Bcc: ${params.bcc}`);
    }

    const rawEmail = Buffer.from(emailLines.join('\r\n')).toString('base64').replace(/\+/g, '-').replace(/\//g, '_');

    // Send the email
    const result = await gmailService.users.messages.send({
      userId: 'me',
      requestBody: {
        raw: rawEmail
      }
    });

    await logAction(
      'send_email',
      'email_mcp',
      params.to,
      'approved',
      'success',
      params
    );

    // Remove the approval file after successful send
    try {
      await fs.unlink(approval.file);
      console.log(`Removed approval file: ${approval.file}`);
    } catch (unlinkError) {
      console.error('Error removing approval file:', unlinkError.message);
    }

    return {
      success: true,
      messageId: result.data.id,
      message: `Email sent successfully to ${params.to}`
    };
  } catch (error) {
    await logAction(
      'send_email',
      'email_mcp',
      params.to,
      'approved',
      `error: ${error.message}`,
      params
    );

    throw new Error(`Failed to send email: ${error.message}`);
  }
}

async function draftEmail(params) {
  try {
    // Create email message
    const emailLines = [
      `To: ${params.to}`,
      `Subject: ${params.subject}`,
      '',
      params.body
    ];

    if (params.cc) {
      emailLines.splice(1, 0, `Cc: ${params.cc}`);
    }

    if (params.bcc) {
      emailLines.splice(1, 0, `Bcc: ${params.bcc}`);
    }

    const rawEmail = Buffer.from(emailLines.join('\r\n')).toString('base64').replace(/\+/g, '-').replace(/\//g, '_');

    // Create the draft
    const result = await gmailService.users.drafts.create({
      userId: 'me',
      requestBody: {
        message: {
          raw: rawEmail
        }
      }
    });

    await logAction(
      'draft_email',
      'email_mcp',
      params.to,
      'n/a',
      'success',
      params
    );

    return {
      success: true,
      draftId: result.data.id,
      message: `Draft created successfully for ${params.to}`
    };
  } catch (error) {
    await logAction(
      'draft_email',
      'email_mcp',
      params.to,
      'n/a',
      `error: ${error.message}`,
      params
    );

    throw new Error(`Failed to create draft: ${error.message}`);
  }
}

async function searchEmails(params) {
  try {
    const maxResults = params.maxResults || 10;

    const result = await gmailService.users.messages.list({
      userId: 'me',
      q: params.query,
      maxResults: maxResults
    });

    const messages = result.data.messages || [];

    // Get details for each message
    const emailDetails = [];
    for (const message of messages) {
      try {
        const msgResult = await gmailService.users.messages.get({
          userId: 'me',
          id: message.id
        });

        const headers = {};
        if (msgResult.data.payload && msgResult.data.payload.headers) {
          for (const header of msgResult.data.payload.headers) {
            headers[header.name.toLowerCase()] = header.value;
          }
        }

        emailDetails.push({
          id: message.id,
          snippet: msgResult.data.snippet,
          headers: headers
        });
      } catch (msgError) {
        console.error(`Error getting message details: ${msgError.message}`);
        continue;
      }
    }

    await logAction(
      'search_emails',
      'email_mcp',
      params.query,
      'n/a',
      'success',
      params
    );

    return {
      success: true,
      count: emailDetails.length,
      results: emailDetails
    };
  } catch (error) {
    await logAction(
      'search_emails',
      'email_mcp',
      params.query,
      'n/a',
      `error: ${error.message}`,
      params
    );

    throw new Error(`Failed to search emails: ${error.message}`);
  }
}

// MCP Registration
async function registerInConfig() {
  try {
    const configPath = path.join(__dirname, '..', '..', 'claude_mcp_config.json');

    let config = {};
    try {
      const configContent = await fs.readFile(configPath, 'utf8');
      config = JSON.parse(configContent);
    } catch (readError) {
      // Config doesn't exist, create new one
      config = { servers: [] };
    }

    // Check if this server is already registered
    const serverIndex = config.servers.findIndex(server => server.name === 'email_mcp');

    if (serverIndex === -1) {
      // Add this server to the config
      config.servers.push({
        name: 'email_mcp',
        command: 'node',
        args: ['./mcp_servers/email_mcp/index.js'],
        env: {
          'VAULT_PATH': VAULT_PATH
        }
      });

      // Write the updated config
      await fs.writeFile(configPath, JSON.stringify(config, null, 2));
      console.log('Email MCP server registered in claude_mcp_config.json');
    } else {
      console.log('Email MCP server already registered');
    }
  } catch (error) {
    console.error('Error registering in config:', error.message);
  }
}

// Main MCP Server
async function main() {
  try {
    await ensureDirectoryExists(path.join(__dirname, '..', '..'));
    await ensureDirectoryExists(APPROVED_DIR);
    await ensureDirectoryExists(LOGS_DIR);

    // Register this server in the config
    await registerInConfig();

    // Initialize Gmail service
    await initializeGmailService();

    // Simple stdin/stdout MCP protocol
    process.stdin.setEncoding('utf8');

    let buffer = '';
    process.stdin.on('data', async (chunk) => {
      buffer += chunk;

      // Process complete JSON objects
      while (buffer.includes('\n')) {
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.trim()) {
            try {
              const request = JSON.parse(line);

              if (request.method === 'tools') {
                // Return available tools
                process.stdout.write(JSON.stringify({
                  jsonrpc: '2.0',
                  id: request.id,
                  result: tools
                }) + '\n');
              } else if (request.method === 'call_tool') {
                // Handle tool call
                try {
                  const result = await handleCall(request.params.name, request.params.arguments);

                  process.stdout.write(JSON.stringify({
                    jsonrpc: '2.0',
                    id: request.id,
                    result: result
                  }) + '\n');
                } catch (error) {
                  process.stdout.write(JSON.stringify({
                    jsonrpc: '2.0',
                    id: request.id,
                    error: {
                      code: -32603,
                      message: error.message
                    }
                  }) + '\n');
                }
              }
            } catch (parseError) {
              console.error('Error parsing request:', parseError.message);
            }
          }
        }
      }
    });
  } catch (error) {
    console.error('Error starting MCP server:', error.message);
    process.exit(1);
  }
}

// Export for testing if needed
module.exports = {
  tools,
  handleCall,
  sendEmail,
  draftEmail,
  searchEmails
};

if (require.main === module) {
  main().catch(console.error);
}