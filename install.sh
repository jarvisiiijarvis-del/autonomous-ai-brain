#!/bin/bash
#
# Autonomous Brain - Installation Script
# Sets up the brain, shared memory, and scheduled services
#

set -e

BRAIN_DIR="$(cd "$(dirname "$0")" && pwd)"
SHARED_MEMORY="$HOME/.claude-shared-memory"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

echo "╔═══════════════════════════════════════════╗"
echo "║     Autonomous Brain - Installation       ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# Create shared memory directory
echo "→ Creating shared memory directory..."
mkdir -p "$SHARED_MEMORY"
chmod 700 "$SHARED_MEMORY"

# Initialize empty JSON files if they don't exist
echo "→ Initializing memory files..."
for file in context.json history.json goals.json metrics.json patterns.json reminders.json; do
    if [ ! -f "$SHARED_MEMORY/$file" ]; then
        echo "{}" > "$SHARED_MEMORY/$file"
        chmod 600 "$SHARED_MEMORY/$file"
    fi
done

# Check for Python
echo "→ Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not installed."
    exit 1
fi
python3 --version

# Build knowledge graph
echo "→ Building knowledge graph..."
python3 "$BRAIN_DIR/knowledge_graph.py" build || echo "  (will build once you have data)"

# Check brain status
echo "→ Checking brain status..."
python3 "$BRAIN_DIR/unified_brain.py" status

# Create LaunchAgents directory
mkdir -p "$LAUNCH_AGENTS"

# Function to create a launchd plist
create_plist() {
    local name=$1
    local script=$2
    local schedule_type=$3
    local schedule_value=$4

    local plist_path="$LAUNCH_AGENTS/com.User.$name.plist"

    cat > "$plist_path" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.User.$name</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>source ~/.zshrc 2>/dev/null || source ~/.bashrc 2>/dev/null; cd $BRAIN_DIR && /usr/bin/python3 $script</string>
    </array>
EOF

    if [ "$schedule_type" = "interval" ]; then
        cat >> "$plist_path" << EOF
    <key>StartInterval</key>
    <integer>$schedule_value</integer>
EOF
    elif [ "$schedule_type" = "calendar" ]; then
        cat >> "$plist_path" << EOF
    <key>StartCalendarInterval</key>
    $schedule_value
EOF
    fi

    cat >> "$plist_path" << EOF
    <key>StandardOutPath</key>
    <string>/tmp/User-$name.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/User-$name.err</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF
    echo "  Created: $plist_path"
}

echo ""
echo "→ Setting up scheduled services..."

# System Monitor - every 5 minutes
create_plist "system-monitor" "monitor.py" "interval" "300"

# Decision Engine - every 2 hours
create_plist "decision-engine" "decision_engine.py run" "interval" "7200"

# Proactive Comms - every hour
create_plist "proactive-comms" "proactive_comms.py notify" "interval" "3600"

# Morning Surprise - 8am daily
create_plist "morning-surprise" "morning_surprise.py" "calendar" "<dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>"

# Nightly Digest - 10pm daily
create_plist "nightly-digest" "nightly_digest.py" "calendar" "<dict><key>Hour</key><integer>22</integer><key>Minute</key><integer>0</integer></dict>"

# Orchestrator - 9am, 3pm, 9pm
cat > "$LAUNCH_AGENTS/com.User.orchestrator.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.User.orchestrator</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>source ~/.zshrc 2>/dev/null; cd $BRAIN_DIR && /usr/bin/python3 orchestrator.py run</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>15</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>21</integer><key>Minute</key><integer>0</integer></dict>
    </array>
    <key>StandardOutPath</key>
    <string>/tmp/User-orchestrator.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/User-orchestrator.err</string>
</dict>
</plist>
EOF
echo "  Created: $LAUNCH_AGENTS/com.User.orchestrator.plist"

# Ask about loading services
echo ""
read -p "→ Load scheduled services now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "→ Loading services..."
    for plist in "$LAUNCH_AGENTS"/com.User.*.plist; do
        launchctl load "$plist" 2>/dev/null || true
    done
    echo "  Services loaded!"
fi

# Environment variables reminder
echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║           Installation Complete!          ║"
echo "╚═══════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "1. Set your Telegram credentials (for notifications):"
echo "   export TELEGRAM_BOT_TOKEN='your-token'"
echo "   export TELEGRAM_CHAT_ID='your-chat-id'"
echo ""
echo "2. Add to ~/.zshrc or ~/.bashrc for persistence"
echo ""
echo "3. Test the brain:"
echo "   python3 $BRAIN_DIR/unified_brain.py status"
echo "   python3 $BRAIN_DIR/unified_brain.py briefing"
echo ""
echo "4. Add your first goal:"
echo "   python3 $BRAIN_DIR/goal_tracker.py add 'My Goal' --milestone 'Step 1'"
echo ""
echo "Logs are in /tmp/User-*.log"
echo ""
