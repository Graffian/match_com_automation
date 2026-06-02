import csv
import random
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ProxyManager:
    """
    Manages a pool of proxies for account creation.
    Each proxy should be assigned to a device to avoid
    IP-based rate limiting.
    """

    def __init__(self, proxy_file: str = None, rotation: str = "round_robin"):
        self.proxies: list[str] = []
        self.rotation = rotation
        self._index = 0

        if proxy_file and Path(proxy_file).exists():
            self._load(proxy_file)

    def _load(self, path: str):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    self.proxies.append(line)
        logger.info("Loaded %d proxies from %s", len(self.proxies), path)

    def get_next(self) -> Optional[str]:
        if not self.proxies:
            return None

        if self.rotation == "random":
            return random.choice(self.proxies)

        proxy = self.proxies[self._index % len(self.proxies)]
        self._index += 1
        return proxy

    def assign_to_devices(self, device_count: int) -> list[str]:
        """Assign (possibly recycling) proxies to N devices."""
        if not self.proxies:
            return [""] * device_count

        assigned = []
        for i in range(device_count):
            if self.rotation == "random":
                assigned.append(random.choice(self.proxies))
            else:
                assigned.append(self.proxies[i % len(self.proxies)])
        return assigned

    def parse_proxy(self, proxy_str: str) -> dict:
        """Parse proxy string into Appium-compatible proxy config."""
        if not proxy_str:
            return {}
        parts = proxy_str.split(":")
        if len(parts) == 2:
            host, port = parts
            return {"http": f"http://{host}:{port}", "https": f"http://{host}:{port}"}
        elif len(parts) == 4:
            host, port, user, pwd = parts
            return {
                "http": f"http://{user}:{pwd}@{host}:{port}",
                "https": f"http://{user}:{pwd}@{host}:{port}",
            }
        return {}
