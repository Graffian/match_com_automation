import time
import logging
from typing import Optional
from appium import webdriver
from selenium.webdriver.common.by import By

from .appium_driver import AppiumHelper
from config.settings import config

logger = logging.getLogger(__name__)


class MatchComAutomation:
    """
    Automates Match.com Android app account creation flow.
    Uses Appium to drive the app on a cloud phone.
    """

    def __init__(self, driver: webdriver.Remote, profile: dict):
        self.driver = driver
        self.profile = profile
        self.helper = AppiumHelper(driver)
        self.package = config.MATCH_APP_PACKAGE

    # ---- Element locators (XPath / ID / Accessibility) ----
    # These are the most common selectors for the Match.com Android app.
    # If the app UI changes, update these or enable the auto-detection fallback.

    LOC_SIGNUP_BTN = (By.ID, "com.match.android:id/sign_up_button")
    LOC_SIGNUP_BTN_ALT = (By.XPATH, "//android.widget.Button[@text='Sign Up' or @text='REGISTER']")
    LOC_LOGIN_BTN = (By.ID, "com.match.android:id/log_in_button")

    LOC_EMAIL_FIELD = (By.ID, "com.match.android:id/email_address")
    LOC_PASSWORD_FIELD = (By.ID, "com.match.android:id/password")
    LOC_CREATE_ACCT_BTN = (By.ID, "com.match.android:id/create_account_button")
    LOC_CONTINUE_BTN = (By.XPATH, "//android.widget.Button[@text='Continue' or @text='NEXT']")

    LOC_FIRST_NAME = (By.ID, "com.match.android:id/first_name")
    LOC_BIRTH_MONTH = (By.ID, "com.match.android:id/birth_month")
    LOC_BIRTH_DAY = (By.ID, "com.match.android:id/birth_day")
    LOC_BIRTH_YEAR = (By.ID, "com.match.android:id/birth_year")
    LOC_ZIP_CODE = (By.ID, "com.match.android:id/zip_code")
    LOC_GENDER_MALE = (By.XPATH, "//android.widget.RadioButton[@text='Man']")
    LOC_GENDER_FEMALE = (By.XPATH, "//android.widget.RadioButton[@text='Woman']")

    LOC_LOOKING_FOR = (By.XPATH, "//android.widget.RadioButton[@text='Women' or @text='Men']")
    LOC_ABOUT_ME = (By.ID, "com.match.android:id/about_me")

    LOC_PHOTO_BTN = (By.ID, "com.match.android:id/add_photo_button")
    LOC_PHOTO_ALLOW = (By.ID, "com.android.permissioncontroller:id/permission_allow_button")
    LOC_PHOTO_SELECT = (By.XPATH, "//android.widget.GridView/android.widget.ImageView[1]")

    LOC_UPLOAD_PHOTO = (By.ID, "com.match.android:id/upload_photo")

    LOC_ALLOW_NOTIFS = (By.ID, "com.android.permissioncontroller:id/permission_deny_button")
    LOC_SKIP_BTN = (By.XPATH, "//android.widget.TextView[@text='Skip' or @text='Not now']")
    LOC_DONE_BTN = (By.XPATH, "//android.widget.Button[@text='Done' or @text='FINISH']")

    LOC_ERROR_MSG = (By.ID, "com.match.android:id/snackbar_text")
    LOC_PHONE_VERIFICATION = (By.XPATH, "//android.widget.TextView[contains(@text,'phone') or contains(@text,'verify')]")
    LOC_PHONE_INPUT = (By.ID, "com.match.android:id/phone_number")
    LOC_VERIFY_CODE_INPUT = (By.ID, "com.match.android:id/verification_code")
    LOC_SUBMIT_CODE = (By.ID, "com.match.android:id/submit_code_button")

    # ================================================================

    def launch(self) -> bool:
        """Launch the Match.com app."""
        try:
            self.driver.activate_app(self.package)
            time.sleep(2)
            logger.info("Launched Match.com app")
            return True
        except Exception as e:
            logger.error("Failed to launch app: %s", e)
            return False

    def click_signup(self) -> bool:
        """Click the Sign Up button on the landing screen."""
        for loc in [self.LOC_SIGNUP_BTN, self.LOC_SIGNUP_BTN_ALT]:
            if self.helper.wait_and_click(*loc, timeout=5):
                time.sleep(1)
                return True
        logger.warning("Could not find Sign Up button")
        return False

    def enter_email_password(self) -> bool:
        """Fill in email and password fields."""
        email = self.profile.get("email", "")
        password = self.profile.get("password", "")
        if not email or not password:
            logger.error("Email/password missing from profile")
            return False

        if not self.helper.wait_and_send_keys(*self.LOC_EMAIL_FIELD, email):
            return False
        time.sleep(0.5)
        if not self.helper.wait_and_send_keys(*self.LOC_PASSWORD_FIELD, password):
            return False
        time.sleep(0.5)
        self.helper.wait_and_click(*self.LOC_CREATE_ACCT_BTN)
        time.sleep(1)
        return True

    def fill_basic_info(self) -> bool:
        """Fill first name, birthday, zip code, gender."""
        fname = self.profile.get("first_name", "")
        month = self.profile.get("birth_month", "01")
        day = self.profile.get("birth_day", "15")
        year = self.profile.get("birth_year", "1990")
        zipcode = self.profile.get("zip_code", "10001")
        gender = self.profile.get("gender", "male")

        if fname:
            self.helper.wait_and_send_keys(*self.LOC_FIRST_NAME, fname)
            time.sleep(0.3)

        self.helper.wait_and_send_keys(*self.LOC_BIRTH_MONTH, month)
        self.helper.wait_and_send_keys(*self.LOC_BIRTH_DAY, day)
        self.helper.wait_and_send_keys(*self.LOC_BIRTH_YEAR, year)
        self.helper.wait_and_send_keys(*self.LOC_ZIP_CODE, zipcode)
        time.sleep(0.3)

        if gender == "male":
            self.helper.wait_and_click(*self.LOC_GENDER_MALE)
        else:
            self.helper.wait_and_click(*self.LOC_GENDER_FEMALE)

        self.helper.wait_and_click(*self.LOC_CONTINUE_BTN)
        time.sleep(1)
        return True

    def fill_preferences(self) -> bool:
        """Set 'looking for' and optional bio."""
        looking_for = self.profile.get("looking_for", "women")
        if looking_for == "women":
            self.helper.wait_and_click(By.XPATH, "//android.widget.RadioButton[@text='Women']", timeout=5)
        else:
            self.helper.wait_and_click(By.XPATH, "//android.widget.RadioButton[@text='Men']", timeout=5)

        bio = self.profile.get("about_me", "")
        if bio:
            self.helper.wait_and_send_keys(*self.LOC_ABOUT_ME, bio)

        self.helper.wait_and_click(*self.LOC_CONTINUE_BTN)
        time.sleep(1)
        return True

    def upload_photo(self, photo_path: str = None) -> bool:
        """Upload a profile photo from the device gallery."""
        photo_path = photo_path or self.profile.get("photo_path", "")
        if not photo_path:
            logger.info("No photo provided, skipping photo upload")
            self._skip_step()
            return False

        self.helper.wait_and_click(*self.LOC_PHOTO_BTN, timeout=5)
        time.sleep(1)
        self.helper.wait_and_click(*self.LOC_PHOTO_ALLOW, timeout=3)
        time.sleep(1)
        self.helper.wait_and_click(*self.LOC_PHOTO_SELECT, timeout=5)
        time.sleep(2)
        self.helper.wait_and_click(*self.LOC_UPLOAD_PHOTO, timeout=10)
        time.sleep(3)
        return True

    def handle_permissions(self) -> bool:
        """Deny notification permissions etc."""
        self.helper.wait_and_click(*self.LOC_ALLOW_NOTIFS, timeout=3)
        return True

    def _skip_step(self):
        """Click Skip/Not Now if available."""
        self.helper.wait_and_click(*self.LOC_SKIP_BTN, timeout=3)

    def handle_phone_verification(self, sms_code: str = None) -> bool:
        """
        If phone verification appears, enter phone and code.
        sms_code should come from an SMS activation service.
        """
        if not self.helper.is_element_present(*self.LOC_PHONE_VERIFICATION, timeout=3):
            logger.info("No phone verification required")
            return True

        phone = self.profile.get("phone", "")
        if phone:
            self.helper.wait_and_send_keys(*self.LOC_PHONE_INPUT, phone)
            self.helper.wait_and_click(*self.LOC_CONTINUE_BTN)
            time.sleep(10)  # wait for SMS

            if sms_code:
                self.helper.wait_and_send_keys(*self.LOC_VERIFY_CODE_INPUT, sms_code)
                self.helper.wait_and_click(*self.LOC_SUBMIT_CODE)
                time.sleep(2)
                return True
        return False

    def check_for_errors(self) -> str:
        """Check if there's an error on screen (e.g. email taken)."""
        if self.helper.is_element_present(*self.LOC_ERROR_MSG, timeout=3):
            try:
                return self.driver.find_element(*self.LOC_ERROR_MSG).text
            except Exception:
                return "Unknown error"
        return ""

    def complete_signup(self) -> bool:
        """Run the full signup flow."""
        logger.info("Starting Match.com signup flow for %s", self.profile.get("email"))

        steps = [
            ("launch", self.launch),
            ("click_signup", self.click_signup),
            ("enter_email_password", self.enter_email_password),
            ("fill_basic_info", self.fill_basic_info),
            ("fill_preferences", self.fill_preferences),
            ("upload_photo", self.upload_photo),
            ("handle_permissions", self.handle_permissions),
        ]

        for step_name, step_func in steps:
            logger.info("Step: %s", step_name)
            if not step_func():
                error = self.check_for_errors()
                logger.warning("Step '%s' failed. Error: %s", step_name, error or "unknown")
                return False
            time.sleep(1)

        logger.info("Signup flow completed for %s", self.profile.get("email"))
        return True
