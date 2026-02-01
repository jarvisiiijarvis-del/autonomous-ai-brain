#!/usr/bin/env python3
"""
Unified Brain - Central intelligence that coordinates all Claude systems
Provides a single interface to query and manage all autonomous capabilities
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Import all subsystems
BRAIN_DIR = Path(__file__).parent


def run_subsystem(script, *args):
    """Run a subsystem script and return output"""
    try:
        cmd = ["python3", str(BRAIN_DIR / script)] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


class UnifiedBrain:
    def __init__(self):
        self.shared_memory = Path.home() / ".claude-shared-memory"

    def get_status(self):
        """Get comprehensive system status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "subsystems": {},
            "health": "healthy",
            "alerts": []
        }

        # Check each subsystem
        subsystems = [
            ("orchestrator", "orchestrator.py", ["health"]),
            ("monitor", "monitor.py", []),
            ("context", "context_engine.py", ["summary"]),
            ("goals", "goal_tracker.py", ["list"]),
            ("predictor", "predictor.py", ["status"]),
            ("knowledge_graph", "knowledge_graph.py", ["stats"]),
            ("self_reflect", "self_reflect.py", ["suggestions"]),
            ("conversation_analyzer", "conversation_analyzer.py", ["summary"]),
            ("session_tracker", "session_tracker.py", ["summary"]),
            ("auto_improver", "auto_improver.py", ["stats"]),
            ("meta_cognition", "meta_cognition.py", ["status"]),
            ("project_scanner", "project_scanner.py", ["summary"]),
            ("proactive_comms", "proactive_comms.py", ["check"]),
            ("memory_consolidator", "memory_consolidator.py", ["stats"]),
            ("decision_engine", "decision_engine.py", ["status"]),
        ]

        for name, script, args in subsystems:
            if (BRAIN_DIR / script).exists():
                status["subsystems"][name] = "active"
            else:
                status["subsystems"][name] = "missing"

        return status

    def think(self, query):
        """Process a query using all available context"""
        response = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "thoughts": [],
            "suggestions": [],
            "actions": []
        }

        query_lower = query.lower()

        # Search memory for relevant context
        memory_search = run_subsystem("memory-cli.py", "search", query) if query else ""
        if memory_search and "result(s)" in memory_search:
            response["thoughts"].append(f"Found relevant memories: {memory_search[:200]}")

        # Get current context
        context = run_subsystem("context_engine.py", "suggest")
        if context:
            response["suggestions"].extend(context.split('\n'))

        # Check goals
        goals = run_subsystem("goal_tracker.py", "next")
        if goals and "→" in goals:
            response["thoughts"].append(f"Current goals: {goals[:200]}")

        # Analyze based on query
        if "status" in query_lower or "how" in query_lower:
            health = run_subsystem("orchestrator.py", "health")
            response["thoughts"].append(f"System health: {health}")

        if "goal" in query_lower:
            all_goals = run_subsystem("goal_tracker.py", "report")
            response["thoughts"].append(all_goals[:500])

        if "learn" in query_lower or "reflect" in query_lower:
            reflection = run_subsystem("self_reflect.py", "report")
            response["thoughts"].append(reflection[:500])

        if "suggest" in query_lower or "what should" in query_lower:
            predictions = run_subsystem("predictor.py", "suggest")
            if predictions:
                response["suggestions"].append(predictions)

        # Use knowledge graph for context
        if any(word in query_lower for word in ["related", "connected", "about", "context"]):
            # Extract key terms from query
            words = query_lower.split()
            for word in words:
                if len(word) > 3 and word not in ["what", "about", "related", "connected"]:
                    graph_ctx = run_subsystem("knowledge_graph.py", "context", word)
                    if graph_ctx and "Context for" in graph_ctx:
                        response["thoughts"].append(f"Knowledge graph: {graph_ctx[:400]}")
                    break

        return response

    def daily_briefing(self):
        """Generate a comprehensive daily briefing"""
        briefing = []
        briefing.append("# Daily Intelligence Briefing")
        briefing.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        briefing.append("")

        # System status
        briefing.append("## System Status")
        health = run_subsystem("orchestrator.py", "health")
        briefing.append(health or "All systems operational")
        briefing.append("")

        # Context
        briefing.append("## Current Context")
        context = run_subsystem("context_engine.py", "time")
        briefing.append(context or "No context available")
        briefing.append("")

        # Goals
        briefing.append("## Goals Progress")
        goals = run_subsystem("goal_tracker.py", "report")
        briefing.append(goals or "No active goals")
        briefing.append("")

        # Self-reflection
        briefing.append("## Performance Insights")
        reflection = run_subsystem("self_reflect.py", "analyze")
        briefing.append(reflection or "No insights available")
        briefing.append("")

        # Predictions
        briefing.append("## Suggested Focus")
        predictions = run_subsystem("predictor.py", "suggest")
        briefing.append(predictions or "No predictions available")
        briefing.append("")

        # Reminders
        briefing.append("## Reminders")
        reminders = run_subsystem("memory-cli.py", "reminders")
        briefing.append(reminders or "No reminders")
        briefing.append("")

        # Session Analysis
        briefing.append("## Session Patterns")
        session = run_subsystem("session_tracker.py", "summary")
        briefing.append(session or "No session data")
        briefing.append("")

        # Conversation Insights
        briefing.append("## Conversation Insights")
        insights = run_subsystem("conversation_analyzer.py", "insights")
        briefing.append(insights or "No insights available")

        return "\n".join(briefing)

    def execute(self, action, *args):
        """Execute an action through the appropriate subsystem"""
        actions = {
            "remind": ("memory-cli.py", ["add-reminder"] + list(args)),
            "goal": ("goal_tracker.py", ["add"] + list(args)),
            "reflect": ("self_reflect.py", ["insight"] + list(args)),
            "search": ("memory-cli.py", ["search"] + list(args)),
            "health": ("orchestrator.py", ["health"]),
            "learn": ("auto_learner.py", []),
            "scan": ("proactive_agent.py", []),
            "graph": ("knowledge_graph.py", ["build"]),
            "related": ("knowledge_graph.py", ["query"] + list(args)),
            "context": ("knowledge_graph.py", ["context"] + list(args)),
            "suggest": ("predictor.py", ["suggest"]),
            "success": ("self_reflect.py", ["success"] + list(args)),
            "failure": ("self_reflect.py", ["failure"] + list(args)),
            "analyze": ("conversation_analyzer.py", ["analyze"]),
            "topics": ("conversation_analyzer.py", ["topics"]),
            "session": ("session_tracker.py", ["track"]),
            "digest": ("nightly_digest.py", ["preview"]),
            "improve": ("auto_improver.py", ["analyze"]),
            "improvements": ("auto_improver.py", ["list"]),
            "meta": ("meta_cognition.py", ["report"]),
            "brain": ("meta_cognition.py", ["status"]),
            "projects": ("project_scanner.py", ["scan"]),
            "debt": ("project_scanner.py", ["debt"]),
            "notify": ("proactive_comms.py", ["notify"]),
            "consolidate": ("memory_consolidator.py", ["consolidate"]),
            "memory": ("memory_consolidator.py", ["stats"]),
            "decide": ("decision_engine.py", ["run"]),
            "decisions": ("decision_engine.py", ["status"]),
        }

        if action in actions:
            script, cmd_args = actions[action]
            return run_subsystem(script, *cmd_args)
        else:
            return f"Unknown action: {action}. Available: {', '.join(actions.keys())}"


def main():
    import sys

    brain = UnifiedBrain()

    if len(sys.argv) < 2:
        print("Unified Brain - Central Intelligence Coordinator")
        print("")
        print("Usage: unified_brain.py <command>")
        print("")
        print("Commands:")
        print("  status              - Get system status")
        print("  briefing            - Daily intelligence briefing")
        print("  think <query>       - Process a query with full context")
        print("  do <action> [args]  - Execute an action")
        print("")
        print("Actions: remind, goal, reflect, search, health, learn, scan,")
        print("         graph, related, context, suggest, success, failure,")
        print("         analyze, topics, session, digest, improve, meta, brain")
        return

    cmd = sys.argv[1]

    if cmd == "status":
        status = brain.get_status()
        print(json.dumps(status, indent=2))

    elif cmd == "briefing":
        print(brain.daily_briefing())

    elif cmd == "think" and len(sys.argv) >= 3:
        query = " ".join(sys.argv[2:])
        result = brain.think(query)
        print(json.dumps(result, indent=2))

    elif cmd == "do" and len(sys.argv) >= 3:
        action = sys.argv[2]
        args = sys.argv[3:] if len(sys.argv) > 3 else []
        result = brain.execute(action, *args)
        print(result)

    else:
        print("Unknown command or missing arguments")


if __name__ == "__main__":
    main()
