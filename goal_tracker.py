#!/usr/bin/env python3
"""
Goal Tracker - Track long-term goals and progress towards them
Breaks down big goals into milestones and tracks completion
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path

SHARED_MEMORY = Path.home() / ".claude-shared-memory"
GOALS_FILE = SHARED_MEMORY / "goals.json"


def load_goals():
    try:
        with open(GOALS_FILE) as f:
            return json.load(f)
    except:
        return {"goals": [], "completed": [], "updated": None}


def save_goals(data):
    data["updated"] = datetime.now().isoformat()
    with open(GOALS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def add_goal(title, description="", target_date=None, milestones=None):
    """Add a new goal with optional milestones"""
    data = load_goals()

    goal = {
        "id": f"goal_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "title": title,
        "description": description,
        "created": datetime.now().isoformat(),
        "target_date": target_date,
        "status": "active",
        "progress": 0,
        "milestones": []
    }

    if milestones:
        for i, m in enumerate(milestones):
            goal["milestones"].append({
                "id": f"m{i+1}",
                "title": m,
                "completed": False,
                "completed_date": None
            })

    data["goals"].append(goal)
    save_goals(data)
    return goal["id"]


def complete_milestone(goal_id, milestone_id):
    """Mark a milestone as complete"""
    data = load_goals()

    for goal in data["goals"]:
        if goal["id"] == goal_id:
            for milestone in goal["milestones"]:
                if milestone["id"] == milestone_id:
                    milestone["completed"] = True
                    milestone["completed_date"] = datetime.now().isoformat()

                    # Update goal progress
                    completed = sum(1 for m in goal["milestones"] if m["completed"])
                    total = len(goal["milestones"])
                    goal["progress"] = int((completed / total) * 100) if total > 0 else 0

                    # Check if goal is complete
                    if goal["progress"] == 100:
                        goal["status"] = "completed"
                        goal["completed_date"] = datetime.now().isoformat()
                        data["completed"].append(goal)
                        data["goals"].remove(goal)

                    save_goals(data)
                    return True

    return False


def update_progress(goal_id, progress):
    """Manually update goal progress (0-100)"""
    data = load_goals()

    for goal in data["goals"]:
        if goal["id"] == goal_id:
            goal["progress"] = min(100, max(0, progress))
            if goal["progress"] == 100:
                goal["status"] = "completed"
                goal["completed_date"] = datetime.now().isoformat()
            save_goals(data)
            return True

    return False


def get_active_goals():
    """Get all active goals"""
    data = load_goals()
    return [g for g in data["goals"] if g["status"] == "active"]


def get_goal_status(goal_id):
    """Get detailed status of a goal"""
    data = load_goals()

    for goal in data["goals"] + data["completed"]:
        if goal["id"] == goal_id:
            return goal

    return None


def get_overdue_goals():
    """Get goals past their target date"""
    data = load_goals()
    today = datetime.now().isoformat()[:10]
    overdue = []

    for goal in data["goals"]:
        if goal.get("target_date") and goal["target_date"] < today:
            overdue.append(goal)

    return overdue


def get_upcoming_milestones(days=7):
    """Get milestones to focus on in the next N days"""
    data = load_goals()
    upcoming = []

    for goal in data["goals"]:
        incomplete = [m for m in goal["milestones"] if not m["completed"]]
        if incomplete:
            # Return first incomplete milestone for each goal
            upcoming.append({
                "goal": goal["title"],
                "goal_id": goal["id"],
                "milestone": incomplete[0]["title"],
                "milestone_id": incomplete[0]["id"],
                "goal_progress": goal["progress"]
            })

    return upcoming


def generate_progress_report():
    """Generate a progress report"""
    data = load_goals()
    active = get_active_goals()
    overdue = get_overdue_goals()
    upcoming = get_upcoming_milestones()

    report = []
    report.append("## Goal Progress Report")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")

    report.append(f"### Summary")
    report.append(f"- Active goals: {len(active)}")
    report.append(f"- Completed goals: {len(data['completed'])}")
    report.append(f"- Overdue goals: {len(overdue)}")
    report.append("")

    if active:
        report.append("### Active Goals")
        for goal in active:
            progress_bar = "█" * (goal["progress"] // 10) + "░" * (10 - goal["progress"] // 10)
            report.append(f"- **{goal['title']}** [{progress_bar}] {goal['progress']}%")
            if goal.get("target_date"):
                report.append(f"  Target: {goal['target_date']}")
        report.append("")

    if upcoming:
        report.append("### Next Milestones")
        for item in upcoming[:5]:
            report.append(f"- [{item['goal']}] {item['milestone']}")
        report.append("")

    if overdue:
        report.append("### ⚠️ Overdue")
        for goal in overdue:
            report.append(f"- {goal['title']} (due: {goal['target_date']})")

    return "\n".join(report)


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: goal_tracker.py <command>")
        print("Commands:")
        print("  add <title> [--target YYYY-MM-DD] [--milestone M1] [--milestone M2]")
        print("  list                        - List active goals")
        print("  status <goal_id>            - Get goal status")
        print("  complete <goal_id> <m_id>   - Complete a milestone")
        print("  progress <goal_id> <0-100>  - Update progress")
        print("  report                      - Progress report")
        print("  next                        - Next milestones to work on")
        return

    cmd = sys.argv[1]

    if cmd == "add" and len(sys.argv) >= 3:
        title = sys.argv[2]
        target = None
        milestones = []

        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--target" and i + 1 < len(sys.argv):
                target = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--milestone" and i + 1 < len(sys.argv):
                milestones.append(sys.argv[i + 1])
                i += 2
            else:
                i += 1

        goal_id = add_goal(title, target_date=target, milestones=milestones)
        print(f"Added goal: {goal_id}")

    elif cmd == "list":
        goals = get_active_goals()
        if goals:
            for g in goals:
                print(f"[{g['id']}] {g['title']} - {g['progress']}%")
        else:
            print("No active goals")

    elif cmd == "status" and len(sys.argv) >= 3:
        status = get_goal_status(sys.argv[2])
        if status:
            print(json.dumps(status, indent=2))
        else:
            print("Goal not found")

    elif cmd == "complete" and len(sys.argv) >= 4:
        if complete_milestone(sys.argv[2], sys.argv[3]):
            print("Milestone completed!")
        else:
            print("Milestone not found")

    elif cmd == "progress" and len(sys.argv) >= 4:
        if update_progress(sys.argv[2], int(sys.argv[3])):
            print("Progress updated")
        else:
            print("Goal not found")

    elif cmd == "report":
        print(generate_progress_report())

    elif cmd == "next":
        upcoming = get_upcoming_milestones()
        if upcoming:
            for item in upcoming:
                print(f"[{item['goal']}] → {item['milestone']}")
        else:
            print("No upcoming milestones")

    else:
        print("Unknown command")


if __name__ == "__main__":
    main()
