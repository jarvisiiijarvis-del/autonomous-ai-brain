#!/usr/bin/env python3
"""
Context Engine - Builds rich context about what the user is working on
Provides relevant suggestions and information based on current activity
"""

import os
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

SHARED_MEMORY = Path.home() / ".claude-shared-memory"
CONTEXT_CACHE = SHARED_MEMORY / "context_cache.json"


def load_cache():
    try:
        with open(CONTEXT_CACHE) as f:
            return json.load(f)
    except:
        return {"current_focus": None, "recent_files": [], "recent_commands": [], "updated": None}


def save_cache(data):
    data["updated"] = datetime.now().isoformat()
    with open(CONTEXT_CACHE, 'w') as f:
        json.dump(data, f, indent=2)


def get_recent_git_activity():
    """Get recent git activity across projects"""
    projects = [
        Path.home() / "telegram-claude-bot",
        Path.home() / "claude-chat",
    ]

    activity = []
    for project in projects:
        if not (project / ".git").exists():
            continue
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-5", "--since=24 hours ago"],
                cwd=project,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout.strip():
                activity.append({
                    "project": project.name,
                    "commits": result.stdout.strip().split('\n')
                })

            # Get modified files
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout.strip():
                files = [line[3:] for line in result.stdout.strip().split('\n') if line]
                activity.append({
                    "project": project.name,
                    "modified_files": files[:10]
                })
        except:
            pass

    return activity


def get_running_processes():
    """Get relevant running processes"""
    relevant = []
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5
        )
        keywords = ["python", "node", "electron", "vite", "npm", "git"]
        for line in result.stdout.split('\n'):
            for keyword in keywords:
                if keyword in line.lower() and "grep" not in line:
                    parts = line.split()
                    if len(parts) > 10:
                        relevant.append({
                            "pid": parts[1],
                            "cmd": ' '.join(parts[10:])[:100]
                        })
                    break
    except:
        pass
    return relevant[:10]


def get_recent_memory():
    """Get recent items from shared memory"""
    context = {}

    # Recent history
    try:
        with open(SHARED_MEMORY / "history.json") as f:
            history = json.load(f)
        recent = history.get("conversations", [])[-5:]
        context["recent_conversations"] = [c.get("summary", "")[:100] for c in recent]
    except:
        pass

    # Pending tasks
    try:
        with open(SHARED_MEMORY / "tasks.json") as f:
            tasks = json.load(f)
        pending = [t for t in tasks.get("queue", []) if t.get("status") == "pending"]
        context["pending_tasks"] = [t.get("task", "")[:50] for t in pending[:5]]
    except:
        pass

    # Today's reminders
    try:
        with open(SHARED_MEMORY / "reminders.json") as f:
            reminders = json.load(f)
        today = datetime.now().strftime("%Y-%m-%d")
        todays = [r for r in reminders.get("reminders", []) if r.get("date") == today]
        context["todays_reminders"] = [r.get("text", "")[:50] for r in todays]
    except:
        pass

    return context


def get_time_context():
    """Get context based on time of day"""
    now = datetime.now()
    hour = now.hour
    day = now.strftime("%A")

    context = {
        "time": now.strftime("%H:%M"),
        "day": day,
        "suggestions": []
    }

    # Time-based suggestions
    if hour < 9:
        context["period"] = "early_morning"
        context["suggestions"].append("Good time for planning and reviewing priorities")
    elif hour < 12:
        context["period"] = "morning"
        context["suggestions"].append("Peak focus time - tackle complex tasks")
    elif hour < 14:
        context["period"] = "midday"
        context["suggestions"].append("Consider taking a break or doing lighter tasks")
    elif hour < 17:
        context["period"] = "afternoon"
        context["suggestions"].append("Good for meetings, reviews, and collaboration")
    elif hour < 20:
        context["period"] = "evening"
        context["suggestions"].append("Wind down - review day, plan tomorrow")
    else:
        context["period"] = "night"
        context["suggestions"].append("Consider rest - or do creative exploration")

    # Day-based suggestions
    if day == "Monday":
        context["suggestions"].append("Start of week - set weekly goals")
    elif day == "Friday":
        context["suggestions"].append("End of week - review progress, tie up loose ends")
    elif day in ["Saturday", "Sunday"]:
        context["suggestions"].append("Weekend - good for learning and side projects")

    return context


def build_full_context():
    """Build comprehensive context"""
    context = {
        "timestamp": datetime.now().isoformat(),
        "time_context": get_time_context(),
        "git_activity": get_recent_git_activity(),
        "running_processes": get_running_processes(),
        "memory": get_recent_memory(),
    }

    # Determine current focus
    focus_signals = []

    # Check git activity
    for activity in context["git_activity"]:
        if "modified_files" in activity:
            focus_signals.append(activity["project"])

    # Check running processes
    for proc in context["running_processes"]:
        if "claude-chat" in proc["cmd"]:
            focus_signals.append("claude-chat")
        elif "telegram" in proc["cmd"] or "bot.py" in proc["cmd"]:
            focus_signals.append("telegram-bot")

    # Determine primary focus
    if focus_signals:
        focus_counts = defaultdict(int)
        for f in focus_signals:
            focus_counts[f] += 1
        context["current_focus"] = max(focus_counts, key=focus_counts.get)
    else:
        context["current_focus"] = "general"

    return context


def get_relevant_suggestions(context=None):
    """Get suggestions relevant to current context"""
    if context is None:
        context = build_full_context()

    suggestions = []

    # Time-based
    suggestions.extend(context["time_context"]["suggestions"])

    # Task-based
    if context["memory"].get("pending_tasks"):
        suggestions.append(f"You have {len(context['memory']['pending_tasks'])} pending tasks")

    # Reminder-based
    if context["memory"].get("todays_reminders"):
        for reminder in context["memory"]["todays_reminders"]:
            suggestions.append(f"Reminder: {reminder}")

    # Focus-based
    if context["current_focus"] == "claude-chat":
        suggestions.append("Working on Claude Chat - voice features recently added")
    elif context["current_focus"] == "telegram-bot":
        suggestions.append("Working on Telegram bot - consider testing new commands")

    return suggestions


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: context_engine.py <command>")
        print("Commands:")
        print("  build      - Build full context")
        print("  focus      - Get current focus")
        print("  suggest    - Get relevant suggestions")
        print("  time       - Get time-based context")
        print("  summary    - Brief context summary")
        return

    cmd = sys.argv[1]

    if cmd == "build":
        context = build_full_context()
        print(json.dumps(context, indent=2))

    elif cmd == "focus":
        context = build_full_context()
        print(f"Current focus: {context['current_focus']}")

    elif cmd == "suggest":
        suggestions = get_relevant_suggestions()
        for s in suggestions:
            print(f"• {s}")

    elif cmd == "time":
        time_ctx = get_time_context()
        print(f"Time: {time_ctx['time']} ({time_ctx['period']})")
        print(f"Day: {time_ctx['day']}")
        for s in time_ctx['suggestions']:
            print(f"• {s}")

    elif cmd == "summary":
        context = build_full_context()
        print(f"Focus: {context['current_focus']}")
        print(f"Time: {context['time_context']['period']}")
        if context['memory'].get('pending_tasks'):
            print(f"Tasks: {len(context['memory']['pending_tasks'])} pending")
        if context['git_activity']:
            print(f"Git: Activity in {len(context['git_activity'])} projects")

    else:
        print("Unknown command")


if __name__ == "__main__":
    main()
