#!/usr/bin/env python3
"""
Proactive Communications - Autonomously sends important notifications
Monitors for events and alerts user via Telegram when action is needed
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
SHARED_MEMORY = Path.home() / ".claude-shared-memory"
COMMS_LOG = SHARED_MEMORY / "comms_log.json"

# Cooldown between similar messages (hours)
MESSAGE_COOLDOWNS = {
    "goal_reminder": 24,
    "disk_warning": 6,
    "error_alert": 2,
    "suggestion": 12,
    "deadline": 4,
}


def load_log():
    try:
        with open(COMMS_LOG) as f:
            return json.load(f)
    except:
        return {"messages": [], "last_sent": {}}


def save_log(data):
    with open(COMMS_LOG, 'w') as f:
        json.dump(data, f, indent=2)


def can_send(message_type):
    """Check if we can send this type of message (cooldown)"""
    log = load_log()
    last = log.get("last_sent", {}).get(message_type)

    if not last:
        return True

    cooldown = MESSAGE_COOLDOWNS.get(message_type, 6)
    last_time = datetime.fromisoformat(last)
    return datetime.now() - last_time > timedelta(hours=cooldown)


def record_sent(message_type, message):
    """Record that a message was sent"""
    log = load_log()
    log["last_sent"][message_type] = datetime.now().isoformat()
    log["messages"].append({
        "type": message_type,
        "message": message[:200],
        "timestamp": datetime.now().isoformat()
    })
    log["messages"] = log["messages"][-100:]  # Keep last 100
    save_log(log)


def send_telegram(text, silent=False):
    """Send message via Telegram"""
    if not TELEGRAM_TOKEN:
        print("No TELEGRAM_BOT_TOKEN set")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_notification": str(silent).lower()
    }).encode()

    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def check_goals():
    """Check for goal deadlines approaching"""
    messages = []

    try:
        with open(SHARED_MEMORY / "goals.json") as f:
            goals = json.load(f)

        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        week = today + timedelta(days=7)

        for goal in goals.get("goals", []):
            if goal.get("status") != "active":
                continue

            target = goal.get("target_date")
            if not target:
                continue

            target_date = datetime.strptime(target, "%Y-%m-%d").date()

            if target_date == today:
                messages.append(
                    f"🎯 *Goal due TODAY*: {goal['title']}\n"
                    f"Progress: {goal.get('progress', 0)}%"
                )
            elif target_date == tomorrow:
                messages.append(
                    f"⏰ *Goal due tomorrow*: {goal['title']}\n"
                    f"Progress: {goal.get('progress', 0)}%"
                )
            elif today < target_date <= week and goal.get("progress", 0) < 50:
                messages.append(
                    f"📊 *Goal needs attention*: {goal['title']}\n"
                    f"Due: {target}, Progress: {goal.get('progress', 0)}%"
                )

    except:
        pass

    return messages


def check_disk_space():
    """Check for low disk space"""
    messages = []

    try:
        result = subprocess.run(
            ["df", "-h", "/"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 5:
                    used_pct = int(parts[4].rstrip('%'))
                    if used_pct >= 90:
                        messages.append(
                            f"🔴 *CRITICAL: Disk {used_pct}% full*\n"
                            f"Available: {parts[3]}"
                        )
                    elif used_pct >= 80:
                        messages.append(
                            f"🟡 *Warning: Disk {used_pct}% full*\n"
                            f"Available: {parts[3]}"
                        )
    except:
        pass

    return messages


def check_errors():
    """Check for recent errors that need attention"""
    messages = []

    try:
        with open(SHARED_MEMORY / "metrics.json") as f:
            metrics = json.load(f)

        errors = metrics.get("errors_encountered", [])
        recent = [e for e in errors
                  if datetime.fromisoformat(e.get("timestamp", "2000-01-01"))
                  > datetime.now() - timedelta(hours=2)]

        if len(recent) >= 3:
            error_types = set(e.get("type", "unknown") for e in recent)
            messages.append(
                f"⚠️ *{len(recent)} errors in last 2 hours*\n"
                f"Types: {', '.join(error_types)}"
            )

    except:
        pass

    return messages


def check_reminders():
    """Check for reminders due soon"""
    messages = []

    try:
        with open(SHARED_MEMORY / "reminders.json") as f:
            reminders = json.load(f)

        today = datetime.now().strftime("%Y-%m-%d")

        for reminder in reminders.get("reminders", []):
            if reminder.get("date") == today:
                messages.append(
                    f"🔔 *Reminder for today*:\n{reminder.get('text', '')}"
                )

    except:
        pass

    return messages


def check_stale_projects():
    """Check for projects with no recent activity"""
    messages = []

    projects = [
        Path.home() / "telegram-claude-bot",
        Path.home() / "claude-chat",
    ]

    for project in projects:
        if not (project / ".git").exists():
            continue

        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ai"],
                cwd=project, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                date_str = result.stdout.strip()[:10]
                last_commit = datetime.strptime(date_str, "%Y-%m-%d")

                if datetime.now() - last_commit > timedelta(days=14):
                    days = (datetime.now() - last_commit).days
                    messages.append(
                        f"💤 *{project.name}* hasn't been touched in {days} days"
                    )

        except:
            pass

    return messages


def run_all_checks():
    """Run all checks and send notifications"""
    all_messages = []

    # Goal checks
    if can_send("goal_reminder"):
        goal_msgs = check_goals()
        if goal_msgs:
            all_messages.extend(goal_msgs)
            record_sent("goal_reminder", goal_msgs[0])

    # Disk check
    if can_send("disk_warning"):
        disk_msgs = check_disk_space()
        if disk_msgs:
            all_messages.extend(disk_msgs)
            record_sent("disk_warning", disk_msgs[0])

    # Error check
    if can_send("error_alert"):
        error_msgs = check_errors()
        if error_msgs:
            all_messages.extend(error_msgs)
            record_sent("error_alert", error_msgs[0])

    # Reminder check (always check)
    reminder_msgs = check_reminders()
    all_messages.extend(reminder_msgs)

    # Stale project check (weekly)
    if datetime.now().weekday() == 0 and can_send("suggestion"):  # Monday
        stale_msgs = check_stale_projects()
        if stale_msgs:
            all_messages.extend(stale_msgs)
            record_sent("suggestion", stale_msgs[0])

    return all_messages


def notify():
    """Run checks and send notifications"""
    messages = run_all_checks()

    if not messages:
        return 0

    # Combine into single message
    combined = "🤖 *Proactive Update*\n\n" + "\n\n".join(messages)

    if send_telegram(combined):
        print(f"Sent {len(messages)} notifications")
        return len(messages)
    else:
        print("Failed to send notifications")
        return 0


def main():
    import sys

    if len(sys.argv) < 2:
        print("Proactive Communications - Autonomous notifications")
        print("")
        print("Usage:")
        print("  python3 proactive_comms.py check    - Run checks (dry run)")
        print("  python3 proactive_comms.py notify   - Run checks and send")
        print("  python3 proactive_comms.py log      - Show message log")
        print("  python3 proactive_comms.py test     - Send test message")
        return

    cmd = sys.argv[1]

    if cmd == "check":
        messages = run_all_checks()
        if messages:
            print(f"Would send {len(messages)} notifications:")
            for msg in messages:
                print(f"\n{msg}")
        else:
            print("No notifications needed")

    elif cmd == "notify":
        count = notify()
        print(f"Sent {count} notifications")

    elif cmd == "log":
        log = load_log()
        print("Recent messages:")
        for msg in log.get("messages", [])[-10:]:
            print(f"  [{msg['type']}] {msg['timestamp'][:16]}")
            print(f"    {msg['message'][:60]}...")

    elif cmd == "test":
        if send_telegram("🤖 *Test*: Proactive communications working!"):
            print("Test message sent")
        else:
            print("Failed to send test message")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
