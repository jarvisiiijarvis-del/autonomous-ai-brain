import os
import re
import json
import sqlite3
import subprocess
import urllib.request
import urllib.error
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import anthropic

# Get tokens from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# SECURITY: Only this user ID can control the bot
ALLOWED_USER_ID = YOUR_TELEGRAM_CHAT_ID

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "conversations.db")

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def is_authorized(user_id: int) -> bool:
    """Check if user is authorized"""
    return user_id == ALLOWED_USER_ID

# Intent patterns for natural language parsing
INTENT_PATTERNS = {
    'run_command': {
        'patterns': [
            r'^run\s+(.+)',
            r'^execute\s+(.+)',
            r'^exec\s+(.+)',
            r"^show\s+me\s+what'?s?\s+in\s+(\S+)\s+directory",
            r'^show\s+me\s+the\s+(\S+)\s+folder',
            r'^list\s+(?:the\s+)?(\S+)\s+(?:directory|folder)',
            r'^what\s+files\s+are\s+in\s+(\S+)',
        ],
        'keywords': ['run ', 'execute ', 'exec '],
    },
    'read_file': {
        'patterns': [
            r'^(?:show|display|read|cat|view)\s+(?:me\s+)?(?:the\s+)?(?:file\s+)?(.+\.(?:py|txt|json|yaml|yml|md|sh|conf|config|log|env|zshrc|bashrc|gitignore|toml|ini|xml|html|css|js|ts)\b)',
            r'^(?:show|display|read|cat|view)\s+(?:me\s+)?(?:the\s+)?(?:contents?\s+of\s+)?([~/][\w./-]+)',
            r"^what'?s?\s+in\s+([~/][\w./-]+)",
            r'^open\s+(?:the\s+)?(?:file\s+)?([~/][\w./-]+)',
        ],
        'keywords': [],
    },
    'moltbook_post': {
        'patterns': [
            r'^post\s+(?:to\s+)?moltbook\s+(?:about\s+)?(.+)',
            r'^share\s+(?:on|to)\s+moltbook\s*[:\-]?\s*(.+)',
            r'^moltbook\s+post\s*[:\-]?\s*(.+)',
            r'^publish\s+(?:to\s+)?moltbook\s+(.+)',
        ],
        'keywords': ['post to moltbook', 'share on moltbook', 'moltbook post', 'publish to moltbook'],
    },
    'system_status': {
        'patterns': [
            r'^(?:check\s+)?(?:the\s+)?(?:system\s+)?(?:disk\s+)?space',
            r'^(?:check\s+)?(?:the\s+)?disk\s+usage',
            r'^(?:how\'?s?\s+)?(?:the\s+)?system(?:\s+doing)?',
            r'^system\s+(?:status|health|info)',
            r'^(?:check\s+)?(?:system\s+)?health',
            r'^(?:what\'?s?\s+the\s+)?(?:system\s+)?(?:load|uptime)',
            r'^(?:check\s+)?memory\s+(?:usage)?',
            r'^(?:how\s+much\s+)?(?:ram|memory)\s+(?:is\s+)?(?:used|free|available)',
            r'^(?:check\s+)?cpu\s+(?:usage)?',
        ],
        'keywords': ['system status', 'system health', 'disk space', 'disk usage', 'check system', 'system info', 'memory usage', 'cpu usage'],
    },
    'search_memory': {
        'patterns': [
            r'^(?:what\s+do\s+you\s+)?remember\s+(?:about\s+)?(.+)',
            r'^search\s+(?:memory\s+)?(?:for\s+)?(.+)',
            r'^find\s+(?:in\s+)?memory\s+(.+)',
            r'^(?:do\s+you\s+)?recall\s+(.+)',
            r'^memory\s+search\s*[:\-]?\s*(.+)',
        ],
        'keywords': ['remember about', 'search memory', 'search for', 'find in memory', 'recall'],
    },
}

def parse_intent(message: str) -> dict:
    """
    Parse natural language message to detect user intent.

    Returns a dict with:
        - intent: The detected intent type or None
        - params: Extracted parameters for the intent
        - confidence: How confident we are (high/medium/low)
    """
    msg_lower = message.lower().strip()

    # Check each intent type
    for intent_type, config in INTENT_PATTERNS.items():
        # Check regex patterns first (more specific)
        for pattern in config['patterns']:
            match = re.search(pattern, msg_lower, re.IGNORECASE)
            if match:
                # Extract the captured group if any
                param = match.group(1) if match.groups() else None
                return {
                    'intent': intent_type,
                    'params': param,
                    'confidence': 'high',
                    'original': message
                }

        # Check keyword matches (less specific, medium confidence)
        for keyword in config.get('keywords', []):
            if keyword in msg_lower:
                # Try to extract what comes after the keyword
                idx = msg_lower.find(keyword)
                param = message[idx + len(keyword):].strip() if idx != -1 else None
                return {
                    'intent': intent_type,
                    'params': param,
                    'confidence': 'medium',
                    'original': message
                }

    # No intent detected
    return {
        'intent': None,
        'params': None,
        'confidence': None,
        'original': message
    }

async def execute_intent(intent_data: dict, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Execute an action based on detected intent.

    Returns True if intent was handled, False otherwise.
    """
    intent = intent_data['intent']
    params = intent_data['params']

    if intent == 'run_command':
        await execute_run_intent(params, update)
        return True

    elif intent == 'read_file':
        await execute_read_intent(params, update)
        return True

    elif intent == 'moltbook_post':
        await execute_moltbook_intent(params, update)
        return True

    elif intent == 'system_status':
        await execute_system_status_intent(update)
        return True

    elif intent == 'search_memory':
        await execute_memory_search_intent(params, update)
        return True

    return False

async def execute_run_intent(command: str, update: Update):
    """Execute a shell command from natural language"""
    if not command:
        await update.message.reply_text("I understood you want to run a command, but couldn't extract which one. Try: run <command>")
        return

    await update.message.chat.send_action("typing")

    # Handle directory listing phrases
    if command.lower() in ['downloads', 'desktop', 'documents']:
        command = f'ls -la ~/{command.capitalize()}'
    elif command.startswith('~') or command.startswith('/'):
        # If it looks like a path, do ls
        command = f'ls -la {command}'

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.path.expanduser("~")
        )

        output = result.stdout or result.stderr or "(no output)"

        if len(output) > 4000:
            output = output[:4000] + "\n... (truncated)"

        status = "OK" if result.returncode == 0 else f"Exit code: {result.returncode}"
        await update.message.reply_text(f"[{status}]\n```\n{output}\n```", parse_mode="Markdown")

    except subprocess.TimeoutExpired:
        await update.message.reply_text("Command timed out (60s limit)")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def execute_read_intent(filepath: str, update: Update):
    """Read a file from natural language request"""
    if not filepath:
        await update.message.reply_text("I understood you want to read a file, but couldn't extract the path. Try: show me ~/path/to/file")
        return

    # Clean up the filepath
    filepath = filepath.strip().rstrip('?').strip()
    filepath = os.path.expanduser(filepath)

    await update.message.chat.send_action("typing")

    try:
        with open(filepath, 'r') as f:
            content = f.read()

        if len(content) > 4000:
            content = content[:4000] + "\n... (truncated)"

        await update.message.reply_text(f"```\n{content}\n```", parse_mode="Markdown")

    except FileNotFoundError:
        await update.message.reply_text(f"File not found: {filepath}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def execute_moltbook_intent(content: str, update: Update):
    """Post to Moltbook from natural language"""
    if not content:
        await update.message.reply_text("I understood you want to post to Moltbook, but need content. Try: post to moltbook Title | Content")
        return

    await update.message.chat.send_action("typing")

    # Parse title and content
    if '|' in content:
        parts = content.split('|', 1)
        title = parts[0].strip()
        body = parts[1].strip()
    else:
        # Use first sentence or first 50 chars as title
        sentences = content.split('.')
        if len(sentences) > 1 and len(sentences[0]) < 100:
            title = sentences[0].strip()
            body = '.'.join(sentences[1:]).strip() or title
        else:
            title = content[:50].strip() + ('...' if len(content) > 50 else '')
            body = content

    try:
        api_key = load_moltbook_api_key()
        if not api_key:
            await update.message.reply_text("Error: Moltbook API key not found.")
            return

        url = "https://www.moltbook.com/api/v1/posts"
        data = json.dumps({
            "submolt": "general",
            "title": title,
            "content": body
        }).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            await update.message.reply_text(f"Posted to Moltbook!\n\nTitle: {title}")

    except FileNotFoundError:
        await update.message.reply_text(f"Error: Moltbook credentials not found at {MOLTBOOK_CREDENTIALS_PATH}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        await update.message.reply_text(f"Moltbook API error ({e.code}): {error_body[:500]}")
    except urllib.error.URLError as e:
        await update.message.reply_text(f"Network error: {str(e.reason)}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def execute_system_status_intent(update: Update):
    """Check system status from natural language"""
    await update.message.chat.send_action("typing")

    try:
        # Gather system info
        commands = {
            'Uptime': 'uptime',
            'Disk': 'df -h / | tail -1',
            'Memory': 'vm_stat | head -5',
            'Load': 'sysctl -n vm.loadavg',
        }

        output_lines = ["System Status:"]

        for label, cmd in commands.items():
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    output_lines.append(f"\n{label}:\n{result.stdout.strip()}")
            except Exception:
                pass

        output = '\n'.join(output_lines)
        await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Error checking system: {str(e)}")

async def execute_memory_search_intent(query: str, update: Update):
    """Search shared memory from natural language"""
    if not query:
        await update.message.reply_text("I understood you want to search memory, but need a query. Try: search memory for <topic>")
        return

    await update.message.chat.send_action("typing")

    memory_cli = os.path.expanduser("~/.claude-shared-memory/memory-cli.py")

    try:
        # Get all memory and search through it
        result = subprocess.run(
            ['python3', memory_cli, 'get'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            await update.message.reply_text("Couldn't access shared memory.")
            return

        memory_data = result.stdout
        query_lower = query.lower().strip()

        # Simple search through the memory output
        lines = memory_data.split('\n')
        matches = []
        for i, line in enumerate(lines):
            if query_lower in line.lower():
                # Include some context
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                context_lines = lines[start:end]
                matches.append('\n'.join(context_lines))

        if matches:
            output = f"Found {len(matches)} match(es) for '{query}':\n\n"
            output += '\n---\n'.join(matches[:5])  # Limit to 5 matches
            if len(matches) > 5:
                output += f"\n\n... and {len(matches) - 5} more matches"
        else:
            output = f"No matches found for '{query}' in memory."

        if len(output) > 4000:
            output = output[:4000] + "\n... (truncated)"

        await update.message.reply_text(output)

    except FileNotFoundError:
        await update.message.reply_text("Shared memory system not found.")
    except Exception as e:
        await update.message.reply_text(f"Error searching memory: {str(e)}")

def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            user_id INTEGER PRIMARY KEY,
            messages TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_conversation(user_id: int) -> list:
    """Get conversation history from database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT messages FROM conversations WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return []

def save_conversation(user_id: int, messages: list):
    """Save conversation history to database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO conversations (user_id, messages) VALUES (?, ?)",
        (user_id, json.dumps(messages))
    )
    conn.commit()
    conn.close()

def clear_conversation(user_id: int):
    """Clear conversation history from database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# Moltbook credentials path
MOLTBOOK_CREDENTIALS_PATH = os.path.expanduser("~/.config/moltbook/credentials.json")

def load_moltbook_api_key() -> str:
    """Load Moltbook API key from credentials file"""
    with open(MOLTBOOK_CREDENTIALS_PATH, 'r') as f:
        creds = json.load(f)
    return creds.get("api_key")

async def moltbook_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Post to Moltbook social network"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /moltbook <title> | <content>")
        return

    # Join args and split on |
    full_text = ' '.join(context.args)
    if '|' not in full_text:
        await update.message.reply_text("Usage: /moltbook <title> | <content>\n\nSeparate title and content with |")
        return

    parts = full_text.split('|', 1)
    title = parts[0].strip()
    content = parts[1].strip()

    if not title or not content:
        await update.message.reply_text("Both title and content are required.")
        return

    await update.message.chat.send_action("typing")

    try:
        # Load API key
        api_key = load_moltbook_api_key()
        if not api_key:
            await update.message.reply_text("Error: Moltbook API key not found in credentials.")
            return

        # Prepare request
        url = "https://www.moltbook.com/api/v1/posts"
        data = json.dumps({
            "submolt": "general",
            "title": title,
            "content": content
        }).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        # Make request
        with urllib.request.urlopen(req, timeout=30) as response:
            response_data = response.read().decode('utf-8')
            await update.message.reply_text(f"Posted to Moltbook!\n\nTitle: {title}")

    except FileNotFoundError:
        await update.message.reply_text(f"Error: Moltbook credentials not found at {MOLTBOOK_CREDENTIALS_PATH}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        await update.message.reply_text(f"Moltbook API error ({e.code}): {error_body[:500]}")
    except urllib.error.URLError as e:
        await update.message.reply_text(f"Network error: {str(e.reason)}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message on /start"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized.")
        return

    clear_conversation(user_id)
    await update.message.reply_text(
        "Hi! I'm connected to Claude with computer control.\n\n"
        "Commands:\n"
        "/run <command> - Execute shell command\n"
        "/read <path> - Read a file\n"
        "/write <path> - Write to file (send content in next message)\n"
        "/ls [path] - List directory\n"
        "/moltbook <title> | <content> - Post to Moltbook\n"
        "/clear - Reset conversation\n\n"
        "Natural language also works:\n"
        "- \"run ls -la\" or \"show me what's in downloads\"\n"
        "- \"show me ~/.zshrc\" or \"what's in ~/config.json\"\n"
        "- \"post to moltbook about my project\"\n"
        "- \"how's the system\" or \"check disk space\"\n"
        "- \"what do you remember about telegram\"\n\n"
        "Or just chat with me normally!"
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized.")
        return

    clear_conversation(user_id)
    await update.message.reply_text("Conversation cleared!")

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute a shell command"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /run <command>")
        return

    command = ' '.join(context.args)
    await update.message.chat.send_action("typing")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.path.expanduser("~")
        )

        output = result.stdout or result.stderr or "(no output)"

        # Truncate if too long
        if len(output) > 4000:
            output = output[:4000] + "\n... (truncated)"

        status = "OK" if result.returncode == 0 else f"Exit code: {result.returncode}"
        await update.message.reply_text(f"[{status}]\n```\n{output}\n```", parse_mode="Markdown")

    except subprocess.TimeoutExpired:
        await update.message.reply_text("Command timed out (60s limit)")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def read_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Read a file"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /read <filepath>")
        return

    filepath = os.path.expanduser(' '.join(context.args))

    try:
        with open(filepath, 'r') as f:
            content = f.read()

        if len(content) > 4000:
            content = content[:4000] + "\n... (truncated)"

        await update.message.reply_text(f"```\n{content}\n```", parse_mode="Markdown")

    except FileNotFoundError:
        await update.message.reply_text(f"File not found: {filepath}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def write_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prepare to write a file - next message will be the content"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /write <filepath>")
        return

    filepath = os.path.expanduser(' '.join(context.args))
    context.user_data['write_path'] = filepath
    await update.message.reply_text(f"Send the content to write to:\n{filepath}")

async def list_dir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List directory contents"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized.")
        return

    path = os.path.expanduser(' '.join(context.args)) if context.args else os.path.expanduser("~")

    try:
        entries = os.listdir(path)
        entries.sort()

        output = []
        for entry in entries[:50]:  # Limit to 50 entries
            full_path = os.path.join(path, entry)
            if os.path.isdir(full_path):
                output.append(f"[DIR] {entry}/")
            else:
                output.append(f"      {entry}")

        if len(entries) > 50:
            output.append(f"... and {len(entries) - 50} more")

        await update.message.reply_text(f"```\n{chr(10).join(output)}\n```", parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages and get Claude response"""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Unauthorized.")
        return

    user_message = update.message.text

    # Check if we're waiting for file content
    if 'write_path' in context.user_data:
        filepath = context.user_data.pop('write_path')
        try:
            with open(filepath, 'w') as f:
                f.write(user_message)
            await update.message.reply_text(f"Written to: {filepath}")
        except Exception as e:
            await update.message.reply_text(f"Error writing file: {str(e)}")
        return

    # Check for natural language intents before sending to Claude
    intent_data = parse_intent(user_message)
    if intent_data['intent']:
        handled = await execute_intent(intent_data, update, context)
        if handled:
            return

    # Get conversation history from database
    messages = get_conversation(user_id)

    # Add user message to history
    messages.append({"role": "user", "content": user_message})

    # Keep only last 20 messages to avoid token limits
    if len(messages) > 20:
        messages = messages[-20:]

    try:
        # Send typing indicator
        await update.message.chat.send_action("typing")

        # Call Claude API
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=messages
        )

        # Extract response text
        assistant_message = response.content[0].text

        # Add assistant response to history
        messages.append({"role": "assistant", "content": assistant_message})

        # Save to database
        save_conversation(user_id, messages)

        # Send response (split if too long for Telegram)
        if len(assistant_message) > 4096:
            for i in range(0, len(assistant_message), 4096):
                await update.message.reply_text(assistant_message[i:i+4096])
        else:
            await update.message.reply_text(assistant_message)

    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

def main():
    """Start the bot"""
    if not TELEGRAM_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set")
        return
    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY not set")
        return

    # Initialize database
    init_db()

    # Create application
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(CommandHandler("read", read_file))
    app.add_handler(CommandHandler("write", write_file))
    app.add_handler(CommandHandler("ls", list_dir))
    app.add_handler(CommandHandler("moltbook", moltbook_post))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print(f"Bot running. Authorized user: {ALLOWED_USER_ID}")
    app.run_polling()

if __name__ == "__main__":
    main()
