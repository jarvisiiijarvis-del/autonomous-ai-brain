#!/usr/bin/env python3
"""
Meta-Cognition System - The brain that watches the brain
Monitors system-wide performance, detects anomalies, and ensures coherent operation
"""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

BRAIN_DIR = Path(__file__).parent
SHARED_MEMORY = Path.home() / ".claude-shared-memory"
META_FILE = SHARED_MEMORY / "meta_cognition.json"

# All subsystems to monitor
SUBSYSTEMS = [
    ("orchestrator.py", "health"),
    ("monitor.py", "status"),
    ("context_engine.py", "summary"),
    ("goal_tracker.py", "list"),
    ("predictor.py", "status"),
    ("knowledge_graph.py", "stats"),
    ("self_reflect.py", "suggestions"),
    ("conversation_analyzer.py", "summary"),
    ("session_tracker.py", "summary"),
    ("auto_improver.py", "stats"),
]


def load_meta():
    try:
        with open(META_FILE) as f:
            return json.load(f)
    except:
        return {
            "health_history": [],
            "anomalies": [],
            "coherence_score": 100,
            "last_check": None
        }


def save_meta(data):
    data["last_check"] = datetime.now().isoformat()
    with open(META_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def run_subsystem(script, *args):
    """Run a subsystem and measure response"""
    start = datetime.now()
    try:
        cmd = ["python3", str(BRAIN_DIR / script)] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        elapsed = (datetime.now() - start).total_seconds()
        return {
            "success": result.returncode == 0,
            "output_length": len(result.stdout),
            "elapsed": elapsed,
            "error": result.stderr[:200] if result.returncode != 0 else None
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout", "elapsed": 10}
    except Exception as e:
        return {"success": False, "error": str(e), "elapsed": 0}


def check_all_subsystems():
    """Run health check on all subsystems"""
    results = {}

    for script, cmd in SUBSYSTEMS:
        name = script.replace(".py", "")
        if (BRAIN_DIR / script).exists():
            results[name] = run_subsystem(script, cmd)
        else:
            results[name] = {"success": False, "error": "missing"}

    return results


def calculate_health_score(results):
    """Calculate overall system health score (0-100)"""
    if not results:
        return 0

    scores = []
    for name, result in results.items():
        if result.get("success"):
            # Base score
            score = 100

            # Penalize slow responses
            elapsed = result.get("elapsed", 0)
            if elapsed > 5:
                score -= 20
            elif elapsed > 2:
                score -= 10

            # Reward output (indicates working system)
            if result.get("output_length", 0) > 0:
                score += 0  # Already at 100

            scores.append(score)
        else:
            scores.append(0)

    return sum(scores) // len(scores) if scores else 0


def detect_anomalies(results, meta):
    """Detect anomalies in system behavior"""
    anomalies = []

    # Check for newly failed subsystems
    for name, result in results.items():
        if not result.get("success"):
            anomalies.append({
                "type": "subsystem_failure",
                "subsystem": name,
                "error": result.get("error", "unknown"),
                "timestamp": datetime.now().isoformat()
            })

    # Check for performance degradation
    history = meta.get("health_history", [])
    if len(history) >= 3:
        recent_scores = [h["score"] for h in history[-3:]]
        current = calculate_health_score(results)

        if all(s > current + 20 for s in recent_scores):
            anomalies.append({
                "type": "performance_degradation",
                "current": current,
                "previous_avg": sum(recent_scores) // len(recent_scores),
                "timestamp": datetime.now().isoformat()
            })

    return anomalies


def check_coherence():
    """Check if subsystems are working coherently"""
    coherence_issues = []

    # Check if knowledge graph is in sync
    graph_path = SHARED_MEMORY / "graph.json"
    history_path = SHARED_MEMORY / "history.json"

    if graph_path.exists() and history_path.exists():
        graph_mtime = graph_path.stat().st_mtime
        history_mtime = history_path.stat().st_mtime

        # If history is much newer than graph, they're out of sync
        if history_mtime > graph_mtime + 86400:  # 24 hours
            coherence_issues.append(
                "Knowledge graph is out of date - run 'unified_brain.py do graph'"
            )

    # Check if metrics are being tracked
    metrics_path = SHARED_MEMORY / "metrics.json"
    if metrics_path.exists():
        metrics_mtime = metrics_path.stat().st_mtime
        if datetime.now().timestamp() - metrics_mtime > 86400 * 7:
            coherence_issues.append(
                "Metrics haven't been updated in 7+ days"
            )

    return coherence_issues


def generate_meta_report():
    """Generate comprehensive meta-cognition report"""
    meta = load_meta()

    # Check all subsystems
    results = check_all_subsystems()
    health_score = calculate_health_score(results)
    anomalies = detect_anomalies(results, meta)
    coherence_issues = check_coherence()

    # Update history
    meta["health_history"].append({
        "timestamp": datetime.now().isoformat(),
        "score": health_score,
        "subsystems_active": sum(1 for r in results.values() if r.get("success")),
        "subsystems_total": len(results)
    })
    meta["health_history"] = meta["health_history"][-100:]  # Keep last 100

    # Record anomalies
    meta["anomalies"].extend(anomalies)
    meta["anomalies"] = meta["anomalies"][-50:]

    # Calculate coherence
    meta["coherence_score"] = 100 - (len(coherence_issues) * 10)

    save_meta(meta)

    # Build report
    report = {
        "timestamp": datetime.now().isoformat(),
        "health_score": health_score,
        "coherence_score": meta["coherence_score"],
        "subsystems": {
            "active": sum(1 for r in results.values() if r.get("success")),
            "total": len(results),
            "details": results
        },
        "anomalies": anomalies,
        "coherence_issues": coherence_issues,
        "recommendations": []
    }

    # Generate recommendations
    if health_score < 80:
        failed = [n for n, r in results.items() if not r.get("success")]
        report["recommendations"].append(
            f"Review failed subsystems: {', '.join(failed)}"
        )

    if coherence_issues:
        report["recommendations"].extend(coherence_issues)

    if anomalies:
        report["recommendations"].append(
            f"Investigate {len(anomalies)} detected anomalies"
        )

    return report


def get_quick_status():
    """Get quick system status"""
    meta = load_meta()
    results = check_all_subsystems()
    health = calculate_health_score(results)

    active = sum(1 for r in results.values() if r.get("success"))
    total = len(results)

    status = []
    status.append(f"Health Score: {health}/100")
    status.append(f"Subsystems: {active}/{total} active")
    status.append(f"Coherence: {meta.get('coherence_score', 100)}%")

    # Show any failures
    failed = [n for n, r in results.items() if not r.get("success")]
    if failed:
        status.append(f"Failed: {', '.join(failed)}")

    return "\n".join(status)


def main():
    import sys

    if len(sys.argv) < 2:
        print("Meta-Cognition System - Brain monitoring")
        print("")
        print("Usage:")
        print("  python3 meta_cognition.py report   - Full meta-cognition report")
        print("  python3 meta_cognition.py status   - Quick status check")
        print("  python3 meta_cognition.py history  - Show health history")
        print("  python3 meta_cognition.py anomaly  - Show recent anomalies")
        return

    cmd = sys.argv[1]

    if cmd == "report":
        report = generate_meta_report()
        print(json.dumps(report, indent=2))

    elif cmd == "status":
        print(get_quick_status())

    elif cmd == "history":
        meta = load_meta()
        history = meta.get("health_history", [])[-10:]
        for h in history:
            ts = h.get("timestamp", "")[:19]
            score = h.get("score", 0)
            active = h.get("subsystems_active", 0)
            total = h.get("subsystems_total", 0)
            print(f"{ts} | Score: {score} | Active: {active}/{total}")

    elif cmd == "anomaly":
        meta = load_meta()
        anomalies = meta.get("anomalies", [])[-10:]
        if anomalies:
            for a in anomalies:
                print(f"[{a.get('type')}] {a.get('timestamp', '')[:19]}")
                if a.get("subsystem"):
                    print(f"  Subsystem: {a['subsystem']}")
                if a.get("error"):
                    print(f"  Error: {a['error'][:80]}")
                print()
        else:
            print("No anomalies recorded")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
