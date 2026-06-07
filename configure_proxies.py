"""
One-time proxy setup for all VMOS devices using smartIp.
Reads devices.json + proxies.txt, assigns one proxy per device.
Each device restarts (~10-30s) to activate the proxy.
"""
import sys, json, time, logging, socket
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from vmos.client import VMOSClient
from utils.proxy import ProxyManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s %(message)s")
logger = logging.getLogger("configure_proxies")

DEVICES_JSON = BASE_DIR / "devices.json"
PROXY_FILE = BASE_DIR / "config" / "proxies.txt"


def get_devices() -> list[str]:
    return json.loads(DEVICES_JSON.read_text()).get("pad_codes", [])


def wait_device_ready(api, pad: str, timeout: int = 300) -> bool:
    for i in range(timeout // 5):
        try:
            r = api.send_adb(pad, "echo ready")
            if r and r[0].get("taskId"):
                return True
        except:
            pass
        time.sleep(5)
    return False


def configure_device(api, pad: str, proxy_str: str) -> bool:
    if not proxy_str:
        logger.warning("[%s] No proxy", pad)
        return False

    parts = proxy_str.split(":", 3)
    userpart = parts[2]
    password = parts[3]
    session = userpart.split("session_")[1].split(",")[0] if "session_" in userpart else "?"
    host = socket.gethostbyname("portal.anyip.io")
    port = 1080

    logger.info("[%s] Assigning proxy session_%s via smartIp...", pad, session)

    # 1. Validate proxy
    try:
        ck = api.check_ip(host=host, port=port, username=userpart,
                          password=password, proxy_type="http")
        if not ck.get("proxyWorking"):
            logger.error("[%s] Proxy check failed!", pad)
            return False
        logger.info("  [%s] Proxy valid: %s (%s)", pad, ck.get("publicIp"), ck.get("proxyLocation"))
    except Exception as e:
        logger.error("  [%s] checkIP error: %s", pad, e)
        return False

    time.sleep(1)

    # 2. Check if device is responsive
    if not wait_device_ready(api, pad, timeout=30):
        logger.error("  [%s] Device not responsive, skipping smartIp", pad)
        return False

    # 3. Apply smartIp
    try:
        task = api.set_smart_ip(
            pad_codes=[pad], host=host, port=port,
            username=userpart, password=password,
            proxy_type="http", mode="proxy"
        )
        logger.info("  [%s] smartIp task: %s", pad, task)
    except Exception as e:
        logger.error("  [%s] smartIp failed: %s", pad, e)
        return False

    # 4. Wait for device to restart and come back
    logger.info("  [%s] Waiting for restart...", pad)
    if wait_device_ready(api, pad, timeout=120):
        logger.info("  [%s] Device back online!", pad)
    else:
        logger.warning("  [%s] Device not back within 120s", pad)
        return False

    # 5. Verify proxy active
    time.sleep(3)
    try:
        r = api.send_adb(pad, "curl -s --connect-timeout 10 ipinfo.io/ip 2>/dev/null || echo fail")
        tid = r[0]["taskId"]
        time.sleep(8)
        d = api.pad_task_detail([tid])
        ip = (d[0].get("taskResult") or d[0].get("errorMsg") or "").strip()
        logger.info("  [%s] Traffic IP: %s", pad, ip)
    except:
        pass

    logger.info("  [%s] Proxy configured!", pad)
    return True


def main():
    codes = get_devices()
    logger.info("Found %d devices: %s", len(codes), codes)

    pm = ProxyManager(str(PROXY_FILE))
    proxies = pm.assign_to_devices(len(codes))
    api = VMOSClient()

    for i, pad in enumerate(codes):
        logger.info("")
        logger.info("=" * 50)
        logger.info("Device %d/%d: %s", i + 1, len(codes), pad)
        logger.info("=" * 50)
        configure_device(api, pad, proxies[i])

    logger.info("")
    logger.info("All devices configured!")


if __name__ == "__main__":
    main()
