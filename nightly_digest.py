#!/usr/bin/env python3
"""
Nightly Digest - Aggregates all system intelligence and sends summary
Runs at end of day to provide reflection and planning for tomorrow
"""

import os
import json
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID"))
BRAIN_DIR = Path(__file__).parent
SHARED_MEMORY = Path.home() / ".claude-shared-memory"


def send_telegram(text):
    """Send message via Telegram"""
    if not TELEGRAM_TOKEN:
        print("Warning: No TELEGRAM_BOT_TOKEN set")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }).encode()

    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"Error sending message: {e}")
        return False


def run_script(script, *args):
    """Run a script and capture output"""
    try:
        cmd = ["python3", str(BRAIN_DIR / script)] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


def get_todays_activity():
    """Summarize today's activity from history"""
    today = datetime.now().strftime("%Y-%m-%d")
    activity = {"conversations": 0, "tags": [], "summaries": []}

    try:
        with open(SHARED_MEMORY / "history.json") as f:
            history = json.load(f)

        for conv in history.get("conversations", []):
            if conv.get("date") == today:
                activity["conversations"] += 1
                activity["tags"].extend(conv.get("tags", []))
                if conv.get("summary"):
                    activity["summaries"].append(conv["summary"][:100])
    except:
        pass

    return activity


def get_goals_progress():
    """Get goal progress from today"""
    try:
        with open(SHARED_MEMORY / "goals.json") as f:
            goals = json.load(f)

        active = [g for g in goals.get("goals", []) if g.get("status") == "active"]
        high_progress = [g for g in active if g.get("progress", 0) >= 50]

        return {
            "active": len(active),
            "high_progress": len(high_progress),
            "goals": [{"title": g["title"], "progress": g["progress"]} for g in active[:3]]
        }
    except:
        return {"active": 0, "high_progress": 0, "goals": []}


def get_metrics():
    """Get performance metrics"""
    try:
        with open(SHARED_MEMORY / "metrics.json") as f:
            metrics = json.load(f)

        today = datetime.now().strftime("%Y-%m-%d")
        today_stats = metrics.get("daily_stats", {}).get(today, {})

        return {
            "today_success": today_stats.get("success", 0),
            "today_failure": today_stats.get("failure", 0),
            "total_completed": metrics.get("tasks_completed", 0),
            "recent_errors": metrics.get("errors_encountered", [])[-3:]
        }
    except:
        return {"today_success": 0, "today_failure": 0, "total_completed": 0, "recent_errors": []}


def get_tomorrows_reminders():
    """Get reminders for tomorrow"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        with open(SHARED_MEMORY / "reminders.json") as f:
            reminders = json.load(f)

        return [r.get("text", "") for r in reminders.get("reminders", [])
                if r.get("date") == tomorrow]
    except:
        return []


def generate_digest():
    """Generate the nightly digest"""
    now = datetime.now()

    msg = []
    msg.append(f"🌙 *Nightly Digest*")
    msg.append(f"_{now.strftime('%A, %B %d, %Y')}_\n")

    # Today's Activity
    activity = get_todays_activity()
    msg.append("📊 *Today's Activity*")
    if activity["conversations"] > 0:
        msg.append(f"• {activity['conversations']} conversations")
        if activity["tags"]:
            unique_tags = list(set(activity["tags"]))[:5]
            msg.append(f"• Topics: {', '.join(unique_tags)}")
    else:
        msg.append("• No recorded activity")
    msg.append("")

    # Performance Metrics
    metrics = get_metrics()
    msg.append("⚡ *Performance*")
    total_today = metrics["today_success"] + metrics["today_failure"]
    if total_today > 0:
        rate = (metrics["today_success"] / total_today) * 100
        msg.append(f"• Success rate: {rate:.0f}%")
        msg.append(f"• Tasks: {metrics['today_success']} completed, {metrics['today_failure']} failed")
    else:
        msg.append("• No task metrics recorded")
    msg.append("")

    # Goals Progress
    goals = get_goals_progress()
    if goals["active"] > 0:
        msg.append("🎯 *Goals*")
        msg.append(f"• {goals['active']} active goals")
        for g in goals["goals"]:
            bar = "█" * (g["progress"] // 20) + "░" * (5 - g["progress"] // 20)
            msg.append(f"  [{bar}] {g['title'][:30]}")
        msg.append("")

    # System Health
    health = run_script("orchestrator.py", "health")
    if health and "Error" not in health:
        msg.append("🖥️ *System Health*")
        msg.append(health[:200])
        msg.append("")

    # Tomorrow's Reminders
    reminders = get_tomorrows_reminders()
    if reminders:
        msg.append("📌 *Tomorrow's Reminders*")
        for r in reminders[:3]:
            msg.append(f"• {r}")
        msg.append("")

    # Suggestions for Tomorrow
    suggestions = run_script("predictor.py", "suggest")
    if suggestions and "Error" not in suggestions:
        msg.append("💡 *Suggestions for Tomorrow*")
        for line in suggestions.split('\n')[:3]:
            if line.strip():
                msg.append(line)
        msg.append("")

    # Reflection
    msg.append("_Rest well and prepare for tomorrow!_ 😴")

    return "\n".join(msg)


def main():
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        # Preview mode - just print
        print(generate_digest())
    else:
        # Send mode
        digest = generate_digest()
        if send_telegram(digest):
            print(f"Nightly digest sent at {datetime.now()}")
        else:
            print("Failed to send digest")
            print(digest)


if __name__ == "__main__":
    main()
