#!/usr/bin/env python3
"""
BlackRoad Kanban Board Implementation

Salesforce-style project management with GitHub integration.
Features:
- Multi-board support (Development, PR Pipeline)
- Card lifecycle management
- Automated state sync
- Hash-based integrity tracking

Author: BlackRoad OS Team
License: Proprietary - BlackRoad OS License
"""

import os
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
import yaml

# Import hashing system
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hashing.sha_infinity import KanbanHasher, sha256_hash


class CardStatus(Enum):
    """Standard kanban card statuses."""
    BACKLOG = "backlog"
    QUALIFIED = "qualified"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    STAGING = "staging"
    DEPLOYED = "deployed"


class CardType(Enum):
    """Card types matching Salesforce objects."""
    FEATURE = "feature"
    BUG = "bug"
    INTEGRATION = "integration"
    AGENT_TASK = "agent_task"


class Priority(Enum):
    """Priority levels."""
    P0 = "P0"  # Critical
    P1 = "P1"  # High
    P2 = "P2"  # Medium
    P3 = "P3"  # Low


@dataclass
class Card:
    """A kanban card."""
    id: str
    title: str
    description: str
    type: CardType
    status: CardStatus
    priority: Priority
    assignee: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    sha_hash: str = ""
    infinity_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Salesforce sync fields
    salesforce_id: Optional[str] = None
    github_issue_number: Optional[int] = None
    github_project_item_id: Optional[str] = None

    def __post_init__(self):
        """Compute hash after initialization."""
        self._update_hash()

    def _update_hash(self) -> None:
        """Update SHA and infinity hash."""
        self.sha_hash = sha256_hash({
            "id": self.id,
            "title": self.title,
            "status": self.status.value,
            "type": self.type.value,
            "priority": self.priority.value,
            "assignee": self.assignee,
            "updated_at": self.updated_at
        })

    def update(self, **kwargs) -> 'Card':
        """Update card fields."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = time.time()
        self._update_hash()
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **asdict(self),
            "type": self.type.value,
            "status": self.status.value,
            "priority": self.priority.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Card':
        """Create from dictionary."""
        data = data.copy()
        data["type"] = CardType(data["type"])
        data["status"] = CardStatus(data["status"])
        data["priority"] = Priority(data["priority"])
        return cls(**data)


@dataclass
class Column:
    """A kanban board column."""
    id: str
    name: str
    status: CardStatus
    wip_limit: Optional[int] = None
    color: str = "#6B7280"
    cards: List[str] = field(default_factory=list)  # Card IDs


@dataclass
class Board:
    """A kanban board."""
    id: str
    name: str
    columns: List[Column]
    cards: Dict[str, Card] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class KanbanBoard:
    """
    Full-featured Kanban board manager.

    Integrates with:
    - Salesforce CRM for state
    - Cloudflare KV for edge cache
    - GitHub Projects for visualization
    - SHA-Infinity for integrity
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Kanban board.

        Args:
            config_path: Path to kanban.yaml config
        """
        self.config_path = config_path or self._find_config()
        self.config = self._load_config()
        self.hasher = KanbanHasher()
        self.boards: Dict[str, Board] = {}
        self._init_boards()

        # Event hooks
        self.on_card_created: List[Callable] = []
        self.on_card_updated: List[Callable] = []
        self.on_card_moved: List[Callable] = []

    def _find_config(self) -> str:
        """Find kanban config file."""
        paths = [
            ".blackroad/kanban.yaml",
            "config/kanban.yaml",
            os.path.expanduser("~/.blackroad/kanban.yaml")
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        return paths[0]  # Default

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "boards": {
                "main": {
                    "name": "Development Pipeline",
                    "columns": [
                        {"id": "backlog", "name": "Backlog", "wip_limit": None},
                        {"id": "qualified", "name": "Qualified", "wip_limit": 10},
                        {"id": "in_progress", "name": "In Progress", "wip_limit": 5},
                        {"id": "review", "name": "Review/QA", "wip_limit": 3},
                        {"id": "staging", "name": "Staging", "wip_limit": 2},
                        {"id": "deployed", "name": "Deployed", "wip_limit": None}
                    ]
                }
            }
        }

    def _init_boards(self) -> None:
        """Initialize boards from config."""
        for board_id, board_config in self.config.get("boards", {}).items():
            columns = []
            for col in board_config.get("columns", []):
                columns.append(Column(
                    id=col["id"],
                    name=col["name"],
                    status=CardStatus(col["id"]),
                    wip_limit=col.get("wip_limit"),
                    color=col.get("color", "#6B7280")
                ))

            self.boards[board_id] = Board(
                id=board_id,
                name=board_config["name"],
                columns=columns
            )

    def create_card(
        self,
        title: str,
        type: CardType,
        description: str = "",
        priority: Priority = Priority.P2,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        board_id: str = "main",
        status: CardStatus = CardStatus.BACKLOG,
        **metadata
    ) -> Card:
        """
        Create a new kanban card.

        Args:
            title: Card title
            type: Card type
            description: Card description
            priority: Priority level
            assignee: Assigned user
            labels: List of labels
            board_id: Target board ID
            status: Initial status
            **metadata: Additional metadata

        Returns:
            Created Card
        """
        card_id = f"CARD-{uuid.uuid4().hex[:8].upper()}"

        card = Card(
            id=card_id,
            title=title,
            description=description,
            type=type,
            status=status,
            priority=priority,
            assignee=assignee,
            labels=labels or [],
            metadata=metadata
        )

        # Compute infinity hash
        card.infinity_hash = self.hasher.hash_card(
            card_id=card.id,
            title=card.title,
            status=card.status.value,
            assignee=card.assignee,
            priority=card.priority.value
        )

        # Add to board
        board = self.boards.get(board_id)
        if board:
            board.cards[card.id] = card
            # Add to appropriate column
            for col in board.columns:
                if col.status == status:
                    col.cards.append(card.id)
                    break

        # Trigger hooks
        for hook in self.on_card_created:
            hook(card)

        return card

    def move_card(
        self,
        card_id: str,
        new_status: CardStatus,
        board_id: str = "main"
    ) -> Optional[Card]:
        """
        Move a card to a new status/column.

        Args:
            card_id: Card ID
            new_status: Target status
            board_id: Board ID

        Returns:
            Updated Card or None
        """
        board = self.boards.get(board_id)
        if not board or card_id not in board.cards:
            return None

        card = board.cards[card_id]
        old_status = card.status

        # Check WIP limit
        target_column = None
        for col in board.columns:
            if col.status == new_status:
                target_column = col
                break

        if target_column and target_column.wip_limit:
            if len(target_column.cards) >= target_column.wip_limit:
                raise ValueError(
                    f"WIP limit reached for {target_column.name} "
                    f"({target_column.wip_limit})"
                )

        # Remove from old column
        for col in board.columns:
            if card_id in col.cards:
                col.cards.remove(card_id)
                break

        # Add to new column
        if target_column:
            target_column.cards.append(card_id)

        # Update card
        card.status = new_status
        card.updated_at = time.time()
        card._update_hash()

        # Update infinity hash
        card.infinity_hash = self.hasher.hash_card(
            card_id=card.id,
            title=card.title,
            status=card.status.value,
            assignee=card.assignee,
            priority=card.priority.value
        )

        # Trigger hooks
        for hook in self.on_card_moved:
            hook(card, old_status, new_status)

        return card

    def update_card(
        self,
        card_id: str,
        board_id: str = "main",
        **updates
    ) -> Optional[Card]:
        """
        Update card fields.

        Args:
            card_id: Card ID
            board_id: Board ID
            **updates: Fields to update

        Returns:
            Updated Card or None
        """
        board = self.boards.get(board_id)
        if not board or card_id not in board.cards:
            return None

        card = board.cards[card_id]
        old_hash = card.sha_hash

        # Apply updates
        card.update(**updates)

        # Update infinity hash
        card.infinity_hash = self.hasher.hash_card(
            card_id=card.id,
            title=card.title,
            status=card.status.value,
            assignee=card.assignee,
            priority=card.priority.value
        )

        # Trigger hooks
        for hook in self.on_card_updated:
            hook(card, old_hash)

        return card

    def get_card(self, card_id: str, board_id: str = "main") -> Optional[Card]:
        """Get a card by ID."""
        board = self.boards.get(board_id)
        if board:
            return board.cards.get(card_id)
        return None

    def get_cards_by_status(
        self,
        status: CardStatus,
        board_id: str = "main"
    ) -> List[Card]:
        """Get all cards with a specific status."""
        board = self.boards.get(board_id)
        if not board:
            return []

        return [
            card for card in board.cards.values()
            if card.status == status
        ]

    def get_cards_by_assignee(
        self,
        assignee: str,
        board_id: str = "main"
    ) -> List[Card]:
        """Get all cards assigned to a user."""
        board = self.boards.get(board_id)
        if not board:
            return []

        return [
            card for card in board.cards.values()
            if card.assignee == assignee
        ]

    def get_board_summary(self, board_id: str = "main") -> Dict[str, Any]:
        """Get a summary of the board state."""
        board = self.boards.get(board_id)
        if not board:
            return {}

        columns_summary = []
        for col in board.columns:
            cards_in_col = [
                board.cards[cid] for cid in col.cards
                if cid in board.cards
            ]
            columns_summary.append({
                "id": col.id,
                "name": col.name,
                "card_count": len(cards_in_col),
                "wip_limit": col.wip_limit,
                "at_limit": col.wip_limit and len(cards_in_col) >= col.wip_limit,
                "cards": [c.to_dict() for c in cards_in_col]
            })

        return {
            "board_id": board.id,
            "board_name": board.name,
            "total_cards": len(board.cards),
            "columns": columns_summary,
            "integrity": self.hasher.get_integrity_report()
        }

    def export_board(self, board_id: str = "main") -> Dict[str, Any]:
        """Export board state for persistence/sync."""
        board = self.boards.get(board_id)
        if not board:
            return {}

        return {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "board": {
                "id": board.id,
                "name": board.name,
                "columns": [
                    {
                        "id": col.id,
                        "name": col.name,
                        "wip_limit": col.wip_limit,
                        "color": col.color,
                        "cards": col.cards
                    }
                    for col in board.columns
                ],
                "cards": {
                    cid: card.to_dict()
                    for cid, card in board.cards.items()
                }
            },
            "integrity": self.hasher.get_integrity_report()
        }

    def import_board(self, data: Dict[str, Any]) -> Board:
        """Import board state from export."""
        board_data = data["board"]

        columns = []
        for col_data in board_data["columns"]:
            columns.append(Column(
                id=col_data["id"],
                name=col_data["name"],
                status=CardStatus(col_data["id"]),
                wip_limit=col_data.get("wip_limit"),
                color=col_data.get("color", "#6B7280"),
                cards=col_data.get("cards", [])
            ))

        board = Board(
            id=board_data["id"],
            name=board_data["name"],
            columns=columns,
            cards={
                cid: Card.from_dict(cdata)
                for cid, cdata in board_data.get("cards", {}).items()
            }
        )

        self.boards[board.id] = board
        return board


# Agent-specific helper functions
def create_agent_task(
    board: KanbanBoard,
    title: str,
    agent_type: str = "claude",
    session_id: Optional[str] = None,
    branch: Optional[str] = None,
    max_attempts: int = 3
) -> Card:
    """
    Create an agent task card.

    Args:
        board: KanbanBoard instance
        title: Task title
        agent_type: Type of agent (claude, explore, bash, plan)
        session_id: Agent session ID
        branch: Git branch name
        max_attempts: Max retry attempts

    Returns:
        Created Card
    """
    return board.create_card(
        title=title,
        type=CardType.AGENT_TASK,
        description=f"Agent task for {agent_type}",
        priority=Priority.P1,
        assignee=f"{agent_type}-agent",
        labels=["agent-task", agent_type],
        agent_type=agent_type,
        session_id=session_id,
        branch=branch,
        max_attempts=max_attempts,
        auto_retry=True
    )


def create_integration_card(
    board: KanbanBoard,
    endpoint_name: str,
    description: str,
    priority: Priority = Priority.P1
) -> Card:
    """
    Create an integration task card.

    Args:
        board: KanbanBoard instance
        endpoint_name: Name of endpoint to integrate
        description: Integration description
        priority: Priority level

    Returns:
        Created Card
    """
    return board.create_card(
        title=f"Integrate {endpoint_name}",
        type=CardType.INTEGRATION,
        description=description,
        priority=priority,
        labels=["integration", endpoint_name.lower()],
        endpoint=endpoint_name
    )


if __name__ == "__main__":
    # Demo usage
    print("BlackRoad Kanban Board Demo")
    print("=" * 50)

    board = KanbanBoard()

    # Create some cards
    card1 = board.create_card(
        title="Implement Cloudflare KV sync",
        type=CardType.INTEGRATION,
        description="Set up state sync with Cloudflare KV",
        priority=Priority.P1,
        assignee="alexa",
        labels=["cloudflare", "integration"]
    )
    print(f"Created: {card1.id} - {card1.title}")

    card2 = create_agent_task(
        board,
        title="Validate all endpoints",
        agent_type="claude",
        session_id="abc123"
    )
    print(f"Created: {card2.id} - {card2.title}")

    # Move card
    board.move_card(card1.id, CardStatus.IN_PROGRESS)
    print(f"Moved {card1.id} to IN_PROGRESS")

    # Get summary
    summary = board.get_board_summary()
    print(f"\nBoard Summary:")
    print(f"  Total Cards: {summary['total_cards']}")
    for col in summary['columns']:
        print(f"  {col['name']}: {col['card_count']} cards")

    # Export
    export = board.export_board()
    print(f"\nExported at: {export['exported_at']}")
    print(f"Integrity valid: {export['integrity']['valid']}")
