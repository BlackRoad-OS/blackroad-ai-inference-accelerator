#!/usr/bin/env python3
"""
BlackRoad Endpoint Validation Script

Validates all configured endpoints before PR creation.
Run this script to ensure all integrations are working.

Usage:
    python scripts/validate_endpoints.py --all
    python scripts/validate_endpoints.py --endpoint cloudflare
    python scripts/validate_endpoints.py --retry 3 --backoff

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

from src.endpoints.client import EndpointManager, check_all_endpoints
from src.hashing.sha_infinity import sha256_hash


async def validate_single_endpoint(manager: EndpointManager, name: str) -> dict:
    """Validate a single endpoint."""
    client = manager.get_client(name)
    if not client:
        return {
            "name": name,
            "status": "not_found",
            "healthy": False,
            "error": f"Endpoint '{name}' not configured"
        }

    try:
        health = await client.health_check()
        return {
            "name": name,
            "status": "checked",
            "healthy": health.healthy,
            "latency_ms": health.latency_ms,
            "status_code": health.status_code,
            "error": health.error
        }
    except Exception as e:
        return {
            "name": name,
            "status": "error",
            "healthy": False,
            "error": str(e)
        }


async def validate_all_endpoints(retry: int = 1, backoff: bool = False) -> dict:
    """Validate all endpoints with optional retry."""
    manager = EndpointManager()

    results = {}
    backoff_times = [2, 4, 8, 16]

    for name in manager.clients.keys():
        for attempt in range(retry):
            result = await validate_single_endpoint(manager, name)
            results[name] = result

            if result["healthy"]:
                break

            if attempt < retry - 1 and backoff:
                wait_time = backoff_times[min(attempt, len(backoff_times) - 1)]
                print(f"  Retrying {name} in {wait_time}s...")
                await asyncio.sleep(wait_time)

    await manager.close_all()

    # Generate report
    healthy_count = sum(1 for r in results.values() if r["healthy"])
    total_count = len(results)

    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "all_healthy": healthy_count == total_count,
        "summary": f"{healthy_count}/{total_count} endpoints healthy",
        "validation_hash": sha256_hash(results),
        "endpoints": results
    }

    return report


def print_report(report: dict, verbose: bool = False):
    """Print validation report."""
    print("\n" + "=" * 60)
    print("BLACKROAD ENDPOINT VALIDATION REPORT")
    print("=" * 60)
    print(f"Timestamp: {report['timestamp']}")
    print(f"Status: {'PASS' if report['all_healthy'] else 'FAIL'}")
    print(f"Summary: {report['summary']}")
    print(f"Hash: {report['validation_hash'][:16]}...")
    print("-" * 60)

    for name, result in report['endpoints'].items():
        status_icon = "OK" if result['healthy'] else "FAIL"
        latency = result.get('latency_ms', 0)

        print(f"[{status_icon}] {name}")
        if verbose or not result['healthy']:
            if latency:
                print(f"     Latency: {latency:.0f}ms")
            if result.get('status_code'):
                print(f"     Status: {result['status_code']}")
            if result.get('error'):
                print(f"     Error: {result['error']}")

    print("=" * 60)

    if not report['all_healthy']:
        print("\nWARNING: Some endpoints are unhealthy!")
        print("Fix issues before creating PR.")
        return 1

    print("\nAll endpoints validated successfully!")
    return 0


async def main():
    parser = argparse.ArgumentParser(description="Validate BlackRoad endpoints")
    parser.add_argument("--all", action="store_true", help="Validate all endpoints")
    parser.add_argument("--endpoint", type=str, help="Validate specific endpoint")
    parser.add_argument("--retry", type=int, default=1, help="Number of retries")
    parser.add_argument("--backoff", action="store_true", help="Use exponential backoff")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.endpoint:
        manager = EndpointManager()
        result = await validate_single_endpoint(manager, args.endpoint)
        await manager.close_all()

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_report({"endpoints": {args.endpoint: result}, "all_healthy": result["healthy"], "timestamp": datetime.utcnow().isoformat(), "summary": "", "validation_hash": ""}, args.verbose)
        sys.exit(0 if result["healthy"] else 1)

    else:  # Default to --all
        report = await validate_all_endpoints(args.retry, args.backoff)

        if args.json:
            print(json.dumps(report, indent=2))
            sys.exit(0 if report['all_healthy'] else 1)
        else:
            exit_code = print_report(report, args.verbose)
            sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
