#!/usr/bin/env python3
"""
BlackRoad Task Initialization Script

Creates a new task with proper kanban card, hashing, and state sync.

Usage:
    python scripts/init_task.py --title "Implement feature X"
    python scripts/init_task.py --title "Fix bug Y" --type bug --priority P0
    python scripts/init_task.py --title "Integrate Z" --type integration --endpoint cloudflare

Author: BlackRoad OS Team
License: Proprietary - BlackRoad OS License
"""

import asyncio
import argparse
import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, '.')

from src.kanban.board import (
    KanbanBoard,
    CardType,
    CardStatus,
    Priority,
    create_agent_task,
    create_integration_card
)
from src.hashing.sha_infinity import KanbanHasher


def get_session_info() -> dict:
    """Get current session info from environment."""
    return {
        "session_id": os.getenv("CLAUDE_SESSION_ID", "unknown"),
        "branch": os.popen("git branch --show-current").read().strip(),
        "user": os.popen("git config user.name").read().strip() or "agent"
    }


async def init_task(
    title: str,
    task_type: str = "feature",
    priority: str = "P2",
    assignee: str = None,
    description: str = "",
    endpoint: str = None,
    labels: list = None
) -> dict:
    """Initialize a new task with all integrations."""

    session = get_session_info()
    board = KanbanBoard()
    hasher = KanbanHasher()

    # Map types
    type_map = {
        "feature": CardType.FEATURE,
        "bug": CardType.BUG,
        "integration": CardType.INTEGRATION,
        "agent": CardType.AGENT_TASK
    }

    priority_map = {
        "P0": Priority.P0,
        "P1": Priority.P1,
        "P2": Priority.P2,
        "P3": Priority.P3
    }

    card_type = type_map.get(task_type, CardType.FEATURE)
    card_priority = priority_map.get(priority, Priority.P2)

    # Create appropriate card
    if task_type == "agent":
        card = create_agent_task(
            board=board,
            title=title,
            agent_type="claude",
            session_id=session["session_id"],
            branch=session["branch"]
        )
    elif task_type == "integration" and endpoint:
        card = create_integration_card(
            board=board,
            endpoint_name=endpoint,
            description=description or f"Integrate {endpoint} endpoint",
            priority=card_priority
        )
    else:
        card = board.create_card(
            title=title,
            type=card_type,
            description=description,
            priority=card_priority,
            assignee=assignee or session["user"],
            labels=labels or []
        )

    # Generate hashes
    card_hash = hasher.hash_card(
        card_id=card.id,
        title=card.title,
        status=card.status.value,
        assignee=card.assignee,
        priority=card.priority.value
    )

    # Create todo template
    todos = generate_todos(card_type, title, endpoint)

    result = {
        "card": {
            "id": card.id,
            "title": card.title,
            "type": card.type.value,
            "status": card.status.value,
            "priority": card.priority.value,
            "assignee": card.assignee,
            "sha_hash": card.sha_hash,
            "infinity_hash": card_hash
        },
        "session": session,
        "todos": todos,
        "created_at": datetime.utcnow().isoformat()
    }

    return result


def generate_todos(card_type: CardType, title: str, endpoint: str = None) -> list:
    """Generate appropriate todos based on task type."""

    base_todos = [
        {"content": f"Research and plan: {title}", "status": "pending"},
        {"content": "Implement core functionality", "status": "pending"},
        {"content": "Add tests", "status": "pending"},
        {"content": "Update documentation", "status": "pending"},
        {"content": "Verify hash integrity", "status": "pending"},
        {"content": "Create PR", "status": "pending"}
    ]

    if card_type == CardType.INTEGRATION:
        integration_todos = [
            {"content": f"Research {endpoint} API documentation", "status": "pending"},
            {"content": f"Add {endpoint} configuration to endpoints.yaml", "status": "pending"},
            {"content": f"Implement {endpoint} client", "status": "pending"},
            {"content": f"Add health check for {endpoint}", "status": "pending"},
            {"content": "Create sync adapter for state management", "status": "pending"},
            {"content": "Add integration tests", "status": "pending"},
            {"content": "Update AGENT_INSTRUCTIONS.md", "status": "pending"},
            {"content": "Compute and verify hashes", "status": "pending"},
            {"content": "Create PR with integrity report", "status": "pending"}
        ]
        return integration_todos

    if card_type == CardType.BUG:
        bug_todos = [
            {"content": "Reproduce the bug", "status": "pending"},
            {"content": "Identify root cause", "status": "pending"},
            {"content": "Implement fix", "status": "pending"},
            {"content": "Add regression test", "status": "pending"},
            {"content": "Verify hash integrity", "status": "pending"},
            {"content": "Create PR", "status": "pending"}
        ]
        return bug_todos

    if card_type == CardType.AGENT_TASK:
        agent_todos = [
            {"content": "Parse task requirements", "status": "pending"},
            {"content": "Search codebase for relevant files", "status": "pending"},
            {"content": "Plan implementation steps", "status": "pending"},
            {"content": "Execute implementation", "status": "pending"},
            {"content": "Validate all endpoints", "status": "pending"},
            {"content": "Sync state to all platforms", "status": "pending"},
            {"content": "Compute integrity hashes", "status": "pending"},
            {"content": "Create PR with full report", "status": "pending"}
        ]
        return agent_todos

    return base_todos


def print_task_info(result: dict):
    """Print task initialization info."""
    print("\n" + "=" * 60)
    print("BLACKROAD TASK INITIALIZED")
    print("=" * 60)

    card = result["card"]
    print(f"Card ID: {card['id']}")
    print(f"Title: {card['title']}")
    print(f"Type: {card['type']}")
    print(f"Priority: {card['priority']}")
    print(f"Status: {card['status']}")
    print(f"Assignee: {card['assignee']}")
    print(f"SHA Hash: {card['sha_hash'][:16]}...")
    print(f"Infinity Hash: {card['infinity_hash'][:16]}...")

    print("-" * 60)
    print("Session Info:")
    session = result["session"]
    print(f"  Session ID: {session['session_id']}")
    print(f"  Branch: {session['branch']}")
    print(f"  User: {session['user']}")

    print("-" * 60)
    print("Todos:")
    for i, todo in enumerate(result["todos"], 1):
        print(f"  {i}. [{todo['status']}] {todo['content']}")

    print("=" * 60)
    print(f"\nTask initialized at {result['created_at']}")
    print("Use TodoWrite tool to track progress.")


async def main():
    parser = argparse.ArgumentParser(description="Initialize a BlackRoad task")
    parser.add_argument("--title", "-t", type=str, required=True, help="Task title")
    parser.add_argument("--type", type=str, default="feature",
                       choices=["feature", "bug", "integration", "agent"],
                       help="Task type")
    parser.add_argument("--priority", "-p", type=str, default="P2",
                       choices=["P0", "P1", "P2", "P3"],
                       help="Priority level")
    parser.add_argument("--assignee", "-a", type=str, help="Assignee")
    parser.add_argument("--description", "-d", type=str, default="", help="Description")
    parser.add_argument("--endpoint", "-e", type=str, help="Endpoint for integration tasks")
    parser.add_argument("--labels", "-l", type=str, help="Labels (comma-separated)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    labels = [l.strip() for l in args.labels.split(",")] if args.labels else []

    result = await init_task(
        title=args.title,
        task_type=args.type,
        priority=args.priority,
        assignee=args.assignee,
        description=args.description,
        endpoint=args.endpoint,
        labels=labels
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_task_info(result)


if __name__ == "__main__":
    asyncio.run(main())
