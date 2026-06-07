import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

from config.settings import config
from vmos.client import VMOSClient
from vmos.device_manager import DeviceManager, DeviceInstance
from automation.profile_generator import ProfileGenerator
from accounts.store import AccountStore
from accounts.models import Account
from utils.proxy import ProxyManager
from utils.logger import get_device_logger
from .worker import DeviceWorker

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    accounts: list[Account] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class Orchestrator:
    """
    Orchestrates the full pipeline:
      1. Spin up / discover VMOS Cloud Phone devices
      2. Generate synthetic profiles
      3. Run Appium workers in parallel (one per device)
      4. Collect results and store in SQLite
    """

    def __init__(
        self,
        device_count: int = 5,
        accounts_per_device: int = 1,
        profile_source: str = None,
        proxy_file: str = None,
        db_path: str = None,
        max_workers: int = None,
        reuse_devices: bool = True,
        sms_client=None,
    ):
        self.device_count = min(device_count, 20)
        self.accounts_per_device = max(accounts_per_device, 1)
        self.max_workers = max_workers or device_count
        self.reuse_devices = reuse_devices

        self.vmos_client = VMOSClient()
        self.device_manager = DeviceManager(self.vmos_client, max_devices=20)
        self.profile_gen = ProfileGenerator(profile_source)
        self.proxy_manager = ProxyManager(proxy_file)
        self.store = AccountStore(db_path or config.ACCOUNTS_DB)
        self.sms_client = sms_client

        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run_batch(self) -> BatchResult:
        """Execute one batch: create accounts on all devices in parallel."""
        start = time.time()
        result = BatchResult()

        # 1. Get devices
        devices = self._prepare_devices()
        if not devices:
            logger.error("No devices available. Aborting batch.")
            return result

        logger.info("Batch starting with %d devices", len(devices))

        # 2. Assign proxies to devices
        proxies = self.proxy_manager.assign_to_devices(len(devices))
        for dev, proxy in zip(devices, proxies):
            self.device_manager.assign_proxy(dev.pad_code, proxy)

        # 3. Generate profiles
        total_accounts = len(devices) * self.accounts_per_device
        all_profiles = self.profile_gen.generate_batch(total_accounts)
        logger.info("Generated %d profiles", len(all_profiles))

        # 4. Run workers in parallel (one thread per device)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_dev = {}

            for idx, device in enumerate(devices):
                start_p = idx * self.accounts_per_device
                end_p = start_p + self.accounts_per_device
                device_profiles = all_profiles[start_p:end_p]

                for profile in device_profiles:
                    if self._stop_requested:
                        break

                    worker = DeviceWorker(
                        device=device,
                        profile=profile,
                        store=self.store,
                        sms_client=self.sms_client,
                    )
                    future = executor.submit(worker.run)
                    future_to_dev[future] = (device, profile)
                    device.busy = True

            # 5. Collect results
            for future in as_completed(future_to_dev):
                device, profile = future_to_dev[future]
                try:
                    account = future.result(timeout=300)
                    result.total += 1
                    if account and account.status.value in ("verified", "active"):
                        result.succeeded += 1
                        result.accounts.append(account)
                    else:
                        result.failed += 1
                        err = account.error_message if account else "No account object"
                        result.errors.append(f"{profile.get('email')}: {err}")
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"{profile.get('email')}: {str(e)}")
                    logger.error("Future exception for %s: %s", profile.get("email"), e)

        result.duration_seconds = time.time() - start
        logger.info(
            "Batch complete: %d succeeded, %d failed in %.1fs",
            result.succeeded,
            result.failed,
            result.duration_seconds,
        )
        return result

    def run_continuous(self, batches: int = 10, interval_seconds: int = 60):
        """Run multiple batches with a pause between them."""
        logger.info("Starting continuous mode: %d batches at %ds intervals", batches, interval_seconds)
        for batch_num in range(1, batches + 1):
            if self._stop_requested:
                break
            logger.info("=== Batch %d/%d ===", batch_num, batches)
            result = self.run_batch()
            logger.info(
                "Batch %d: %d/%d succeeded (%.1fs)",
                batch_num,
                result.succeeded,
                result.total,
                result.duration_seconds,
            )
            if batch_num < batches and not self._stop_requested:
                logger.info("Waiting %ds before next batch...", interval_seconds)
                time.sleep(interval_seconds)
        logger.info("Continuous mode finished")

    def _prepare_devices(self) -> list[DeviceInstance]:
        """Discover or create the required number of devices and boot them."""
        self.device_manager.discover_existing()

        existing_count = len(self.device_manager.all_devices)
        if existing_count < self.device_count:
            to_create = self.device_count - existing_count
            logger.info("Creating %d new devices...", to_create)
            self.device_manager.create_pool(to_create)

        devices = list(self.device_manager.all_devices)
        pad_codes = [d.pad_code for d in devices]

        self.device_manager.boot_pool(pad_codes)

        ready = [d for d in devices if d.status == "running"]
        logger.info("%d/%d devices ready", len(ready), self.device_count)
        return ready[:self.device_count]

    def print_summary(self):
        counts = self.store.count_by_status()
        total = self.store.total_count()
        logger.info("=" * 40)
        logger.info("Account Store Summary")
        logger.info("Total accounts: %d", total)
        for status, cnt in sorted(counts.items()):
            logger.info("  %s: %d", status, cnt)
        logger.info("=" * 40)

    def shutdown(self):
        """Clean shutdown: stop devices, close DB."""
        logger.info("Shutting down orchestrator...")
        self.device_manager.shutdown_all()
        self.store.close()
