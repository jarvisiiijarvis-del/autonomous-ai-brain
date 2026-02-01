# Autonomous AI Brain - Quick Start Guide

Get your AI assistant running in 10 minutes.

## Step 1: Prerequisites

```bash
# Check Python version (need 3.8+)
python3 --version

# Install required packages
pip3 install -r requirements.txt
```

## Step 2: Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit with your values
nano .env
```

Required values:
- `TELEGRAM_BOT_TOKEN` - Get from @BotFather on Telegram
- `TELEGRAM_CHAT_ID` - Get from @userinfobot on Telegram
- `ANTHROPIC_API_KEY` - Get from console.anthropic.com (optional)

## Step 3: Initialize Shared Memory

```bash
# Create memory directory
mkdir -p ~/.claude-shared-memory

# Initialize with your info
cat > ~/.claude-shared-memory/context.json << 'EOF'
{
  "user": {
    "name": "Your Name",
    "preferences": ["Your preferences here"],
    "timezone": "local"
  },
  "facts": [],
  "updated": ""
}
EOF

# Initialize history
echo '{"conversations": [], "updated": ""}' > ~/.claude-shared-memory/history.json

# Initialize goals
echo '{"goals": [], "completed": [], "updated": ""}' > ~/.claude-shared-memory/goals.json
```

## Step 4: Test Core Systems

```bash
# Check unified brain status
python3 unified_brain.py status

# Build knowledge graph
python3 knowledge_graph.py build

# Get your first briefing
python3 unified_brain.py briefing
```

## Step 5: Set Up Scheduled Jobs

### macOS (launchd)

```bash
# Run the installer
./install.sh
```

### Linux (cron)

```bash
# Edit crontab
crontab -e

# Add these lines:
0 8 * * * /usr/bin/python3 /path/to/morning_surprise.py
*/5 * * * * /usr/bin/python3 /path/to/monitor.py
0 9,15,21 * * * /usr/bin/python3 /path/to/orchestrator.py
0 22 * * * /usr/bin/python3 /path/to/nightly_digest.py
```

## Step 6: Verify Everything Works

```bash
# Check services are running (macOS)
launchctl list | grep autonomousbrain

# Manually trigger morning briefing
python3 morning_surprise.py
```

Check your Telegram - you should receive a message!

## Common Commands

```bash
# System status
python3 unified_brain.py status

# Daily briefing
python3 unified_brain.py briefing

# Add a goal
python3 goal_tracker.py add "My Goal" --milestone "Step 1" --milestone "Step 2"

# Search memory
python3 unified_brain.py do search "keyword"

# Rebuild knowledge graph
python3 knowledge_graph.py build
```

## Troubleshooting

**"TELEGRAM_BOT_TOKEN not set"**
→ Make sure you've created .env and sourced it: `source .env`

**"No module named X"**
→ Run: `pip3 install -r requirements.txt`

**Services not running**
→ Check logs: `tail -f /tmp/autonomousbrain-*.log`

## Next Steps

1. Customize `morning_surprise.py` with your own tips and prompts
2. Add goals using `goal_tracker.py`
3. Review `decision_engine.py` and add your own automation rules
4. Check the full README.md for advanced usage

## Need Help?

- GitHub Issues: [repo URL]
- Email: [your email]

---

*Built with Claude. MIT Licensed.*
