import time
import logging
from typing import Optional
from appium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from .models import Account, AccountStatus
from .store import AccountStore

logger = logging.getLogger(__name__)


class AccountValidator:
    """
    Validates whether created accounts are active by
    attempting a login and checking for success indicators.
    """

    LOC_EMAIL_INPUT = (By.ID, "com.match.android:id/email_address")
    LOC_PASSWORD_INPUT = (By.ID, "com.match.android:id/password")
    LOC_LOGIN_BTN = (By.ID, "com.match.android:id/log_in_button")
    LOC_LOGGED_IN_INDICATOR = (
        By.XPATH,
        "//android.widget.TextView[@text='Matches' or @text='Discover' or @text='Inbox']",
    )
    LOC_ERROR_BANNER = (By.ID, "com.match.android:id/snackbar_text")

    def __init__(self, store: AccountStore):
        self.store = store

    def validate(self, driver: webdriver.Remote, account: Account) -> bool:
        logger.info("Validating account %s", account.email)
        try:
            driver.activate_app("com.match.android")
            time.sleep(2)

            # Click Log In
            login_btn = driver.find_element(*self.LOC_LOGIN_BTN)
            login_btn.click()
            time.sleep(1)

            # Enter credentials
            email_el = driver.find_element(*self.LOC_EMAIL_INPUT)
            email_el.send_keys(account.email)
            pass_el = driver.find_element(*self.LOC_PASSWORD_INPUT)
            pass_el.send_keys(account.password)
            time.sleep(0.5)
            driver.find_element(*self.LOC_LOGIN_BTN).click()
            time.sleep(5)

            # Check for success indicator
            try:
                driver.find_element(*self.LOC_LOGGED_IN_INDICATOR)
                self.store.update_status(account.id, AccountStatus.ACTIVE)
                logger.info("Account %s is ACTIVE", account.email)
                return True
            except NoSuchElementException:
                try:
                    err = driver.find_element(*self.LOC_ERROR_BANNER).text
                    logger.warning("Account %s validation error: %s", account.email, err)
                    self.store.update_status(account.id, AccountStatus.ERROR, error=err)
                except NoSuchElementException:
                    self.store.update_status(account.id, AccountStatus.ERROR,
                                             error="Unknown validation failure")
                return False

        except Exception as e:
            logger.error("Validation exception for %s: %s", account.email, e)
            self.store.update_status(account.id, AccountStatus.ERROR, error=str(e))
            return False
