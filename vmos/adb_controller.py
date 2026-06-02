import subprocess
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ADBController:
    """
    Controls a cloud phone via ADB.
    Connects to the VMOS Cloud Phone's ADB endpoint
    and executes shell commands / taps / inputs.
    """

    def __init__(self, adb_host: str, adb_port: int, serial: str = ""):
        self.adb_host = adb_host
        self.adb_port = adb_port
        self.serial = serial or f"{adb_host}:{adb_port}"
        self._connected = False

    @property
    def adb_target(self) -> str:
        return f"{self.adb_host}:{self.adb_port}"

    def connect(self) -> bool:
        try:
            r = subprocess.run(
                ["adb", "connect", self.adb_target],
                capture_output=True, text=True, timeout=10
            )
            self._connected = "connected" in r.stdout or "already" in r.stdout
            if self._connected:
                logger.info("ADB connected to %s", self.adb_target)
            return self._connected
        except Exception as e:
            logger.error("ADB connect failed: %s", e)
            return False

    def disconnect(self):
        subprocess.run(
            ["adb", "disconnect", self.adb_target],
            capture_output=True, timeout=5
        )
        self._connected = False

    def shell(self, command: str) -> str:
        r = subprocess.run(
            ["adb", "-s", self.adb_target, "shell", command],
            capture_output=True, text=True, timeout=30
        )
        return r.stdout.strip()

    def install_apk(self, apk_path: str) -> bool:
        r = subprocess.run(
            ["adb", "-s", self.adb_target, "install", "-r", apk_path],
            capture_output=True, text=True, timeout=120
        )
        success = "Success" in r.stdout
        if not success:
            logger.error("APK install failed: %s", r.stderr)
        return success

    def tap(self, x: int, y: int):
        self.shell(f"input tap {x} {y}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        self.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    def text(self, text: str):
        safe = text.replace(" ", "%s").replace("'", "\\'")
        self.shell(f"input text '{safe}'")

    def keyevent(self, keycode: int):
        self.shell(f"input keyevent {keycode}")

    def screenshot(self, save_path: str):
        self.shell(f"screencap -p /sdcard/screen.png")
        subprocess.run(
            ["adb", "-s", self.adb_target, "pull", "/sdcard/screen.png", save_path],
            capture_output=True, timeout=15
        )

    def clear_app_data(self, package: str):
        self.shell(f"pm clear {package}")

    def force_stop(self, package: str):
        self.shell(f"am force-stop {package}")

    def is_app_installed(self, package: str) -> bool:
        out = self.shell(f"pm list packages {package}")
        return package in out

    def get_current_activity(self) -> str:
        out = self.shell("dumpsys window windows | grep mCurrentFocus")
        return out.strip()
