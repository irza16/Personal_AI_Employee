const fs = require('fs').promises;
const path = require('path');
const { spawn } = require('child_process');
require('dotenv').config();

// Configuration
const VAULT_PATH = process.env.VAULT_PATH || path.join(__dirname, '..', '..');
const ACCOUNTING_DIR = path.join(VAULT_PATH, 'Accounting');
const INVOICES_DIR = path.join(VAULT_PATH, 'Invoices');
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

// Read the current month's accounting file
async function readCurrentMonthAccounting() {
  const currentMonth = new Date().toISOString().slice(0, 7); // YYYY-MM
  const accountingFile = path.join(ACCOUNTING_DIR, `${currentMonth}_Current_Month.md`);

  try {
    const content = await fs.readFile(accountingFile, 'utf8');
    return { exists: true, content, filePath: accountingFile };
  } catch (error) {
    // File doesn't exist, return empty data
    return { exists: false, content: '', filePath: accountingFile };
  }
}

// Write to the current month's accounting file
async function writeCurrentMonthAccounting(content) {
  const currentMonth = new Date().toISOString().slice(0, 7); // YYYY-MM
  const accountingFile = path.join(ACCOUNTING_DIR, `${currentMonth}_Current_Month.md`);

  try {
    await fs.writeFile(accountingFile, content);
    return { success: true, filePath: accountingFile };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// MCP Tools
const tools = [
  {
    name: 'log_transaction',
    description: 'Log a financial transaction to the current month\'s accounting file.',
    inputSchema: {
      type: 'object',
      properties: {
        date: { type: 'string', description: 'Date of the transaction (YYYY-MM-DD)' },
        type: { type: 'string', description: 'Type of transaction (income, expense, payment, refund)' },
        category: { type: 'string', description: 'Category of the transaction (e.g., marketing, operations, travel)' },
        amount: { type: 'number', description: 'Amount of the transaction' },
        description: { type: 'string', description: 'Description of the transaction' },
        from: { type: 'string', description: 'Source of income or vendor for expense' },
        to: { type: 'string', description: 'Recipient of payment or source of income' }
      },
      required: ['date', 'type', 'amount', 'description']
    }
  },
  {
    name: 'get_balance',
    description: 'Get the current balance from the accounting records.',
    inputSchema: {
      type: 'object',
      properties: {
        month: { type: 'string', description: 'Month to get balance for (YYYY-MM format, defaults to current month)' }
      }
    }
  },
  {
    name: 'generate_invoice',
    description: 'Generate an invoice markdown file in the Invoices/ folder.',
    inputSchema: {
      type: 'object',
      properties: {
        client: { type: 'string', description: 'Client name' },
        invoice_number: { type: 'string', description: 'Invoice number' },
        date: { type: 'string', description: 'Invoice date (YYYY-MM-DD)' },
        due_date: { type: 'string', description: 'Due date for payment (YYYY-MM-DD)' },
        items: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              description: { type: 'string', description: 'Item description' },
              quantity: { type: 'number', description: 'Quantity' },
              unit_price: { type: 'number', description: 'Price per unit' }
            },
            required: ['description', 'quantity', 'unit_price']
          }
        },
        notes: { type: 'string', description: 'Additional notes for the invoice' }
      },
      required: ['client', 'invoice_number', 'date', 'items']
    }
  }
];

// MCP Handler
async function handleCall(toolName, parameters) {
  switch (toolName) {
    case 'log_transaction':
      return await logTransaction(parameters);
    case 'get_balance':
      return await getBalance(parameters);
    case 'generate_invoice':
      return await generateInvoice(parameters);
    default:
      throw new Error(`Unknown tool: ${toolName}`);
  }
}

async function logTransaction(params) {
  try {
    // Read current month's accounting file
    const accountingData = await readCurrentMonthAccounting();

    // Calculate new transaction
    const transaction = {
      date: params.date || new Date().toISOString().split('T')[0],
      type: params.type || 'expense',
      category: params.category || 'general',
      amount: params.amount,
      description: params.description,
      from: params.from || 'unknown',
      to: params.to || 'unknown',
      timestamp: new Date().toISOString()
    };

    // Prepare transaction entry
    const transactionEntry = `
## Transaction: ${transaction.description}
- **Date:** ${transaction.date}
- **Type:** ${transaction.type}
- **Category:** ${transaction.category}
- **Amount:** $${transaction.amount.toFixed(2)}
- **From:** ${transaction.from}
- **To:** ${transaction.to}
- **Timestamp:** ${transaction.timestamp}

`;

    // Append to existing content or create new content
    let newContent = accountingData.content;
    if (!accountingData.exists) {
      // Create new file with header
      newContent = `---
month: ${new Date().toISOString().slice(0, 7)}
generated: ${new Date().toISOString()}
---

# Accounting Record - ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long' })}
\n`;
    }

    newContent += transactionEntry;

    // Write back to file
    const writeResult = await writeCurrentMonthAccounting(newContent);

    if (writeResult.success) {
      await logAction(
        'log_transaction',
        'accounting_mcp',
        `${transaction.type}_${transaction.amount}`,
        'n/a',
        'success',
        params
      );

      return {
        success: true,
        message: `Transaction logged successfully`,
        transaction: transaction,
        filePath: writeResult.filePath
      };
    } else {
      await logAction(
        'log_transaction',
        'accounting_mcp',
        `${params.type}_${params.amount}`,
        'n/a',
        `error: ${writeResult.error}`,
        params
      );

      throw new Error(`Failed to write transaction: ${writeResult.error}`);
    }
  } catch (error) {
    await logAction(
      'log_transaction',
      'accounting_mcp',
      `${params.type}_${params.amount}`,
      'n/a',
      `error: ${error.message}`,
      params
    );

    throw new Error(`Failed to log transaction: ${error.message}`);
  }
}

async function getBalance(params) {
  try {
    const month = params.month || new Date().toISOString().slice(0, 7); // Use specified month or current month
    const accountingFile = path.join(ACCOUNTING_DIR, `${month}_Current_Month.md`);

    let content = '';
    try {
      content = await fs.readFile(accountingFile, 'utf8');
    } catch (error) {
      // File doesn't exist, return zero balance
      return {
        success: true,
        month: month,
        balance: 0,
        income: 0,
        expenses: 0,
        message: `No accounting records found for ${month}`
      };
    }

    // Parse transactions and calculate balance
    const lines = content.split('\n');
    let totalIncome = 0;
    let totalExpenses = 0;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.includes('**Type:**') && line.includes('income')) {
        // Find the amount in the next few lines
        for (let j = i; j < Math.min(i + 10, lines.length); j++) {
          const amountLine = lines[j];
          const amountMatch = amountLine.match(/\*\*Amount:\*\* \$(\d+\.?\d*)/);
          if (amountMatch) {
            totalIncome += parseFloat(amountMatch[1]);
            break;
          }
        }
      } else if (line.includes('**Type:**') && (line.includes('expense') || line.includes('payment'))) {
        // Find the amount in the next few lines
        for (let j = i; j < Math.min(i + 10, lines.length); j++) {
          const amountLine = lines[j];
          const amountMatch = amountLine.match(/\*\*Amount:\*\* \$(\d+\.?\d*)/);
          if (amountMatch) {
            totalExpenses += parseFloat(amountMatch[1]);
            break;
          }
        }
      }
    }

    const balance = totalIncome - totalExpenses;

    await logAction(
      'get_balance',
      'accounting_mcp',
      month,
      'n/a',
      'success',
      { month, balance, income: totalIncome, expenses: totalExpenses }
    );

    return {
      success: true,
      month: month,
      balance: balance,
      income: totalIncome,
      expenses: totalExpenses,
      message: `Balance calculated for ${month}`
    };
  } catch (error) {
    await logAction(
      'get_balance',
      'accounting_mcp',
      params.month || new Date().toISOString().slice(0, 7),
      'n/a',
      `error: ${error.message}`,
      params
    );

    throw new Error(`Failed to get balance: ${error.message}`);
  }
}

async function generateInvoice(params) {
  try {
    // Create invoices directory if it doesn't exist
    await ensureDirectoryExists(INVOICES_DIR);

    // Calculate totals
    let subtotal = 0;
    for (const item of params.items) {
      subtotal += item.quantity * item.unit_price;
    }
    const taxRate = 0.0; // Assuming no tax by default, could be configurable
    const tax = subtotal * taxRate;
    const total = subtotal + tax;

    // Create invoice content
    const invoiceContent = `---
invoice_number: ${params.invoice_number}
client: ${params.client}
date: ${params.date}
due_date: ${params.due_date}
status: issued
---

# Invoice #${params.invoice_number}

**Bill To:** ${params.client}

**Date:** ${params.date}
**Due Date:** ${params.due_date}

## Items

| Description | Quantity | Unit Price | Total |
|-------------|----------|------------|-------|
${params.items.map(item => `| ${item.description} | ${item.quantity} | $${item.unit_price.toFixed(2)} | $${(item.quantity * item.unit_price).toFixed(2)} |`).join('\n')}

## Totals

| Item | Amount |
|------|--------|
| Subtotal | $${subtotal.toFixed(2)} |
| Tax (${(taxRate * 100).toFixed(2)}%) | $${tax.toFixed(2)} |
| **Total** | **$${total.toFixed(2)}** |

## Notes
${params.notes || 'Thank you for your business!'}

---

Generated on ${new Date().toISOString()}
`;

    // Write invoice file
    const invoiceFilename = `INVOICE_${params.invoice_number}_${params.client.replace(/[^a-zA-Z0-9]/g, '_')}.md`;
    const invoicePath = path.join(INVOICES_DIR, invoiceFilename);

    await fs.writeFile(invoicePath, invoiceContent);

    await logAction(
      'generate_invoice',
      'accounting_mcp',
      params.invoice_number,
      'n/a',
      'success',
      params
    );

    return {
      success: true,
      message: 'Invoice generated successfully',
      invoice_number: params.invoice_number,
      client: params.client,
      total: total,
      invoice_path: invoicePath
    };
  } catch (error) {
    await logAction(
      'generate_invoice',
      'accounting_mcp',
      params.invoice_number,
      'n/a',
      `error: ${error.message}`,
      params
    );

    throw new Error(`Failed to generate invoice: ${error.message}`);
  }
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
    const serverIndex = config.servers.findIndex(server => server.name === 'accounting_mcp');

    if (serverIndex === -1) {
      // Add this server to the config
      config.servers.push({
        name: 'accounting_mcp',
        command: 'node',
        args: ['./mcp_servers/accounting_mcp/index.js'],
        env: {
          'VAULT_PATH': VAULT_PATH
        }
      });

      // Write the updated config
      await fs.writeFile(configPath, JSON.stringify(config, null, 2));
      console.log('Accounting MCP server registered in claude_mcp_config.json');
    } else {
      console.log('Accounting MCP server already registered');
    }
  } catch (error) {
    console.error('Error registering in config:', error.message);
  }
}

// Main MCP Server
async function main() {
  try {
    await ensureDirectoryExists(VAULT_PATH);
    await ensureDirectoryExists(ACCOUNTING_DIR);
    await ensureDirectoryExists(INVOICES_DIR);
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
  logTransaction,
  getBalance,
  generateInvoice
};

if (require.main === module) {
  main().catch(console.error);
}