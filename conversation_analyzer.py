#!/usr/bin/env python3
"""
Conversation Analyzer - Analyzes conversation patterns and extracts insights
Looks for recurring themes, questions, productivity patterns, and learning opportunities
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter

SHARED_MEMORY = Path.home() / ".claude-shared-memory"
HISTORY_FILE = SHARED_MEMORY / "history.json"
INSIGHTS_FILE = SHARED_MEMORY / "conversation_insights.json"


def load_history():
    try:
        with open(HISTORY_FILE) as f:
            return json.load(f)
    except:
        return {"conversations": []}


def load_insights():
    try:
        with open(INSIGHTS_FILE) as f:
            return json.load(f)
    except:
        return {"insights": [], "patterns": {}, "updated": None}


def save_insights(data):
    data["updated"] = datetime.now().isoformat()
    with open(INSIGHTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def extract_topics(text):
    """Extract key topics from text"""
    # Simple keyword extraction
    keywords = []
    patterns = {
        "coding": r"\b(code|coding|programming|function|class|bug|fix|feature|api|database|python|javascript|typescript)\b",
        "security": r"\b(security|password|token|key|encrypt|auth|permission|credential)\b",
        "automation": r"\b(automat|schedule|cron|launchd|service|daemon|background)\b",
        "ai": r"\b(claude|ai|gpt|llm|model|prompt|completion|chat)\b",
        "learning": r"\b(learn|study|research|understand|explore|discover)\b",
        "productivity": r"\b(task|todo|goal|plan|organize|manage|track)\b",
    }

    text_lower = text.lower()
    for topic, pattern in patterns.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            keywords.append(topic)

    return keywords


def analyze_time_patterns(conversations):
    """Analyze when conversations happen"""
    hour_counts = defaultdict(int)
    day_counts = defaultdict(int)

    for conv in conversations:
        if "timestamp" in conv:
            try:
                dt = datetime.fromisoformat(conv["timestamp"].replace("Z", "+00:00"))
                hour_counts[dt.hour] += 1
                day_counts[dt.strftime("%A")] += 1
            except:
                pass

    return {
        "most_active_hours": sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3],
        "most_active_days": sorted(day_counts.items(), key=lambda x: x[1], reverse=True)[:3],
    }


def analyze_topics(conversations):
    """Analyze topic distribution across conversations"""
    topic_counts = Counter()
    topic_by_date = defaultdict(list)

    for conv in conversations:
        summary = conv.get("summary", "")
        tags = conv.get("tags", [])
        date = conv.get("date", "")

        topics = extract_topics(summary) + tags
        topic_counts.update(topics)

        if date:
            topic_by_date[date].extend(topics)

    return {
        "top_topics": topic_counts.most_common(10),
        "topic_evolution": dict(topic_by_date),
    }


def find_recurring_themes(conversations, min_occurrences=2):
    """Find themes that recur across multiple conversations"""
    # Extract meaningful phrases (2-3 words)
    phrase_counts = Counter()

    for conv in conversations:
        summary = conv.get("summary", "").lower()
        words = re.findall(r'\b[a-z]+\b', summary)

        # Extract bigrams
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            if len(words[i]) > 3 and len(words[i+1]) > 3:
                phrase_counts[phrase] += 1

    recurring = [(phrase, count) for phrase, count in phrase_counts.items()
                 if count >= min_occurrences]
    recurring.sort(key=lambda x: x[1], reverse=True)

    return recurring[:20]


def detect_productivity_patterns(conversations):
    """Detect productivity-related patterns"""
    patterns = {
        "tasks_completed": 0,
        "bugs_fixed": 0,
        "features_added": 0,
        "learning_sessions": 0,
        "research_done": 0,
    }

    for conv in conversations:
        summary = conv.get("summary", "").lower()
        tags = [t.lower() for t in conv.get("tags", [])]

        if any(w in summary for w in ["completed", "finished", "done", "implemented"]):
            patterns["tasks_completed"] += 1
        if any(w in summary or w in tags for w in ["fixed", "bug", "fix", "resolved"]):
            patterns["bugs_fixed"] += 1
        if any(w in summary or w in tags for w in ["added", "feature", "new", "created"]):
            patterns["features_added"] += 1
        if any(w in summary or w in tags for w in ["learned", "learning", "study", "understand"]):
            patterns["learning_sessions"] += 1
        if any(w in summary or w in tags for w in ["research", "explore", "investigate"]):
            patterns["research_done"] += 1

    return patterns


def generate_insights(analysis):
    """Generate actionable insights from analysis"""
    insights = []

    # Time-based insights
    time_patterns = analysis.get("time_patterns", {})
    if time_patterns.get("most_active_hours"):
        peak_hour = time_patterns["most_active_hours"][0][0]
        if 9 <= peak_hour <= 12:
            insights.append("You're most productive in the morning - schedule complex tasks then")
        elif 14 <= peak_hour <= 17:
            insights.append("Afternoon is your peak time - good for focused work")
        elif peak_hour >= 20:
            insights.append("You often work late - consider whether this affects quality")

    # Topic-based insights
    topics = analysis.get("topics", {})
    top_topics = topics.get("top_topics", [])
    if top_topics:
        primary_focus = top_topics[0][0]
        insights.append(f"Your primary focus area is '{primary_focus}' - consider documenting expertise")

    # Productivity insights
    productivity = analysis.get("productivity", {})
    total_tasks = productivity.get("tasks_completed", 0)
    bugs = productivity.get("bugs_fixed", 0)
    features = productivity.get("features_added", 0)

    if total_tasks > 10:
        bug_ratio = bugs / total_tasks if total_tasks > 0 else 0
        if bug_ratio > 0.3:
            insights.append("High bug-fixing ratio - consider more upfront design or testing")
        feature_ratio = features / total_tasks if total_tasks > 0 else 0
        if feature_ratio > 0.5:
            insights.append("Strong feature development pace - good momentum!")

    # Recurring themes
    themes = analysis.get("recurring_themes", [])
    if themes:
        top_theme = themes[0][0]
        insights.append(f"Recurring focus on '{top_theme}' - might benefit from deeper documentation")

    return insights


def analyze_all():
    """Run complete conversation analysis"""
    history = load_history()
    conversations = history.get("conversations", [])

    if not conversations:
        return {"error": "No conversation history found"}

    # Run all analyses
    analysis = {
        "conversation_count": len(conversations),
        "time_patterns": analyze_time_patterns(conversations),
        "topics": analyze_topics(conversations),
        "recurring_themes": find_recurring_themes(conversations),
        "productivity": detect_productivity_patterns(conversations),
        "analyzed_at": datetime.now().isoformat(),
    }

    # Generate insights
    analysis["insights"] = generate_insights(analysis)

    # Save insights
    insights_data = load_insights()
    insights_data["patterns"] = analysis
    insights_data["insights"].extend([
        {"text": insight, "timestamp": datetime.now().isoformat()}
        for insight in analysis["insights"]
    ])
    # Keep only last 50 insights
    insights_data["insights"] = insights_data["insights"][-50:]
    save_insights(insights_data)

    return analysis


def get_summary():
    """Get a brief summary of conversation patterns"""
    history = load_history()
    conversations = history.get("conversations", [])

    if not conversations:
        return "No conversation history found"

    topics = analyze_topics(conversations)
    productivity = detect_productivity_patterns(conversations)

    summary = []
    summary.append(f"Total conversations: {len(conversations)}")

    if topics["top_topics"]:
        top = ", ".join([t[0] for t in topics["top_topics"][:3]])
        summary.append(f"Main topics: {top}")

    summary.append(f"Tasks completed: {productivity['tasks_completed']}")
    summary.append(f"Features added: {productivity['features_added']}")
    summary.append(f"Bugs fixed: {productivity['bugs_fixed']}")

    return "\n".join(summary)


def main():
    import sys

    if len(sys.argv) < 2:
        print("Conversation Analyzer - Extract insights from conversation history")
        print("")
        print("Usage:")
        print("  python3 conversation_analyzer.py analyze   - Full analysis")
        print("  python3 conversation_analyzer.py summary   - Brief summary")
        print("  python3 conversation_analyzer.py topics    - Topic analysis")
        print("  python3 conversation_analyzer.py insights  - View saved insights")
        return

    cmd = sys.argv[1]

    if cmd == "analyze":
        analysis = analyze_all()
        print(json.dumps(analysis, indent=2, default=str))

    elif cmd == "summary":
        print(get_summary())

    elif cmd == "topics":
        history = load_history()
        topics = analyze_topics(history.get("conversations", []))
        print("Top Topics:")
        for topic, count in topics["top_topics"]:
            print(f"  {topic}: {count}")

    elif cmd == "insights":
        insights = load_insights()
        print("Recent Insights:")
        for insight in insights.get("insights", [])[-10:]:
            print(f"  - {insight['text']}")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
