import time
import logging
from dataclasses import dataclass, field
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from .client import VMOSClient

logger = logging.getLogger(__name__)


@dataclass
class DeviceInstance:
    device_id: str
    name: str
    serial: str = ""
    adb_host: str = ""
    adb_port: int = 0
    status: str = "created"
    proxy: str = ""
    session_id: str = ""
    busy: bool = False

    @property
    def adb_connected(self) -> bool:
        return bool(self.adb_host and self.adb_port)

    @property
    def appium_desired_caps(self) -> dict:
        caps = {
            "platformName": "Android",
            "deviceName": self.name,
            "udid": self.serial or self.device_id,
            "noReset": False,
            "fullReset": False,
            "automationName": "UiAutomator2",
            "adbPort": self.adb_port,
            "adbHost": self.adb_host,
        }
        if self.proxy:
            caps["proxy"] = self.proxy
        return caps


class DeviceManager:
    """
    Manages a pool of VMOS Cloud Phone instances.
    Handles creation, lifecycle, and connection details.
    """

    def __init__(self, client: VMOSClient = None, max_devices: int = 20):
        self.client = client or VMOSClient()
        self.max_devices = max_devices
        self._devices: dict[str, DeviceInstance] = {}

    @property
    def available_devices(self) -> list[DeviceInstance]:
        return [d for d in self._devices.values() if not d.busy]

    @property
    def all_devices(self) -> list[DeviceInstance]:
        return list(self._devices.values())

    def discover_existing(self):
        """Load existing cloud phone instances from VMOS."""
        raw_list = self.client.list_devices()
        for item in raw_list:
            dev = DeviceInstance(
                device_id=item["device_id"],
                name=item.get("name", item["device_id"]),
                serial=item.get("serial", ""),
                status=item.get("status", "unknown"),
            )
            self._devices[dev.device_id] = dev
        logger.info("Discovered %d existing devices", len(raw_list))

    def create_pool(self, count: int, spec: dict = None) -> list[DeviceInstance]:
        """Create N cloud phone instances and return them."""
        spec = spec or {
            "os_version": "12",
            "region": "us-east-1",
            "ram": 4096,
            "storage": 32768,
            "resolution": "1080x1920",
        }
        count = min(count, self.max_devices - len(self._devices))
        devices = []

        for i in range(count):
            try:
                spec_copy = spec.copy()
                spec_copy["name"] = f"match-bot-{len(self._devices) + i + 1}"
                result = self.client.create_device(spec_copy)
                dev_id = result["device_id"]
                dev = DeviceInstance(
                    device_id=dev_id,
                    name=spec_copy["name"],
                    status="created",
                )
                self._devices[dev_id] = dev
                devices.append(dev)
                logger.info("Created device %s (%s)", dev.name, dev_id)
            except Exception as e:
                logger.error("Failed to create device %d: %s", i, e)
        return devices

    def boot_pool(self, device_ids: list[str] = None,
                  wait_ready: bool = True, max_workers: int = 10):
        """Start devices in parallel using a thread pool."""
        targets = device_ids or list(self._devices.keys())
        logger.info("Booting %d devices with %d workers...", len(targets), max_workers)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self._boot_single, d_id): d_id
                for d_id in targets
            }
            for future in as_completed(futures):
                d_id = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error("Device %s boot failed: %s", d_id, e)

        if wait_ready:
            self._wait_all_ready(targets)

    def _boot_single(self, device_id: str):
        dev = self._devices.get(device_id)
        if not dev:
            return
        try:
            adb_info = self.client.start_device(device_id)
            time.sleep(3)
            adb_info = self.client.get_device_adb(device_id)
            dev.adb_host = adb_info.get("host", "")
            dev.adb_port = int(adb_info.get("port", 0))
            dev.serial = adb_info.get("serial", device_id)
            dev.status = "running"
        except Exception as e:
            logger.error("_boot_single %s error: %s", device_id, e)
            dev.status = "error"

    def _wait_all_ready(self, device_ids: list[str], timeout: int = 120):
        for d_id in device_ids:
            dev = self._devices.get(d_id)
            if dev and dev.status == "running":
                try:
                    self.client.wait_for_device_ready(d_id, timeout=timeout)
                except TimeoutError:
                    dev.status = "timeout"

    def assign_proxy(self, device_id: str, proxy: str):
        dev = self._devices.get(device_id)
        if dev:
            dev.proxy = proxy

    def release_device(self, device_id: str):
        dev = self._devices.get(device_id)
        if dev:
            dev.busy = False

    def shutdown_pool(self, device_ids: list[str] = None):
        targets = device_ids or list(self._devices.keys())
        with ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(self.client.stop_device, targets))
        logger.info("Shutdown %d devices", len(targets))

    def shutdown_all(self):
        self.shutdown_pool(list(self._devices.keys()))
