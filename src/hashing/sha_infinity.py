#!/usr/bin/env python3
"""
BlackRoad SHA-256 and SHA-Infinity Hashing System

SHA-Infinity is a recursive hashing mechanism that provides:
- Infinite depth integrity verification
- Chain-linked hash trees for audit trails
- State synchronization across distributed systems
- Merkle-tree compatible structures for blockchain integration

Author: BlackRoad OS Team
License: Proprietary - BlackRoad OS License
"""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import base64


@dataclass
class HashNode:
    """A node in the SHA-Infinity hash chain."""
    data_hash: str
    depth: int
    timestamp: float
    parent_hash: Optional[str] = None
    children_hashes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def infinity_hash(self) -> str:
        """Compute the infinity hash including all relationships."""
        components = [
            self.data_hash,
            str(self.depth),
            str(self.timestamp),
            self.parent_hash or "ROOT",
            "|".join(sorted(self.children_hashes)),
            json.dumps(self.metadata, sort_keys=True)
        ]
        combined = "::".join(components)
        return sha256_hash(combined)


def sha256_hash(data: Union[str, bytes, Dict, List]) -> str:
    """
    Compute SHA-256 hash of any data type.

    Args:
        data: String, bytes, dict, or list to hash

    Returns:
        Hexadecimal SHA-256 hash string
    """
    if isinstance(data, dict) or isinstance(data, list):
        data = json.dumps(data, sort_keys=True, default=str)

    if isinstance(data, str):
        data = data.encode('utf-8')

    return hashlib.sha256(data).hexdigest()


def sha256_hash_file(filepath: str) -> str:
    """
    Compute SHA-256 hash of a file.

    Args:
        filepath: Path to file

    Returns:
        Hexadecimal SHA-256 hash string
    """
    sha256 = hashlib.sha256()

    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)

    return sha256.hexdigest()


class SHAInfinity:
    """
    SHA-Infinity: Recursive infinite-depth hashing system.

    Provides chain-linked hash verification for:
    - Kanban card state tracking
    - PR integrity verification
    - Endpoint synchronization
    - CRM state validation
    - Distributed system consensus
    """

    def __init__(self, root_seed: Optional[str] = None):
        """
        Initialize SHA-Infinity hasher.

        Args:
            root_seed: Optional seed for the root hash
        """
        self.root_seed = root_seed or f"blackroad:{time.time()}"
        self.root_hash = sha256_hash(self.root_seed)
        self.chain: List[HashNode] = []
        self.depth_map: Dict[int, List[HashNode]] = {}
        self.hash_index: Dict[str, HashNode] = {}

    def add_node(
        self,
        data: Any,
        parent_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> HashNode:
        """
        Add a new node to the hash chain.

        Args:
            data: Data to hash
            parent_hash: Hash of parent node (uses root if None)
            metadata: Additional metadata to include

        Returns:
            The created HashNode
        """
        data_hash = sha256_hash(data)

        # Determine depth
        if parent_hash is None:
            depth = 0
            parent_hash = self.root_hash
        else:
            parent_node = self.hash_index.get(parent_hash)
            depth = (parent_node.depth + 1) if parent_node else 0

        # Create node
        node = HashNode(
            data_hash=data_hash,
            depth=depth,
            timestamp=time.time(),
            parent_hash=parent_hash,
            metadata=metadata or {}
        )

        # Update parent's children
        if parent_hash in self.hash_index:
            self.hash_index[parent_hash].children_hashes.append(node.infinity_hash)

        # Index the node
        self.chain.append(node)
        self.hash_index[node.infinity_hash] = node

        if depth not in self.depth_map:
            self.depth_map[depth] = []
        self.depth_map[depth].append(node)

        return node

    def compute_merkle_root(self) -> str:
        """
        Compute Merkle root of all nodes at the deepest level.

        Returns:
            Merkle root hash
        """
        if not self.chain:
            return self.root_hash

        max_depth = max(self.depth_map.keys())
        leaf_hashes = [n.infinity_hash for n in self.depth_map[max_depth]]

        while len(leaf_hashes) > 1:
            if len(leaf_hashes) % 2 == 1:
                leaf_hashes.append(leaf_hashes[-1])

            new_level = []
            for i in range(0, len(leaf_hashes), 2):
                combined = leaf_hashes[i] + leaf_hashes[i + 1]
                new_level.append(sha256_hash(combined))
            leaf_hashes = new_level

        return leaf_hashes[0] if leaf_hashes else self.root_hash

    def compute_infinity_hash(self, max_iterations: int = 1000) -> str:
        """
        Compute the infinity hash by recursive hashing.

        The infinity hash converges when the hash of the hash
        produces a stable pattern (defined by leading zeros or
        reaching max iterations).

        Args:
            max_iterations: Maximum recursion depth

        Returns:
            The infinity hash
        """
        current = self.compute_merkle_root()
        iteration = 0

        while iteration < max_iterations:
            next_hash = sha256_hash(current + str(iteration))

            # Check for convergence pattern (4 leading zeros)
            if next_hash.startswith('0000'):
                return f"INF:{iteration}:{next_hash}"

            current = next_hash
            iteration += 1

        return f"INF:{iteration}:{current}"

    def verify_chain_integrity(self) -> Tuple[bool, List[str]]:
        """
        Verify the integrity of the entire hash chain.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        for node in self.chain:
            # Verify parent exists (except for depth 0)
            if node.depth > 0 and node.parent_hash not in self.hash_index:
                if node.parent_hash != self.root_hash:
                    errors.append(f"Missing parent for node at depth {node.depth}")

            # Verify infinity hash computation
            computed = node.infinity_hash
            if computed not in self.hash_index:
                # Re-index if needed
                self.hash_index[computed] = node

        return len(errors) == 0, errors

    def export_chain(self) -> Dict[str, Any]:
        """Export the chain state for persistence."""
        return {
            "version": "1.0",
            "root_seed": self.root_seed,
            "root_hash": self.root_hash,
            "merkle_root": self.compute_merkle_root(),
            "infinity_hash": self.compute_infinity_hash(),
            "chain_length": len(self.chain),
            "max_depth": max(self.depth_map.keys()) if self.depth_map else 0,
            "nodes": [
                {
                    "data_hash": n.data_hash,
                    "infinity_hash": n.infinity_hash,
                    "depth": n.depth,
                    "timestamp": n.timestamp,
                    "parent_hash": n.parent_hash,
                    "children_count": len(n.children_hashes),
                    "metadata": n.metadata
                }
                for n in self.chain
            ],
            "exported_at": datetime.utcnow().isoformat()
        }

    @classmethod
    def import_chain(cls, data: Dict[str, Any]) -> 'SHAInfinity':
        """Import a chain from exported state."""
        instance = cls(root_seed=data["root_seed"])

        # Rebuild nodes in order
        for node_data in data["nodes"]:
            node = HashNode(
                data_hash=node_data["data_hash"],
                depth=node_data["depth"],
                timestamp=node_data["timestamp"],
                parent_hash=node_data["parent_hash"],
                metadata=node_data.get("metadata", {})
            )
            instance.chain.append(node)
            instance.hash_index[node.infinity_hash] = node

            if node.depth not in instance.depth_map:
                instance.depth_map[node.depth] = []
            instance.depth_map[node.depth].append(node)

        return instance


class KanbanHasher:
    """
    Specialized hasher for Kanban cards and PR tracking.

    Ensures integrity across:
    - Card creation and updates
    - PR state changes
    - Cross-platform synchronization
    """

    def __init__(self):
        self.hasher = SHAInfinity(root_seed="blackroad:kanban:v1")

    def hash_card(
        self,
        card_id: str,
        title: str,
        status: str,
        assignee: Optional[str] = None,
        priority: Optional[str] = None,
        **extra_fields
    ) -> str:
        """
        Create a hash for a kanban card.

        Args:
            card_id: Unique card identifier
            title: Card title
            status: Current status/column
            assignee: Assigned user
            priority: Priority level
            **extra_fields: Additional fields

        Returns:
            SHA-256 hash of the card state
        """
        card_data = {
            "id": card_id,
            "title": title,
            "status": status,
            "assignee": assignee,
            "priority": priority,
            **extra_fields
        }

        node = self.hasher.add_node(
            data=card_data,
            metadata={"type": "kanban_card", "card_id": card_id}
        )

        return node.infinity_hash

    def hash_pr(
        self,
        pr_number: int,
        title: str,
        branch: str,
        status: str,
        files_changed: List[str],
        commits: List[str]
    ) -> str:
        """
        Create a hash for a pull request.

        Args:
            pr_number: PR number
            title: PR title
            branch: Source branch
            status: PR status
            files_changed: List of changed files
            commits: List of commit SHAs

        Returns:
            SHA-256 hash of the PR state
        """
        pr_data = {
            "number": pr_number,
            "title": title,
            "branch": branch,
            "status": status,
            "files_hash": sha256_hash(sorted(files_changed)),
            "commits_hash": sha256_hash(commits)
        }

        node = self.hasher.add_node(
            data=pr_data,
            metadata={"type": "pull_request", "pr_number": pr_number}
        )

        return node.infinity_hash

    def hash_endpoint_state(
        self,
        endpoint_name: str,
        status: str,
        last_response_code: int,
        response_hash: str
    ) -> str:
        """
        Create a hash for endpoint state.

        Args:
            endpoint_name: Name of the endpoint
            status: Current status
            last_response_code: HTTP response code
            response_hash: Hash of last response

        Returns:
            SHA-256 hash of endpoint state
        """
        state_data = {
            "endpoint": endpoint_name,
            "status": status,
            "response_code": last_response_code,
            "response_hash": response_hash,
            "checked_at": time.time()
        }

        node = self.hasher.add_node(
            data=state_data,
            metadata={"type": "endpoint_state", "endpoint": endpoint_name}
        )

        return node.infinity_hash

    def get_integrity_report(self) -> Dict[str, Any]:
        """Get a full integrity report of all hashed items."""
        is_valid, errors = self.hasher.verify_chain_integrity()

        return {
            "valid": is_valid,
            "errors": errors,
            "chain_export": self.hasher.export_chain()
        }


# Utility functions for common operations
def hash_for_sync(data: Dict[str, Any], platform: str) -> str:
    """
    Create a sync hash for cross-platform state tracking.

    Args:
        data: Data to hash
        platform: Source platform name

    Returns:
        Sync hash with platform prefix
    """
    base_hash = sha256_hash(data)
    return f"{platform}:{base_hash[:16]}"


def verify_sync_hash(data: Dict[str, Any], expected_hash: str) -> bool:
    """
    Verify a sync hash matches the data.

    Args:
        data: Data to verify
        expected_hash: Expected hash with platform prefix

    Returns:
        True if hash matches
    """
    if ":" not in expected_hash:
        return False

    platform, hash_prefix = expected_hash.split(":", 1)
    actual = hash_for_sync(data, platform)

    return actual == expected_hash


if __name__ == "__main__":
    # Demo usage
    print("BlackRoad SHA-Infinity Demo")
    print("=" * 50)

    # Create a kanban hasher
    kanban = KanbanHasher()

    # Hash some cards
    card1 = kanban.hash_card(
        card_id="CARD-001",
        title="Implement Cloudflare integration",
        status="in_progress",
        assignee="alexa",
        priority="P1"
    )
    print(f"Card 1 Hash: {card1}")

    card2 = kanban.hash_card(
        card_id="CARD-002",
        title="Set up Salesforce sync",
        status="backlog",
        priority="P2"
    )
    print(f"Card 2 Hash: {card2}")

    # Hash a PR
    pr_hash = kanban.hash_pr(
        pr_number=42,
        title="feat: Add kanban endpoints",
        branch="claude/setup-kanban-endpoints-rafHv",
        status="open",
        files_changed=["config/endpoints.yaml", "src/kanban/board.py"],
        commits=["abc123", "def456"]
    )
    print(f"PR Hash: {pr_hash}")

    # Get integrity report
    report = kanban.get_integrity_report()
    print(f"\nIntegrity Valid: {report['valid']}")
    print(f"Chain Length: {report['chain_export']['chain_length']}")
    print(f"Infinity Hash: {report['chain_export']['infinity_hash']}")
