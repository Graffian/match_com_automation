import time
import hmac
import hashlib
import requests
from typing import Optional
from config.settings import config


class VMOSAPIError(Exception):
    pass


class VMOSClient:
    """
    VMOS Cloud REST API client.
    API docs: https://docs.vmoscloud.com
    """

    def __init__(self, api_key: str = None, api_secret: str = None, base_url: str = None):
        self.api_key = api_key or config.VMOS_API_KEY
        self.api_secret = api_secret or config.VMOS_API_SECRET
        self.base_url = base_url or config.VMOS_BASE_URL
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def _sign(self, params: dict) -> str:
        sorted_keys = sorted(params.keys())
        raw = "&".join(f"{k}={params[k]}" for k in sorted_keys)
        return hmac.new(
            self.api_secret.encode(), raw.encode(), hashlib.sha256
        ).hexdigest()

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        ts = str(int(time.time()))
        params = kwargs.pop("params", {})
        params.update({"api_key": self.api_key, "timestamp": ts})
        params["sign"] = self._sign(params)

        resp = self._session.request(method, url, params=params, **kwargs, timeout=30)
        data = resp.json()
        if data.get("code") != 0:
            raise VMOSAPIError(f"API error {data.get('code')}: {data.get('msg', resp.text)}")
        return data.get("data", {})

    # ---- Device / Cloud Phone API ----

    def list_devices(self) -> list[dict]:
        """List all cloud phone instances."""
        return self._request("GET", "/device/list")

    def create_device(self, spec: dict) -> dict:
        """Create a new cloud phone instance.
        spec: {
            'name': str,
            'os_version': str,    # e.g. '12'
            'region': str,        # e.g. 'us-east-1'
            'ram': int,           # MB
            'storage': int,       # MB
            'resolution': str     # e.g. '1080x1920'
        }
        """
        return self._request("POST", "/device/create", json=spec)

    def start_device(self, device_id: str) -> dict:
        """Power on a cloud phone."""
        return self._request("POST", "/device/start", json={"device_id": device_id})

    def stop_device(self, device_id: str) -> dict:
        return self._request("POST", "/device/stop", json={"device_id": device_id})

    def restart_device(self, device_id: str) -> dict:
        return self._request("POST", "/device/restart", json={"device_id": device_id})

    def delete_device(self, device_id: str) -> dict:
        return self._request("POST", "/device/delete", json={"device_id": device_id})

    def get_device_status(self, device_id: str) -> dict:
        return self._request("GET", "/device/status", params={"device_id": device_id})

    def get_device_adb(self, device_id: str) -> dict:
        """Get ADB connection details for a cloud phone.
        Returns { 'host': str, 'port': int, 'serial': str } or similar.
        """
        return self._request("GET", "/device/adb", params={"device_id": device_id})

    # ---- App Management ----

    def install_app(self, device_id: str, apk_url: str) -> dict:
        return self._request("POST", "/device/app/install", json={
            "device_id": device_id, "apk_url": apk_url
        })

    def launch_app(self, device_id: str, package_name: str) -> dict:
        return self._request("POST", "/device/app/launch", json={
            "device_id": device_id, "package": package_name
        })

    def close_app(self, device_id: str, package_name: str) -> dict:
        return self._request("POST", "/device/app/close", json={
            "device_id": device_id, "package": package_name
        })

    def wait_for_device_ready(self, device_id: str, timeout: int = 120, poll: int = 5):
        """Block until device is online and ready for ADB."""
        elapsed = 0
        while elapsed < timeout:
            status = self.get_device_status(device_id)
            if status.get("status") == "running":
                try:
                    adb_info = self.get_device_adb(device_id)
                    if adb_info.get("host"):
                        return adb_info
                except VMOSAPIError:
                    pass
            time.sleep(poll)
            elapsed += poll
        raise TimeoutError(f"Device {device_id} not ready after {timeout}s")
