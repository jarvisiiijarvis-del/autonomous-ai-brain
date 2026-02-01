#!/usr/bin/env python3
"""
Self-Reflection System - Analyzes Claude's own performance and suggests improvements
Tracks success/failure patterns and learns from them
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

SHARED_MEMORY = Path.home() / ".claude-shared-memory"
REFLECTION_FILE = SHARED_MEMORY / "reflections.json"
METRICS_FILE = SHARED_MEMORY / "metrics.json"


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return None


def save_json(path, data):
    data["updated"] = datetime.now().isoformat()
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def load_metrics():
    data = load_json(METRICS_FILE)
    if not data:
        data = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "commands_run": 0,
            "errors_encountered": [],
            "successful_patterns": [],
            "daily_stats": {},
            "updated": None
        }
    return data


def load_reflections():
    data = load_json(REFLECTION_FILE)
    if not data:
        data = {
            "insights": [],
            "improvements": [],
            "patterns_noticed": [],
            "updated": None
        }
    return data


def record_success(action_type, details=""):
    """Record a successful action for pattern learning"""
    metrics = load_metrics()
    metrics["tasks_completed"] += 1

    today = datetime.now().strftime("%Y-%m-%d")
    if today not in metrics["daily_stats"]:
        metrics["daily_stats"][today] = {"success": 0, "failure": 0}
    metrics["daily_stats"][today]["success"] += 1

    if details:
        pattern = {"type": action_type, "details": details, "timestamp": datetime.now().isoformat()}
        metrics["successful_patterns"].append(pattern)
        # Keep only last 100 patterns
        metrics["successful_patterns"] = metrics["successful_patterns"][-100:]

    save_json(METRICS_FILE, metrics)


def record_failure(action_type, error_msg):
    """Record a failed action for learning"""
    metrics = load_metrics()
    metrics["tasks_failed"] += 1

    today = datetime.now().strftime("%Y-%m-%d")
    if today not in metrics["daily_stats"]:
        metrics["daily_stats"][today] = {"success": 0, "failure": 0}
    metrics["daily_stats"][today]["failure"] += 1

    error = {
        "type": action_type,
        "error": error_msg[:200],
        "timestamp": datetime.now().isoformat()
    }
    metrics["errors_encountered"].append(error)
    # Keep only last 50 errors
    metrics["errors_encountered"] = metrics["errors_encountered"][-50:]

    save_json(METRICS_FILE, metrics)


def add_insight(insight):
    """Add a self-reflection insight"""
    reflections = load_reflections()
    reflections["insights"].append({
        "insight": insight,
        "timestamp": datetime.now().isoformat()
    })
    reflections["insights"] = reflections["insights"][-50:]
    save_json(REFLECTION_FILE, reflections)


def add_improvement(improvement):
    """Suggest an improvement based on reflection"""
    reflections = load_reflections()
    reflections["improvements"].append({
        "suggestion": improvement,
        "status": "pending",
        "timestamp": datetime.now().isoformat()
    })
    save_json(REFLECTION_FILE, reflections)


def analyze_patterns():
    """Analyze patterns in successes and failures"""
    metrics = load_metrics()
    reflections = load_reflections()

    analysis = {
        "success_rate": 0,
        "common_errors": [],
        "peak_productivity_times": [],
        "suggestions": []
    }

    # Calculate success rate
    total = metrics["tasks_completed"] + metrics["tasks_failed"]
    if total > 0:
        analysis["success_rate"] = metrics["tasks_completed"] / total * 100

    # Find common errors
    error_types = defaultdict(int)
    for error in metrics["errors_encountered"]:
        error_types[error.get("type", "unknown")] += 1

    analysis["common_errors"] = sorted(
        error_types.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    # Analyze daily patterns
    daily = metrics.get("daily_stats", {})
    if daily:
        best_day = max(daily.items(), key=lambda x: x[1].get("success", 0), default=(None, {}))
        if best_day[0]:
            analysis["suggestions"].append(f"Best productive day: {best_day[0]} with {best_day[1].get('success', 0)} successes")

    # Generate suggestions based on patterns
    if analysis["success_rate"] < 80 and total > 10:
        analysis["suggestions"].append("Success rate below 80% - consider reviewing error patterns")

    if len(analysis["common_errors"]) > 0:
        top_error = analysis["common_errors"][0]
        analysis["suggestions"].append(f"Most common error type: {top_error[0]} ({top_error[1]} times) - consider adding better handling")

    return analysis


def generate_reflection():
    """Generate a self-reflection report"""
    metrics = load_metrics()
    analysis = analyze_patterns()

    report = []
    report.append("## Self-Reflection Report")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")

    report.append("### Performance Metrics")
    report.append(f"- Tasks completed: {metrics['tasks_completed']}")
    report.append(f"- Tasks failed: {metrics['tasks_failed']}")
    report.append(f"- Success rate: {analysis['success_rate']:.1f}%")
    report.append("")

    if analysis["common_errors"]:
        report.append("### Common Errors")
        for error_type, count in analysis["common_errors"]:
            report.append(f"- {error_type}: {count} occurrences")
        report.append("")

    if analysis["suggestions"]:
        report.append("### Suggestions for Improvement")
        for suggestion in analysis["suggestions"]:
            report.append(f"- {suggestion}")
        report.append("")

    # Check recent errors for patterns
    recent_errors = metrics.get("errors_encountered", [])[-5:]
    if recent_errors:
        report.append("### Recent Errors to Learn From")
        for error in recent_errors:
            report.append(f"- [{error.get('type', 'unknown')}] {error.get('error', 'No details')[:100]}")

    return "\n".join(report)


def get_improvement_suggestions():
    """Get pending improvement suggestions"""
    reflections = load_reflections()
    pending = [i for i in reflections.get("improvements", []) if i.get("status") == "pending"]
    return pending


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: self_reflect.py <command>")
        print("Commands:")
        print("  success <type> [details]  - Record a success")
        print("  failure <type> <error>    - Record a failure")
        print("  insight <text>            - Add an insight")
        print("  improve <suggestion>      - Add improvement suggestion")
        print("  analyze                   - Analyze patterns")
        print("  report                    - Generate reflection report")
        print("  suggestions               - Get pending improvements")
        return

    cmd = sys.argv[1]

    if cmd == "success" and len(sys.argv) >= 3:
        details = sys.argv[3] if len(sys.argv) > 3 else ""
        record_success(sys.argv[2], details)
        print(f"Recorded success: {sys.argv[2]}")

    elif cmd == "failure" and len(sys.argv) >= 4:
        record_failure(sys.argv[2], sys.argv[3])
        print(f"Recorded failure: {sys.argv[2]}")

    elif cmd == "insight" and len(sys.argv) >= 3:
        add_insight(" ".join(sys.argv[2:]))
        print("Insight added")

    elif cmd == "improve" and len(sys.argv) >= 3:
        add_improvement(" ".join(sys.argv[2:]))
        print("Improvement suggestion added")

    elif cmd == "analyze":
        analysis = analyze_patterns()
        print(json.dumps(analysis, indent=2))

    elif cmd == "report":
        print(generate_reflection())

    elif cmd == "suggestions":
        suggestions = get_improvement_suggestions()
        if suggestions:
            for s in suggestions:
                print(f"- {s['suggestion']}")
        else:
            print("No pending improvements")

    else:
        print("Unknown command or missing arguments")


if __name__ == "__main__":
    main()
