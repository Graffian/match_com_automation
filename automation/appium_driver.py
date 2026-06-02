import time
import logging
from typing import Optional
from appium import webdriver
from appium.webdriver.appium_service import AppiumService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from config.settings import config

logger = logging.getLogger(__name__)


class AppiumDriverFactory:
    """
    Manages Appium driver sessions for cloud phone instances.
    Supports local Appium server or cloud Appium (e.g. BrowserStack).
    """

    _service: Optional[AppiumService] = None

    @classmethod
    def start_appium_server(cls, port: int = None) -> AppiumService:
        if cls._service and cls._service.is_running:
            return cls._service
        cls._service = AppiumService()
        cls._service.start(
            args=["--port", str(port or config.APPIUM_PORT), "--log-level", "error"]
        )
        logger.info("Appium server started on port %s", port or config.APPIUM_PORT)
        return cls._service

    @classmethod
    def stop_appium_server(cls):
        if cls._service and cls._service.is_running:
            cls._service.stop()
            logger.info("Appium server stopped")

    @classmethod
    def create_driver(cls, desired_caps: dict,
                      appium_url: str = None) -> webdriver.Remote:
        """
        Create an Appium WebDriver session for a cloud phone.
        desired_caps: from DeviceInstance.appium_desired_caps
        """
        url = appium_url or config.appium_url
        logger.debug("Creating Appium session at %s with caps: %s", url, desired_caps)
        driver = webdriver.Remote(
            command_executor=url,
            desired_capabilities=desired_caps,
        )
        driver.implicitly_wait(10)
        return driver


class AppiumHelper:
    """
    Common wait / action helpers for Appium.
    """

    def __init__(self, driver: webdriver.Remote, timeout: int = 15):
        self.driver = driver
        self.timeout = timeout

    def wait_and_click(self, by: str, value: str, timeout: int = None) -> bool:
        try:
            el = WebDriverWait(self.driver, timeout or self.timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            el.click()
            return True
        except Exception as e:
            logger.warning("wait_and_click(%s=%s) failed: %s", by, value, e)
            return False

    def wait_and_send_keys(self, by: str, value: str, text: str,
                           timeout: int = None) -> bool:
        try:
            el = WebDriverWait(self.driver, timeout or self.timeout).until(
                EC.presence_of_element_located((by, value))
            )
            el.clear()
            el.send_keys(text)
            return True
        except Exception as e:
            logger.warning("wait_and_send_keys(%s=%s) failed: %s", by, value, e)
            return False

    def wait_for_element(self, by: str, value: str,
                         timeout: int = None):
        return WebDriverWait(self.driver, timeout or self.timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def is_element_present(self, by: str, value: str, timeout: int = 3) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except Exception:
            return False

    def scroll_down(self, swipe_ratio: float = 0.6):
        size = self.driver.get_window_size()
        w, h = size["width"], size["height"]
        x = w // 2
        y_start = int(h * 0.7)
        y_end = int(h * (1 - swipe_ratio))
        self.driver.swipe(x, y_start, x, y_end, 500)

    def scroll_up(self, swipe_ratio: float = 0.6):
        size = self.driver.get_window_size()
        w, h = size["width"], size["height"]
        x = w // 2
        y_start = int(h * 0.3)
        y_end = int(h * swipe_ratio)
        self.driver.swipe(x, y_start, x, y_end, 500)

    def take_screenshot(self, path: str):
        self.driver.save_screenshot(path)

    def close_app(self, package: str):
        self.driver.terminate_app(package)

    def reset_app(self, package: str):
        self.driver.reset()
