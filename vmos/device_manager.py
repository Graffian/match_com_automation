import time
import logging
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from .client import VMOSClient

logger = logging.getLogger(__name__)


@dataclass
class DeviceInstance:
    pad_code: str
    name: str
    status: str = "created"
    proxy: str = ""
    adb_host: str = ""
    adb_port: int = 0
    busy: bool = False

    @property
    def appium_desired_caps(self) -> dict:
        caps = {
            "platformName": "Android",
            "deviceName": self.name,
            "udid": self.pad_code,
            "noReset": False,
            "fullReset": False,
            "automationName": "UiAutomator2",
        }
        if self.proxy:
            caps["proxy"] = self.proxy
        return caps


class DeviceManager:
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
        raw_list = self.client.list_devices()
        for item in raw_list if isinstance(raw_list, list) else raw_list.get("list", []):
            pc = item.get("padCode") or item.get("device_id")
            if not pc:
                continue
            dev = DeviceInstance(
                pad_code=pc,
                name=item.get("name", item.get("padName", pc)),
                status=item.get("status", "unknown"),
            )
            self._devices[dev.pad_code] = dev
        logger.info("Discovered %d existing devices", len(self._devices))

    def create_pool(self, count: int, spec: dict = None) -> list[DeviceInstance]:
        spec = spec or {
            "osVersion": "12",
            "region": "us-east-1",
            "ram": 4096,
            "storage": 32768,
            "resolution": "1080x1920",
        }
        count = min(count, self.max_devices - len(self._devices))
        devices = []
        for i in range(count):
            try:
                copy = spec.copy()
                copy["name"] = f"match-bot-{len(self._devices) + i + 1}"
                result = self.client.create_device(copy)
                # Response varies — try common keys
                pc = result.get("padCode") or result.get("instanceId") or result.get("id", "")
                dev = DeviceInstance(pad_code=pc, name=copy["name"])
                self._devices[pc] = dev
                devices.append(dev)
                logger.info("Created device %s (%s)", dev.name, pc)
            except Exception as e:
                logger.error("Create device %d failed: %s", i, e)
        return devices

    def boot_pool(self, pad_codes: list[str] = None, wait_ready: bool = True,
                  max_workers: int = 10):
        targets = pad_codes or list(self._devices.keys())
        logger.info("Booting %d devices...", len(targets))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            pool.map(self._boot_single, targets)

        if wait_ready:
            time.sleep(5)

    def _boot_single(self, pad_code: str):
        dev = self._devices.get(pad_code)
        if not dev:
            return
        try:
            self.client.start_device(pad_code)
            dev.status = "running"
            logger.info("Device %s started", pad_code)
        except Exception as e:
            logger.error("Start %s failed: %s", pad_code, e)
            dev.status = "error"

    def assign_proxy(self, pad_code: str, proxy: str):
        dev = self._devices.get(pad_code)
        if dev:
            dev.proxy = proxy

    def release_device(self, pad_code: str):
        dev = self._devices.get(pad_code)
        if dev:
            dev.busy = False

    def shutdown_pool(self, pad_codes: list[str] = None):
        targets = pad_codes or list(self._devices.keys())
        with ThreadPoolExecutor(max_workers=10) as pool:
            pool.map(self.client.stop_device, targets)
        logger.info("Shutdown %d devices", len(targets))

    def shutdown_all(self):
        self.shutdown_pool(list(self._devices.keys()))
