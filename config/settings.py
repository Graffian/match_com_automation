import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    def __init__(self, env_file: str = None):
        self._load_dotenv(env_file or BASE_DIR / ".env")

        # VMOS Cloud
        self.VMOS_API_KEY = os.getenv("VMOS_API_KEY", "")
        self.VMOS_API_SECRET = os.getenv("VMOS_API_SECRET", "")
        self.VMOS_BASE_URL = os.getenv("VMOS_BASE_URL", "https://api.vmoscloud.com/v1")

        # Appium
        self.APPIUM_HOST = os.getenv("APPIUM_HOST", "127.0.0.1")
        self.APPIUM_PORT = int(os.getenv("APPIUM_PORT", "4723"))

        # Match.com app
        self.MATCH_APP_PACKAGE = os.getenv("MATCH_APP_PACKAGE", "com.match.android")
        self.MATCH_APP_ACTIVITY = os.getenv("MATCH_APP_ACTIVITY", "com.match.android.activity.StartActivity")

        # SMS service
        self.SMS_PROVIDER = os.getenv("SMS_PROVIDER", "getatext")
        self.SMS_API_KEY = os.getenv("SMS_API_KEY", "")
        self.SMS_SERVICE = os.getenv("SMS_SERVICE", "match")
        self.SMS_COUNTRY = os.getenv("SMS_COUNTRY", "us")

        # Proxy
        self.PROXY_FILE = os.getenv("PROXY_FILE", str(BASE_DIR / "config" / "proxies.txt"))
        self.PROXY_ROTATION = os.getenv("PROXY_ROTATION", "round_robin")

        # VMOS Dashboard
        self.VMOS_DASHBOARD_EMAIL = os.getenv("VMOS_DASHBOARD_EMAIL", "")
        self.VMOS_DASHBOARD_PASSWORD = os.getenv("VMOS_DASHBOARD_PASSWORD", "")

        self.ACCOUNTS_DB = str(BASE_DIR / "data" / "accounts.db")

    def _load_dotenv(self, path: str):
        if not os.path.exists(path):
            return
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip()
                if not key:
                    continue
                os.environ.setdefault(key, val)

    @property
    def appium_url(self) -> str:
        return f"http://{self.APPIUM_HOST}:{self.APPIUM_PORT}"

    @classmethod
    def load(cls, path: str = None) -> "Config":
        return cls(path)


config = Config()
