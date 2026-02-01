#!/usr/bin/env python3
"""
Proactive Agent - Monitors system and suggests improvements
Can be queried by Claude Code or triggered automatically
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

class ProactiveAgent:
    def __init__(self):
        self.home = Path.home()
        self.shared_memory = self.home / ".claude-shared-memory"
        self.suggestions_file = self.shared_memory / "suggestions.json"

    def analyze_codebase_health(self):
        """Check for code quality issues"""
        suggestions = []

        # Check for TODO comments in projects
        projects = [
            self.home / "telegram-claude-bot",
            self.home / "claude-chat",
        ]

        for project in projects:
            if not project.exists():
                continue

            try:
                result = subprocess.run(
                    ["grep", "-r", "TODO", "--include=*.py", "--include=*.ts", "--include=*.tsx", "."],
                    cwd=project,
                    capture_output=True,
                    text=True
                )
                if result.stdout:
                    todo_count = len(result.stdout.strip().split('\n'))
                    if todo_count > 5:
                        suggestions.append({
                            "type": "code_quality",
                            "project": project.name,
                            "issue": f"Found {todo_count} TODO comments",
                            "action": "Review and address TODO items"
                        })
            except:
                pass

        return suggestions

    def analyze_security(self):
        """Check for potential security issues"""
        suggestions = []

        # Check for exposed secrets in common locations
        sensitive_patterns = ["API_KEY", "SECRET", "PASSWORD", "TOKEN"]
        check_files = list(self.home.glob("*/.env")) + list(self.home.glob("*/*.env"))

        for env_file in check_files:
            try:
                perms = oct(env_file.stat().st_mode)[-3:]
                if perms != "600":
                    suggestions.append({
                        "type": "security",
                        "file": str(env_file),
                        "issue": f"Insecure permissions ({perms})",
                        "action": f"Run: chmod 600 {env_file}"
                    })
            except:
                pass

        return suggestions

    def analyze_disk_usage(self):
        """Check disk usage and suggest cleanup"""
        suggestions = []

        try:
            result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                used_pct = int(parts[4].rstrip('%'))
                if used_pct > 80:
                    suggestions.append({
                        "type": "maintenance",
                        "issue": f"Disk usage at {used_pct}%",
                        "action": "Run cleanup: brew cleanup, docker system prune, clear caches"
                    })
        except:
            pass

        # Check for large log files
        log_dirs = [
            self.home / "telegram-claude-bot",
            self.home / "Library/Logs",
        ]

        for log_dir in log_dirs:
            if not log_dir.exists():
                continue
            for log_file in log_dir.glob("*.log"):
                try:
                    size_mb = log_file.stat().st_size / (1024 * 1024)
                    if size_mb > 100:
                        suggestions.append({
                            "type": "maintenance",
                            "issue": f"Large log file: {log_file.name} ({size_mb:.0f}MB)",
                            "action": f"Rotate or clear: {log_file}"
                        })
                except:
                    pass

        return suggestions

    def analyze_services(self):
        """Check running services and suggest improvements"""
        suggestions = []

        # Check if key services are configured to auto-start
        expected_services = [
            "com.User.morning-surprise",
        ]

        try:
            result = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
            running = result.stdout

            for service in expected_services:
                if service not in running:
                    suggestions.append({
                        "type": "automation",
                        "issue": f"Service not loaded: {service}",
                        "action": f"Load service: launchctl load ~/Library/LaunchAgents/{service}.plist"
                    })
        except:
            pass

        return suggestions

    def get_all_suggestions(self):
        """Run all analyzers and return suggestions"""
        all_suggestions = []
        all_suggestions.extend(self.analyze_codebase_health())
        all_suggestions.extend(self.analyze_security())
        all_suggestions.extend(self.analyze_disk_usage())
        all_suggestions.extend(self.analyze_services())

        # Add timestamp
        result = {
            "generated_at": datetime.now().isoformat(),
            "suggestions": all_suggestions,
            "count": len(all_suggestions)
        }

        # Save to file
        with open(self.suggestions_file, 'w') as f:
            json.dump(result, f, indent=2)

        return result

    def get_priority_suggestion(self):
        """Get the most important suggestion"""
        result = self.get_all_suggestions()

        priority_order = ["security", "maintenance", "code_quality", "automation"]

        for priority_type in priority_order:
            for suggestion in result["suggestions"]:
                if suggestion["type"] == priority_type:
                    return suggestion

        return None


def main():
    agent = ProactiveAgent()
    result = agent.get_all_suggestions()

    print(f"Found {result['count']} suggestions:")
    for s in result["suggestions"]:
        print(f"  [{s['type']}] {s['issue']}")
        print(f"    Action: {s['action']}")
        print()


if __name__ == "__main__":
    main()
