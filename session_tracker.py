#!/usr/bin/env python3
"""
Session Tracker - Tracks Claude Code sessions and extracts insights
Automatically saves learnings and patterns from each session
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from collections import Counter

SHARED_MEMORY = Path.home() / ".claude-shared-memory"
SESSIONS_FILE = SHARED_MEMORY / "sessions.json"
CLAUDE_DIR = Path.home() / ".claude"


def load_sessions():
    try:
        with open(SESSIONS_FILE) as f:
            return json.load(f)
    except:
        return {"sessions": [], "stats": {}, "updated": None}


def save_sessions(data):
    data["updated"] = datetime.now().isoformat()
    with open(SESSIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def find_recent_sessions(limit=5):
    """Find recent Claude Code session files"""
    sessions = []
    projects_dir = CLAUDE_DIR / "projects"

    if not projects_dir.exists():
        return sessions

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        for session_file in project_dir.glob("*.jsonl"):
            try:
                stat = session_file.stat()
                sessions.append({
                    "path": str(session_file),
                    "project": project_dir.name,
                    "modified": stat.st_mtime,
                    "size": stat.st_size
                })
            except:
                pass

    sessions.sort(key=lambda x: x["modified"], reverse=True)
    return sessions[:limit]


def analyze_session_file(filepath):
    """Analyze a single session JSONL file"""
    analysis = {
        "tools_used": Counter(),
        "files_touched": set(),
        "commands_run": [],
        "errors": [],
        "message_count": 0,
        "assistant_messages": 0,
        "topics": []
    }

    try:
        with open(filepath) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    analysis["message_count"] += 1

                    if entry.get("type") == "assistant":
                        analysis["assistant_messages"] += 1

                        # Extract tool usage
                        content = entry.get("message", {}).get("content", [])
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "tool_use":
                                    tool = item.get("name", "unknown")
                                    analysis["tools_used"][tool] += 1

                                    # Track file operations
                                    input_data = item.get("input", {})
                                    if "file_path" in input_data:
                                        analysis["files_touched"].add(input_data["file_path"])
                                    if "command" in input_data:
                                        analysis["commands_run"].append(input_data["command"][:100])

                    # Track errors
                    if entry.get("toolUseResult", "").startswith("Error"):
                        analysis["errors"].append(entry.get("toolUseResult", "")[:200])

                except json.JSONDecodeError:
                    continue

    except Exception as e:
        analysis["parse_error"] = str(e)

    # Convert sets to lists for JSON
    analysis["files_touched"] = list(analysis["files_touched"])
    analysis["tools_used"] = dict(analysis["tools_used"])

    return analysis


def extract_session_insights(analysis):
    """Extract actionable insights from session analysis"""
    insights = []

    # Tool usage patterns
    tools = analysis.get("tools_used", {})
    if tools:
        most_used = max(tools, key=tools.get)
        insights.append(f"Most used tool: {most_used} ({tools[most_used]} times)")

    # Error patterns
    errors = analysis.get("errors", [])
    if len(errors) > 3:
        insights.append(f"Session had {len(errors)} errors - review error handling")

    # File activity
    files = analysis.get("files_touched", [])
    if len(files) > 10:
        # Find common directories
        dirs = [Path(f).parent.name for f in files if f]
        common_dir = Counter(dirs).most_common(1)
        if common_dir:
            insights.append(f"Focused on: {common_dir[0][0]} ({common_dir[0][1]} files)")

    # Command patterns
    commands = analysis.get("commands_run", [])
    if commands:
        git_commands = sum(1 for c in commands if "git" in c)
        if git_commands > 0:
            insights.append(f"Git operations: {git_commands} commands")

    return insights


def track_current_session():
    """Track the current active session"""
    recent = find_recent_sessions(limit=1)
    if not recent:
        return {"error": "No recent sessions found"}

    current = recent[0]
    analysis = analyze_session_file(current["path"])
    insights = extract_session_insights(analysis)

    session_data = {
        "project": current["project"],
        "analyzed_at": datetime.now().isoformat(),
        "stats": {
            "messages": analysis["message_count"],
            "assistant_turns": analysis["assistant_messages"],
            "tools_used": len(analysis["tools_used"]),
            "files_touched": len(analysis["files_touched"]),
            "errors": len(analysis["errors"])
        },
        "top_tools": dict(Counter(analysis["tools_used"]).most_common(5)),
        "insights": insights
    }

    # Save to sessions history
    sessions = load_sessions()
    sessions["sessions"].append(session_data)
    sessions["sessions"] = sessions["sessions"][-50:]  # Keep last 50

    # Update aggregate stats
    if "aggregate" not in sessions:
        sessions["aggregate"] = {"total_sessions": 0, "tool_totals": {}}

    sessions["aggregate"]["total_sessions"] += 1
    for tool, count in analysis["tools_used"].items():
        sessions["aggregate"]["tool_totals"][tool] = \
            sessions["aggregate"]["tool_totals"].get(tool, 0) + count

    save_sessions(sessions)

    return session_data


def get_session_summary():
    """Get summary of all tracked sessions"""
    sessions = load_sessions()

    if not sessions.get("sessions"):
        return "No sessions tracked yet"

    recent = sessions["sessions"][-5:]
    aggregate = sessions.get("aggregate", {})

    summary = []
    summary.append(f"Total sessions tracked: {aggregate.get('total_sessions', 0)}")

    if aggregate.get("tool_totals"):
        top_tools = Counter(aggregate["tool_totals"]).most_common(5)
        summary.append("\nAll-time most used tools:")
        for tool, count in top_tools:
            summary.append(f"  {tool}: {count}")

    summary.append("\nRecent sessions:")
    for s in recent:
        summary.append(f"  • {s.get('project', 'unknown')}: "
                      f"{s['stats']['messages']} messages, "
                      f"{s['stats']['files_touched']} files")

    return "\n".join(summary)


def main():
    import sys

    if len(sys.argv) < 2:
        print("Session Tracker - Track and analyze Claude Code sessions")
        print("")
        print("Usage:")
        print("  python3 session_tracker.py track    - Track current session")
        print("  python3 session_tracker.py summary  - Get session summary")
        print("  python3 session_tracker.py recent   - Show recent sessions")
        return

    cmd = sys.argv[1]

    if cmd == "track":
        result = track_current_session()
        print(json.dumps(result, indent=2))

    elif cmd == "summary":
        print(get_session_summary())

    elif cmd == "recent":
        recent = find_recent_sessions()
        for s in recent:
            mod_time = datetime.fromtimestamp(s["modified"])
            print(f"• {s['project']}")
            print(f"  Modified: {mod_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"  Size: {s['size'] // 1024} KB")
            print()

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
