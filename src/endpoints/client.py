#!/usr/bin/env python3
"""
BlackRoad Universal Endpoint Client

Unified client for all configured endpoints:
- Cloud: Cloudflare, Vercel, DigitalOcean
- CRM: Salesforce
- AI: Claude, Ollama
- Edge: Raspberry Pi fleet
- Mobile: Termius, iSH, Shellfish, Working Copy, Pyto
- VCS: GitHub

Author: BlackRoad OS Team
License: Proprietary - BlackRoad OS License
"""

import os
import json
import time
import asyncio
import aiohttp
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import yaml
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("blackroad.endpoints")


class EndpointType(Enum):
    """Endpoint categories."""
    CLOUD = "cloud"
    CRM = "crm"
    AI = "ai"
    AI_LOCAL = "ai_local"
    EDGE = "edge"
    MOBILE = "mobile"
    VCS = "vcs"
    DATABASE = "database"
    CACHE = "cache"
    DEPLOYMENT = "deployment"
    MODEL_HUB = "model_hub"
    SSH_MANAGEMENT = "ssh_management"
    FILE_TRANSFER = "file_transfer"
    GIT_CLIENT = "git_client"
    PYTHON_IDE = "python_ide"


class AuthType(Enum):
    """Authentication types."""
    API_KEY = "api_key"
    BEARER = "bearer"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    X_API_KEY = "x-api-key"
    NONE = "none"


@dataclass
class EndpointHealth:
    """Health check result."""
    name: str
    healthy: bool
    latency_ms: float
    status_code: Optional[int] = None
    error: Optional[str] = None
    checked_at: float = field(default_factory=time.time)


@dataclass
class EndpointConfig:
    """Configuration for an endpoint."""
    name: str
    type: EndpointType
    enabled: bool
    base_url: str
    auth_type: AuthType
    env_var: Optional[str] = None
    rate_limit: Optional[Dict[str, int]] = None
    timeout: int = 30
    retry_attempts: int = 3
    retry_backoff: List[int] = field(default_factory=lambda: [2, 4, 8, 16])


class EndpointClient:
    """
    Universal endpoint client with retry logic and health monitoring.
    """

    def __init__(self, config: EndpointConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_request_time = 0
        self._request_count = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )
        return self.session

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        headers = {}

        if not self.config.env_var:
            return headers

        token = os.getenv(self.config.env_var)
        if not token:
            logger.warning(f"No token found for {self.config.name}")
            return headers

        if self.config.auth_type == AuthType.BEARER:
            headers["Authorization"] = f"Bearer {token}"
        elif self.config.auth_type == AuthType.API_KEY:
            headers["Authorization"] = f"ApiKey {token}"
        elif self.config.auth_type == AuthType.X_API_KEY:
            headers["x-api-key"] = token

        return headers

    async def request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Tuple[int, Any]:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method
            path: URL path
            data: Request body
            params: Query parameters
            headers: Additional headers

        Returns:
            Tuple of (status_code, response_data)
        """
        url = f"{self.config.base_url}{path}"
        request_headers = {
            "Content-Type": "application/json",
            **self._get_auth_headers(),
            **(headers or {})
        }

        session = await self._get_session()

        for attempt in range(self.config.retry_attempts):
            try:
                async with session.request(
                    method,
                    url,
                    json=data,
                    params=params,
                    headers=request_headers
                ) as response:
                    try:
                        body = await response.json()
                    except:
                        body = await response.text()

                    return response.status, body

            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
            except aiohttp.ClientError as e:
                logger.warning(f"Client error on attempt {attempt + 1}: {e}")

            if attempt < self.config.retry_attempts - 1:
                backoff = self.config.retry_backoff[min(attempt, len(self.config.retry_backoff) - 1)]
                await asyncio.sleep(backoff)

        return 0, {"error": "Max retries exceeded"}

    async def health_check(self) -> EndpointHealth:
        """Perform health check on the endpoint."""
        start = time.time()

        try:
            status, _ = await self.request("GET", "/health")
            latency = (time.time() - start) * 1000

            return EndpointHealth(
                name=self.config.name,
                healthy=200 <= status < 300,
                latency_ms=latency,
                status_code=status
            )
        except Exception as e:
            return EndpointHealth(
                name=self.config.name,
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                error=str(e)
            )

    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()


class CloudflareClient(EndpointClient):
    """Cloudflare-specific client."""

    def __init__(self, account_id: Optional[str] = None):
        config = EndpointConfig(
            name="Cloudflare",
            type=EndpointType.CLOUD,
            enabled=True,
            base_url=f"https://api.cloudflare.com/client/v4/accounts/{account_id or os.getenv('CLOUDFLARE_ACCOUNT_ID', '')}",
            auth_type=AuthType.BEARER,
            env_var="CLOUDFLARE_API_TOKEN"
        )
        super().__init__(config)

    async def kv_get(self, namespace_id: str, key: str) -> Optional[str]:
        """Get value from KV."""
        status, data = await self.request(
            "GET",
            f"/storage/kv/namespaces/{namespace_id}/values/{key}"
        )
        return data if status == 200 else None

    async def kv_put(self, namespace_id: str, key: str, value: str) -> bool:
        """Put value to KV."""
        status, _ = await self.request(
            "PUT",
            f"/storage/kv/namespaces/{namespace_id}/values/{key}",
            data=value
        )
        return status == 200

    async def workers_deploy(self, script_name: str, script_content: str) -> bool:
        """Deploy a Worker script."""
        status, _ = await self.request(
            "PUT",
            f"/workers/scripts/{script_name}",
            data={"script": script_content}
        )
        return status == 200

    async def health_check(self) -> EndpointHealth:
        """Check Cloudflare API access."""
        start = time.time()
        status, data = await self.request("GET", "")
        latency = (time.time() - start) * 1000

        return EndpointHealth(
            name="Cloudflare",
            healthy=status == 200 and data.get("success", False),
            latency_ms=latency,
            status_code=status
        )


class SalesforceClient(EndpointClient):
    """Salesforce CRM client."""

    def __init__(self, instance_url: Optional[str] = None):
        config = EndpointConfig(
            name="Salesforce",
            type=EndpointType.CRM,
            enabled=True,
            base_url=instance_url or os.getenv("SALESFORCE_INSTANCE_URL", ""),
            auth_type=AuthType.BEARER,
            env_var="SALESFORCE_ACCESS_TOKEN"
        )
        super().__init__(config)
        self.api_version = "v59.0"

    async def query(self, soql: str) -> List[Dict]:
        """Execute a SOQL query."""
        status, data = await self.request(
            "GET",
            f"/services/data/{self.api_version}/query",
            params={"q": soql}
        )
        return data.get("records", []) if status == 200 else []

    async def get_sobject(self, sobject: str, record_id: str) -> Optional[Dict]:
        """Get a single sObject record."""
        status, data = await self.request(
            "GET",
            f"/services/data/{self.api_version}/sobjects/{sobject}/{record_id}"
        )
        return data if status == 200 else None

    async def upsert_sobject(
        self,
        sobject: str,
        external_id_field: str,
        external_id: str,
        data: Dict
    ) -> bool:
        """Upsert a record."""
        status, _ = await self.request(
            "PATCH",
            f"/services/data/{self.api_version}/sobjects/{sobject}/{external_id_field}/{external_id}",
            data=data
        )
        return status in [200, 201, 204]


class ClaudeClient(EndpointClient):
    """Anthropic Claude API client."""

    def __init__(self):
        config = EndpointConfig(
            name="Claude",
            type=EndpointType.AI,
            enabled=True,
            base_url="https://api.anthropic.com/v1",
            auth_type=AuthType.X_API_KEY,
            env_var="ANTHROPIC_API_KEY",
            rate_limit={"requests_per_minute": 50}
        )
        super().__init__(config)

    async def send_message(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-haiku-3-5-20241022",
        max_tokens: int = 1024,
        system: Optional[str] = None
    ) -> Optional[str]:
        """Send a message to Claude."""
        data = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages
        }
        if system:
            data["system"] = system

        status, response = await self.request("POST", "/messages", data=data)

        if status == 200 and "content" in response:
            return response["content"][0].get("text")
        return None

    async def health_check(self) -> EndpointHealth:
        """Check Claude API access with a minimal request."""
        start = time.time()

        try:
            response = await self.send_message(
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            latency = (time.time() - start) * 1000

            return EndpointHealth(
                name="Claude",
                healthy=response is not None,
                latency_ms=latency,
                status_code=200 if response else 0
            )
        except Exception as e:
            return EndpointHealth(
                name="Claude",
                healthy=False,
                latency_ms=(time.time() - start) * 1000,
                error=str(e)
            )


class VercelClient(EndpointClient):
    """Vercel deployment client."""

    def __init__(self):
        config = EndpointConfig(
            name="Vercel",
            type=EndpointType.DEPLOYMENT,
            enabled=True,
            base_url="https://api.vercel.com",
            auth_type=AuthType.BEARER,
            env_var="VERCEL_TOKEN"
        )
        super().__init__(config)

    async def list_projects(self) -> List[Dict]:
        """List all projects."""
        status, data = await self.request("GET", "/v9/projects")
        return data.get("projects", []) if status == 200 else []

    async def create_deployment(self, project_id: str, files: Dict[str, str]) -> Optional[Dict]:
        """Create a new deployment."""
        status, data = await self.request(
            "POST",
            "/v13/deployments",
            data={"projectId": project_id, "files": files}
        )
        return data if status == 200 else None

    async def health_check(self) -> EndpointHealth:
        """Check Vercel API access."""
        start = time.time()
        status, data = await self.request("GET", "/v2/user")
        latency = (time.time() - start) * 1000

        return EndpointHealth(
            name="Vercel",
            healthy=status == 200,
            latency_ms=latency,
            status_code=status
        )


class DigitalOceanClient(EndpointClient):
    """DigitalOcean client."""

    def __init__(self):
        config = EndpointConfig(
            name="DigitalOcean",
            type=EndpointType.CLOUD,
            enabled=True,
            base_url="https://api.digitalocean.com/v2",
            auth_type=AuthType.BEARER,
            env_var="DIGITALOCEAN_TOKEN"
        )
        super().__init__(config)

    async def list_droplets(self) -> List[Dict]:
        """List all droplets."""
        status, data = await self.request("GET", "/droplets")
        return data.get("droplets", []) if status == 200 else []

    async def create_droplet(
        self,
        name: str,
        region: str,
        size: str,
        image: str
    ) -> Optional[Dict]:
        """Create a new droplet."""
        status, data = await self.request(
            "POST",
            "/droplets",
            data={
                "name": name,
                "region": region,
                "size": size,
                "image": image
            }
        )
        return data.get("droplet") if status == 202 else None


class RaspberryPiClient(EndpointClient):
    """Raspberry Pi fleet client."""

    def __init__(self, host: str, port: int = 8080):
        config = EndpointConfig(
            name=f"RaspberryPi@{host}",
            type=EndpointType.EDGE,
            enabled=True,
            base_url=f"http://{host}:{port}",
            auth_type=AuthType.NONE,
            timeout=10
        )
        super().__init__(config)
        self.host = host

    async def inference(self, model: str, input_data: Dict) -> Optional[Dict]:
        """Run inference on the Pi."""
        status, data = await self.request(
            "POST",
            "/v1/inference",
            data={"model": model, "input": input_data}
        )
        return data if status == 200 else None

    async def health_check(self) -> EndpointHealth:
        """Check Pi health."""
        start = time.time()
        status, data = await self.request("GET", "/health")
        latency = (time.time() - start) * 1000

        return EndpointHealth(
            name=f"Pi@{self.host}",
            healthy=status == 200 and data.get("status") == "healthy",
            latency_ms=latency,
            status_code=status
        )


class GitHubClient(EndpointClient):
    """GitHub API client."""

    def __init__(self):
        config = EndpointConfig(
            name="GitHub",
            type=EndpointType.VCS,
            enabled=True,
            base_url="https://api.github.com",
            auth_type=AuthType.BEARER,
            env_var="GITHUB_TOKEN"
        )
        super().__init__(config)

    async def get_repo(self, owner: str, repo: str) -> Optional[Dict]:
        """Get repository info."""
        status, data = await self.request("GET", f"/repos/{owner}/{repo}")
        return data if status == 200 else None

    async def list_prs(self, owner: str, repo: str, state: str = "open") -> List[Dict]:
        """List pull requests."""
        status, data = await self.request(
            "GET",
            f"/repos/{owner}/{repo}/pulls",
            params={"state": state}
        )
        return data if status == 200 else []

    async def create_pr(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str
    ) -> Optional[Dict]:
        """Create a pull request."""
        status, data = await self.request(
            "POST",
            f"/repos/{owner}/{repo}/pulls",
            data={
                "title": title,
                "head": head,
                "base": base,
                "body": body
            }
        )
        return data if status == 201 else None


class EndpointManager:
    """
    Manages all endpoint clients.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/endpoints.yaml"
        self.clients: Dict[str, EndpointClient] = {}
        self._init_clients()

    def _init_clients(self):
        """Initialize all enabled clients."""
        # Core clients
        self.clients["cloudflare"] = CloudflareClient()
        self.clients["salesforce"] = SalesforceClient()
        self.clients["claude"] = ClaudeClient()
        self.clients["vercel"] = VercelClient()
        self.clients["digitalocean"] = DigitalOceanClient()
        self.clients["github"] = GitHubClient()

        # Pi fleet from environment
        pi_hosts = os.getenv("PI_FLEET_HOSTS", "").split(",")
        for i, host in enumerate(pi_hosts):
            if host.strip():
                self.clients[f"pi-{i}"] = RaspberryPiClient(host.strip())

    def get_client(self, name: str) -> Optional[EndpointClient]:
        """Get a client by name."""
        return self.clients.get(name)

    async def health_check_all(self) -> Dict[str, EndpointHealth]:
        """Run health checks on all endpoints."""
        results = {}

        tasks = [
            (name, client.health_check())
            for name, client in self.clients.items()
        ]

        for name, task in tasks:
            try:
                results[name] = await task
            except Exception as e:
                results[name] = EndpointHealth(
                    name=name,
                    healthy=False,
                    latency_ms=0,
                    error=str(e)
                )

        return results

    async def close_all(self):
        """Close all client sessions."""
        for client in self.clients.values():
            await client.close()

    def get_health_report(self, results: Dict[str, EndpointHealth]) -> Dict[str, Any]:
        """Generate a health report."""
        healthy_count = sum(1 for r in results.values() if r.healthy)
        total_count = len(results)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "healthy_count": healthy_count,
            "total_count": total_count,
            "all_healthy": healthy_count == total_count,
            "endpoints": {
                name: {
                    "healthy": r.healthy,
                    "latency_ms": r.latency_ms,
                    "status_code": r.status_code,
                    "error": r.error
                }
                for name, r in results.items()
            }
        }


# Convenience functions
async def check_all_endpoints() -> Dict[str, Any]:
    """Check all configured endpoints."""
    manager = EndpointManager()
    results = await manager.health_check_all()
    report = manager.get_health_report(results)
    await manager.close_all()
    return report


if __name__ == "__main__":
    async def main():
        print("BlackRoad Endpoint Client Demo")
        print("=" * 50)

        manager = EndpointManager()

        print("\nRunning health checks...")
        results = await manager.health_check_all()
        report = manager.get_health_report(results)

        print(f"\nHealth Report:")
        print(f"  All Healthy: {report['all_healthy']}")
        print(f"  Healthy: {report['healthy_count']}/{report['total_count']}")

        print("\nEndpoints:")
        for name, status in report['endpoints'].items():
            icon = "OK" if status['healthy'] else "FAIL"
            print(f"  [{icon}] {name}: {status['latency_ms']:.0f}ms")
            if status['error']:
                print(f"       Error: {status['error']}")

        await manager.close_all()

    asyncio.run(main())
