"""Auto-fetch and refresh proxies from multiple sources."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

import httpx
import structlog
from bs4 import BeautifulSoup

from .proxy import ProxyPool, Proxy


class FreeProxyFetcher:
    """Fetch free proxies from public sources."""

    def __init__(self):
        self.logger = structlog.get_logger()
        self.sources = [
            self._fetch_free_proxy_list,
            self._fetch_proxy_scrape,
            self._fetch_geonode,
            self._fetch_spys,
            self._fetch_openproxy,
            self._fetch_proxyscrape_raw,
            self._fetch_pubproxy,
            self._fetch_speedx,
            self._fetch_monosans,
            self._fetch_roosterkid,
            self._fetch_proxylistplus,
            self._fetch_freshproxylist,
        ]

    async def fetch_all(self, limit: int = 100) -> list[str]:
        """Fetch proxies from all sources."""
        all_proxies = []

        for source in self.sources:
            try:
                proxies = await source(limit // len(self.sources))
                all_proxies.extend(proxies)
                self.logger.info("proxies_fetched", source=source.__name__, count=len(proxies))
            except Exception as e:
                self.logger.warning("proxy_fetch_failed", source=source.__name__, error=str(e))

        # Deduplicate
        unique = list(set(all_proxies))
        self.logger.info("total_proxies_fetched", count=len(unique))
        return unique[:limit]

    async def _fetch_free_proxy_list(self, limit: int = 50) -> list[str]:
        """Fetch from free-proxy-list.net"""
        proxies = []
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://free-proxy-list.net/",
                    timeout=15,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                soup = BeautifulSoup(response.text, "lxml")
                table = soup.find("table", class_="table")
                if table:
                    for row in table.find_all("tr")[1:limit+1]:
                        cols = row.find_all("td")
                        if len(cols) >= 7:
                            ip = cols[0].text.strip()
                            port = cols[1].text.strip()
                            protocol = "https" if cols[6].text.strip() == "yes" else "http"
                            proxies.append(f"{protocol}://{ip}:{port}")
            except Exception as e:
                self.logger.warning("free_proxy_list_failed", error=str(e))
        return proxies

    async def _fetch_proxy_scrape(self, limit: int = 50) -> list[str]:
        """Fetch from proxy-scrape.com API"""
        proxies = []
        async with httpx.AsyncClient() as client:
            try:
                # HTTP proxies
                response = await client.get(
                    "https://api.proxyscrape.com/v2/",
                    params={
                        "request": "getproxies",
                        "protocol": "http",
                        "timeout": "5000",
                        "country": "US,GB,DE,FR,NL",
                        "ssl": "yes",
                        "anonymity": "elite",
                    },
                    timeout=15,
                )
                if response.status_code == 200:
                    for line in response.text.strip().split("\n")[:limit//2]:
                        line = line.strip()
                        if line and ":" in line:
                            proxies.append(f"http://{line}")

                # SOCKS5 proxies
                response = await client.get(
                    "https://api.proxyscrape.com/v2/",
                    params={
                        "request": "getproxies",
                        "protocol": "socks5",
                        "timeout": "5000",
                        "country": "US,GB,DE,FR,NL",
                    },
                    timeout=15,
                )
                if response.status_code == 200:
                    for line in response.text.strip().split("\n")[:limit//2]:
                        line = line.strip()
                        if line and ":" in line:
                            proxies.append(f"socks5://{line}")
            except Exception as e:
                self.logger.warning("proxy_scrape_failed", error=str(e))
        return proxies

    async def _fetch_geonode(self, limit: int = 50) -> list[str]:
        """Fetch from Geonode API"""
        proxies = []
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://proxylist.geonode.com/api/proxy-list",
                    params={
                        "limit": limit,
                        "page": 1,
                        "sort_by": "lastChecked",
                        "sort_type": "desc",
                        "protocols": "http,https,socks5",
                        "speed": "fast",
                    },
                    timeout=15,
                )
                if response.status_code == 200:
                    data = response.json()
                    for proxy in data.get("data", []):
                        ip = proxy.get("ip")
                        port = proxy.get("port")
                        protocols = proxy.get("protocols", [])
                        if ip and port:
                            proto = "socks5" if "socks5" in protocols else "https" if "https" in protocols else "http"
                            proxies.append(f"{proto}://{ip}:{port}")
            except Exception as e:
                self.logger.warning("geonode_failed", error=str(e))
        return proxies

    async def _fetch_spys(self, limit: int = 50) -> list[str]:
        """Fetch from spys.one"""
        proxies = []
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://spys.one/free-proxy-list/",
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=15,
                )
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "lxml")
                    table = soup.find("table", class_="proxy-table")
                    if table:
                        for row in table.find_all("tr")[1:limit+1]:
                            cols = row.find_all("td")
                            if cols:
                                text = cols[0].text.strip()
                                if ":" in text:
                                    proxies.append(f"http://{text}")
            except Exception as e:
                self.logger.warning("spys_failed", error=str(e))
        return proxies

    async def _fetch_openproxy(self, limit: int = 50) -> list[str]:
        """Fetch from openproxy.space"""
        proxies = []
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://openproxy.space/list.txt",
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=15,
                )
                if response.status_code == 200:
                    for line in response.text.strip().split("\n")[:limit]:
                        line = line.strip()
                        if line and ":" in line and not line.startswith("#"):
                            proxies.append(f"http://{line}")
            except Exception as e:
                self.logger.warning("openproxy_failed", error=str(e))
        return proxies

    async def _fetch_proxyscrape_raw(self, limit: int = 50) -> list[str]:
        """Fetch raw proxy list from proxyscrape.com"""
        proxies = []
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://api.proxyscrape.com/v2/",
                    params={
                        "request": "getproxies",
                        "protocol": "http",
                        "timeout": "10000",
                        "ssl": "yes",
                        "anonymity": "elite",
                    },
                    timeout=15,
                )
                if response.status_code == 200:
                    for line in response.text.strip().split("\n")[:limit]:
                        line = line.strip()
                        if line and ":" in line:
                            proxies.append(f"http://{line}")
            except Exception as e:
                self.logger.warning("proxyscrape_raw_failed", error=str(e))
        return proxies

    async def _fetch_pubproxy(self, limit: int = 50) -> list[str]:
        """Fetch from pubproxy.com"""
        proxies = []
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "http://pubproxy.com/api/proxy",
                    params={
                        "limit": limit,
                        "type": "http",
                        "level": "elite",
                        "https": "true",
                    },
                    timeout=15,
                )
                if response.status_code == 200:
                    data = response.json()
                    for p in data.get("data", []):
                        ip = p.get("ip")
                        port = p.get("port")
                        if ip and port:
                            proxies.append(f"http://{ip}:{port}")
            except Exception as e:
                self.logger.warning("pubproxy_failed", error=str(e))
        return proxies

    async def _fetch_speedx(self, limit: int = 50) -> list[str]:
        """Fetch from thespeedx.com proxy list"""
        proxies = []
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=15,
                )
                if response.status_code == 200:
                    for line in response.text.strip().split("\n")[:limit]:
                        line = line.strip()
                        if line and ":" in line:
                            proxies.append(f"http://{line}")
            except Exception as e:
                self.logger.warning("speedx_failed", error=str(e))
        return proxies

    async def _fetch_monosans(self, limit: int = 50) -> list[str]:
        """Fetch from monosans proxy list"""
        proxies = []
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=15,
                )
                if response.status_code == 200:
                    for line in response.text.strip().split("\n")[:limit]:
                        line = line.strip()
                        if line and ":" in line:
                            proxies.append(f"http://{line}")
            except Exception as e:
                self.logger.warning("monosans_failed", error=str(e))
        return proxies

    async def _fetch_roosterkid(self, limit: int = 50) -> list[str]:
        """Fetch from roosterkid proxy list"""
        proxies = []
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=15,
                )
                if response.status_code == 200:
                    for line in response.text.strip().split("\n")[:limit]:
                        line = line.strip()
                        if line and ":" in line and not line.startswith("#"):
                            proxies.append(f"http://{line}")
            except Exception as e:
                self.logger.warning("roosterkid_failed", error=str(e))
        return proxies

    async def _fetch_proxylistplus(self, limit: int = 50) -> list[str]:
        """Fetch from proxylistplus.com"""
        proxies = []
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=15,
                )
                if response.status_code == 200:
                    for line in response.text.strip().split("\n")[:limit]:
                        line = line.strip()
                        if line and ":" in line:
                            proxies.append(f"http://{line}")
            except Exception as e:
                self.logger.warning("proxylistplus_failed", error=str(e))
        return proxies

    async def _fetch_freshproxylist(self, limit: int = 50) -> list[str]:
        """Fetch from freshproxylist.com"""
        proxies = []
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://www.freshproxylist.com/out.php?q=",
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=15,
                )
                if response.status_code == 200:
                    for line in response.text.strip().split("\n")[:limit]:
                        line = line.strip()
                        if line and ":" in line:
                            proxies.append(f"http://{line}")
            except Exception as e:
                self.logger.warning("freshproxylist_failed", error=str(e))
        return proxies


class ProxyProvider:
    """Interface for paid proxy providers."""

    def __init__(self, provider: str, api_key: str, **kwargs):
        self.provider = provider
        self.api_key = api_key
        self.logger = structlog.get_logger()
        self.config = kwargs

    async def get_proxies(self, count: int = 10) -> list[str]:
        """Get proxies from provider."""
        if self.provider == "brightdata":
            return await self._brightdata(count)
        elif self.provider == "smartproxy":
            return await self._smartproxy(count)
        elif self.provider == "oxylabs":
            return await self._oxylabs(count)
        elif self.provider == "proxyrack":
            return await self._proxyrack(count)
        else:
            self.logger.error("unknown_provider", provider=self.provider)
            return []

    async def _brightdata(self, count: int) -> list[str]:
        """Bright Data (Luminati) proxy."""
        # Bright Data uses hostname:port with auth
        host = self.config.get("host", "brd.superproxy.io")
        port = self.config.get("port", 22225)
        username = self.config.get("username", f"brd-customer-{self.api_key}")
        password = self.config.get("password", "")

        proxies = []
        for i in range(count):
            session_id = f"session_{i}"
            proxies.append(
                f"http://{username}-session-{session_id}:{password}@{host}:{port}"
            )
        return proxies

    async def _smartproxy(self, count: int) -> list[str]:
        """SmartProxy."""
        host = self.config.get("host", "gate.smartproxy.com")
        port = self.config.get("port", 7000)
        username = self.config.get("username", self.api_key)
        password = self.config.get("password", "")

        proxies = []
        for i in range(count):
            session_id = f"session_{i}"
            proxies.append(
                f"http://{username}-session-{session_id}:{password}@{host}:{port}"
            )
        return proxies

    async def _oxylabs(self, count: int) -> list[str]:
        """Oxylabs."""
        host = self.config.get("host", "pr.oxylabs.io")
        port = self.config.get("port", 7777)
        username = self.config.get("username", "customer-{self.api_key}")
        password = self.config.get("password", "")

        proxies = []
        for i in range(count):
            session_id = f"session_{i}"
            proxies.append(
                f"http://{username}-session-{session_id}:{password}@{host}:{port}"
            )
        return proxies

    async def _proxyrack(self, count: int) -> list[str]:
        """ProxyRack."""
        # ProxyRack uses API to get proxy list
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.proxyrack.net/api/proxy",
                params={"api_key": self.api_key, "count": count},
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                return [f"http://{p['ip']}:{p['port']}" for p in data.get("proxies", [])]
        return []


class ProxyRefresher:
    """Auto-refresh proxy pool to prevent exhaustion."""

    def __init__(
        self,
        pool: ProxyPool,
        min_proxies: int = 10,
        refresh_interval: int = 300,  # 5 minutes
        fetch_free: bool = True,
        providers: list[dict] | None = None,
    ):
        self.pool = pool
        self.min_proxies = min_proxies
        self.refresh_interval = refresh_interval
        self.fetch_free = fetch_free
        self.providers = [
            ProxyProvider(**p) for p in (providers or [])
        ]
        self.free_fetcher = FreeProxyFetcher() if fetch_free else None
        self.logger = structlog.get_logger()
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start background refresh loop."""
        self._running = True
        self._task = asyncio.create_task(self._refresh_loop())
        self.logger.info("proxy_refresher_started")

    async def stop(self) -> None:
        """Stop refresh loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.logger.info("proxy_refresher_stopped")

    async def _refresh_loop(self) -> None:
        """Background loop to refresh proxies."""
        while self._running:
            try:
                await asyncio.sleep(self.refresh_interval)
                await self.refresh_if_needed()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("refresh_loop_error", error=str(e))
                await asyncio.sleep(60)

    async def refresh_if_needed(self) -> int:
        """Refresh proxies if pool is low."""
        stats = self.pool.get_stats()
        healthy = stats["healthy"]

        if healthy >= self.min_proxies:
            self.logger.debug("proxy_pool_sufficient", healthy=healthy)
            return 0

        needed = self.min_proxies - healthy
        self.logger.info("proxy_pool_low", healthy=healthy, needed=needed)

        new_proxies = []

        # Fetch from paid providers first (more reliable)
        for provider in self.providers:
            try:
                proxies = await provider.get_proxies(needed // max(len(self.providers), 1))
                new_proxies.extend(proxies)
            except Exception as e:
                self.logger.warning("provider_fetch_failed", error=str(e))

        # Fill remaining with free proxies
        if len(new_proxies) < needed and self.free_fetcher:
            try:
                free = await self.free_fetcher.fetch_all(needed - len(new_proxies))
                new_proxies.extend(free)
            except Exception as e:
                self.logger.warning("free_fetch_failed", error=str(e))

        # Add to pool
        for proxy_url in new_proxies:
            self.pool.add_proxy(proxy_url)

        self.logger.info("proxies_refreshed", count=len(new_proxies))
        return len(new_proxies)

    async def force_refresh(self) -> int:
        """Force refresh regardless of pool size."""
        self.logger.info("forcing_proxy_refresh")
        return await self.refresh_if_needed()


class RotatingProxyManager:
    """High-level proxy management with auto-rotation and refresh."""

    def __init__(
        self,
        proxies: list[str] | None = None,
        proxy_file: str | None = None,
        auto_refresh: bool = True,
        min_proxies: int = 10,
        providers: list[dict] | None = None,
    ):
        self.pool = ProxyPool(proxies)
        self.refresher: ProxyRefresher | None = None

        if proxy_file:
            self.pool.load_from_file(proxy_file)

        if auto_refresh:
            self.refresher = ProxyRefresher(
                pool=self.pool,
                min_proxies=min_proxies,
                providers=providers,
            )

        self.logger = structlog.get_logger()

    async def start(self) -> None:
        """Start proxy management."""
        # Initial refresh if pool is empty
        if not self.pool._proxies:
            await self.refresher.force_refresh() if self.refresher else None

        if self.refresher:
            await self.refresher.start()

        self.logger.info("proxy_manager_started", pool_size=len(self.pool._proxies))

    async def stop(self) -> None:
        """Stop proxy management."""
        if self.refresher:
            await self.refresher.stop()

    def get_client(self, **kwargs):
        """Get a proxy-aware HTTP client."""
        from .proxy import ProxyAwareClient
        return ProxyAwareClient(pool=self.pool, **kwargs)

    def get_stats(self) -> dict:
        """Get proxy statistics."""
        stats = self.pool.get_stats()
        if self.refresher:
            stats["auto_refresh"] = True
        return stats
