#!/usr/bin/env python3
"""
Auto Learner - Analyzes recent activity and extracts insights
Runs periodically to build up knowledge in the Second Brain
"""

import os
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

SECOND_BRAIN_DIR = Path.home() / "second-brain-data"
SHARED_MEMORY_DIR = Path.home() / ".claude-shared-memory"
STATE_FILE = SHARED_MEMORY_DIR / "learner_state.json"

def load_state():
    """Load learner state"""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"last_run": None, "insights_count": 0}

def save_state(state):
    """Save learner state"""
    state["last_run"] = datetime.now().isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def get_recent_git_activity():
    """Get recent git commits from projects"""
    insights = []
    git_dirs = [
        Path.home() / "telegram-claude-bot",
        Path.home() / "claude-chat",
    ]

    for git_dir in git_dirs:
        if not (git_dir / ".git").exists():
            continue
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "--since=24 hours ago", "-10"],
                cwd=git_dir,
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                insights.append({
                    "type": "git_activity",
                    "project": git_dir.name,
                    "commits": result.stdout.strip().split('\n')
                })
        except:
            pass

    return insights

def get_recent_history():
    """Get recent conversation history"""
    try:
        history_file = SHARED_MEMORY_DIR / "history.json"
        with open(history_file, 'r') as f:
            data = json.load(f)

        # Get conversations from last 24 hours
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()[:10]
        recent = [c for c in data.get("conversations", [])
                  if c.get("date", "") >= cutoff]

        return recent
    except:
        return []

def get_completed_tasks():
    """Get recently completed tasks"""
    try:
        tasks_file = SHARED_MEMORY_DIR / "tasks.json"
        with open(tasks_file, 'r') as f:
            data = json.load(f)

        completed = data.get("completed", [])
        # Get tasks completed in last 24 hours
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        recent = [t for t in completed
                  if t.get("completedAt", "") >= cutoff]

        return recent
    except:
        return []

def extract_patterns(history, tasks):
    """Extract patterns and insights from activity"""
    insights = []

    # Count tags to find focus areas
    tag_counts = {}
    for conv in history:
        for tag in conv.get("tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    if tag_counts:
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        insights.append({
            "type": "focus_areas",
            "areas": [t[0] for t in top_tags]
        })

    # Count task completions
    if tasks:
        insights.append({
            "type": "productivity",
            "tasks_completed": len(tasks),
            "task_summaries": [t.get("task", "")[:50] for t in tasks[:5]]
        })

    return insights

def save_daily_summary(insights, git_activity):
    """Save a daily summary to Second Brain"""
    today = datetime.now().strftime("%Y-%m-%d")
    summary_dir = SECOND_BRAIN_DIR / "daily"
    summary_dir.mkdir(exist_ok=True)

    summary_file = summary_dir / f"{today}.md"

    # Build summary content
    lines = [f"# Daily Summary - {today}\n"]

    if git_activity:
        lines.append("## Code Activity\n")
        for activity in git_activity:
            lines.append(f"### {activity['project']}\n")
            for commit in activity['commits'][:5]:
                lines.append(f"- {commit}\n")
        lines.append("\n")

    for insight in insights:
        if insight["type"] == "focus_areas":
            lines.append("## Focus Areas\n")
            lines.append(f"Today's main topics: {', '.join(insight['areas'])}\n\n")

        elif insight["type"] == "productivity":
            lines.append("## Productivity\n")
            lines.append(f"Tasks completed: {insight['tasks_completed']}\n")
            if insight.get("task_summaries"):
                for summary in insight["task_summaries"]:
                    lines.append(f"- {summary}\n")
            lines.append("\n")

    # Only write if we have content
    if len(lines) > 1:
        with open(summary_file, 'w') as f:
            f.writelines(lines)
        return str(summary_file)

    return None

def main():
    state = load_state()

    # Get activity data
    git_activity = get_recent_git_activity()
    history = get_recent_history()
    tasks = get_completed_tasks()

    # Extract insights
    insights = extract_patterns(history, tasks)

    # Save daily summary
    summary_path = save_daily_summary(insights, git_activity)

    # Update state
    state["insights_count"] = state.get("insights_count", 0) + len(insights)
    save_state(state)

    if summary_path:
        print(f"Daily summary saved to: {summary_path}")
    else:
        print("No significant activity to summarize")

if __name__ == "__main__":
    main()
