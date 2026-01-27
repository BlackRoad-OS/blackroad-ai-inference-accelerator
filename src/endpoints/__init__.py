"""
BlackRoad Endpoints Module

Universal endpoint client for all integrations.
"""

from .client import (
    EndpointManager,
    EndpointClient,
    CloudflareClient,
    SalesforceClient,
    ClaudeClient,
    VercelClient,
    DigitalOceanClient,
    GitHubClient,
    RaspberryPiClient,
    check_all_endpoints
)

__all__ = [
    "EndpointManager",
    "EndpointClient",
    "CloudflareClient",
    "SalesforceClient",
    "ClaudeClient",
    "VercelClient",
    "DigitalOceanClient",
    "GitHubClient",
    "RaspberryPiClient",
    "check_all_endpoints"
]
