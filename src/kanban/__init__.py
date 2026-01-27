"""
BlackRoad Kanban Module

Salesforce-style project management for GitHub.
"""

from .board import (
    KanbanBoard,
    Card,
    CardType,
    CardStatus,
    Priority,
    create_agent_task,
    create_integration_card
)

__all__ = [
    "KanbanBoard",
    "Card",
    "CardType",
    "CardStatus",
    "Priority",
    "create_agent_task",
    "create_integration_card"
]
