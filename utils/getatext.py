import time
import logging
from typing import Optional
import requests

logger = logging.getLogger(__name__)


class GetATextClient:
    """
    GetAText SMS verification API client.
    Docs: https://getatext.com/api-docs

    Provides real US non-VoIP phone numbers for SMS verification.
    """

    BASE_URL = "https://getatext.com"

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({
            "Auth": self.api_key or "",
            "Content-Type": "application/json",
        })

    # ---- REST API v1 ----

    RATE_LIMIT_DELAY = 6  # seconds between API calls (10 req/min)

    def get_balance(self) -> float:
        resp = self._session.get(f"{self.BASE_URL}/api/v1/balance", timeout=10)
        data = resp.json()
        if data.get("status") != "success":
            raise Exception(f"Balance check failed: {data}")
        return float(data["balance"])

    def get_prices(self) -> list[dict]:
        """Get all available services and their prices."""
        resp = self._session.get(f"{self.BASE_URL}/api/v1/prices-info", timeout=10)
        return resp.json()

    def rent_number(self, service: str, max_price: float = None,
                    carrier: str = None, area_codes: str = None) -> Optional[dict]:
        body = {"service": service}
        if max_price is not None:
            body["max_price"] = max_price
        if carrier:
            body["carrier"] = carrier
        if area_codes:
            body["area_codes"] = ",".join(area_codes) if isinstance(area_codes, list) else area_codes

        resp = self._session.post(
            f"{self.BASE_URL}/api/v1/rent-a-number",
            json=body, timeout=15,
        )
        data = resp.json()
        if resp.status_code == 201 and data.get("status") == "success":
            logger.info("Rented number %s for %s ($%s)",
                        data["number"], service, data["price"])
            return data
        else:
            err = data.get("errors") or data.get("message", "Unknown error")
            logger.warning("Rent number failed: %s", err)
            return None

    def get_rental_status(self, rental_id: int) -> Optional[dict]:
        try:
            resp = self._session.post(
                f"{self.BASE_URL}/api/v1/rental-status",
                json={"id": rental_id}, timeout=10,
            )
            if resp.status_code != 200:
                logger.debug("Rental status HTTP %d", resp.status_code)
                return None
            data = resp.json()
            if data.get("status"):
                return data
        except Exception:
            logger.debug("Rental status parse error", exc_info=True)
        return None

    def get_sms_code(self, rental_id: int, timeout: int = 120,
                     poll_interval: int = 5) -> Optional[str]:
        """Poll for SMS code. Blocks until received or timeout."""
        elapsed = 0
        while elapsed < timeout:
            status = self.get_rental_status(rental_id)
            if status:
                code = status.get("code")
                if code:
                    logger.info("SMS code received: %s", code)
                    return str(code)
                st = status.get("status")
                if st in ("cancelled", "completed", "expired"):
                    logger.warning("Rental ended with status: %s", st)
                    return None
            if elapsed % 15 == 0:
                logger.info("Waiting for SMS code... %ds elapsed", elapsed)
            time.sleep(poll_interval)
            elapsed += poll_interval
        logger.warning("SMS code timeout after %ds", timeout)
        return None

    def wait_for_codes(self, rental_ids: list[int], timeout: int = 300) -> list[str]:
        """
        Poll all rentals sequentially respecting rate limits.
        Returns list of codes (empty string for failed/timeout).
        Safe for any device count — rate limited to ~10 req/min.
        """
        n = len(rental_ids)
        codes: list[Optional[str]] = [None] * n
        elapsed = 0

        while elapsed < timeout:
            all_done = True
            for i, rid in enumerate(rental_ids):
                if codes[i] is not None:
                    continue
                all_done = False
                status = self.get_rental_status(rid)
                time.sleep(self.RATE_LIMIT_DELAY)
                elapsed += self.RATE_LIMIT_DELAY
                if not status:
                    continue
                code = status.get("code")
                if code:
                    logger.info("SMS code received for rental %d: %s", rid, code)
                    codes[i] = str(code)
                    continue
                st = status.get("status")
                if st in ("cancelled", "completed", "expired"):
                    logger.warning("Rental %d ended: %s", rid, st)
                    codes[i] = ""

            if all_done:
                break

            if elapsed % 30 < self.RATE_LIMIT_DELAY:
                got = sum(1 for c in codes if c is not None)
                logger.info("SMS codes: %d/%d received (%ds elapsed)", got, n, elapsed)

            if elapsed >= timeout:
                break

        for i in range(n):
            if codes[i] is None:
                logger.warning("Rental %d timed out", rental_ids[i])
                codes[i] = ""

        return codes  # type: ignore[return-value]

    def cancel_rental(self, rental_id: int) -> bool:
        resp = self._session.post(
            f"{self.BASE_URL}/api/v1/cancel-rental",
            json={"id": rental_id}, timeout=10,
        )
        data = resp.json()
        return data.get("status") == "cancelled"

    def mark_completed(self, rental_id: int) -> bool:
        resp = self._session.post(
            f"{self.BASE_URL}/api/v1/rental-status/{rental_id}/completed",
            timeout=10,
        )
        data = resp.json()
        return data.get("status") == "success"

    # ---- Legacy API (sms-activate compatible) ----
    # Useful as fallback or for simpler integration.

    def legacy_get_number(self, service: str) -> Optional[dict]:
        params = {
            "api_key": self.api_key,
            "action": "getNumber",
            "service": service,
        }
        try:
            r = requests.get(
                f"{self.BASE_URL}/stubs/handler_api.php",
                params=params, timeout=15,
            )
            text = r.text.strip()
            if text.startswith("ACCESS_NUMBER:"):
                parts = text.split(":")
                return {"activation_id": int(parts[1]), "phone": parts[2]}
            logger.warning("Legacy getNumber: %s", text)
            return None
        except Exception as e:
            logger.error("Legacy getNumber error: %s", e)
            return None

    def legacy_get_sms_code(self, activation_id: int, timeout: int = 120,
                            poll_interval: int = 5) -> Optional[str]:
        elapsed = 0
        while elapsed < timeout:
            params = {
                "api_key": self.api_key,
                "action": "getStatus",
                "id": activation_id,
            }
            try:
                r = requests.get(
                    f"{self.BASE_URL}/stubs/handler_api.php",
                    params=params, timeout=10,
                )
                text = r.text.strip()
                if text.startswith("STATUS_OK:"):
                    code = text.split(":")[1]
                    logger.info("Legacy SMS code: %s", code)
                    return code
                elif text == "STATUS_WAIT_CODE":
                    pass
                else:
                    logger.debug("Legacy status: %s", text)
            except Exception as e:
                logger.error("Legacy poll error: %s", e)

            time.sleep(poll_interval)
            elapsed += poll_interval
        return None
