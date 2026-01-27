"""
BlackRoad State Module

State synchronization across platforms.
"""

from .sync_manager import (
    StateSyncManager,
    Platform,
    ConflictResolution,
    StateEntry,
    SyncResult,
    sync_all,
    check_all_health
)

__all__ = [
    "StateSyncManager",
    "Platform",
    "ConflictResolution",
    "StateEntry",
    "SyncResult",
    "sync_all",
    "check_all_health"
]
