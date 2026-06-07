import time
import logging
from typing import Optional
from .client import VMOSClient

logger = logging.getLogger(__name__)


class VmosAutomation:
    def __init__(self, client: VMOSClient, pad_code: str,
                 width: int = 1080, height: int = 1920):
        self.client = client
        self.pad_code = pad_code
        self.w = width
        self.h = height

    def tap(self, x: int, y: int):
        self.client.simulate_click(self.pad_code, x, y, self.w, self.h)
        time.sleep(0.3)

    def text(self, text: str):
        self.client.input_text(self.pad_code, text)
        time.sleep(0.3)

    def swipe(self, direction: str = "TOP_TO_BOTTOM"):
        self.client.simulate_swipe(self.pad_code, direction, width=self.w, height=self.h)
        time.sleep(0.5)

    def scroll_down(self, times: int = 1):
        for _ in range(times):
            self.swipe()
            time.sleep(0.5)

    def open_app(self, package: str):
        try:
            self.client.start_app(self.pad_code, package)
        except Exception:
            pass
        time.sleep(3)

    def run_adb(self, cmd: str):
        try:
            self.client.send_adb(self.pad_code, cmd)
        except Exception:
            pass

    def screenshot(self) -> dict:
        try:
            return self.client.screenshot(self.pad_code, rotation=0)
        except Exception:
            return {}

    def set_proxy(self, ip: str, port: int, username: str = None, password: str = None):
        try:
            self.client.set_proxy([self.pad_code], ip=ip, port=port,
                                  username=username, password=password)
        except Exception:
            pass


class MatchComVmosAutomation:
    """
    Match.com signup automation using VMOS Cloud REST API.
    Coordinates are estimated for 1080x1920 screen.
    """

    def __init__(self, vmos: VmosAutomation, profile: dict):
        self.v = vmos
        self.profile = profile

    def launch(self):
        """Launch Match.com app."""
        self.v.open_app("com.match.android")
        time.sleep(3)

    def click_signup(self):
        """Tap Sign Up button (bottom of screen)."""
        self.v.tap(self.v.w // 2, int(self.v.h * 0.85))
        time.sleep(2)

    def enter_email_password(self):
        email = self.profile.get("email", "")
        password = self.profile.get("password", "")

        # Tap email field (top half)
        self.v.tap(self.v.w // 2, int(self.v.h * 0.30))
        time.sleep(1)
        self.v.text(email)
        time.sleep(0.5)

        # Tap password field
        self.v.tap(self.v.w // 2, int(self.v.h * 0.40))
        time.sleep(1)
        self.v.text(password)
        time.sleep(0.5)

        # Tap create account button
        self.v.tap(self.v.w // 2, int(self.v.h * 0.50))
        time.sleep(2)

    def fill_basic_info(self):
        fname = self.profile.get("first_name", "John")
        month = self.profile.get("birth_month", "06")
        day = self.profile.get("birth_day", "15")
        year = self.profile.get("birth_year", "1990")
        zipcode = self.profile.get("zip_code", "10001")

        # First name
        self.v.tap(self.v.w // 2, int(self.v.h * 0.25))
        time.sleep(1)
        self.v.text(fname)
        time.sleep(0.3)

        # Birthday fields
        self.v.tap(self.v.w // 2, int(self.v.h * 0.35))
        time.sleep(0.5)
        self.v.text(month)
        time.sleep(0.3)

        self.v.tap(self.v.w // 2, int(self.v.h * 0.40))
        time.sleep(0.5)
        self.v.text(day)
        time.sleep(0.3)

        self.v.tap(self.v.w // 2, int(self.v.h * 0.45))
        time.sleep(0.5)
        self.v.text(year)
        time.sleep(0.3)

        # Zip code
        self.v.tap(self.v.w // 2, int(self.v.h * 0.52))
        time.sleep(0.5)
        self.v.text(zipcode)
        time.sleep(0.3)

        # Gender
        gender = self.profile.get("gender", "male")
        if gender == "male":
            self.v.tap(int(self.v.w * 0.3), int(self.v.h * 0.60))
        else:
            self.v.tap(int(self.v.w * 0.7), int(self.v.h * 0.60))
        time.sleep(0.5)

        # Continue
        self.v.tap(self.v.w // 2, int(self.v.h * 0.75))
        time.sleep(2)

    def fill_preferences(self):
        looking_for = self.profile.get("looking_for", "women")
        if looking_for == "women":
            self.v.tap(int(self.v.w * 0.3), int(self.v.h * 0.35))
        else:
            self.v.tap(int(self.v.w * 0.7), int(self.v.h * 0.35))
        time.sleep(0.5)

        bio = self.profile.get("about_me", "")
        if bio:
            self.v.tap(self.v.w // 2, int(self.v.h * 0.50))
            time.sleep(0.5)
            self.v.text(bio)
            time.sleep(0.3)

        # Continue
        self.v.tap(self.v.w // 2, int(self.v.h * 0.80))
        time.sleep(2)

    def skip_photo(self):
        """Skip photo upload if possible."""
        # Tap Skip button (usually bottom right or center)
        self.v.tap(int(self.v.w * 0.85), int(self.v.h * 0.92))
        time.sleep(1)

    def handle_phone_verification(self, phone: str = None):
        """Handle phone verification if screen appears."""
        # Check if phone field is visible by trying to type
        if not phone:
            # Just skip/continue
            self.v.tap(self.v.w // 2, int(self.v.h * 0.85))
            time.sleep(1)
            return

        # Enter phone number
        self.v.tap(self.v.w // 2, int(self.v.h * 0.40))
        time.sleep(0.5)
        self.v.text(phone)
        time.sleep(0.5)

        # Submit
        self.v.tap(self.v.w // 2, int(self.v.h * 0.55))
        time.sleep(10)

    def handle_deny_permissions(self):
        """Deny notification/photo permissions."""
        self.v.tap(int(self.v.w * 0.3), int(self.v.h * 0.65))
        time.sleep(1)

    def complete_signup(self) -> bool:
        logger.info("Starting VMOS Match.com signup for %s", self.profile.get("email"))

        steps = [
            ("launch", self.launch),
            ("click_signup", self.click_signup),
            ("enter_email_password", self.enter_email_password),
            ("fill_basic_info", self.fill_basic_info),
            ("fill_preferences", self.fill_preferences),
            ("skip_photo", self.skip_photo),
            ("handle_deny_permissions", self.handle_deny_permissions),
        ]

        for step_name, step_func in steps:
            logger.info("[%s] Step: %s", self.v.pad_code, step_name)
            try:
                step_func()
                time.sleep(1)
            except Exception as e:
                logger.warning("[%s] Step '%s' failed: %s", self.v.pad_code, step_name, e)
                return False

        logger.info("[%s] Signup completed for %s", self.v.pad_code, self.profile.get("email"))
        return True
