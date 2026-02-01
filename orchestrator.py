#!/usr/bin/env python3
"""
Orchestrator - Central coordinator for autonomous Claude systems
Manages scheduled tasks, cross-system communication, and intelligent automation
"""

import os
import json
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

class Orchestrator:
    def __init__(self):
        self.home = Path.home()
        self.shared_memory = self.home / ".claude-shared-memory"
        self.config_dir = self.home / ".config" / "claude-orchestrator"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.config_dir / "state.json"

        # Telegram config
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID")

    def load_state(self):
        try:
            with open(self.state_file) as f:
                return json.load(f)
        except:
            return {
                "last_health_check": None,
                "last_learning_summary": None,
                "last_proactive_scan": None,
                "alerts_sent": [],
                "daily_stats": {}
            }

    def save_state(self, state):
        state["updated"] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def send_telegram(self, message):
        """Send a Telegram message"""
        if not self.telegram_token:
            print("No Telegram token configured")
            return False

        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }).encode()

        try:
            req = urllib.request.Request(url, data=data)
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception as e:
            print(f"Telegram error: {e}")
            return False

    def run_health_check(self):
        """Run system health check"""
        issues = []

        # Check disk space
        try:
            result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
            parts = result.stdout.strip().split('\n')[1].split()
            used_pct = int(parts[4].rstrip('%'))
            if used_pct > 85:
                issues.append(f"⚠️ Disk usage critical: {used_pct}%")
            elif used_pct > 75:
                issues.append(f"📀 Disk usage high: {used_pct}%")
        except:
            pass

        # Check memory
        try:
            result = subprocess.run(["vm_stat"], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'Pages free' in line:
                    pages = int(line.split(':')[1].strip().rstrip('.'))
                    free_gb = (pages * 4096) / (1024**3)
                    if free_gb < 0.5:
                        issues.append(f"⚠️ Low memory: {free_gb:.1f}GB free")
                    break
        except:
            pass

        # Check if key services are running
        services = {
            "telegram-claude-bot/bot.py": "Telegram Bot",
        }

        for proc_name, display_name in services.items():
            try:
                result = subprocess.run(
                    ["pgrep", "-f", proc_name],
                    capture_output=True
                )
                if result.returncode != 0:
                    issues.append(f"🔴 {display_name} not running")
            except:
                pass

        return issues

    def run_learning_cycle(self):
        """Run the auto-learning cycle"""
        try:
            learner_path = self.home / "telegram-claude-bot" / "auto_learner.py"
            if learner_path.exists():
                result = subprocess.run(
                    ["python3", str(learner_path)],
                    capture_output=True,
                    text=True
                )
                return result.stdout.strip()
        except Exception as e:
            return f"Learning error: {e}"
        return None

    def run_proactive_scan(self):
        """Run proactive improvement scan"""
        try:
            agent_path = self.home / "telegram-claude-bot" / "proactive_agent.py"
            if agent_path.exists():
                result = subprocess.run(
                    ["python3", str(agent_path)],
                    capture_output=True,
                    text=True
                )
                return result.stdout.strip()
        except Exception as e:
            return f"Scan error: {e}"
        return None

    def check_pending_tasks(self):
        """Check for pending tasks from Claude Chat"""
        try:
            tasks_file = self.shared_memory / "tasks.json"
            with open(tasks_file) as f:
                data = json.load(f)

            pending = [t for t in data.get('queue', []) if t.get('status') == 'pending']
            high_priority = [t for t in pending if t.get('priority') == 'high']

            return {
                "total": len(pending),
                "high_priority": len(high_priority),
                "tasks": pending[:3]  # Return top 3
            }
        except:
            return {"total": 0, "high_priority": 0, "tasks": []}

    def daily_report(self):
        """Generate a daily status report"""
        state = self.load_state()

        # Health check
        health_issues = self.run_health_check()

        # Task status
        task_info = self.check_pending_tasks()

        # Build report
        report = ["🤖 *Daily System Report*", ""]

        if health_issues:
            report.append("*Health Issues:*")
            report.extend(health_issues)
            report.append("")
        else:
            report.append("✅ *System Health:* All good")
            report.append("")

        if task_info["total"] > 0:
            report.append(f"📋 *Pending Tasks:* {task_info['total']}")
            if task_info["high_priority"] > 0:
                report.append(f"  🔴 High priority: {task_info['high_priority']}")
            report.append("")

        # Add learning summary if available
        learning = self.run_learning_cycle()
        if learning and "saved to" in learning.lower():
            report.append("📚 Daily learning summary saved")

        return '\n'.join(report)

    def run_scheduled_checks(self):
        """Run all scheduled checks based on timing"""
        state = self.load_state()
        now = datetime.now()
        messages = []

        # Health check every hour
        last_health = state.get("last_health_check")
        if not last_health or (now - datetime.fromisoformat(last_health)) > timedelta(hours=1):
            issues = self.run_health_check()
            if issues:
                # Only alert if these are new issues
                new_issues = [i for i in issues if i not in state.get("alerts_sent", [])]
                if new_issues:
                    messages.append("*System Alert*\n" + '\n'.join(new_issues))
                    state["alerts_sent"] = issues
            else:
                state["alerts_sent"] = []
            state["last_health_check"] = now.isoformat()

        # Learning cycle once per day (at night)
        last_learning = state.get("last_learning_summary")
        if not last_learning or (now - datetime.fromisoformat(last_learning)) > timedelta(hours=20):
            if now.hour >= 22 or now.hour <= 2:
                self.run_learning_cycle()
                state["last_learning_summary"] = now.isoformat()

        # Proactive scan every 6 hours
        last_scan = state.get("last_proactive_scan")
        if not last_scan or (now - datetime.fromisoformat(last_scan)) > timedelta(hours=6):
            self.run_proactive_scan()
            state["last_proactive_scan"] = now.isoformat()

        self.save_state(state)

        # Send any accumulated messages
        for msg in messages:
            self.send_telegram(msg)

        return messages


def main():
    import sys

    orchestrator = Orchestrator()

    if len(sys.argv) < 2:
        print("Usage: orchestrator.py <command>")
        print("Commands:")
        print("  health    - Run health check")
        print("  learn     - Run learning cycle")
        print("  scan      - Run proactive scan")
        print("  report    - Generate daily report")
        print("  check     - Run scheduled checks")
        print("  tasks     - Show pending tasks")
        return

    cmd = sys.argv[1]

    if cmd == "health":
        issues = orchestrator.run_health_check()
        if issues:
            for issue in issues:
                print(issue)
        else:
            print("✅ All systems healthy")

    elif cmd == "learn":
        result = orchestrator.run_learning_cycle()
        print(result or "Learning cycle complete")

    elif cmd == "scan":
        result = orchestrator.run_proactive_scan()
        print(result or "Scan complete")

    elif cmd == "report":
        report = orchestrator.daily_report()
        print(report)

    elif cmd == "check":
        messages = orchestrator.run_scheduled_checks()
        if messages:
            for msg in messages:
                print(msg)
        else:
            print("No alerts")

    elif cmd == "tasks":
        info = orchestrator.check_pending_tasks()
        print(f"Pending tasks: {info['total']}")
        for task in info['tasks']:
            print(f"  - [{task.get('priority', 'normal')}] {task['task'][:50]}")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
