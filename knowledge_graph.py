#!/usr/bin/env python3
"""
Knowledge Graph Builder for Shared Memory System

Builds connections between concepts extracted from shared memory files.
Uses simple keyword/co-occurrence based linking (no ML required).

Usage:
    python3 knowledge_graph.py build          # Build/rebuild the graph
    python3 knowledge_graph.py query <entity> # Find related concepts
    python3 knowledge_graph.py suggest        # Find potential connections
    python3 knowledge_graph.py context <topic> # Get all context about a topic
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Paths
SHARED_MEMORY_DIR = Path.home() / ".claude-shared-memory"
GRAPH_PATH = SHARED_MEMORY_DIR / "graph.json"

# Entity extraction patterns
ENTITY_PATTERNS = {
    "project": r"\b(telegram-claude-bot|claude-chat|second-brain-data|moltbook)\b",
    "tool": r"\b(python|electron|typescript|sqlite|launchd|npm|git|docker|api)\b",
    "concept": r"\b(memory|security|automation|voice|streaming|encryption|bot|chat|ai|claude|agent|monitor|orchestrator)\b",
    "date": r"\b(\d{4}-\d{2}-\d{2})\b",
    "person": r"\b(User|longshot77|shredbot)\b",
    "feature": r"\b(reminder|surprise|speech|text-to-speech|voice-input|voice-output)\b",
    "service": r"\b(telegram|anthropic|moltbook)\b",
}

# Stop words to exclude from keyword extraction
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "each", "few",
    "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just",
    "and", "but", "if", "or", "because", "as", "until", "while",
    "this", "that", "these", "those", "it", "its", "i", "my", "me",
    "we", "our", "you", "your", "he", "him", "his", "she", "her",
    "they", "them", "their", "what", "which", "who", "whom",
    "using", "uses", "used", "via", "enabled", "set", "up", "now",
    "also", "both", "about", "across", "new", "added", "built",
    "fixed", "created", "updated", "working", "runs", "active",
}


class KnowledgeGraph:
    """Simple knowledge graph using adjacency list representation."""

    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}  # entity -> metadata
        self.edges: Dict[str, Dict[str, float]] = defaultdict(dict)  # entity -> {related: weight}
        self.entity_sources: Dict[str, List[str]] = defaultdict(list)  # entity -> [source files]
        self.updated: str = ""

    def load_shared_memory(self) -> Dict[str, Any]:
        """Load all shared memory files."""
        data = {}
        files = ["context.json", "history.json", "projects.json", "reminders.json"]

        for filename in files:
            filepath = SHARED_MEMORY_DIR / filename
            if filepath.exists():
                try:
                    with open(filepath, "r") as f:
                        data[filename] = json.load(f)
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse {filename}")
                    data[filename] = {}
            else:
                data[filename] = {}

        return data

    def extract_entities(self, text: str, source: str) -> List[Tuple[str, str]]:
        """Extract entities from text using patterns."""
        entities = []
        text_lower = text.lower()

        for entity_type, pattern in ENTITY_PATTERNS.items():
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                entity = match.lower().strip()
                if entity:
                    entities.append((entity, entity_type))
                    if source not in self.entity_sources[entity]:
                        self.entity_sources[entity].append(source)

        return entities

    def extract_keywords(self, text: str, source: str) -> List[Tuple[str, str]]:
        """Extract meaningful keywords from text."""
        keywords = []
        # Extract words that might be meaningful
        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]{2,}\b", text.lower())

        for word in words:
            if word not in STOP_WORDS and len(word) > 2:
                keywords.append((word, "keyword"))
                if source not in self.entity_sources[word]:
                    self.entity_sources[word].append(source)

        return keywords

    def add_node(self, entity: str, entity_type: str, metadata: Optional[Dict] = None):
        """Add a node to the graph."""
        if entity not in self.nodes:
            self.nodes[entity] = {
                "type": entity_type,
                "metadata": metadata or {},
                "first_seen": datetime.now().isoformat(),
            }
        elif metadata:
            self.nodes[entity]["metadata"].update(metadata)

    def add_edge(self, entity1: str, entity2: str, weight: float = 1.0):
        """Add or strengthen an edge between two entities."""
        if entity1 != entity2:
            current_weight = self.edges[entity1].get(entity2, 0)
            self.edges[entity1][entity2] = current_weight + weight
            self.edges[entity2][entity1] = current_weight + weight

    def build_from_context(self, context_data: dict, source: str = "context.json"):
        """Build graph from context.json data."""
        # Extract from user preferences
        if "user" in context_data:
            user = context_data["user"]
            if "preferences" in user:
                for pref in user["preferences"]:
                    entities = self.extract_entities(pref, source)
                    keywords = self.extract_keywords(pref, source)
                    all_items = entities + keywords

                    for entity, etype in all_items:
                        self.add_node(entity, etype)

                    # Connect co-occurring entities
                    for i, (e1, _) in enumerate(all_items):
                        for e2, _ in all_items[i + 1:]:
                            self.add_edge(e1, e2, 0.5)

        # Extract from facts
        if "facts" in context_data:
            for fact in context_data["facts"]:
                entities = self.extract_entities(fact, source)
                keywords = self.extract_keywords(fact, source)
                all_items = entities + keywords

                for entity, etype in all_items:
                    self.add_node(entity, etype)

                for i, (e1, _) in enumerate(all_items):
                    for e2, _ in all_items[i + 1:]:
                        self.add_edge(e1, e2, 1.0)

    def build_from_history(self, history_data: dict, source: str = "history.json"):
        """Build graph from history.json data."""
        if "conversations" not in history_data:
            return

        for conv in history_data["conversations"]:
            summary = conv.get("summary", "")
            tags = conv.get("tags", [])
            date = conv.get("date", "")

            # Extract entities from summary
            entities = self.extract_entities(summary, source)
            keywords = self.extract_keywords(summary, source)

            # Add tags as entities
            for tag in tags:
                entities.append((tag.lower(), "tag"))
                if source not in self.entity_sources[tag.lower()]:
                    self.entity_sources[tag.lower()].append(source)

            all_items = entities + keywords

            for entity, etype in all_items:
                self.add_node(entity, etype, {"date": date} if date else None)

            # Strongly connect items in same conversation
            for i, (e1, _) in enumerate(all_items):
                for e2, _ in all_items[i + 1:]:
                    self.add_edge(e1, e2, 1.5)

            # Connect tags to all entities in the summary
            for tag in tags:
                for entity, _ in entities + keywords:
                    if tag.lower() != entity:
                        self.add_edge(tag.lower(), entity, 2.0)

    def build_from_projects(self, projects_data: dict, source: str = "projects.json"):
        """Build graph from projects.json data."""
        if "projects" not in projects_data:
            return

        for project_name, project_info in projects_data["projects"].items():
            project_name_lower = project_name.lower()
            self.add_node(project_name_lower, "project", {
                "path": project_info.get("path"),
                "status": project_info.get("status"),
            })

            # Extract from description
            desc = project_info.get("description", "")
            entities = self.extract_entities(desc, source)
            keywords = self.extract_keywords(desc, source)

            for entity, etype in entities + keywords:
                self.add_node(entity, etype)
                self.add_edge(project_name_lower, entity, 2.0)

            # Extract from notes
            for note in project_info.get("notes", []):
                note_entities = self.extract_entities(note, source)
                note_keywords = self.extract_keywords(note, source)

                for entity, etype in note_entities + note_keywords:
                    self.add_node(entity, etype)
                    self.add_edge(project_name_lower, entity, 1.5)

    def build_from_reminders(self, reminders_data: dict, source: str = "reminders.json"):
        """Build graph from reminders.json data."""
        if "reminders" not in reminders_data:
            return

        for reminder in reminders_data["reminders"]:
            text = reminder.get("text", "")
            date = reminder.get("date", "")

            entities = self.extract_entities(text, source)
            keywords = self.extract_keywords(text, source)
            all_items = entities + keywords

            for entity, etype in all_items:
                self.add_node(entity, etype, {"reminder_date": date} if date else None)

            for i, (e1, _) in enumerate(all_items):
                for e2, _ in all_items[i + 1:]:
                    self.add_edge(e1, e2, 1.0)

    def build(self):
        """Build the complete knowledge graph from all sources."""
        print("Loading shared memory files...")
        data = self.load_shared_memory()

        print("Building graph from context.json...")
        self.build_from_context(data.get("context.json", {}))

        print("Building graph from history.json...")
        self.build_from_history(data.get("history.json", {}))

        print("Building graph from projects.json...")
        self.build_from_projects(data.get("projects.json", {}))

        print("Building graph from reminders.json...")
        self.build_from_reminders(data.get("reminders.json", {}))

        self.updated = datetime.now().isoformat()
        self.save()

        print(f"\nGraph built successfully!")
        print(f"  Nodes: {len(self.nodes)}")
        print(f"  Edges: {sum(len(e) for e in self.edges.values()) // 2}")
        print(f"  Saved to: {GRAPH_PATH}")

    def save(self):
        """Save graph to JSON file."""
        graph_data = {
            "nodes": self.nodes,
            "edges": {k: dict(v) for k, v in self.edges.items()},
            "sources": dict(self.entity_sources),
            "updated": self.updated,
        }

        SHARED_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        with open(GRAPH_PATH, "w") as f:
            json.dump(graph_data, f, indent=2)

        # Set secure permissions
        os.chmod(GRAPH_PATH, 0o600)

    def load(self) -> bool:
        """Load graph from JSON file."""
        if not GRAPH_PATH.exists():
            return False

        try:
            with open(GRAPH_PATH, "r") as f:
                data = json.load(f)

            self.nodes = data.get("nodes", {})
            self.edges = defaultdict(dict, {k: v for k, v in data.get("edges", {}).items()})
            self.entity_sources = defaultdict(list, data.get("sources", {}))
            self.updated = data.get("updated", "")
            return True
        except (json.JSONDecodeError, KeyError):
            return False

    def get_related(self, entity: str, limit: int = 10) -> List[Tuple[str, float, str]]:
        """
        Find entities related to the given entity.

        Returns list of (entity, weight, type) tuples sorted by weight.
        """
        entity = entity.lower()

        if entity not in self.edges:
            # Try partial match
            matches = [e for e in self.edges if entity in e or e in entity]
            if matches:
                entity = matches[0]
            else:
                return []

        related = []
        for related_entity, weight in self.edges[entity].items():
            entity_type = self.nodes.get(related_entity, {}).get("type", "unknown")
            related.append((related_entity, weight, entity_type))

        related.sort(key=lambda x: x[1], reverse=True)
        return related[:limit]

    def get_context(self, topic: str) -> Dict[str, Any]:
        """
        Get all context about a topic, including related entities and sources.
        """
        topic = topic.lower()
        context = {
            "topic": topic,
            "found": False,
            "node_info": None,
            "related": [],
            "sources": [],
            "connected_topics": [],
        }

        # Direct match or partial match
        if topic in self.nodes:
            context["found"] = True
            context["node_info"] = self.nodes[topic]
            context["sources"] = self.entity_sources.get(topic, [])
        else:
            # Try partial match
            for node in self.nodes:
                if topic in node or node in topic:
                    context["found"] = True
                    context["node_info"] = self.nodes[node]
                    context["sources"] = self.entity_sources.get(node, [])
                    context["topic"] = node
                    break

        if context["found"]:
            # Get related entities
            related = self.get_related(context["topic"], limit=15)
            context["related"] = [
                {"entity": e, "weight": w, "type": t}
                for e, w, t in related
            ]

            # Find second-degree connections (topics connected to related topics)
            connected = set()
            for related_entity, _, _ in related[:5]:
                for second_entity, weight in self.edges.get(related_entity, {}).items():
                    if second_entity != context["topic"] and second_entity not in [r["entity"] for r in context["related"]]:
                        connected.add((second_entity, weight * 0.5))

            context["connected_topics"] = sorted(
                [{"entity": e, "weight": w} for e, w in connected],
                key=lambda x: x["weight"],
                reverse=True
            )[:10]

        return context

    def suggest_connections(self, min_common: int = 2) -> List[Dict[str, Any]]:
        """
        Find potentially related but unlinked items based on shared connections.
        """
        suggestions = []
        nodes_list = list(self.nodes.keys())

        for i, node1 in enumerate(nodes_list):
            neighbors1 = set(self.edges.get(node1, {}).keys())

            for node2 in nodes_list[i + 1:]:
                # Skip if already connected
                if node2 in neighbors1:
                    continue

                neighbors2 = set(self.edges.get(node2, {}).keys())
                common = neighbors1 & neighbors2

                if len(common) >= min_common:
                    suggestions.append({
                        "entity1": node1,
                        "entity2": node2,
                        "type1": self.nodes[node1].get("type", "unknown"),
                        "type2": self.nodes[node2].get("type", "unknown"),
                        "common_connections": list(common),
                        "strength": len(common),
                    })

        suggestions.sort(key=lambda x: x["strength"], reverse=True)
        return suggestions[:20]

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        type_counts = defaultdict(int)
        for node_info in self.nodes.values():
            type_counts[node_info.get("type", "unknown")] += 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": sum(len(e) for e in self.edges.values()) // 2,
            "nodes_by_type": dict(type_counts),
            "updated": self.updated,
        }


def print_related(graph: KnowledgeGraph, entity: str):
    """Print related entities in a formatted way."""
    related = graph.get_related(entity)

    if not related:
        print(f"No entities found related to '{entity}'")
        print("Try one of these entities:", ", ".join(list(graph.nodes.keys())[:10]))
        return

    print(f"\nEntities related to '{entity}':")
    print("-" * 50)

    for rel_entity, weight, etype in related:
        print(f"  {rel_entity:<25} (weight: {weight:.1f}, type: {etype})")


def print_context(graph: KnowledgeGraph, topic: str):
    """Print full context about a topic."""
    context = graph.get_context(topic)

    if not context["found"]:
        print(f"No information found about '{topic}'")
        print("Available topics:", ", ".join(list(graph.nodes.keys())[:15]))
        return

    print(f"\n=== Context for '{context['topic']}' ===\n")

    if context["node_info"]:
        print(f"Type: {context['node_info'].get('type', 'unknown')}")
        if context["node_info"].get("metadata"):
            print(f"Metadata: {json.dumps(context['node_info']['metadata'], indent=2)}")

    if context["sources"]:
        print(f"\nFound in: {', '.join(context['sources'])}")

    if context["related"]:
        print(f"\nDirectly related ({len(context['related'])} items):")
        for item in context["related"]:
            print(f"  - {item['entity']} ({item['type']}, weight: {item['weight']:.1f})")

    if context["connected_topics"]:
        print(f"\nSecond-degree connections ({len(context['connected_topics'])} items):")
        for item in context["connected_topics"][:5]:
            print(f"  - {item['entity']} (inferred weight: {item['weight']:.1f})")


def print_suggestions(graph: KnowledgeGraph):
    """Print suggested connections."""
    suggestions = graph.suggest_connections()

    if not suggestions:
        print("No connection suggestions found.")
        return

    print("\n=== Suggested Connections ===")
    print("These items share common connections but aren't directly linked:\n")

    for i, sugg in enumerate(suggestions[:10], 1):
        print(f"{i}. {sugg['entity1']} <-> {sugg['entity2']}")
        print(f"   Types: {sugg['type1']} / {sugg['type2']}")
        print(f"   Common connections: {', '.join(sugg['common_connections'][:5])}")
        print()


def print_stats(graph: KnowledgeGraph):
    """Print graph statistics."""
    stats = graph.get_stats()

    print("\n=== Knowledge Graph Statistics ===\n")
    print(f"Total nodes: {stats['total_nodes']}")
    print(f"Total edges: {stats['total_edges']}")
    print(f"Last updated: {stats['updated']}")
    print("\nNodes by type:")
    for etype, count in sorted(stats["nodes_by_type"].items(), key=lambda x: x[1], reverse=True):
        print(f"  {etype}: {count}")


def main():
    """CLI interface for knowledge graph."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()
    graph = KnowledgeGraph()

    if command == "build":
        graph.build()

    elif command == "query":
        if len(sys.argv) < 3:
            print("Usage: python3 knowledge_graph.py query <entity>")
            sys.exit(1)

        if not graph.load():
            print("Graph not found. Run 'python3 knowledge_graph.py build' first.")
            sys.exit(1)

        entity = " ".join(sys.argv[2:])
        print_related(graph, entity)

    elif command == "context":
        if len(sys.argv) < 3:
            print("Usage: python3 knowledge_graph.py context <topic>")
            sys.exit(1)

        if not graph.load():
            print("Graph not found. Run 'python3 knowledge_graph.py build' first.")
            sys.exit(1)

        topic = " ".join(sys.argv[2:])
        print_context(graph, topic)

    elif command == "suggest":
        if not graph.load():
            print("Graph not found. Run 'python3 knowledge_graph.py build' first.")
            sys.exit(1)

        print_suggestions(graph)

    elif command == "stats":
        if not graph.load():
            print("Graph not found. Run 'python3 knowledge_graph.py build' first.")
            sys.exit(1)

        print_stats(graph)

    elif command == "list":
        if not graph.load():
            print("Graph not found. Run 'python3 knowledge_graph.py build' first.")
            sys.exit(1)

        print("\n=== All Entities ===\n")
        by_type = defaultdict(list)
        for entity, info in graph.nodes.items():
            by_type[info.get("type", "unknown")].append(entity)

        for etype, entities in sorted(by_type.items()):
            print(f"\n{etype.upper()}:")
            for entity in sorted(entities):
                print(f"  - {entity}")

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
