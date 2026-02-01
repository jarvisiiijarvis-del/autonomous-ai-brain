#!/usr/bin/env python3
"""
System Monitor for User
Checks system health and sends Telegram alerts when issues are detected.
Designed to run every 5 minutes via launchd.
"""

import os
import json
import shutil
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = YOUR_TELEGRAM_CHAT_ID

# Thresholds
DISK_FREE_THRESHOLD_PERCENT = 10  # Alert if less than 10% free
MEMORY_FREE_THRESHOLD_GB = 1  # Alert if less than 1GB free

# State file to track alerts (avoid spam)
STATE_FILE = Path(__file__).parent / ".monitor_state.json"

# Services to monitor (process name patterns)
SERVICES = {
    "telegram_bot": ["python", "bot.py"],
    "claude_chat": ["Electron", "claude-chat"],
}


def load_state() -> dict:
    """Load alert state from file."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"alerts": {}}


def save_state(state: dict):
    """Save alert state to file."""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except IOError as e:
        print(f"Warning: Could not save state: {e}")


def send_telegram_alert(message: str) -> bool:
    """Send alert via Telegram Bot API."""
    if not TELEGRAM_TOKEN:
        print(f"Error: TELEGRAM_BOT_TOKEN not set. Alert: {message}")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": CHAT_ID,
        "text": f"[System Monitor]\n{message}",
        "parse_mode": "HTML"
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")
        return False


def check_disk_space() -> tuple[bool, str]:
    """Check if disk space is low. Returns (is_ok, message)."""
    try:
        usage = shutil.disk_usage("/")
        free_percent = (usage.free / usage.total) * 100
        free_gb = usage.free / (1024 ** 3)

        if free_percent < DISK_FREE_THRESHOLD_PERCENT:
            return False, f"Low disk space: {free_gb:.1f}GB free ({free_percent:.1f}%)"
        return True, f"Disk OK: {free_gb:.1f}GB free ({free_percent:.1f}%)"
    except Exception as e:
        return False, f"Disk check failed: {e}"


def check_memory() -> tuple[bool, str]:
    """Check if memory is low. Returns (is_ok, message)."""
    try:
        # Use vm_stat on macOS
        result = subprocess.run(
            ["vm_stat"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return False, "Memory check failed: vm_stat error"

        # Parse vm_stat output
        stats = {}
        for line in result.stdout.strip().split("\n")[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                # Remove trailing period and convert to int
                value = value.strip().rstrip(".")
                try:
                    stats[key.strip()] = int(value)
                except ValueError:
                    pass

        # Page size (usually 16384 on Apple Silicon, 4096 on Intel)
        page_size_result = subprocess.run(
            ["pagesize"],
            capture_output=True,
            text=True,
            timeout=5
        )
        page_size = int(page_size_result.stdout.strip()) if page_size_result.returncode == 0 else 16384

        # Calculate free memory (free + inactive pages)
        free_pages = stats.get("Pages free", 0)
        inactive_pages = stats.get("Pages inactive", 0)
        # Speculative pages can also be freed
        speculative_pages = stats.get("Pages speculative", 0)

        free_bytes = (free_pages + inactive_pages + speculative_pages) * page_size
        free_gb = free_bytes / (1024 ** 3)

        if free_gb < MEMORY_FREE_THRESHOLD_GB:
            return False, f"Low memory: {free_gb:.2f}GB available"
        return True, f"Memory OK: {free_gb:.2f}GB available"

    except Exception as e:
        return False, f"Memory check failed: {e}"


def is_process_running(patterns: list[str]) -> bool:
    """Check if a process matching all patterns is running."""
    try:
        result = subprocess.run(
            ["pgrep", "-fl", patterns[0]],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return False

        # Check if all patterns match any line
        for line in result.stdout.strip().split("\n"):
            if all(p.lower() in line.lower() for p in patterns):
                return True
        return False

    except Exception:
        return False


def check_services() -> list[tuple[str, bool]]:
    """Check if monitored services are running. Returns list of (service, is_running)."""
    results = []
    for name, patterns in SERVICES.items():
        is_running = is_process_running(patterns)
        results.append((name, is_running))
    return results


def main():
    """Run system health checks and send alerts if needed."""
    print(f"[{datetime.now().isoformat()}] Running system monitor...")

    state = load_state()
    alerts_to_send = []
    current_issues = {}

    # Check disk space
    disk_ok, disk_msg = check_disk_space()
    print(f"  Disk: {disk_msg}")
    if not disk_ok:
        current_issues["disk"] = disk_msg

    # Check memory
    mem_ok, mem_msg = check_memory()
    print(f"  Memory: {mem_msg}")
    if not mem_ok:
        current_issues["memory"] = mem_msg

    # Check services (only alert if previously running and now stopped)
    service_results = check_services()
    for service_name, is_running in service_results:
        status = "running" if is_running else "stopped"
        print(f"  Service {service_name}: {status}")

        # Track service state to detect when it stops
        prev_state = state.get("services", {}).get(service_name, None)

        if not is_running and prev_state == "running":
            current_issues[f"service_{service_name}"] = f"Service stopped: {service_name}"

        # Update service state
        if "services" not in state:
            state["services"] = {}
        state["services"][service_name] = "running" if is_running else "stopped"

    # Determine which alerts to send (new issues only)
    for issue_key, message in current_issues.items():
        if issue_key not in state["alerts"]:
            alerts_to_send.append(message)
            state["alerts"][issue_key] = {
                "message": message,
                "first_seen": datetime.now().isoformat()
            }

    # Clear resolved issues from state
    resolved = [k for k in state["alerts"] if k not in current_issues]
    for key in resolved:
        print(f"  Issue resolved: {key}")
        del state["alerts"][key]

    # Send alerts
    if alerts_to_send:
        alert_text = "\n".join(f"- {msg}" for msg in alerts_to_send)
        print(f"  Sending alert: {alert_text}")
        send_telegram_alert(alert_text)
    else:
        print("  No new issues to alert.")

    # Save state
    save_state(state)
    print("  Monitor complete.")


if __name__ == "__main__":
    main()
