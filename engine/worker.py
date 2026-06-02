import time
import threading
import logging
from typing import Optional

from appium import webdriver

from config.settings import config
from vmos.device_manager import DeviceInstance
from automation.appium_driver import AppiumDriverFactory
from automation.match_com import MatchComAutomation
from accounts.models import Account, AccountStatus
from accounts.store import AccountStore
from utils.logger import get_device_logger


class DeviceWorker:
    """
    Runs the Match.com signup flow on a single cloud phone device.
    Designed to run in its own thread.
    """

    def __init__(
        self,
        device: DeviceInstance,
        profile: dict,
        store: AccountStore,
        appium_url: str = None,
        sms_client=None,
    ):
        self.device = device
        self.profile = profile
        self.store = store
        self.appium_url = appium_url or config.appium_url
        self.sms_client = sms_client
        self.driver: Optional[webdriver.Remote] = None
        self.account: Optional[Account] = None
        self.logger = get_device_logger(device.device_id)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self) -> Optional[Account]:
        """Execute the full signup flow on this device."""
        self.logger.info(
            "Worker starting for %s on device %s",
            self.profile.get("email"),
            self.device.name,
        )

        try:
            self._create_account_record()
            self.driver = AppiumDriverFactory.create_driver(
                self.device.appium_desired_caps,
                self.appium_url,
            )
            self.store.update_status(self.account.id, AccountStatus.CREATING)

            automation = MatchComAutomation(self.driver, self.profile)
            success = automation.complete_signup()

            if success:
                self.store.update_status(
                    self.account.id,
                    AccountStatus.VERIFIED,
                    match_id=self.account.match_id,
                )
                self.logger.info(
                    "Account %s created successfully!", self.profile.get("email")
                )
            else:
                error = automation.check_for_errors() or "Signup flow failed"
                self.store.update_status(
                    self.account.id, AccountStatus.ERROR, error=error
                )
                self.logger.warning("Account creation failed: %s", error)

            return self.account

        except Exception as e:
            self.logger.error("Worker exception: %s", e, exc_info=True)
            if self.account:
                self.store.update_status(
                    self.account.id, AccountStatus.ERROR, error=str(e)
                )
            return None

        finally:
            self._cleanup()

    def _create_account_record(self):
        """Insert the account into the DB before starting."""
        self.account = Account(
            email=self.profile.get("email", ""),
            password=self.profile.get("password", ""),
            first_name=self.profile.get("first_name", ""),
            last_name=self.profile.get("last_name", ""),
            gender=self.profile.get("gender", "male"),
            birth_month=self.profile.get("birth_month", "01"),
            birth_day=self.profile.get("birth_day", "01"),
            birth_year=self.profile.get("birth_year", "1990"),
            zip_code=self.profile.get("zip_code", ""),
            phone=self.profile.get("phone", ""),
            status=AccountStatus.PENDING,
            device_id=self.device.device_id,
            proxy=self.device.proxy,
        )
        self.store.insert(self.account)
        self.logger.info(
            "Account record created: ID=%d, email=%s",
            self.account.id,
            self.account.email,
        )

    def _cleanup(self):
        """Close the Appium session."""
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        finally:
            self.device.busy = False
