#!/usr/bin/env python3
"""
Memory Consolidator - Consolidates, summarizes, and prunes old memories
Keeps the memory system efficient while preserving important information
"""

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

SHARED_MEMORY = Path.home() / ".claude-shared-memory"
ARCHIVE_DIR = SHARED_MEMORY / "archive"
CONSOLIDATION_LOG = SHARED_MEMORY / "consolidation_log.json"

# How long to keep detailed entries before consolidating
CONSOLIDATION_THRESHOLDS = {
    "history": 30,      # days - conversation history
    "metrics": 14,      # days - detailed metrics
    "sessions": 14,     # days - session data
    "insights": 60,     # days - insights
}


def load_log():
    try:
        with open(CONSOLIDATION_LOG) as f:
            return json.load(f)
    except:
        return {"consolidations": [], "last_run": None}


def save_log(data):
    data["last_run"] = datetime.now().isoformat()
    with open(CONSOLIDATION_LOG, 'w') as f:
        json.dump(data, f, indent=2)


def backup_file(filepath):
    """Create a backup before modifying"""
    ARCHIVE_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = ARCHIVE_DIR / f"{filepath.name}.{timestamp}.bak"
    shutil.copy(filepath, backup_path)
    return backup_path


def consolidate_history():
    """Consolidate old conversation history into summaries"""
    history_file = SHARED_MEMORY / "history.json"
    if not history_file.exists():
        return {"status": "no_file"}

    try:
        with open(history_file) as f:
            history = json.load(f)
    except:
        return {"status": "parse_error"}

    conversations = history.get("conversations", [])
    if len(conversations) < 20:
        return {"status": "too_few", "count": len(conversations)}

    threshold = datetime.now() - timedelta(days=CONSOLIDATION_THRESHOLDS["history"])
    threshold_str = threshold.isoformat()[:10]

    # Separate old and recent
    old = []
    recent = []
    for conv in conversations:
        if conv.get("date", "9999") < threshold_str:
            old.append(conv)
        else:
            recent.append(conv)

    if len(old) < 10:
        return {"status": "insufficient_old", "old_count": len(old)}

    # Create consolidated summary
    backup_file(history_file)

    # Group old by week
    weekly = defaultdict(list)
    for conv in old:
        date = conv.get("date", "unknown")
        if date != "unknown":
            week = date[:8] + "01"  # Group by month instead
            weekly[week].append(conv)

    # Create summary entries
    consolidated = []
    for week, convs in sorted(weekly.items()):
        tags = set()
        summaries = []
        for c in convs:
            tags.update(c.get("tags", []))
            if c.get("summary"):
                summaries.append(c["summary"][:100])

        consolidated.append({
            "date": week,
            "summary": f"[Consolidated {len(convs)} conversations] Topics: {', '.join(list(tags)[:5])}",
            "tags": list(tags)[:10],
            "consolidated": True,
            "original_count": len(convs)
        })

    # Save updated history
    history["conversations"] = consolidated + recent
    history["last_consolidated"] = datetime.now().isoformat()

    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)

    return {
        "status": "consolidated",
        "old_removed": len(old),
        "consolidated_into": len(consolidated),
        "remaining": len(recent)
    }


def consolidate_metrics():
    """Consolidate old daily metrics into weekly summaries"""
    metrics_file = SHARED_MEMORY / "metrics.json"
    if not metrics_file.exists():
        return {"status": "no_file"}

    try:
        with open(metrics_file) as f:
            metrics = json.load(f)
    except:
        return {"status": "parse_error"}

    daily_stats = metrics.get("daily_stats", {})
    if len(daily_stats) < 14:
        return {"status": "too_few", "count": len(daily_stats)}

    threshold = (datetime.now() - timedelta(days=CONSOLIDATION_THRESHOLDS["metrics"])).strftime("%Y-%m-%d")

    # Separate old and recent
    old_days = {k: v for k, v in daily_stats.items() if k < threshold}
    recent_days = {k: v for k, v in daily_stats.items() if k >= threshold}

    if len(old_days) < 7:
        return {"status": "insufficient_old", "old_count": len(old_days)}

    backup_file(metrics_file)

    # Group by week and aggregate
    weekly = defaultdict(lambda: {"success": 0, "failure": 0, "days": 0})
    for day, stats in old_days.items():
        # Get week start (Monday)
        dt = datetime.strptime(day, "%Y-%m-%d")
        week_start = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
        weekly[week_start]["success"] += stats.get("success", 0)
        weekly[week_start]["failure"] += stats.get("failure", 0)
        weekly[week_start]["days"] += 1

    # Convert to weekly_stats format
    if "weekly_stats" not in metrics:
        metrics["weekly_stats"] = {}

    for week, stats in weekly.items():
        metrics["weekly_stats"][week] = stats

    metrics["daily_stats"] = recent_days
    metrics["last_consolidated"] = datetime.now().isoformat()

    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    return {
        "status": "consolidated",
        "days_removed": len(old_days),
        "weeks_created": len(weekly),
        "days_remaining": len(recent_days)
    }


def prune_errors():
    """Prune old error entries"""
    metrics_file = SHARED_MEMORY / "metrics.json"
    if not metrics_file.exists():
        return {"status": "no_file"}

    try:
        with open(metrics_file) as f:
            metrics = json.load(f)
    except:
        return {"status": "parse_error"}

    errors = metrics.get("errors_encountered", [])
    original_count = len(errors)

    if original_count < 50:
        return {"status": "too_few", "count": original_count}

    # Keep only last 30
    metrics["errors_encountered"] = errors[-30:]

    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    return {
        "status": "pruned",
        "removed": original_count - 30,
        "remaining": 30
    }


def prune_sessions():
    """Prune old session data"""
    sessions_file = SHARED_MEMORY / "sessions.json"
    if not sessions_file.exists():
        return {"status": "no_file"}

    try:
        with open(sessions_file) as f:
            sessions = json.load(f)
    except:
        return {"status": "parse_error"}

    session_list = sessions.get("sessions", [])
    original_count = len(session_list)

    if original_count < 50:
        return {"status": "too_few", "count": original_count}

    # Keep only last 30
    sessions["sessions"] = session_list[-30:]

    with open(sessions_file, 'w') as f:
        json.dump(sessions, f, indent=2)

    return {
        "status": "pruned",
        "removed": original_count - 30,
        "remaining": 30
    }


def get_memory_stats():
    """Get current memory usage stats"""
    stats = {}

    for filename in ["history.json", "metrics.json", "sessions.json",
                     "context.json", "goals.json", "graph.json"]:
        filepath = SHARED_MEMORY / filename
        if filepath.exists():
            size = filepath.stat().st_size
            stats[filename] = {
                "size_kb": size // 1024,
                "size_mb": round(size / (1024 * 1024), 2)
            }

    # Count entries
    try:
        with open(SHARED_MEMORY / "history.json") as f:
            history = json.load(f)
        stats["history.json"]["entries"] = len(history.get("conversations", []))
    except:
        pass

    try:
        with open(SHARED_MEMORY / "metrics.json") as f:
            metrics = json.load(f)
        stats["metrics.json"]["daily_entries"] = len(metrics.get("daily_stats", {}))
        stats["metrics.json"]["errors"] = len(metrics.get("errors_encountered", []))
    except:
        pass

    return stats


def run_consolidation():
    """Run full consolidation"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "history": consolidate_history(),
        "metrics": consolidate_metrics(),
        "errors": prune_errors(),
        "sessions": prune_sessions(),
    }

    # Log the consolidation
    log = load_log()
    log["consolidations"].append({
        "timestamp": datetime.now().isoformat(),
        "results": results
    })
    log["consolidations"] = log["consolidations"][-20:]
    save_log(log)

    return results


def main():
    import sys

    if len(sys.argv) < 2:
        print("Memory Consolidator - Manage memory efficiency")
        print("")
        print("Usage:")
        print("  python3 memory_consolidator.py stats       - Show memory stats")
        print("  python3 memory_consolidator.py consolidate - Run consolidation")
        print("  python3 memory_consolidator.py log         - Show consolidation log")
        print("  python3 memory_consolidator.py archive     - List archived backups")
        return

    cmd = sys.argv[1]

    if cmd == "stats":
        stats = get_memory_stats()
        print("Memory Usage:\n")
        total = 0
        for filename, info in sorted(stats.items()):
            size = info.get("size_kb", 0)
            total += size
            extras = []
            if "entries" in info:
                extras.append(f"{info['entries']} entries")
            if "daily_entries" in info:
                extras.append(f"{info['daily_entries']} days")
            if "errors" in info:
                extras.append(f"{info['errors']} errors")
            extra_str = f" ({', '.join(extras)})" if extras else ""
            print(f"  {filename}: {size} KB{extra_str}")
        print(f"\nTotal: {total} KB ({total / 1024:.2f} MB)")

    elif cmd == "consolidate":
        print("Running consolidation...")
        results = run_consolidation()
        print(json.dumps(results, indent=2))

    elif cmd == "log":
        log = load_log()
        print(f"Last run: {log.get('last_run', 'never')}\n")
        for entry in log.get("consolidations", [])[-5:]:
            print(f"=== {entry['timestamp'][:16]} ===")
            for key, result in entry.get("results", {}).items():
                print(f"  {key}: {result.get('status', 'unknown')}")

    elif cmd == "archive":
        ARCHIVE_DIR.mkdir(exist_ok=True)
        archives = list(ARCHIVE_DIR.glob("*.bak"))
        if archives:
            print(f"Archived backups ({len(archives)}):\n")
            for f in sorted(archives)[-10:]:
                size = f.stat().st_size // 1024
                print(f"  {f.name} ({size} KB)")
        else:
            print("No archived backups")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
