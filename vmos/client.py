import time
import hashlib
import json as json_lib
import requests
from config.settings import config


class VMOSAPIError(Exception):
    pass


class VMOSClient:
    """
    VMOS Cloud REST API client (V2 Simplified Signature).
    Docs: https://cloud.vmoscloud.com/vmoscloud/doc/en/server/example-v2.html
    """

    def __init__(self, api_key: str = None, api_secret: str = None, base_url: str = None):
        self.api_key = api_key or config.VMOS_API_KEY
        self.api_secret = api_secret or config.VMOS_API_SECRET
        self.base_url = (base_url or config.VMOS_BASE_URL).rstrip("/")
        self._session = requests.Session()

    # ------------------------------------------------
    # V2 Signing
    # ------------------------------------------------
    def _sign(self, ts: str, path: str, body_or_query: str) -> str:
        raw = f"{self.api_secret}{ts}{path}{body_or_query}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    FILE_UPLOAD_PATHS = {
        "/vcpcloud/api/padApi/asyncCmd",
        "/vcpcloud/api/padApi/syncCmd",
    }

    def _request(self, method: str, path: str, body: dict = None,
                 query: dict = None, file_upload: bool = None) -> dict:
        url = f"{self.base_url}{path}"
        ts = str(int(time.time()))

        if method == "GET":
            qs = ""
            if query:
                qs = "&".join(f"{k}={v}" for k, v in sorted(query.items()))
                url = f"{url}?{qs}"
            sign_str = qs
            body_str = ""
        else:  # POST
            body_str = json_lib.dumps(body, separators=(",", ":")) if body else ""
            if file_upload is None:
                file_upload = path in self.FILE_UPLOAD_PATHS
            sign_str = "" if file_upload else body_str

        headers = {
            "X-Access-Key": self.api_key,
            "X-Timestamp": ts,
            "X-Sign": self._sign(ts, path, sign_str),
            "Content-Type": "application/json",
        }

        resp = self._session.request(
            method, url, headers=headers,
            data=body_str.encode("utf-8") if method == "POST" else None,
            timeout=30,
        )

        try:
            data = resp.json()
        except Exception:
            raise VMOSAPIError(f"Non-JSON response: {resp.text[:500]}")

        code = data.get("code")
        if code is not None and code != 200:
            raise VMOSAPIError(f"API error {code}: {data.get('msg', '')} | path={path}")
        return data.get("data", data)

    # ------------------------------------------------
    # Cloud Phone Lifecycle
    # ------------------------------------------------
    # padCode = device instance ID (e.g. "AC32010601132")

    def create_device(self, spec: dict) -> dict:
        """Create a new cloud phone instance."""
        return self._request("POST", "/vcpcloud/api/padApi/createMoneyOrder", body=spec)

    def list_devices(self) -> dict:
        """List all cloud phone instances. Returns { total, pageData }."""
        return self._request("POST", "/vcpcloud/api/padApi/infos", body={})

    def get_device_info(self, pad_code: str) -> dict:
        """Get info about a single cloud phone."""
        return self._request("POST", "/vcpcloud/api/padApi/padInfo",
                             body={"padCode": pad_code})

    def start_device(self, pad_code: str) -> dict:
        return self._request("POST", "/vcpcloud/api/padApi/restart",
                             body={"padCodes": [pad_code]})

    def stop_device(self, pad_code: str) -> dict:
        return self._request("POST", "/vcpcloud/api/padApi/dissolveRoom",
                             body={"padCodes": [pad_code]})

    def reset_device(self, pad_code: str) -> dict:
        return self._request("POST", "/vcpcloud/api/padApi/reset",
                             body={"padCode": pad_code})

    # ------------------------------------------------
    # App Management
    # ------------------------------------------------
    def start_app(self, pad_code: str, pkg_name: str):
        return self._request("POST", "/vcpcloud/api/padApi/startApp",
                             body={"pkgName": pkg_name, "padCodes": [pad_code]})

    def stop_app(self, pad_code: str, pkg_name: str):
        return self._request("POST", "/vcpcloud/api/padApi/stopApp",
                             body={"pkgName": pkg_name, "padCodes": [pad_code]})

    def list_installed_apps(self, pad_code: str) -> list[dict]:
        return self._request("POST", "/vcpcloud/api/padApi/listInstalledApp",
                             body={"padCodes": [pad_code]})

    # ------------------------------------------------
    # ADB / Touch Simulation
    # ------------------------------------------------
    def simulate_click(self, pad_code: str, x: int, y: int, width=720, height=1280):
        return self._request("POST", "/vcpcloud/api/padApi/simulateClick",
                             body={"padCodes": [pad_code], "x": x, "y": y,
                                   "width": width, "height": height})

    def simulate_swipe(self, pad_code: str, direction: str = "TOP_TO_BOTTOM",
                       start_x=None, start_y=None, end_x=None, end_y=None,
                       width=1080, height=1920):
        """direction: LEFT_TO_RIGHT, RIGHT_TO_LEFT, TOP_TO_BOTTOM, BOTTOM_TO_TOP"""
        body = {"padCodes": [pad_code], "direction": direction,
                "width": width, "height": height}
        if start_x is not None:
            body.update(startX=start_x, startY=start_y, endX=end_x, endY=end_y)
        return self._request("POST", "/vcpcloud/api/padApi/simulateSwipe", body=body)

    def input_text(self, pad_code: str, text: str):
        return self._request("POST", "/vcpcloud/api/padApi/inputText",
                             body={"padCodes": [pad_code], "text": text})

    def send_adb(self, pad_code: str, command: str):
        """Execute ADB command asynchronously."""
        return self._request("POST", "/vcpcloud/api/padApi/asyncCmd",
                             body={"padCodes": [pad_code], "scriptContent": command},
                             file_upload=True)

    def pad_task_detail(self, task_ids: list):
        """Query task execution result."""
        return self._request("POST", "/vcpcloud/api/padApi/padTaskDetail",
                             body={"taskIds": task_ids})

    def restart_app(self, pad_code: str, pkg_name: str):
        return self._request("POST", "/vcpcloud/api/padApi/restartApp",
                             body={"pkgName": pkg_name, "padCodes": [pad_code]})

    def uninstall_app(self, pad_code: str, pkg_name: str):
        return self._request("POST", "/vcpcloud/api/padApi/uninstallApp",
                             body={"pkgName": pkg_name, "padCodes": [pad_code]})

    def get_list_installed_app(self, pad_codes: list[str]) -> list[dict]:
        return self._request("POST", "/vcpcloud/api/padApi/getListInstalledApp",
                             body={"padCodeList": pad_codes})

    # ------------------------------------------------
    # Proxy
    # ------------------------------------------------
    def set_proxy(self, pad_codes: list[str], ip: str = None, port: int = None,
                  username: str = None, password: str = None,
                  enable: bool = True, proxy_type: str = "proxy",
                  proxy_name: str = "http-relay",
                  bypass_packages: list[str] = None,
                  bypass_ips: list[str] = None,
                  bypass_domains: list[str] = None):
        body = {"padCodes": pad_codes, "enable": enable,
                "proxyType": proxy_type, "proxyName": proxy_name}
        if ip is not None:
            body["ip"] = ip
        if port is not None:
            body["port"] = port
        if username is not None:
            body["account"] = username
        if password is not None:
            body["password"] = password
        if bypass_packages:
            body["bypassPackageList"] = bypass_packages
        if bypass_ips:
            body["bypassIpList"] = bypass_ips
        if bypass_domains:
            body["bypassDomainList"] = bypass_domains
        return self._request("POST", "/vcpcloud/api/padApi/setProxy", body=body)

    def check_ip(self, host: str, port: int, username: str, password: str,
                 proxy_type: str = "http", country: str = None):
        """Smart IP Proxy Detection - validate proxy before setting."""
        body = {"host": host, "port": port, "account": username,
                "password": password, "type": proxy_type}
        if country:
            body["country"] = country
        return self._request("POST", "/vcpcloud/api/padApi/checkIP", body=body)

    def not_smart_ip(self, pad_codes: list[str]):
        """Cancel Smart IP, restore default routing."""
        return self._request("POST", "/vcpcloud/api/padApi/notSmartIp",
                             body={"padCodes": pad_codes})

    def set_smart_ip(self, pad_codes: list[str], host: str, port: int,
                     username: str, password: str,
                     proxy_type: str = "http", mode: str = "proxy",
                     bypass_packages: list[str] = None,
                     bypass_ips: list[str] = None,
                     bypass_domains: list[str] = None):
        """Set Smart IP for cloud device. Device auto-restarts to apply."""
        body = {"padCodes": pad_codes, "host": host, "port": port,
                "account": username, "password": password,
                "type": proxy_type, "mode": mode}
        if bypass_packages:
            body["bypassPackageList"] = bypass_packages
        if bypass_ips:
            body["bypassIpList"] = bypass_ips
        if bypass_domains:
            body["bypassDomainList"] = bypass_domains
        return self._request("POST", "/vcpcloud/api/padApi/smartIp", body=body)

    # ------------------------------------------------
    # Screenshot
    # ------------------------------------------------
    def screenshot(self, pad_code: str, rotation: int = 0,
                   definition: int = None, width: int = None, height: int = None):
        body = {"padCodes": [pad_code], "rotation": rotation}
        if definition is not None:
            body["definition"] = definition
        if width is not None:
            body["resolutionWidth"] = width
        if height is not None:
            body["resolutionHeight"] = height
        return self._request("POST", "/vcpcloud/api/padApi/screenshot", body=body)

    def screenshot_info(self, task_ids: int):
        return self._request("POST", "/vcpcloud/api/padApi/screenshotInfo",
                             body={"taskIds": task_ids})

    # ------------------------------------------------
    # File Upload
    # ------------------------------------------------
    def upload_file_v3(self, pad_code: str, file_url: str,
                       file_name: str = None,
                       file_path: str = "/Pictures/"):
        body = {"padCodes": [pad_code], "url": file_url,
                "customizeFilePath": file_path}
        if file_name:
            body["fileName"] = file_name
        return self._request("POST", "/vcpcloud/api/padApi/uploadFileV3",
                             body=body, file_upload=True)
