#!/usr/bin/env python3
"""
BlackRoad State Synchronization Manager

Manages state across:
- Salesforce CRM (Primary state store)
- Cloudflare KV (Edge cache)
- GitHub Projects (Kanban view)
- Local agent state (Working memory)

Author: BlackRoad OS Team
License: Proprietary - BlackRoad OS License
"""

import os
import json
import time
import asyncio
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
import hashlib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blackroad.state")


class Platform(Enum):
    """Supported state platforms."""
    GITHUB = "github"
    SALESFORCE = "salesforce"
    CLOUDFLARE = "cloudflare"
    LOCAL = "local"


class ConflictResolution(Enum):
    """Conflict resolution strategies."""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MANUAL = "manual"
    MERGE = "merge"


@dataclass
class StateEntry:
    """A single state entry."""
    id: str
    type: str  # card, pr, endpoint, etc.
    data: Dict[str, Any]
    sha_hash: str
    created_at: float
    updated_at: float
    synced_at: Dict[str, float] = field(default_factory=dict)
    version: int = 1

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of the entry."""
        content = json.dumps({
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "version": self.version
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def validate_hash(self) -> bool:
        """Validate the stored hash matches computed hash."""
        return self.sha_hash == self.compute_hash()


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    source: Platform
    target: Platform
    entries_synced: int
    entries_failed: int
    conflicts: List[Dict[str, Any]]
    duration_ms: float
    timestamp: float = field(default_factory=time.time)


class PlatformAdapter:
    """Base adapter for platform integrations."""

    def __init__(self, platform: Platform):
        self.platform = platform

    async def get(self, entry_id: str) -> Optional[StateEntry]:
        raise NotImplementedError

    async def put(self, entry: StateEntry) -> bool:
        raise NotImplementedError

    async def delete(self, entry_id: str) -> bool:
        raise NotImplementedError

    async def list_entries(self, entry_type: Optional[str] = None) -> List[StateEntry]:
        raise NotImplementedError

    async def health_check(self) -> bool:
        raise NotImplementedError


class SalesforceAdapter(PlatformAdapter):
    """Salesforce CRM adapter."""

    def __init__(self):
        super().__init__(Platform.SALESFORCE)
        self.base_url = os.getenv("SALESFORCE_INSTANCE_URL", "")
        self.access_token = None

    async def authenticate(self) -> bool:
        """Authenticate with Salesforce OAuth2."""
        # OAuth2 flow would go here
        client_id = os.getenv("SALESFORCE_CLIENT_ID")
        client_secret = os.getenv("SALESFORCE_CLIENT_SECRET")
        username = os.getenv("SALESFORCE_USERNAME")
        password = os.getenv("SALESFORCE_PASSWORD")

        if not all([client_id, client_secret, username, password]):
            logger.warning("Salesforce credentials not configured")
            return False

        # Simulated auth - real implementation would call Salesforce OAuth
        logger.info("Salesforce authentication configured")
        return True

    async def get(self, entry_id: str) -> Optional[StateEntry]:
        """Get entry from Salesforce."""
        # Real implementation would query Salesforce REST API
        # GET /services/data/v59.0/sobjects/BlackRoad_State__c/{entry_id}
        logger.info(f"Salesforce GET: {entry_id}")
        return None

    async def put(self, entry: StateEntry) -> bool:
        """Put entry to Salesforce."""
        # Real implementation would upsert to Salesforce
        # PATCH /services/data/v59.0/sobjects/BlackRoad_State__c/{entry_id}
        logger.info(f"Salesforce PUT: {entry.id}")
        return True

    async def list_entries(self, entry_type: Optional[str] = None) -> List[StateEntry]:
        """List entries from Salesforce."""
        # SOQL query: SELECT Id, Data__c FROM BlackRoad_State__c WHERE Type__c = :entry_type
        logger.info(f"Salesforce LIST: type={entry_type}")
        return []

    async def health_check(self) -> bool:
        """Check Salesforce connectivity."""
        return await self.authenticate()


class CloudflareKVAdapter(PlatformAdapter):
    """Cloudflare KV adapter."""

    def __init__(self):
        super().__init__(Platform.CLOUDFLARE)
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        self.namespace_id = os.getenv("CLOUDFLARE_KV_STATE_ID")
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN")

    async def get(self, entry_id: str) -> Optional[StateEntry]:
        """Get entry from Cloudflare KV."""
        # GET https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/values/{key}
        logger.info(f"Cloudflare KV GET: {entry_id}")
        return None

    async def put(self, entry: StateEntry) -> bool:
        """Put entry to Cloudflare KV."""
        # PUT https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/values/{key}
        logger.info(f"Cloudflare KV PUT: {entry.id}")
        return True

    async def delete(self, entry_id: str) -> bool:
        """Delete entry from Cloudflare KV."""
        logger.info(f"Cloudflare KV DELETE: {entry_id}")
        return True

    async def list_entries(self, entry_type: Optional[str] = None) -> List[StateEntry]:
        """List entries from Cloudflare KV."""
        # GET /keys with prefix filtering
        logger.info(f"Cloudflare KV LIST: type={entry_type}")
        return []

    async def health_check(self) -> bool:
        """Check Cloudflare connectivity."""
        return bool(self.api_token)


class GitHubProjectsAdapter(PlatformAdapter):
    """GitHub Projects V2 adapter."""

    def __init__(self):
        super().__init__(Platform.GITHUB)
        self.token = os.getenv("GITHUB_TOKEN")
        self.org = "BlackRoad-OS"
        self.repo = "blackroad-ai-inference-accelerator"

    async def get(self, entry_id: str) -> Optional[StateEntry]:
        """Get entry from GitHub Projects."""
        # GraphQL query for project item
        logger.info(f"GitHub Projects GET: {entry_id}")
        return None

    async def put(self, entry: StateEntry) -> bool:
        """Put entry to GitHub Projects."""
        # GraphQL mutation for project item
        logger.info(f"GitHub Projects PUT: {entry.id}")
        return True

    async def list_entries(self, entry_type: Optional[str] = None) -> List[StateEntry]:
        """List entries from GitHub Projects."""
        logger.info(f"GitHub Projects LIST: type={entry_type}")
        return []

    async def health_check(self) -> bool:
        """Check GitHub connectivity."""
        return bool(self.token)


class LocalAdapter(PlatformAdapter):
    """Local file-based state adapter."""

    def __init__(self, state_dir: str = ".blackroad/state"):
        super().__init__(Platform.LOCAL)
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)

    def _get_path(self, entry_id: str) -> str:
        """Get file path for entry."""
        return os.path.join(self.state_dir, f"{entry_id}.json")

    async def get(self, entry_id: str) -> Optional[StateEntry]:
        """Get entry from local state."""
        path = self._get_path(entry_id)
        if not os.path.exists(path):
            return None

        with open(path, 'r') as f:
            data = json.load(f)
            return StateEntry(**data)

    async def put(self, entry: StateEntry) -> bool:
        """Put entry to local state."""
        path = self._get_path(entry.id)
        with open(path, 'w') as f:
            json.dump(asdict(entry), f, indent=2)
        return True

    async def delete(self, entry_id: str) -> bool:
        """Delete entry from local state."""
        path = self._get_path(entry_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    async def list_entries(self, entry_type: Optional[str] = None) -> List[StateEntry]:
        """List entries from local state."""
        entries = []
        for filename in os.listdir(self.state_dir):
            if filename.endswith('.json'):
                entry = await self.get(filename[:-5])
                if entry and (entry_type is None or entry.type == entry_type):
                    entries.append(entry)
        return entries

    async def health_check(self) -> bool:
        """Check local state directory."""
        return os.path.isdir(self.state_dir)


class StateSyncManager:
    """
    Manages state synchronization across all platforms.

    Implements:
    - Bi-directional sync between platforms
    - Conflict resolution
    - Hash-based integrity verification
    - Automatic retry with backoff
    """

    def __init__(
        self,
        primary: Platform = Platform.SALESFORCE,
        conflict_resolution: ConflictResolution = ConflictResolution.LAST_WRITE_WINS
    ):
        self.primary = primary
        self.conflict_resolution = conflict_resolution

        # Initialize adapters
        self.adapters: Dict[Platform, PlatformAdapter] = {
            Platform.SALESFORCE: SalesforceAdapter(),
            Platform.CLOUDFLARE: CloudflareKVAdapter(),
            Platform.GITHUB: GitHubProjectsAdapter(),
            Platform.LOCAL: LocalAdapter()
        }

        # Sync configuration
        self.sync_interval = 30  # seconds
        self.retry_attempts = 4
        self.retry_backoff = [2, 4, 8, 16]  # seconds

        # Sync hooks
        self.pre_sync_hooks: List[Callable] = []
        self.post_sync_hooks: List[Callable] = []

    def add_pre_sync_hook(self, hook: Callable) -> None:
        """Add a pre-sync hook."""
        self.pre_sync_hooks.append(hook)

    def add_post_sync_hook(self, hook: Callable) -> None:
        """Add a post-sync hook."""
        self.post_sync_hooks.append(hook)

    async def sync(
        self,
        source: Platform,
        targets: List[Platform],
        entry_type: Optional[str] = None,
        force: bool = False
    ) -> List[SyncResult]:
        """
        Sync state from source to targets.

        Args:
            source: Source platform
            targets: Target platforms
            entry_type: Filter by entry type
            force: Force sync even if hashes match

        Returns:
            List of sync results
        """
        results = []
        start_time = time.time()

        # Run pre-sync hooks
        for hook in self.pre_sync_hooks:
            await hook(source, targets)

        # Get source adapter
        source_adapter = self.adapters[source]

        # Get all entries from source
        source_entries = await source_adapter.list_entries(entry_type)
        logger.info(f"Found {len(source_entries)} entries in {source.value}")

        # Sync to each target
        for target in targets:
            if target == source:
                continue

            target_adapter = self.adapters[target]
            synced = 0
            failed = 0
            conflicts = []

            for entry in source_entries:
                try:
                    # Check if target has this entry
                    target_entry = await target_adapter.get(entry.id)

                    if target_entry is None:
                        # New entry - just put it
                        entry.synced_at[target.value] = time.time()
                        success = await self._put_with_retry(target_adapter, entry)
                        if success:
                            synced += 1
                        else:
                            failed += 1

                    elif force or entry.sha_hash != target_entry.sha_hash:
                        # Entry differs - resolve conflict
                        resolved = await self._resolve_conflict(entry, target_entry)

                        if resolved:
                            resolved.synced_at[target.value] = time.time()
                            success = await self._put_with_retry(target_adapter, resolved)
                            if success:
                                synced += 1
                            else:
                                failed += 1
                        else:
                            conflicts.append({
                                "entry_id": entry.id,
                                "source_hash": entry.sha_hash,
                                "target_hash": target_entry.sha_hash
                            })

                except Exception as e:
                    logger.error(f"Failed to sync {entry.id} to {target.value}: {e}")
                    failed += 1

            results.append(SyncResult(
                success=failed == 0,
                source=source,
                target=target,
                entries_synced=synced,
                entries_failed=failed,
                conflicts=conflicts,
                duration_ms=(time.time() - start_time) * 1000
            ))

        # Run post-sync hooks
        for hook in self.post_sync_hooks:
            await hook(results)

        return results

    async def _resolve_conflict(
        self,
        source_entry: StateEntry,
        target_entry: StateEntry
    ) -> Optional[StateEntry]:
        """Resolve conflict between entries."""
        if self.conflict_resolution == ConflictResolution.LAST_WRITE_WINS:
            if source_entry.updated_at >= target_entry.updated_at:
                return source_entry
            return target_entry

        elif self.conflict_resolution == ConflictResolution.FIRST_WRITE_WINS:
            if source_entry.created_at <= target_entry.created_at:
                return source_entry
            return target_entry

        elif self.conflict_resolution == ConflictResolution.MERGE:
            # Merge data fields
            merged_data = {**target_entry.data, **source_entry.data}
            merged = StateEntry(
                id=source_entry.id,
                type=source_entry.type,
                data=merged_data,
                sha_hash="",  # Will be computed
                created_at=min(source_entry.created_at, target_entry.created_at),
                updated_at=time.time(),
                synced_at={**target_entry.synced_at, **source_entry.synced_at},
                version=max(source_entry.version, target_entry.version) + 1
            )
            merged.sha_hash = merged.compute_hash()
            return merged

        else:
            # Manual - return None to mark as conflict
            return None

    async def _put_with_retry(
        self,
        adapter: PlatformAdapter,
        entry: StateEntry
    ) -> bool:
        """Put entry with retry logic."""
        for attempt in range(self.retry_attempts):
            try:
                success = await adapter.put(entry)
                if success:
                    return True
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

            if attempt < self.retry_attempts - 1:
                await asyncio.sleep(self.retry_backoff[attempt])

        return False

    async def health_check_all(self) -> Dict[Platform, bool]:
        """Check health of all platforms."""
        results = {}
        for platform, adapter in self.adapters.items():
            try:
                results[platform] = await adapter.health_check()
            except Exception as e:
                logger.error(f"Health check failed for {platform.value}: {e}")
                results[platform] = False
        return results

    async def create_entry(
        self,
        entry_id: str,
        entry_type: str,
        data: Dict[str, Any],
        sync_to: Optional[List[Platform]] = None
    ) -> StateEntry:
        """
        Create a new state entry and optionally sync.

        Args:
            entry_id: Unique identifier
            entry_type: Type of entry (card, pr, endpoint)
            data: Entry data
            sync_to: Platforms to sync to (default: all)

        Returns:
            Created StateEntry
        """
        now = time.time()
        entry = StateEntry(
            id=entry_id,
            type=entry_type,
            data=data,
            sha_hash="",
            created_at=now,
            updated_at=now,
            synced_at={},
            version=1
        )
        entry.sha_hash = entry.compute_hash()

        # Save to primary
        primary_adapter = self.adapters[self.primary]
        await primary_adapter.put(entry)
        entry.synced_at[self.primary.value] = now

        # Sync to other platforms
        if sync_to is None:
            sync_to = [p for p in Platform if p != self.primary]

        for platform in sync_to:
            adapter = self.adapters[platform]
            success = await self._put_with_retry(adapter, entry)
            if success:
                entry.synced_at[platform.value] = time.time()

        return entry

    async def get_entry(
        self,
        entry_id: str,
        platform: Optional[Platform] = None
    ) -> Optional[StateEntry]:
        """Get entry from specified platform or primary."""
        platform = platform or self.primary
        adapter = self.adapters[platform]
        return await adapter.get(entry_id)

    def generate_sync_report(self, results: List[SyncResult]) -> Dict[str, Any]:
        """Generate a sync report from results."""
        total_synced = sum(r.entries_synced for r in results)
        total_failed = sum(r.entries_failed for r in results)
        total_conflicts = sum(len(r.conflicts) for r in results)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_success": all(r.success for r in results),
            "total_entries_synced": total_synced,
            "total_entries_failed": total_failed,
            "total_conflicts": total_conflicts,
            "total_duration_ms": sum(r.duration_ms for r in results),
            "results_by_target": {
                r.target.value: {
                    "success": r.success,
                    "synced": r.entries_synced,
                    "failed": r.entries_failed,
                    "conflicts": len(r.conflicts)
                }
                for r in results
            }
        }


# Convenience functions
async def sync_all(force: bool = False) -> Dict[str, Any]:
    """Sync all platforms from primary."""
    manager = StateSyncManager()
    results = await manager.sync(
        source=Platform.SALESFORCE,
        targets=[Platform.CLOUDFLARE, Platform.GITHUB, Platform.LOCAL],
        force=force
    )
    return manager.generate_sync_report(results)


async def check_all_health() -> Dict[str, bool]:
    """Check health of all platforms."""
    manager = StateSyncManager()
    return await manager.health_check_all()


if __name__ == "__main__":
    # Demo usage
    async def main():
        print("BlackRoad State Sync Manager Demo")
        print("=" * 50)

        manager = StateSyncManager()

        # Health check
        print("\nHealth Check:")
        health = await manager.health_check_all()
        for platform, status in health.items():
            print(f"  {platform.value}: {'OK' if status else 'FAIL'}")

        # Create an entry
        print("\nCreating entry...")
        entry = await manager.create_entry(
            entry_id="CARD-001",
            entry_type="kanban_card",
            data={
                "title": "Test Card",
                "status": "in_progress",
                "priority": "P1"
            }
        )
        print(f"  Created: {entry.id}")
        print(f"  Hash: {entry.sha_hash}")
        print(f"  Synced to: {list(entry.synced_at.keys())}")

        # Sync
        print("\nSyncing...")
        results = await manager.sync(
            source=Platform.LOCAL,
            targets=[Platform.CLOUDFLARE]
        )

        report = manager.generate_sync_report(results)
        print(f"  Success: {report['overall_success']}")
        print(f"  Synced: {report['total_entries_synced']}")

    asyncio.run(main())
