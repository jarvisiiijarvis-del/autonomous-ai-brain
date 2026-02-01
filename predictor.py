#!/usr/bin/env python3
"""
Pattern-based Predictor for User
Tracks command/action patterns and makes contextual suggestions.

Features:
- Tracks what commands are run at what times
- Stores patterns in ~/.claude-shared-memory/patterns.json
- Suggests relevant actions based on time, day, and recent activity
- Integrates with morning_surprise.py
"""

import os
import json
from datetime import datetime
from collections import defaultdict

PATTERNS_FILE = os.path.expanduser("~/.claude-shared-memory/patterns.json")

# Default time-based suggestions
TIME_SUGGESTIONS = {
    # Morning (6-10 AM)
    "morning": [
        {"action": "Check git repos", "command": "git status", "reason": "Start the day by reviewing code changes"},
        {"action": "Review tasks", "command": "python3 ~/.claude-shared-memory/memory-cli.py tasks", "reason": "Check pending tasks from Claude Chat"},
        {"action": "Check system health", "command": "df -h && vm_stat", "reason": "Ensure system is running well"},
    ],
    # Midday (10 AM - 2 PM)
    "midday": [
        {"action": "Take a break", "command": None, "reason": "You've been working for a while"},
        {"action": "Review progress", "command": None, "reason": "Check what you've accomplished today"},
    ],
    # Afternoon (2-6 PM)
    "afternoon": [
        {"action": "Commit changes", "command": "git add . && git commit", "reason": "Save your afternoon work"},
        {"action": "Update documentation", "command": None, "reason": "Document while context is fresh"},
    ],
    # Evening (6-10 PM)
    "evening": [
        {"action": "Push changes", "command": "git push", "reason": "Sync your work before end of day"},
        {"action": "Plan tomorrow", "command": None, "reason": "Set priorities for the next day"},
        {"action": "Log learnings", "command": "python3 ~/.claude-shared-memory/memory-cli.py add-fact", "reason": "Capture what you learned today"},
    ],
    # Night (10 PM - 6 AM)
    "night": [
        {"action": "Consider rest", "command": None, "reason": "Late night coding can lead to bugs"},
    ],
}

# Day-of-week suggestions
DAY_SUGGESTIONS = {
    "Monday": [
        {"action": "Weekly planning", "command": None, "reason": "Set goals for the week"},
        {"action": "Check project status", "command": "git log --oneline -10", "reason": "Review where things stand"},
    ],
    "Friday": [
        {"action": "Weekly review", "command": None, "reason": "Reflect on what you accomplished this week"},
        {"action": "Backup important files", "command": None, "reason": "End of week backup is good practice"},
        {"action": "Clean up branches", "command": "git branch --merged", "reason": "Remove old merged branches"},
    ],
    "Sunday": [
        {"action": "Prepare for Monday", "command": None, "reason": "Review upcoming week's priorities"},
    ],
}


def load_patterns():
    """Load patterns from file"""
    if os.path.exists(PATTERNS_FILE):
        try:
            with open(PATTERNS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "commands": {},      # command -> {hour: count, day: count}
        "last_updated": None,
        "total_tracked": 0
    }


def save_patterns(patterns):
    """Save patterns to file"""
    patterns["last_updated"] = datetime.now().isoformat()
    os.makedirs(os.path.dirname(PATTERNS_FILE), exist_ok=True)
    with open(PATTERNS_FILE, 'w') as f:
        json.dump(patterns, f, indent=2)


def track_command(command: str):
    """Track a command execution with time context"""
    patterns = load_patterns()
    now = datetime.now()
    hour = now.hour
    day = now.strftime("%A")

    # Normalize command (take first word for common commands)
    cmd_key = command.split()[0] if command else "unknown"

    if cmd_key not in patterns["commands"]:
        patterns["commands"][cmd_key] = {
            "by_hour": {},
            "by_day": {},
            "total": 0,
            "last_used": None
        }

    cmd_data = patterns["commands"][cmd_key]

    # Track by hour
    hour_str = str(hour)
    cmd_data["by_hour"][hour_str] = cmd_data["by_hour"].get(hour_str, 0) + 1

    # Track by day
    cmd_data["by_day"][day] = cmd_data["by_day"].get(day, 0) + 1

    cmd_data["total"] += 1
    cmd_data["last_used"] = now.isoformat()
    patterns["total_tracked"] += 1

    save_patterns(patterns)


def get_time_period():
    """Get current time period"""
    hour = datetime.now().hour
    if 6 <= hour < 10:
        return "morning"
    elif 10 <= hour < 14:
        return "midday"
    elif 14 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 22:
        return "evening"
    else:
        return "night"


def get_pattern_based_suggestions():
    """Get suggestions based on learned patterns"""
    patterns = load_patterns()
    suggestions = []
    now = datetime.now()
    hour = now.hour
    day = now.strftime("%A")

    if not patterns["commands"]:
        return suggestions

    # Find commands frequently run at this hour
    hour_str = str(hour)
    for cmd, data in patterns["commands"].items():
        hour_count = data["by_hour"].get(hour_str, 0)
        if hour_count >= 3:  # Threshold for pattern
            suggestions.append({
                "action": f"Run {cmd}",
                "command": cmd,
                "reason": f"You often run this at {hour}:00 ({hour_count} times)",
                "confidence": min(hour_count / 10, 1.0),
                "source": "pattern"
            })

    # Find commands frequently run on this day
    for cmd, data in patterns["commands"].items():
        day_count = data["by_day"].get(day, 0)
        if day_count >= 3:  # Threshold for pattern
            # Avoid duplicates
            if not any(s.get("command") == cmd for s in suggestions):
                suggestions.append({
                    "action": f"Run {cmd}",
                    "command": cmd,
                    "reason": f"You often run this on {day}s ({day_count} times)",
                    "confidence": min(day_count / 10, 1.0),
                    "source": "pattern"
                })

    # Sort by confidence
    suggestions.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    return suggestions[:5]  # Return top 5


def get_time_based_suggestions():
    """Get suggestions based on time of day"""
    time_period = get_time_period()
    day = datetime.now().strftime("%A")

    suggestions = []

    # Add time-based suggestions
    for s in TIME_SUGGESTIONS.get(time_period, []):
        suggestions.append({
            **s,
            "source": "time",
            "confidence": 0.5
        })

    # Add day-based suggestions
    for s in DAY_SUGGESTIONS.get(day, []):
        suggestions.append({
            **s,
            "source": "day",
            "confidence": 0.7
        })

    return suggestions


def get_suggestions(include_patterns=True, include_time=True, max_results=5):
    """
    Get contextual suggestions based on patterns and time.

    Args:
        include_patterns: Include suggestions from learned patterns
        include_time: Include time/day based suggestions
        max_results: Maximum number of suggestions to return

    Returns:
        List of suggestion dictionaries with:
        - action: What to do
        - command: Optional command to run
        - reason: Why this is suggested
        - source: Where the suggestion came from (pattern/time/day)
        - confidence: How confident the suggestion is (0-1)
    """
    suggestions = []

    if include_patterns:
        suggestions.extend(get_pattern_based_suggestions())

    if include_time:
        suggestions.extend(get_time_based_suggestions())

    # Remove duplicates by action
    seen = set()
    unique = []
    for s in suggestions:
        if s["action"] not in seen:
            seen.add(s["action"])
            unique.append(s)

    # Sort by confidence
    unique.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    return unique[:max_results]


def format_suggestions_for_telegram(suggestions):
    """Format suggestions for Telegram message"""
    if not suggestions:
        return "No suggestions at this time."

    lines = []
    for i, s in enumerate(suggestions, 1):
        action = s["action"]
        reason = s.get("reason", "")
        cmd = s.get("command")

        line = f"{i}. *{action}*"
        if reason:
            line += f"\n   _{reason}_"
        if cmd:
            line += f"\n   `{cmd}`"
        lines.append(line)

    return "\n\n".join(lines)


def get_morning_suggestions():
    """
    Get personalized suggestions for morning_surprise.py integration.
    Returns a formatted string suitable for Telegram.
    """
    suggestions = get_suggestions(max_results=3)

    if not suggestions:
        return None

    # Filter to most relevant
    relevant = [s for s in suggestions if s.get("confidence", 0) >= 0.3]

    if not relevant:
        return None

    lines = []
    for s in relevant[:3]:
        action = s["action"]
        if s.get("command"):
            lines.append(f"- {action}: `{s['command']}`")
        else:
            lines.append(f"- {action}")

    return "\n".join(lines)


def get_pattern_stats():
    """Get statistics about tracked patterns"""
    patterns = load_patterns()

    stats = {
        "total_tracked": patterns.get("total_tracked", 0),
        "unique_commands": len(patterns.get("commands", {})),
        "last_updated": patterns.get("last_updated"),
        "top_commands": []
    }

    # Get top commands
    commands = patterns.get("commands", {})
    sorted_cmds = sorted(commands.items(), key=lambda x: x[1].get("total", 0), reverse=True)

    for cmd, data in sorted_cmds[:5]:
        stats["top_commands"].append({
            "command": cmd,
            "total": data.get("total", 0),
            "last_used": data.get("last_used")
        })

    return stats


def reset_patterns():
    """Reset all tracked patterns"""
    save_patterns({
        "commands": {},
        "last_updated": None,
        "total_tracked": 0
    })


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "track" and len(sys.argv) > 2:
            command = " ".join(sys.argv[2:])
            track_command(command)
            print(f"Tracked: {command}")

        elif cmd == "suggest":
            suggestions = get_suggestions()
            print("\nSuggestions for now:\n")
            print(format_suggestions_for_telegram(suggestions))

        elif cmd == "stats":
            stats = get_pattern_stats()
            print(f"\nPattern Statistics:")
            print(f"  Total commands tracked: {stats['total_tracked']}")
            print(f"  Unique commands: {stats['unique_commands']}")
            print(f"  Last updated: {stats['last_updated']}")
            if stats['top_commands']:
                print(f"\n  Top commands:")
                for c in stats['top_commands']:
                    print(f"    - {c['command']}: {c['total']} times")

        elif cmd == "reset":
            reset_patterns()
            print("Patterns reset.")

        elif cmd == "morning":
            suggestions = get_morning_suggestions()
            if suggestions:
                print("\nMorning suggestions:")
                print(suggestions)
            else:
                print("No personalized suggestions yet. Keep using commands to build patterns!")

        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python predictor.py [track <command>|suggest|stats|reset|morning]")

    else:
        # Default: show suggestions
        suggestions = get_suggestions()
        print("\nContextual Suggestions:\n")
        for s in suggestions:
            print(f"- {s['action']}")
            if s.get('reason'):
                print(f"  Reason: {s['reason']}")
            if s.get('command'):
                print(f"  Command: {s['command']}")
            print()
