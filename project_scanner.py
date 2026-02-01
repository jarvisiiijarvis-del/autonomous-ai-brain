#!/usr/bin/env python3
"""
Project Scanner - Autonomously scans codebases and generates insights
Detects patterns, tech debt, opportunities, and project health
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from collections import Counter, defaultdict

SHARED_MEMORY = Path.home() / ".claude-shared-memory"
SCANS_FILE = SHARED_MEMORY / "project_scans.json"

# Known project locations
PROJECTS = [
    Path.home() / "telegram-claude-bot",
    Path.home() / "claude-chat",
]

# File patterns to analyze
CODE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".json": "config",
    ".md": "docs",
    ".sh": "shell",
}

# Patterns that indicate tech debt or issues
DEBT_PATTERNS = {
    "TODO": "todo_comment",
    "FIXME": "fixme_comment",
    "HACK": "hack_comment",
    "XXX": "xxx_comment",
    "DEPRECATED": "deprecated",
    "# type: ignore": "type_ignore",
    "pylint: disable": "linter_disable",
    "eslint-disable": "linter_disable",
    "noqa": "linter_skip",
}


def load_scans():
    try:
        with open(SCANS_FILE) as f:
            return json.load(f)
    except:
        return {"scans": [], "updated": None}


def save_scans(data):
    data["updated"] = datetime.now().isoformat()
    with open(SCANS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_git_stats(project_path):
    """Get git statistics for a project"""
    stats = {}

    try:
        # Last commit
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H|%s|%ai"],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split("|")
            stats["last_commit"] = {
                "hash": parts[0][:8],
                "message": parts[1][:50],
                "date": parts[2][:10]
            }

        # Uncommitted changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            changes = result.stdout.strip().split('\n')
            stats["uncommitted"] = len([c for c in changes if c.strip()])

        # Branch info
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            stats["branch"] = result.stdout.strip()

        # Commit count (last 30 days)
        result = subprocess.run(
            ["git", "rev-list", "--count", "--since=30 days ago", "HEAD"],
            cwd=project_path, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            stats["commits_30d"] = int(result.stdout.strip() or 0)

    except Exception as e:
        stats["error"] = str(e)

    return stats


def scan_files(project_path):
    """Scan files in a project"""
    file_stats = {
        "total_files": 0,
        "by_type": Counter(),
        "lines_of_code": 0,
        "largest_files": [],
    }

    all_files = []

    for root, dirs, files in os.walk(project_path):
        # Skip hidden and common ignore directories
        dirs[:] = [d for d in dirs if not d.startswith('.')
                   and d not in ['node_modules', '__pycache__', 'venv', 'dist', 'build']]

        for filename in files:
            if filename.startswith('.'):
                continue

            filepath = Path(root) / filename
            ext = filepath.suffix.lower()

            if ext in CODE_EXTENSIONS:
                file_stats["total_files"] += 1
                file_stats["by_type"][CODE_EXTENSIONS[ext]] += 1

                try:
                    size = filepath.stat().st_size
                    with open(filepath, 'r', errors='ignore') as f:
                        lines = len(f.readlines())
                    file_stats["lines_of_code"] += lines
                    all_files.append({
                        "path": str(filepath.relative_to(project_path)),
                        "lines": lines,
                        "size": size
                    })
                except:
                    pass

    # Get largest files
    all_files.sort(key=lambda x: x["lines"], reverse=True)
    file_stats["largest_files"] = all_files[:5]
    file_stats["by_type"] = dict(file_stats["by_type"])

    return file_stats


def find_tech_debt(project_path):
    """Find tech debt indicators in code"""
    debt = defaultdict(list)

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')
                   and d not in ['node_modules', '__pycache__', 'venv', 'dist', 'build']]

        for filename in files:
            filepath = Path(root) / filename
            ext = filepath.suffix.lower()

            if ext not in CODE_EXTENSIONS:
                continue

            try:
                with open(filepath, 'r', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        for pattern, debt_type in DEBT_PATTERNS.items():
                            if pattern in line:
                                debt[debt_type].append({
                                    "file": str(filepath.relative_to(project_path)),
                                    "line": line_num,
                                    "text": line.strip()[:80]
                                })
            except:
                pass

    return dict(debt)


def analyze_dependencies(project_path):
    """Analyze project dependencies"""
    deps = {"python": [], "node": []}

    # Check requirements.txt
    req_file = project_path / "requirements.txt"
    if req_file.exists():
        try:
            with open(req_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        deps["python"].append(line.split('==')[0].split('>=')[0])
        except:
            pass

    # Check package.json
    pkg_file = project_path / "package.json"
    if pkg_file.exists():
        try:
            with open(pkg_file) as f:
                pkg = json.load(f)
            deps["node"] = list(pkg.get("dependencies", {}).keys())
        except:
            pass

    return deps


def generate_health_score(scan_result):
    """Generate a health score (0-100) for the project"""
    score = 100

    # Deduct for uncommitted changes
    uncommitted = scan_result.get("git", {}).get("uncommitted", 0)
    if uncommitted > 10:
        score -= 15
    elif uncommitted > 5:
        score -= 10
    elif uncommitted > 0:
        score -= 5

    # Deduct for tech debt
    debt = scan_result.get("tech_debt", {})
    total_debt = sum(len(items) for items in debt.values())
    if total_debt > 50:
        score -= 20
    elif total_debt > 20:
        score -= 10
    elif total_debt > 5:
        score -= 5

    # Deduct for no recent commits
    commits_30d = scan_result.get("git", {}).get("commits_30d", 0)
    if commits_30d == 0:
        score -= 10

    # Bonus for docs
    by_type = scan_result.get("files", {}).get("by_type", {})
    if by_type.get("docs", 0) > 0:
        score = min(100, score + 5)

    return max(0, score)


def scan_project(project_path):
    """Full scan of a single project"""
    if not project_path.exists():
        return {"error": "Project not found"}

    scan = {
        "project": project_path.name,
        "path": str(project_path),
        "scanned_at": datetime.now().isoformat(),
        "git": get_git_stats(project_path),
        "files": scan_files(project_path),
        "tech_debt": find_tech_debt(project_path),
        "dependencies": analyze_dependencies(project_path),
    }

    scan["health_score"] = generate_health_score(scan)

    return scan


def scan_all_projects():
    """Scan all known projects"""
    results = []

    for project in PROJECTS:
        if project.exists():
            scan = scan_project(project)
            results.append(scan)

    # Save scans
    scans = load_scans()
    scans["scans"] = results
    save_scans(scans)

    return results


def get_summary():
    """Get summary of all project scans"""
    scans = load_scans()

    if not scans.get("scans"):
        return "No scans available. Run: python3 project_scanner.py scan"

    summary = []
    for scan in scans["scans"]:
        health = scan.get("health_score", 0)
        health_emoji = "🟢" if health >= 80 else "🟡" if health >= 60 else "🔴"

        summary.append(f"{health_emoji} {scan['project']} (Health: {health}%)")
        summary.append(f"   Files: {scan['files']['total_files']}, "
                      f"LOC: {scan['files']['lines_of_code']}")

        uncommitted = scan.get("git", {}).get("uncommitted", 0)
        if uncommitted > 0:
            summary.append(f"   ⚠️ {uncommitted} uncommitted changes")

        debt = scan.get("tech_debt", {})
        total_debt = sum(len(items) for items in debt.values())
        if total_debt > 0:
            summary.append(f"   📝 {total_debt} tech debt items")

    return "\n".join(summary)


def main():
    import sys

    if len(sys.argv) < 2:
        print("Project Scanner - Analyze codebases for insights")
        print("")
        print("Usage:")
        print("  python3 project_scanner.py scan              - Scan all projects")
        print("  python3 project_scanner.py scan <path>       - Scan specific project")
        print("  python3 project_scanner.py summary           - Show summary")
        print("  python3 project_scanner.py debt              - Show tech debt")
        print("  python3 project_scanner.py health            - Show health scores")
        return

    cmd = sys.argv[1]

    if cmd == "scan":
        if len(sys.argv) > 2:
            path = Path(sys.argv[2]).expanduser()
            result = scan_project(path)
            print(json.dumps(result, indent=2, default=str))
        else:
            results = scan_all_projects()
            print(f"Scanned {len(results)} projects")
            print(get_summary())

    elif cmd == "summary":
        print(get_summary())

    elif cmd == "debt":
        scans = load_scans()
        for scan in scans.get("scans", []):
            print(f"\n=== {scan['project']} ===")
            debt = scan.get("tech_debt", {})
            for debt_type, items in debt.items():
                if items:
                    print(f"\n{debt_type} ({len(items)}):")
                    for item in items[:5]:
                        print(f"  {item['file']}:{item['line']}")

    elif cmd == "health":
        scans = load_scans()
        for scan in scans.get("scans", []):
            health = scan.get("health_score", 0)
            bar = "█" * (health // 10) + "░" * (10 - health // 10)
            print(f"{scan['project']}: [{bar}] {health}%")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
