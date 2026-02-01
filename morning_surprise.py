#!/usr/bin/env python3
"""
Morning Surprise Script for User
Runs daily and sends via Telegram:
- Tech tip/fact
- System health report
- Task suggestion for the day
- Latest openclaw innovations
"""

import os
import json
import random
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime

# Import predictor for personalized suggestions
try:
    from predictor import get_morning_suggestions
    HAS_PREDICTOR = True
except ImportError:
    HAS_PREDICTOR = False

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID"))
OPENCLAW_CHANGELOG = os.path.expanduser("~/.npm-global/lib/node_modules/openclaw/CHANGELOG.md")
REMINDERS_FILE = os.path.expanduser("~/.claude-shared-memory/reminders.json")

TECH_TIPS = [
    "Use `cmd + shift + .` to show hidden files in Finder.",
    "Try `pbcopy` and `pbpaste` to copy/paste from terminal to clipboard.",
    "`caffeinate -d` keeps your Mac awake until you stop it.",
    "Use `mdfind` instead of `find` for faster Spotlight-powered searches.",
    "`open -a 'App Name'` launches apps from terminal.",
    "Press `ctrl + r` in terminal to search command history.",
    "`diskutil list` shows all connected drives and partitions.",
    "Use `say 'text'` to make your Mac speak.",
    "`networkQuality` tests your internet speed (macOS 12+).",
    "Hold Option while clicking WiFi icon for detailed network info.",
    "`defaults write com.apple.finder AppleShowAllFiles YES` shows hidden files permanently.",
    "Use `killall Dock` to restart Dock if it freezes.",
    "`top -o cpu` shows processes sorted by CPU usage.",
    "Triple-click to select entire paragraph in most apps.",
    "`python3 -m http.server 8000` starts a quick web server.",
    "Use `&&` to chain commands that only run if previous succeeds.",
    "`ctrl + a` goes to start of line, `ctrl + e` to end in terminal.",
    "Use `!!` to repeat the last command in bash/zsh.",
    "`sudo !!` runs the last command with sudo.",
    "Use `lsof -i :PORT` to see what's using a port.",
]

TASK_SUGGESTIONS = [
    "Review and clean up your Downloads folder",
    "Update your installed packages: `brew update && brew upgrade`",
    "Check for macOS updates in System Settings",
    "Back up important files to an external drive or cloud",
    "Review your running services: `launchctl list | grep User`",
    "Clean up Docker: `docker system prune -a`",
    "Check disk space: `df -h`",
    "Review your cron jobs and scheduled tasks",
    "Update your Second Brain with recent learnings",
    "Test your Telegram bot commands",
    "Review and rotate any API keys older than 90 days",
    "Check your git repos for uncommitted changes",
    "Clear browser cache and cookies",
    "Review your shell aliases - add new shortcuts",
    "Document a process you do frequently",
]

# Daily learning topics - rotate through these
LEARNING_TOPICS = [
    {"topic": "Systems Thinking", "prompt": "What system in your life could be optimized?", "resource": "Thinking in Systems by Donella Meadows"},
    {"topic": "First Principles", "prompt": "Break down a problem to its fundamental truths today.", "resource": "The First 20 Hours by Josh Kaufman"},
    {"topic": "Automation", "prompt": "What repetitive task can you automate this week?", "resource": "Automate the Boring Stuff with Python"},
    {"topic": "Business Models", "prompt": "How could you create value for 100 people?", "resource": "Business Model Generation by Osterwalder"},
    {"topic": "Mental Models", "prompt": "Apply inversion: What would guarantee failure?", "resource": "Poor Charlie's Almanack"},
    {"topic": "Deep Work", "prompt": "Block 2 hours today for focused, undistracted work.", "resource": "Deep Work by Cal Newport"},
    {"topic": "Financial Independence", "prompt": "What's one expense you could eliminate?", "resource": "The Simple Path to Wealth by JL Collins"},
    {"topic": "Product Thinking", "prompt": "What problem do 1000 people have that you could solve?", "resource": "The Mom Test by Rob Fitzpatrick"},
    {"topic": "Writing", "prompt": "Write 500 words about something you learned recently.", "resource": "On Writing Well by William Zinsser"},
    {"topic": "Networking", "prompt": "Reach out to one person who inspires you.", "resource": "Never Eat Alone by Keith Ferrazzi"},
    {"topic": "Innovation", "prompt": "Combine two unrelated ideas into something new.", "resource": "The Innovator's Dilemma by Clayton Christensen"},
    {"topic": "Habits", "prompt": "What small habit would compound into big results?", "resource": "Atomic Habits by James Clear"},
    {"topic": "Leadership", "prompt": "How can you help someone else succeed today?", "resource": "Leaders Eat Last by Simon Sinek"},
    {"topic": "Creativity", "prompt": "Take a 15-minute walk without your phone. Notice things.", "resource": "Steal Like an Artist by Austin Kleon"},
]

THINKING_PROMPTS = [
    "If you had unlimited resources, what would you build?",
    "What's the biggest bottleneck in your current projects?",
    "What would your 80-year-old self thank you for starting today?",
    "What are you avoiding that you know you should do?",
    "If you could only work 2 hours/day, what would you focus on?",
    "What's a belief you held strongly but have since changed?",
    "Who is doing what you want to do? What can you learn from them?",
    "What would you do if you knew you couldn't fail?",
    "What small experiment could you run this week?",
    "What's the ONE thing that would make everything else easier?",
]

def send_telegram(text):
    """Send message via Telegram"""
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
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

def get_system_health():
    """Get system health report"""
    report = []

    # Uptime
    try:
        uptime = subprocess.check_output(["uptime"], text=True).strip()
        report.append(f"*Uptime:* {uptime.split('up ')[1].split(',')[0] if 'up ' in uptime else uptime}")
    except:
        pass

    # Disk space
    try:
        df = subprocess.check_output(["df", "-h", "/"], text=True)
        lines = df.strip().split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            used_pct = parts[4] if len(parts) > 4 else "?"
            avail = parts[3] if len(parts) > 3 else "?"
            report.append(f"*Disk:* {used_pct} used, {avail} free")
    except:
        pass

    # Memory
    try:
        vm = subprocess.check_output(["vm_stat"], text=True)
        # Parse pages free
        for line in vm.split('\n'):
            if 'Pages free' in line:
                pages = int(line.split(':')[1].strip().rstrip('.'))
                free_gb = (pages * 4096) / (1024**3)
                report.append(f"*Free RAM:* {free_gb:.1f} GB")
                break
    except:
        pass

    # Bot status
    try:
        result = subprocess.run(["pgrep", "-f", "telegram-claude-bot/bot.py"], capture_output=True)
        bot_status = "running" if result.returncode == 0 else "stopped"
        report.append(f"*Telegram Bot:* {bot_status}")
    except:
        pass

    # Second Brain status
    try:
        result = subprocess.run(["pgrep", "-f", "Electron.*second-brain"], capture_output=True)
        sb_status = "running" if result.returncode == 0 else "stopped"
        report.append(f"*Second Brain:* {sb_status}")
    except:
        pass

    return '\n'.join(report) if report else "Could not get system info"

def get_openclaw_updates():
    """Get latest openclaw changelog entries"""
    try:
        with open(OPENCLAW_CHANGELOG, 'r') as f:
            content = f.read()

        # Get the latest version section
        sections = content.split('\n## ')
        if len(sections) > 1:
            latest = sections[1]
            version = latest.split('\n')[0].strip()

            # Get first few changes
            changes = []
            for line in latest.split('\n')[1:15]:
                line = line.strip()
                if line.startswith('- '):
                    # Clean up the line
                    change = line[2:].split('(#')[0].strip()
                    if len(change) > 80:
                        change = change[:77] + "..."
                    changes.append(f"• {change}")
                    if len(changes) >= 4:
                        break

            if changes:
                return f"*OpenClaw {version}*\n" + '\n'.join(changes)

        return "No recent updates found"
    except Exception as e:
        return f"Could not read changelog: {e}"

def get_greeting():
    """Get time-appropriate greeting"""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"

def get_daily_learning():
    """Get today's learning topic based on day of year"""
    day_of_year = datetime.now().timetuple().tm_yday
    topic_index = day_of_year % len(LEARNING_TOPICS)
    prompt_index = day_of_year % len(THINKING_PROMPTS)

    learning = LEARNING_TOPICS[topic_index]
    thinking = THINKING_PROMPTS[prompt_index]

    return {
        "topic": learning["topic"],
        "prompt": learning["prompt"],
        "resource": learning["resource"],
        "thinking": thinking
    }

def get_reminders():
    """Get reminders for today"""
    try:
        with open(REMINDERS_FILE, 'r') as f:
            data = json.load(f)

        today = datetime.now().strftime('%Y-%m-%d')
        today_reminders = []
        remaining = []

        for r in data.get('reminders', []):
            if r.get('date') == today:
                today_reminders.append(r.get('text', ''))
            elif r.get('date') > today:
                remaining.append(r)

        # Save back only future reminders
        if len(remaining) != len(data.get('reminders', [])):
            data['reminders'] = remaining
            with open(REMINDERS_FILE, 'w') as f:
                json.dump(data, f, indent=2)

        return today_reminders
    except:
        return []

def main():
    now = datetime.now()
    greeting = get_greeting()

    # Build the message
    msg = f"🌅 *{greeting}, User!*\n"
    msg += f"_{now.strftime('%A, %B %d, %Y')}_\n\n"

    # Tech tip
    msg += f"💡 *Tech Tip of the Day:*\n{random.choice(TECH_TIPS)}\n\n"

    # System health
    msg += f"🖥️ *System Health:*\n{get_system_health()}\n\n"

    # Daily Learning (for independence goal)
    learning = get_daily_learning()
    msg += f"📚 *Today's Learning: {learning['topic']}*\n"
    msg += f"_{learning['prompt']}_\n"
    msg += f"📖 Resource: {learning['resource']}\n\n"

    # Thinking prompt
    msg += f"🧠 *Think About:*\n_{learning['thinking']}_\n\n"

    # Task suggestion
    msg += f"✅ *Suggested Task:*\n{random.choice(TASK_SUGGESTIONS)}\n\n"

    # OpenClaw updates
    msg += f"🦞 *OpenClaw Latest:*\n{get_openclaw_updates()}\n\n"

    # Personalized suggestions from predictor
    if HAS_PREDICTOR:
        personalized = get_morning_suggestions()
        if personalized:
            msg += "🎯 *Based on Your Patterns:*\n"
            msg += personalized + "\n\n"

    # Reminders
    reminders = get_reminders()
    if reminders:
        msg += "🔔 *Reminders:*\n"
        for r in reminders:
            msg += f"• {r}\n"
        msg += "\n"

    msg += "_Have a productive day!_"

    send_telegram(msg)
    print(f"Morning surprise sent at {now}")

if __name__ == "__main__":
    main()
