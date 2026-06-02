import time
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)


class SMSActivationClient:
    """
    Integration with SMS activation services (e.g., sms-activate.org, 5sim.net).
    Used to receive phone verification codes during signup.

    This is a template — adapt to your preferred SMS provider.
    """

    def __init__(self, api_key: str, service: str = "match", country: str = "us"):
        self.api_key = api_key
        self.service = service
        self.country = country
        self.base_url = "https://api.sms-activate.org/stubs/handler_api.php"

    def get_balance(self) -> float:
        params = {"api_key": self.api_key, "action": "getBalance"}
        try:
            r = requests.get(self.base_url, params=params, timeout=10)
            return float(r.text.replace("ACCESS_BALANCE:", ""))
        except Exception as e:
            logger.error("SMS balance check failed: %s", e)
            return 0.0

    def get_number(self) -> Optional[dict]:
        """Request a phone number for verification."""
        params = {
            "api_key": self.api_key,
            "action": "getNumber",
            "service": self.service,
            "country": self.country,
        }
        try:
            r = requests.get(self.base_url, params=params, timeout=15)
            text = r.text.strip()
            if text.startswith("ACCESS_NUMBER:"):
                parts = text.split(":")
                return {"activation_id": parts[1], "phone": parts[2]}
            logger.warning("SMS getNumber response: %s", text)
            return None
        except Exception as e:
            logger.error("SMS getNumber failed: %s", e)
            return None

    def get_sms_code(self, activation_id: str, timeout: int = 120,
                     poll_interval: int = 5) -> Optional[str]:
        """Poll for SMS code. Blocks until received or timeout."""
        elapsed = 0
        while elapsed < timeout:
            params = {
                "api_key": self.api_key,
                "action": "getStatus",
                "id": activation_id,
            }
            try:
                r = requests.get(self.base_url, params=params, timeout=10)
                text = r.text.strip()
                if text.startswith("STATUS_OK:"):
                    code = text.split(":")[1]
                    logger.info("SMS code received: %s", code)
                    return code
                elif text == "STATUS_WAIT_CODE":
                    logger.debug("Waiting for SMS... (%ds)", elapsed)
                else:
                    logger.warning("SMS status: %s", text)
            except Exception as e:
                logger.error("SMS poll error: %s", e)

            time.sleep(poll_interval)
            elapsed += poll_interval

        logger.warning("SMS code timeout after %ds", timeout)
        return None

    def set_status(self, activation_id: str, status: int) -> bool:
        params = {
            "api_key": self.api_key,
            "action": "setStatus",
            "id": activation_id,
            "status": status,
        }
        try:
            r = requests.get(self.base_url, params=params, timeout=10)
            return "ACCESS" in r.text
        except Exception as e:
            logger.error("SMS setStatus failed: %s", e)
            return False
