#!/usr/bin/env python3
"""
BlackRoad State Synchronization Script

Synchronizes state between platforms:
- GitHub (code)
- Salesforce CRM (primary state)
- Cloudflare KV (edge cache)

Usage:
    python scripts/sync_state.py --all
    python scripts/sync_state.py --source github --targets salesforce,cloudflare
    python scripts/sync_state.py --force --resolve last_write_wins

Author: BlackRoad OS Team
License: Proprietary - BlackRoad OS License
"""

import asyncio
import argparse
import sys
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, '.')

from src.state.sync_manager import (
    StateSyncManager,
    Platform,
    ConflictResolution,
    sync_all,
    check_all_health
)
from src.hashing.sha_infinity import sha256_hash


async def run_sync(
    source: str,
    targets: list,
    force: bool = False,
    resolve: str = "last_write_wins",
    entry_type: str = None
) -> dict:
    """Run state synchronization."""

    # Parse platforms
    source_platform = Platform(source)
    target_platforms = [Platform(t) for t in targets]
    resolution = ConflictResolution(resolve)

    # Create manager
    manager = StateSyncManager(
        primary=source_platform,
        conflict_resolution=resolution
    )

    # Run sync
    results = await manager.sync(
        source=source_platform,
        targets=target_platforms,
        entry_type=entry_type,
        force=force
    )

    # Generate report
    report = manager.generate_sync_report(results)
    report["sync_hash"] = sha256_hash(report)

    return report


async def run_health_check() -> dict:
    """Run health check on all platforms."""
    health = await check_all_health()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "platforms": {
            p.value: status for p, status in health.items()
        },
        "all_healthy": all(health.values())
    }


def print_sync_report(report: dict, verbose: bool = False):
    """Print sync report."""
    print("\n" + "=" * 60)
    print("BLACKROAD STATE SYNC REPORT")
    print("=" * 60)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Status: {'SUCCESS' if report['overall_success'] else 'FAILED'}")
    print(f"Total Synced: {report['total_entries_synced']}")
    print(f"Total Failed: {report['total_entries_failed']}")
    print(f"Conflicts: {report['total_conflicts']}")
    print(f"Duration: {report['total_duration_ms']:.0f}ms")
    print(f"Hash: {report.get('sync_hash', 'N/A')[:16]}...")
    print("-" * 60)

    if verbose and report.get('results_by_target'):
        print("\nBy Target:")
        for target, stats in report['results_by_target'].items():
            status = "OK" if stats['success'] else "FAIL"
            print(f"  [{status}] {target}")
            print(f"       Synced: {stats['synced']}")
            print(f"       Failed: {stats['failed']}")
            print(f"       Conflicts: {stats['conflicts']}")

    print("=" * 60)
    return 0 if report['overall_success'] else 1


def print_health_report(report: dict):
    """Print health check report."""
    print("\n" + "=" * 60)
    print("BLACKROAD PLATFORM HEALTH CHECK")
    print("=" * 60)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Status: {'ALL HEALTHY' if report['all_healthy'] else 'ISSUES DETECTED'}")
    print("-" * 60)

    for platform, healthy in report['platforms'].items():
        status = "OK" if healthy else "FAIL"
        print(f"  [{status}] {platform}")

    print("=" * 60)
    return 0 if report['all_healthy'] else 1


async def main():
    parser = argparse.ArgumentParser(description="Synchronize BlackRoad state")
    parser.add_argument("--all", action="store_true", help="Sync all platforms from primary")
    parser.add_argument("--source", type=str, default="salesforce",
                       choices=["github", "salesforce", "cloudflare", "local"],
                       help="Source platform")
    parser.add_argument("--targets", type=str,
                       help="Target platforms (comma-separated)")
    parser.add_argument("--force", action="store_true", help="Force sync even if hashes match")
    parser.add_argument("--resolve", type=str, default="last_write_wins",
                       choices=["last_write_wins", "first_write_wins", "manual", "merge"],
                       help="Conflict resolution strategy")
    parser.add_argument("--type", type=str, help="Filter by entry type")
    parser.add_argument("--health", action="store_true", help="Run health check only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.health:
        report = await run_health_check()
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            exit_code = print_health_report(report)
        sys.exit(0 if report['all_healthy'] else 1)

    # Determine targets
    if args.all:
        targets = ["cloudflare", "github", "local"]
        targets = [t for t in targets if t != args.source]
    elif args.targets:
        targets = [t.strip() for t in args.targets.split(",")]
    else:
        targets = ["cloudflare", "github"]

    # Run sync
    report = await run_sync(
        source=args.source,
        targets=targets,
        force=args.force,
        resolve=args.resolve,
        entry_type=args.type
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        exit_code = print_sync_report(report, args.verbose)
        sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
