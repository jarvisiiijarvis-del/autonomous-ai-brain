# Autonomous AI Brain

A self-monitoring, self-improving AI assistant system with 15 autonomous subsystems. Built to run continuously, learn from patterns, make decisions, and keep you productive.

## Features

- **15 Autonomous Subsystems** - Each handles a specific aspect of intelligence
- **Self-Monitoring** - Meta-cognition layer watches the brain itself
- **Pattern Learning** - Learns your habits and predicts your needs
- **Proactive Communication** - Sends alerts and reminders via Telegram
- **Knowledge Graph** - Connects concepts across all your data
- **Decision Engine** - Makes and executes maintenance decisions autonomously
- **Memory Management** - Automatically consolidates and archives old data

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        UNIFIED BRAIN                            │
│                   (Central Coordinator)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Orchestrator│  │   Monitor   │  │   Context   │             │
│  │  (health)   │  │ (resources) │  │  (activity) │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    Goals    │  │  Predictor  │  │  Knowledge  │             │
│  │  (tracking) │  │ (patterns)  │  │   Graph     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Self-Reflect│  │ Conversation│  │   Session   │             │
│  │ (learning)  │  │  Analyzer   │  │  Tracker    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    Auto     │  │    Meta     │  │   Project   │             │
│  │  Improver   │  │  Cognition  │  │   Scanner   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Proactive  │  │   Memory    │  │  Decision   │             │
│  │   Comms     │  │ Consolidator│  │   Engine    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SCHEDULED SERVICES                           │
│  • Morning Surprise (8am)    • System Monitor (5 min)          │
│  • Orchestrator (9am/3pm/9pm) • Nightly Digest (10pm)          │
│  • Proactive Comms (hourly)   • Decision Engine (2 hours)      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SHARED MEMORY                                │
│              ~/.claude-shared-memory/                           │
│  • context.json  • history.json  • goals.json  • graph.json   │
│  • metrics.json  • sessions.json • patterns.json • ...         │
└─────────────────────────────────────────────────────────────────┘
```

## Subsystems

| Subsystem | File | Purpose |
|-----------|------|---------|
| **orchestrator** | `orchestrator.py` | Central coordination and health checks |
| **monitor** | `monitor.py` | System resource monitoring with smart alerts |
| **context** | `context_engine.py` | Builds context from current activity |
| **goals** | `goal_tracker.py` | Long-term goal tracking with milestones |
| **predictor** | `predictor.py` | Pattern-based predictions and suggestions |
| **knowledge_graph** | `knowledge_graph.py` | Connects concepts across all data |
| **self_reflect** | `self_reflect.py` | Tracks performance and learns from it |
| **conversation_analyzer** | `conversation_analyzer.py` | Extracts insights from conversations |
| **session_tracker** | `session_tracker.py` | Analyzes Claude Code sessions |
| **auto_improver** | `auto_improver.py` | Generates improvement suggestions |
| **meta_cognition** | `meta_cognition.py` | Monitors the brain itself for anomalies |
| **project_scanner** | `project_scanner.py` | Analyzes codebases for health/tech debt |
| **proactive_comms** | `proactive_comms.py` | Sends autonomous notifications |
| **memory_consolidator** | `memory_consolidator.py` | Archives old data, keeps memory efficient |
| **decision_engine** | `decision_engine.py` | Makes autonomous maintenance decisions |

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/autonomous-brain.git
cd autonomous-brain
./install.sh
```

### 2. Configure

```bash
# Set your Telegram bot token and chat ID
export TELEGRAM_BOT_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"

# Add to ~/.zshrc or ~/.bashrc for persistence
```

### 3. Initialize

```bash
# Build the knowledge graph
python3 knowledge_graph.py build

# Check system status
python3 unified_brain.py status

# Get your first briefing
python3 unified_brain.py briefing
```

## Usage

### Unified Brain Commands

```bash
# System status
python3 unified_brain.py status

# Daily intelligence briefing
python3 unified_brain.py briefing

# Think about something (uses all context)
python3 unified_brain.py think "what should I focus on?"

# Execute actions
python3 unified_brain.py do <action> [args]
```

### Available Actions

| Action | Description |
|--------|-------------|
| `remind <text>` | Add a reminder |
| `goal <title>` | Add a goal |
| `search <query>` | Search memory |
| `health` | System health check |
| `graph` | Rebuild knowledge graph |
| `related <topic>` | Find related concepts |
| `context <topic>` | Get full context about topic |
| `improve` | Generate improvement suggestions |
| `meta` | Full meta-cognition report |
| `brain` | Quick brain status |
| `projects` | Scan all projects |
| `decide` | Run decision engine |
| `memory` | Memory usage stats |

### Goal Tracking

```bash
# Add a goal with milestones
python3 goal_tracker.py add "Launch my product" \
  --milestone "Build MVP" \
  --milestone "Get 10 beta users" \
  --milestone "Launch publicly"

# List goals
python3 goal_tracker.py list

# Complete a milestone
python3 goal_tracker.py complete <goal_id> <milestone_id>

# Progress report
python3 goal_tracker.py report
```

### Knowledge Graph

```bash
# Build/rebuild the graph
python3 knowledge_graph.py build

# Query related concepts
python3 knowledge_graph.py query security

# Get full context
python3 knowledge_graph.py context telegram

# Find suggested connections
python3 knowledge_graph.py suggest

# Statistics
python3 knowledge_graph.py stats
```

## Scheduled Services

The brain runs continuously via macOS launchd services:

| Service | Schedule | Purpose |
|---------|----------|---------|
| `com.User.morning-surprise` | 8am daily | Morning briefing with tips |
| `com.User.system-monitor` | Every 5 min | Resource monitoring |
| `com.User.orchestrator` | 9am, 3pm, 9pm | Coordination runs |
| `com.User.nightly-digest` | 10pm daily | End of day summary |
| `com.User.proactive-comms` | Every hour | Check for alerts to send |
| `com.User.decision-engine` | Every 2 hours | Autonomous decisions |

### Managing Services

```bash
# List running services
launchctl list | grep User

# Start a service
launchctl load ~/Library/LaunchAgents/com.User.<service>.plist

# Stop a service
launchctl unload ~/Library/LaunchAgents/com.User.<service>.plist

# Check logs
tail -f /tmp/User-*.log
```

## Shared Memory

All data is stored in `~/.claude-shared-memory/`:

| File | Purpose |
|------|---------|
| `context.json` | User preferences and facts |
| `history.json` | Conversation summaries |
| `goals.json` | Goals and milestones |
| `graph.json` | Knowledge graph |
| `metrics.json` | Performance metrics |
| `patterns.json` | Learned behavior patterns |
| `sessions.json` | Session tracking data |
| `reminders.json` | Upcoming reminders |

## Extending the Brain

### Adding a New Subsystem

1. Create your subsystem file (e.g., `my_system.py`)
2. Add CLI interface with standard commands
3. Register in `unified_brain.py`:

```python
# In get_status(), add to subsystems list:
("my_system", "my_system.py", ["status"]),

# In execute(), add action:
"myaction": ("my_system.py", ["run"]),
```

### Adding Decision Rules

Edit `decision_engine.py` and add to `RULES`:

```python
{
    "name": "my_rule",
    "description": "What this rule does",
    "condition": "my_condition",
    "action": ["my_script.py", "command"],
    "cooldown_hours": 24,
}
```

Then implement the condition in `evaluate_condition()`.

## Requirements

- Python 3.8+
- macOS (for launchd services) or Linux (use cron/systemd)
- Telegram Bot Token (optional, for notifications)

## License

MIT License - Use it, modify it, build on it.

## Author

Built with Claude Code as an experiment in autonomous AI systems.

---

*"The goal is not to build AI that thinks for you, but AI that thinks with you."*
