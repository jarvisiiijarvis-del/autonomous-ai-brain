#!/usr/bin/env python3
"""
Auto-Improver - Learns from patterns and suggests system improvements
Analyzes error patterns, success rates, and generates actionable improvements
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict

SHARED_MEMORY = Path.home() / ".claude-shared-memory"
IMPROVEMENTS_FILE = SHARED_MEMORY / "improvements.json"


def load_metrics():
    try:
        with open(SHARED_MEMORY / "metrics.json") as f:
            return json.load(f)
    except:
        return {}


def load_sessions():
    try:
        with open(SHARED_MEMORY / "sessions.json") as f:
            return json.load(f)
    except:
        return {"sessions": []}


def load_reflections():
    try:
        with open(SHARED_MEMORY / "reflections.json") as f:
            return json.load(f)
    except:
        return {"insights": [], "improvements": []}


def load_improvements():
    try:
        with open(IMPROVEMENTS_FILE) as f:
            return json.load(f)
    except:
        return {"suggestions": [], "implemented": [], "updated": None}


def save_improvements(data):
    data["updated"] = datetime.now().isoformat()
    with open(IMPROVEMENTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def analyze_error_patterns():
    """Analyze error patterns to suggest fixes"""
    metrics = load_metrics()
    errors = metrics.get("errors_encountered", [])

    if not errors:
        return []

    suggestions = []

    # Group errors by type
    error_types = Counter(e.get("type", "unknown") for e in errors)
    most_common = error_types.most_common(3)

    for error_type, count in most_common:
        if count >= 3:
            # Get sample errors
            samples = [e.get("error", "")[:100] for e in errors
                      if e.get("type") == error_type][:2]

            suggestions.append({
                "type": "error_pattern",
                "title": f"Reduce {error_type} errors",
                "description": f"Occurred {count} times. Examples: {', '.join(samples)}",
                "priority": "high" if count >= 5 else "medium",
                "category": error_type,
            })

    return suggestions


def analyze_tool_usage():
    """Analyze tool usage patterns for optimization opportunities"""
    sessions = load_sessions()

    if not sessions.get("aggregate", {}).get("tool_totals"):
        return []

    suggestions = []
    tool_totals = sessions["aggregate"]["tool_totals"]

    # Check for tool imbalances
    total_uses = sum(tool_totals.values())
    if total_uses < 10:
        return []

    # If Read tool is used much more than Edit
    read_count = tool_totals.get("Read", 0)
    edit_count = tool_totals.get("Edit", 0)

    if read_count > edit_count * 3 and read_count > 20:
        suggestions.append({
            "type": "efficiency",
            "title": "Reduce redundant file reads",
            "description": f"Read tool used {read_count}x vs Edit {edit_count}x. "
                          "Consider caching file contents.",
            "priority": "low",
            "category": "optimization",
        })

    # If Bash is heavily used
    bash_count = tool_totals.get("Bash", 0)
    if bash_count > total_uses * 0.5:
        suggestions.append({
            "type": "efficiency",
            "title": "Consider specialized tools",
            "description": f"Bash used for {bash_count}/{total_uses} operations. "
                          "Specialized tools may be more efficient.",
            "priority": "low",
            "category": "optimization",
        })

    return suggestions


def analyze_success_patterns():
    """Analyze successful patterns to reinforce"""
    metrics = load_metrics()
    reflections = load_reflections()

    suggestions = []

    # Check success rate trends
    daily = metrics.get("daily_stats", {})
    if len(daily) >= 3:
        recent_days = sorted(daily.keys())[-7:]
        rates = []
        for day in recent_days:
            stats = daily[day]
            total = stats.get("success", 0) + stats.get("failure", 0)
            if total > 0:
                rates.append(stats["success"] / total)

        if rates:
            avg_rate = sum(rates) / len(rates)
            if avg_rate < 0.8:
                suggestions.append({
                    "type": "quality",
                    "title": "Improve success rate",
                    "description": f"Average success rate is {avg_rate*100:.0f}%. "
                                  "Review recent failures for patterns.",
                    "priority": "high",
                    "category": "reliability",
                })
            elif avg_rate > 0.95:
                suggestions.append({
                    "type": "recognition",
                    "title": "High success rate maintained",
                    "description": f"Excellent {avg_rate*100:.0f}% success rate! "
                                  "Document current practices.",
                    "priority": "low",
                    "category": "documentation",
                })

    # Check for pending improvement suggestions
    pending = [i for i in reflections.get("improvements", [])
               if i.get("status") == "pending"]

    if len(pending) > 5:
        suggestions.append({
            "type": "process",
            "title": "Review pending improvements",
            "description": f"{len(pending)} improvement suggestions pending. "
                          "Schedule time to review and implement.",
            "priority": "medium",
            "category": "process",
        })

    return suggestions


def analyze_knowledge_gaps():
    """Identify knowledge gaps from conversation patterns"""
    try:
        with open(SHARED_MEMORY / "history.json") as f:
            history = json.load(f)
    except:
        return []

    suggestions = []
    conversations = history.get("conversations", [])

    if len(conversations) < 5:
        return []

    # Look for repeated questions or research
    topics = Counter()
    for conv in conversations:
        tags = conv.get("tags", [])
        summary = conv.get("summary", "").lower()

        for tag in tags:
            topics[tag] += 1

        if "research" in summary or "learn" in summary:
            topics["learning"] += 1

    # If certain topics keep recurring
    for topic, count in topics.most_common(5):
        if count >= 3:
            suggestions.append({
                "type": "learning",
                "title": f"Document {topic} knowledge",
                "description": f"Topic '{topic}' appeared {count} times. "
                              "Consider creating reference documentation.",
                "priority": "medium" if count >= 5 else "low",
                "category": "documentation",
            })

    return suggestions


def generate_all_improvements():
    """Generate comprehensive improvement suggestions"""
    all_suggestions = []

    # Gather from all analyzers
    all_suggestions.extend(analyze_error_patterns())
    all_suggestions.extend(analyze_tool_usage())
    all_suggestions.extend(analyze_success_patterns())
    all_suggestions.extend(analyze_knowledge_gaps())

    # Deduplicate and prioritize
    seen_titles = set()
    unique = []
    for s in all_suggestions:
        if s["title"] not in seen_titles:
            seen_titles.add(s["title"])
            unique.append(s)

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    unique.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 2))

    # Save improvements
    improvements = load_improvements()
    for s in unique:
        s["generated_at"] = datetime.now().isoformat()
        s["status"] = "pending"

    improvements["suggestions"].extend(unique)
    improvements["suggestions"] = improvements["suggestions"][-100:]
    save_improvements(improvements)

    return unique


def get_actionable_improvements(limit=5):
    """Get the most actionable current improvements"""
    improvements = load_improvements()
    pending = [s for s in improvements.get("suggestions", [])
               if s.get("status") == "pending"]

    # Sort by priority and recency
    priority_order = {"high": 0, "medium": 1, "low": 2}
    pending.sort(key=lambda x: (
        priority_order.get(x.get("priority", "low"), 2),
        x.get("generated_at", "")
    ))

    return pending[:limit]


def mark_implemented(title):
    """Mark an improvement as implemented"""
    improvements = load_improvements()

    for s in improvements.get("suggestions", []):
        if s.get("title") == title and s.get("status") == "pending":
            s["status"] = "implemented"
            s["implemented_at"] = datetime.now().isoformat()
            improvements["implemented"].append(s)
            save_improvements(improvements)
            return True

    return False


def main():
    import sys

    if len(sys.argv) < 2:
        print("Auto-Improver - Learn and improve from patterns")
        print("")
        print("Usage:")
        print("  python3 auto_improver.py analyze        - Generate improvements")
        print("  python3 auto_improver.py list           - List pending improvements")
        print("  python3 auto_improver.py implement <t>  - Mark improvement as done")
        print("  python3 auto_improver.py stats          - Show improvement stats")
        return

    cmd = sys.argv[1]

    if cmd == "analyze":
        improvements = generate_all_improvements()
        if improvements:
            print(f"Generated {len(improvements)} improvement suggestions:\n")
            for i in improvements:
                print(f"[{i['priority'].upper()}] {i['title']}")
                print(f"  {i['description'][:100]}")
                print()
        else:
            print("No new improvements identified.")

    elif cmd == "list":
        improvements = get_actionable_improvements(10)
        if improvements:
            print("Pending improvements:\n")
            for i, imp in enumerate(improvements, 1):
                print(f"{i}. [{imp['priority'].upper()}] {imp['title']}")
                print(f"   {imp['description'][:80]}")
                print()
        else:
            print("No pending improvements.")

    elif cmd == "implement" and len(sys.argv) >= 3:
        title = " ".join(sys.argv[2:])
        if mark_implemented(title):
            print(f"Marked as implemented: {title}")
        else:
            print("Improvement not found or already implemented")

    elif cmd == "stats":
        improvements = load_improvements()
        pending = len([s for s in improvements.get("suggestions", [])
                      if s.get("status") == "pending"])
        implemented = len(improvements.get("implemented", []))
        print(f"Pending improvements: {pending}")
        print(f"Implemented: {implemented}")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
