#!/usr/bin/env python3
"""
Decision Engine - Makes autonomous decisions based on system state
Evaluates conditions and executes appropriate actions
"""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

BRAIN_DIR = Path(__file__).parent
SHARED_MEMORY = Path.home() / ".claude-shared-memory"
DECISIONS_LOG = SHARED_MEMORY / "decisions.json"

# Decision rules: condition -> action
RULES = [
    {
        "name": "rebuild_stale_graph",
        "description": "Rebuild knowledge graph if history is newer",
        "condition": "graph_stale",
        "action": ["knowledge_graph.py", "build"],
        "cooldown_hours": 24,
    },
    {
        "name": "consolidate_memory",
        "description": "Consolidate memory when usage is high",
        "condition": "memory_high",
        "action": ["memory_consolidator.py", "consolidate"],
        "cooldown_hours": 72,
    },
    {
        "name": "run_improvement_analysis",
        "description": "Analyze for improvements weekly",
        "condition": "weekly_improvement",
        "action": ["auto_improver.py", "analyze"],
        "cooldown_hours": 168,
    },
    {
        "name": "scan_projects",
        "description": "Scan projects daily for health",
        "condition": "daily_scan",
        "action": ["project_scanner.py", "scan"],
        "cooldown_hours": 24,
    },
    {
        "name": "track_session",
        "description": "Track session periodically",
        "condition": "session_tracking",
        "action": ["session_tracker.py", "track"],
        "cooldown_hours": 4,
    },
]


def load_decisions():
    try:
        with open(DECISIONS_LOG) as f:
            return json.load(f)
    except:
        return {"decisions": [], "last_actions": {}}


def save_decisions(data):
    with open(DECISIONS_LOG, 'w') as f:
        json.dump(data, f, indent=2)


def check_cooldown(rule_name, cooldown_hours):
    """Check if rule is still in cooldown"""
    decisions = load_decisions()
    last = decisions.get("last_actions", {}).get(rule_name)

    if not last:
        return False

    last_time = datetime.fromisoformat(last)
    return datetime.now() - last_time < timedelta(hours=cooldown_hours)


def record_action(rule_name, result):
    """Record that an action was taken"""
    decisions = load_decisions()
    decisions["last_actions"][rule_name] = datetime.now().isoformat()
    decisions["decisions"].append({
        "rule": rule_name,
        "timestamp": datetime.now().isoformat(),
        "result": result[:200] if result else "no output"
    })
    decisions["decisions"] = decisions["decisions"][-100:]
    save_decisions(decisions)


def evaluate_condition(condition):
    """Evaluate a condition and return True/False"""

    if condition == "graph_stale":
        graph_path = SHARED_MEMORY / "graph.json"
        history_path = SHARED_MEMORY / "history.json"
        if graph_path.exists() and history_path.exists():
            graph_mtime = graph_path.stat().st_mtime
            history_mtime = history_path.stat().st_mtime
            return history_mtime > graph_mtime + 3600  # 1 hour tolerance
        return not graph_path.exists()

    elif condition == "memory_high":
        total_size = 0
        for f in SHARED_MEMORY.glob("*.json"):
            total_size += f.stat().st_size
        return total_size > 5 * 1024 * 1024  # 5 MB threshold

    elif condition == "weekly_improvement":
        # Run once a week on Monday
        return datetime.now().weekday() == 0

    elif condition == "daily_scan":
        # Run daily
        return True

    elif condition == "session_tracking":
        # Always eligible (cooldown controls frequency)
        return True

    return False


def execute_action(script, args):
    """Execute an action script"""
    try:
        cmd = ["python3", str(BRAIN_DIR / script)] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.stdout.strip()[:500]
    except Exception as e:
        return f"Error: {e}"


def run_decisions():
    """Evaluate all rules and execute actions"""
    executed = []

    for rule in RULES:
        name = rule["name"]
        cooldown = rule.get("cooldown_hours", 24)

        # Check cooldown
        if check_cooldown(name, cooldown):
            continue

        # Evaluate condition
        if not evaluate_condition(rule["condition"]):
            continue

        # Execute action
        script = rule["action"][0]
        args = rule["action"][1:] if len(rule["action"]) > 1 else []

        result = execute_action(script, args)
        record_action(name, result)

        executed.append({
            "rule": name,
            "description": rule["description"],
            "result": result[:100]
        })

    return executed


def get_pending_decisions():
    """Get decisions that could be executed"""
    pending = []

    for rule in RULES:
        name = rule["name"]
        cooldown = rule.get("cooldown_hours", 24)

        in_cooldown = check_cooldown(name, cooldown)
        condition_met = evaluate_condition(rule["condition"])

        pending.append({
            "rule": name,
            "description": rule["description"],
            "condition_met": condition_met,
            "in_cooldown": in_cooldown,
            "would_execute": condition_met and not in_cooldown
        })

    return pending


def main():
    import sys

    if len(sys.argv) < 2:
        print("Decision Engine - Autonomous decision making")
        print("")
        print("Usage:")
        print("  python3 decision_engine.py run      - Run decisions")
        print("  python3 decision_engine.py status   - Show pending decisions")
        print("  python3 decision_engine.py log      - Show decision log")
        print("  python3 decision_engine.py rules    - List all rules")
        return

    cmd = sys.argv[1]

    if cmd == "run":
        executed = run_decisions()
        if executed:
            print(f"Executed {len(executed)} decisions:\n")
            for d in executed:
                print(f"✓ {d['rule']}: {d['description']}")
                print(f"  Result: {d['result'][:80]}")
                print()
        else:
            print("No decisions to execute (all in cooldown or conditions not met)")

    elif cmd == "status":
        pending = get_pending_decisions()
        print("Decision Status:\n")
        for p in pending:
            status = "🟢 READY" if p["would_execute"] else "⏸️ WAITING"
            if p["in_cooldown"]:
                status = "⏳ COOLDOWN"
            elif not p["condition_met"]:
                status = "❌ CONDITION"
            print(f"{status} {p['rule']}")
            print(f"       {p['description']}")

    elif cmd == "log":
        decisions = load_decisions()
        print("Recent decisions:\n")
        for d in decisions.get("decisions", [])[-10:]:
            print(f"[{d['timestamp'][:16]}] {d['rule']}")
            print(f"  {d['result'][:60]}")
            print()

    elif cmd == "rules":
        print("Available rules:\n")
        for rule in RULES:
            print(f"• {rule['name']}")
            print(f"  {rule['description']}")
            print(f"  Condition: {rule['condition']}, Cooldown: {rule['cooldown_hours']}h")
            print()

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
