const fs = require('fs').promises;
const path = require('path');
const { spawn } = require('child_process');
require('dotenv').config();

// Configuration
const VAULT_PATH = process.env.VAULT_PATH || path.join(__dirname, '..', '..');
const PENDING_APPROVAL_DIR = path.join(VAULT_PATH, 'Pending_Approval');
const APPROVED_DIR = path.join(VAULT_PATH, 'Approved');
const LOGS_DIR = path.join(VAULT_PATH, 'Logs');

// Ensure directories exist
async function ensureDirectoryExists(dirPath) {
  try {
    await fs.access(dirPath);
  } catch {
    await fs.mkdir(dirPath, { recursive: true });
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

// MCP Tools
const tools = [
  {
    name: 'post_to_facebook',
    description: 'Post content to Facebook. Requires approval file in Pending_Approval/ folder.',
    inputSchema: {
      type: 'object',
      properties: {
        content: { type: 'string', description: 'Content to post to Facebook' },
        image_path: { type: 'string', description: 'Path to image to upload (optional)' }
      },
      required: ['content']
    }
  },
  {
    name: 'post_to_instagram',
    description: 'Post content to Instagram. Requires approval file in Pending_Approval/ folder.',
    inputSchema: {
      type: 'object',
      properties: {
        content: { type: 'string', description: 'Content to post to Instagram' },
        image_path: { type: 'string', description: 'Path to image to upload (optional)' }
      },
      required: ['content']
    }
  },
  {
    name: 'post_to_twitter',
    description: 'Post content to Twitter/X. Requires approval file in Pending_Approval/ folder.',
    inputSchema: {
      type: 'object',
      properties: {
        content: { type: 'string', description: 'Content to post to Twitter/X' },
        image_path: { type: 'string', description: 'Path to image to upload (optional)' }
      },
      required: ['content']
    }
  }
];

// Check for approval file
async function checkApproval(requiredParams) {
  try {
    const files = await fs.readdir(PENDING_APPROVAL_DIR);

    for (const file of files) {
      if (file.endsWith('.md')) {
        const filePath = path.join(PENDING_APPROVAL_DIR, file);
        const content = await fs.readFile(filePath, 'utf8');

        // Check if this approval file matches the required parameters
        if (content.includes('action: facebook_post') && content.includes(requiredParams.content)) {
          return { approved: false, file: filePath, platform: 'facebook' };
        } else if (content.includes('action: instagram_post') && content.includes(requiredParams.content)) {
          return { approved: false, file: filePath, platform: 'instagram' };
        } else if (content.includes('action: twitter_post') && content.includes(requiredParams.content)) {
          return { approved: false, file: filePath, platform: 'twitter' };
        }
      }
    }

    return { approved: false, file: null, platform: null };
  } catch (error) {
    console.error('Error checking approval:', error.message);
    return { approved: false, file: null, platform: null };
  }
}

// MCP Handler
async function handleCall(toolName, parameters) {
  switch (toolName) {
    case 'post_to_facebook':
      return await postToFacebook(parameters);
    case 'post_to_instagram':
      return await postToInstagram(parameters);
    case 'post_to_twitter':
      return await postToTwitter(parameters);
    default:
      throw new Error(`Unknown tool: ${toolName}`);
  }
}

async function postToFacebook(params) {
  // Check for approval
  const approval = await checkApproval({ content: params.content });

  if (approval.platform === 'facebook' && !approval.approved) {
    // Create approval request file
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const approvalFile = path.join(PENDING_APPROVAL_DIR, `FACEBOOK_POST_APPROVAL_${timestamp}.md`);

    const approvalContent = `---
type: approval_request
action: facebook_post
created: ${new Date().toISOString()}
status: pending
---

## Facebook Post Content
${params.content}

## Action Required
Move this file to /Approved folder to post this content to Facebook.
`;

    try {
      await fs.writeFile(approvalFile, approvalContent);
      await logAction(
        'post_to_facebook',
        'social_mcp',
        'facebook',
        'pending',
        'approval_required',
        params
      );
      return {
        success: false,
        message: 'Approval required. Created approval request file.',
        approval_file: approvalFile
      };
    } catch (error) {
      await logAction(
        'post_to_facebook',
        'social_mcp',
        'facebook',
        'pending',
        `error: ${error.message}`,
        params
      );
      throw new Error(`Failed to create approval request: ${error.message}`);
    }
  }

  // If approved, we would normally post to Facebook
  // For now, we'll just simulate the posting
  await logAction(
    'post_to_facebook',
    'social_mcp',
    'facebook',
    'approved',
    'simulated_post',
    params
  );

  return {
    success: true,
    message: 'Facebook post approved and simulated (would post in production)',
    content: params.content
  };
}

async function postToInstagram(params) {
  // Check for approval
  const approval = await checkApproval({ content: params.content });

  if (approval.platform === 'instagram' && !approval.approved) {
    // Create approval request file
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const approvalFile = path.join(PENDING_APPROVAL_DIR, `INSTAGRAM_POST_APPROVAL_${timestamp}.md`);

    const approvalContent = `---
type: approval_request
action: instagram_post
created: ${new Date().toISOString()}
status: pending
---

## Instagram Post Content
${params.content}

## Action Required
Move this file to /Approved folder to post this content to Instagram.
`;

    try {
      await fs.writeFile(approvalFile, approvalContent);
      await logAction(
        'post_to_instagram',
        'social_mcp',
        'instagram',
        'pending',
        'approval_required',
        params
      );
      return {
        success: false,
        message: 'Approval required. Created approval request file.',
        approval_file: approvalFile
      };
    } catch (error) {
      await logAction(
        'post_to_instagram',
        'social_mcp',
        'instagram',
        'pending',
        `error: ${error.message}`,
        params
      );
      throw new Error(`Failed to create approval request: ${error.message}`);
    }
  }

  // If approved, we would normally post to Instagram
  // For now, we'll just simulate the posting
  await logAction(
    'post_to_instagram',
    'social_mcp',
    'instagram',
    'approved',
    'simulated_post',
    params
  );

  return {
    success: true,
    message: 'Instagram post approved and simulated (would post in production)',
    content: params.content
  };
}

async function postToTwitter(params) {
  // Check for approval
  const approval = await checkApproval({ content: params.content });

  if (approval.platform === 'twitter' && !approval.approved) {
    // Create approval request file
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const approvalFile = path.join(PENDING_APPROVAL_DIR, `TWITTER_POST_APPROVAL_${timestamp}.md`);

    const approvalContent = `---
type: approval_request
action: twitter_post
created: ${new Date().toISOString()}
status: pending
---

## Twitter/X Post Content
${params.content}

## Action Required
Move this file to /Approved folder to post this content to Twitter/X.
`;

    try {
      await fs.writeFile(approvalFile, approvalContent);
      await logAction(
        'post_to_twitter',
        'social_mcp',
        'twitter',
        'pending',
        'approval_required',
        params
      );
      return {
        success: false,
        message: 'Approval required. Created approval request file.',
        approval_file: approvalFile
      };
    } catch (error) {
      await logAction(
        'post_to_twitter',
        'social_mcp',
        'twitter',
        'pending',
        `error: ${error.message}`,
        params
      );
      throw new Error(`Failed to create approval request: ${error.message}`);
    }
  }

  // If approved, we would normally post to Twitter
  // For now, we'll just simulate the posting
  await logAction(
    'post_to_twitter',
    'social_mcp',
    'twitter',
    'approved',
    'simulated_post',
    params
  );

  return {
    success: true,
    message: 'Twitter post approved and simulated (would post in production)',
    content: params.content
  };
}

// Register this server in claude_mcp_config.json
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
    const serverIndex = config.servers.findIndex(server => server.name === 'social_mcp');

    if (serverIndex === -1) {
      // Add this server to the config
      config.servers.push({
        name: 'social_mcp',
        command: 'node',
        args: ['./mcp_servers/social_mcp/index.js'],
        env: {
          'VAULT_PATH': VAULT_PATH
        }
      });

      // Write the updated config
      await fs.writeFile(configPath, JSON.stringify(config, null, 2));
      console.log('Social MCP server registered in claude_mcp_config.json');
    } else {
      console.log('Social MCP server already registered');
    }
  } catch (error) {
    console.error('Error registering in config:', error.message);
  }
}

// Main MCP Server
async function main() {
  try {
    await ensureDirectoryExists(VAULT_PATH);
    await ensureDirectoryExists(PENDING_APPROVAL_DIR);
    await ensureDirectoryExists(APPROVED_DIR);
    await ensureDirectoryExists(LOGS_DIR);

    // Register this server in the config
    await registerInConfig();

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
  postToFacebook,
  postToInstagram,
  postToTwitter
};

if (require.main === module) {
  main().catch(console.error);
}