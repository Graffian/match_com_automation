import sys
import time
import json
import random
import socket
import logging
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from vmos.client import VMOSClient, VMOSAPIError
from vmos.automation import VmosAutomation
from utils.proxy import ProxyManager
from config.settings import config as cfg
from tools.vmos_dashboard import (
    _make_driver, login, dismiss_all_overlays,
    scrape_pad_codes, buy_phones, save_pad_codes,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s %(message)s")
logger = logging.getLogger("run_all")

DEVICES_JSON = BASE_DIR / "devices.json"
FOLDER_INDEX_FILE = BASE_DIR / "folder_index.txt"
FLOW_JSON = BASE_DIR / "flow.json"
PHOTOS_ROOT = Path("C:/match_photos")
CYCLE_SECONDS = 50 * 60
PHOTOS_PER_DEVICE = 6
TARGET_COUNT = 20
MATCH_PACKAGE = "com.match.android.matchmobile"
PROXY_FILE = BASE_DIR / "config" / "proxies.txt"

GIRL_NAMES = [
    "Evelyn", "Ava", "Elizabeth", "Mia", "Sophia", "Charlotte", "Amelia", "Isabella",
    "Emma", "Olivia", "Luna", "Harper", "Ella", "Scarlett", "Grace", "Chloe",
    "Zoey", "Lily", "Aria", "Nora", "Camila", "Riley", "Avery", "Hannah",
    "Leah", "Audrey", "Savannah", "Samantha", "Skylar", "Victoria", "Kaylee", "Brooklyn",
    "Peyton", "Layla", "Allison", "Anna", "Madelyn", "Hailey", "Genesis", "Naomi",
]
BIRTHDAYS = [
    "01081997", "01171997", "05171997", "11211997",
    "03151998", "07091998", "09221998", "12111998",
    "02101999", "04181999", "06151999", "08301999",
    "01102000", "03142000", "05262000", "07212000",
]
ABOUT_ME = [
    "Hockey fan and trivia night champion. Double date?",
    "Dog mom who loves outdoor adventures and live music.",
    "Fitness enthusiast who also loves a good Netflix binge.",
    "Sushi addict who enjoys hiking and board games on weekends.",
    "Bookworm and coffee connoisseur looking for my next adventure.",
    "Weekend brunch enthusiast who loves road trips and live music.",
    "Yoga lover who's always down for live music and good food.",
    "Art museum wanderer with a soft spot for rom-coms and tacos.",
    "Foodie who loves trying new recipes and exploring local breweries.",
    "Travel bug who's been to 12 countries and counting. Let's compare stories.",
    "Music festival junkie looking for a duet partner in karaoke.",
    "Running my own small business and looking for someone to share takeout with.",
    "Plant mom by day, karaoke queen by night.",
    "Thrift store enthusiast who can assemble IKEA furniture without instructions.",
    "True crime podcasts and long walks with my golden retriever.",
]
JOBS = [
    "Software Engineer", "Content Writer", "Barista", "Designer",
    "Marketing Manager", "Nurse", "Teacher", "Photographer",
    "Accountant", "Graphic Designer", "Event Planner", "Yoga Instructor",
    "Social Media Manager", "Dental Hygienist", "Data Analyst", "Chef",
]
COMPANIES = [
    "Capture Photography", "BrewHouse Cafe", "ContentLab", "RetailPro",
    "TechVista", "GreenLeaf Marketing", "Pinnacle Health", "BrightPath Media",
    "Summit Designs", "Crestline Studios", "Meridian Group", "Aspire Wellness",
    "RiverOak Digital", "NorthStar Solutions", "Bluegrass Creative", "HarborView Inc",
]


def read_folder_index() -> int:
    try:
        return int(FOLDER_INDEX_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def write_folder_index(idx: int) -> None:
    FOLDER_INDEX_FILE.write_text(str(idx))


def get_next_photo_folders(count: int) -> list[Path]:
    if not PHOTOS_ROOT.is_dir():
        logger.warning("Photo root %s does not exist", PHOTOS_ROOT)
        return []
    folders = sorted([p for p in PHOTOS_ROOT.iterdir() if p.is_dir()])
    if not folders:
        logger.warning("No photo folders in %s", PHOTOS_ROOT)
        return []
    idx = read_folder_index()
    selected = []
    for _ in range(count):
        if idx >= len(folders):
            idx = 0
        selected.append(folders[idx])
        idx += 1
    write_folder_index(idx)
    return selected


def generate_profiles(count: int) -> list[dict]:
    profiles = []
    used_emails = set()
    for i in range(count):
        name = random.choice(GIRL_NAMES)
        bday = random.choice(BIRTHDAYS)
        about = random.choice(ABOUT_ME)
        job = random.choice(JOBS)
        company = random.choice(COMPANIES)
        tag = f"match{random.randint(10000,99999)}"
        email = f"{tag}@mailinator.com"
        while email in used_emails:
            tag = f"match{random.randint(10000,99999)}"
            email = f"{tag}@mailinator.com"
        used_emails.add(email)
        profiles.append({
            "email": email,
            "password": f"{name.capitalize()}{random.randint(1000,9999)}!",
            "first_name": name,
            "phone": "",
            "birthday": bday,
            "zip": "40202",
            "city_name": "Louisville",
            "city_state": "Louisville KY",
            "city_full": "Louisville, Louisville KY",
            "about_me": about,
            "job": job,
            "company": company,
            "gender": "female",
            "looking_for": "men",
        })
    return profiles


def upload_photos(api, pad_code: str, folder: Path,
                  catbox_proxy: str = None) -> None:
    import requests
    photos = sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.png"))
    photos = photos[:PHOTOS_PER_DEVICE]
    if not photos:
        logger.warning("[%s] No photos in %s", pad_code, folder.name)
        return
    proxies = {"http": catbox_proxy, "https": catbox_proxy} if catbox_proxy else None
    for j, path in enumerate(photos):
        try:
            resp = requests.post("https://catbox.moe/user/api.php",
                                 data={"reqtype": "fileupload"},
                                 files={"fileToUpload": open(path, "rb")},
                                 proxies=proxies,
                                 timeout=60)
            if resp.status_code != 200:
                logger.error("[%s] catbox failed: %s", pad_code, resp.text[:100])
                continue
            api.upload_file_v3(pad_code, resp.text.strip(),
                               file_name=f"photo_{j+1}.jpg",
                               file_path="/Pictures/")
        except Exception as e:
            logger.error("[%s] photo %d failed: %s", pad_code, j + 1, e)
        time.sleep(1)


def load_or_fetch_pad_codes() -> list[str]:
    if DEVICES_JSON.exists():
        try:
            data = json.loads(DEVICES_JSON.read_text())
            codes = data.get("pad_codes", [])
            if codes:
                logger.info("Loaded %d pad codes from %s", len(codes), DEVICES_JSON.name)
                return codes
        except Exception:
            pass
    logger.info("No saved pad codes — opening dashboard to scrape existing phones")
    driver = _make_driver(headless=True)
    try:
        login(driver, cfg.VMOS_DASHBOARD_EMAIL, cfg.VMOS_DASHBOARD_PASSWORD)
        dismiss_all_overlays(driver)
        codes = scrape_pad_codes(driver)
        if not codes:
            logger.error("No pad codes found on dashboard!")
            return []
        save_pad_codes(codes)
        logger.info("Found %d existing phones — no phones purchased", len(codes))
        return codes
    finally:
        driver.quit()


def clear_app_data(api, pad_code: str) -> None:
    try:
        api.send_adb(pad_code, "input keyevent 3")
        time.sleep(1)
        api.send_adb(pad_code, f"pm clear {MATCH_PACKAGE}")
        logger.info("[%s] App data cleared", pad_code)
    except VMOSAPIError as e:
        logger.warning("[%s] Clear failed: %s", pad_code, e)


def clear_device_photos(api, pad_code: str) -> None:
    try:
        api.send_adb(pad_code, "rm -rf /sdcard/Pictures/*.jpg /sdcard/Pictures/*.png 2>/dev/null")
        api.send_adb(pad_code, "am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/Pictures/ 2>/dev/null")
        logger.info("[%s] Photos deleted", pad_code)
    except Exception as e:
        logger.warning("[%s] Photo delete failed, moving on: %s", pad_code, e)


PLACEHOLDER_MAP = {
    "{EMAIL}": "email", "{PASSWORD}": "password", "{PHONE}": "phone",
    "{FIRST_NAME}": "first_name", "{BIRTHDAY}": "birthday", "{ZIP}": "zip",
    "{CITY_NAME}": "city_name", "{CITY_STATE}": "city_state",
    "{CITY_FULL}": "city_full", "{BIO}": "about_me", "{JOB}": "job",
    "{COMPANY}": "company", "{GENDER}": "gender", "{LOOKING_FOR}": "looking_for",
}

def resolve_label(label: str, profile: dict) -> str:
    if not label:
        return ""
    for ph, key in PLACEHOLDER_MAP.items():
        if ph == label or ph.lower() == label.lower():
            return profile.get(key, "")
    return label


def burst_tap(autos, x, y):
    threads = []
    for a in autos:
        t = threading.Thread(target=a.tap, args=(x, y))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()


def burst_adb(autos, codes, cmds):
    threads = []
    for i, a in enumerate(autos):
        t = threading.Thread(target=a.client.send_adb, args=(codes[i], cmds[i]))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()


def burst_swipe(autos, direction):
    threads = []
    for a in autos:
        t = threading.Thread(target=a.swipe, args=(direction,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()


class SyncSMS:
    def __init__(self):
        self._rentals = {}

    def ensure_rented(self, idx: int, profile: dict, pad_code: str):
        if idx in self._rentals:
            return self._rentals[idx]["number"]
        from utils.getatext import GetATextClient
        from config.settings import Config
        cfg = Config()
        sms = GetATextClient(api_key=cfg.SMS_API_KEY)
        result = sms.rent_number(service="match", area_codes="502,859")
        rent_id = result.get("id")
        number = result.get("number")
        profile["phone"] = number
        self._rentals[idx] = {"id": rent_id, "number": number}
        logger.info("[%s] Rented %s (id=%s, price=%.2f)", pad_code, number, rent_id, result.get("price", 0))
        return number

    def get_code(self, idx: int, pad_code: str) -> str:
        if idx not in self._rentals:
            logger.error("[%s] No rental ID!", pad_code)
            return ""
        from utils.getatext import GetATextClient
        from config.settings import Config
        cfg = Config()
        sms = GetATextClient(api_key=cfg.SMS_API_KEY)
        code = sms.get_sms_code(rental_id=self._rentals[idx]["id"], timeout=180, poll_interval=3)
        if code:
            logger.info("[%s] SMS code: %s", pad_code, code)
        else:
            logger.error("[%s] SMS code not received", pad_code)
        return code or ""

    def wait_all_codes(self, pad_count: int) -> list[str]:
        """Fetch SMS codes for all rentals respecting rate limits."""
        ids = [self._rentals[i]["id"] for i in range(pad_count) if i in self._rentals]
        if not ids:
            return []
        from utils.getatext import GetATextClient
        from config.settings import Config
        cfg = Config()
        sms = GetATextClient(api_key=cfg.SMS_API_KEY)
        codes = sms.wait_for_codes(ids, timeout=300)
        for i, code in enumerate(codes):
            orig = self._rentals.get(i)
            if orig:
                logger.info("[%s] SMS code: %s", orig.get("number", f"idx={i}"), code or "(none)")
        return codes


def cycle(t0):
    start = t0
    logger.info("=" * 60)
    logger.info("CYCLE START — %s", time.strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    api = VMOSClient()
    codes = load_or_fetch_pad_codes()
    if not codes:
        logger.error("No pad codes — aborting cycle")
        return False

    catbox_pm = ProxyManager(str(PROXY_FILE))
    if catbox_pm.proxies:
        p = catbox_pm.proxies[0].split(":", 3)
        catbox_proxy = f"http://{p[2]}:{p[3]}@{p[0]}:{p[1]}"
        logger.info("Using proxy for catbox uploads: %s:%s", p[0], p[1])
    else:
        catbox_proxy = None
        logger.warning("No proxies available — catbox will connect directly")

    folders = get_next_photo_folders(len(codes))
    if folders:
        for pc, folder in zip(codes, folders):
            logger.info("[%s] Uploading photos from %s", pc, folder.name)
            upload_photos(api, pc, folder, catbox_proxy=catbox_proxy)
    else:
        logger.warning("Skipping photo upload")

    profiles = generate_profiles(len(codes))
    logger.info("Generated %d fresh profiles for this cycle", len(profiles))

    flow = json.loads(FLOW_JSON.read_text(encoding="utf-8"))
    res_w = flow.get("resolution", {}).get("width", 540)
    res_h = flow.get("resolution", {}).get("height", 960)
    screenshots = flow.get("screenshots", [])

    all_actions = []
    for screen in screenshots:
        for action in screen["actions"]:
            all_actions.append(action)

    loop_cfg = flow.get("flow_loop", {})
    loop_start = loop_cfg.get("start_step")
    loop_end = loop_cfg.get("end_step")

    if loop_start and loop_end:
        loop_actions = all_actions[loop_start - 1:loop_end]
        main_actions = all_actions[:loop_start - 1]
    else:
        loop_actions = []
        main_actions = all_actions

    autos = [VmosAutomation(VMOSClient(), pc) for pc in codes]
    for a in autos:
        a.w = res_w
        a.h = res_h

    pm = ProxyManager(str(PROXY_FILE))
    proxies = pm.assign_to_devices(len(codes))

    for i, a in enumerate(autos):
        pr = proxies[i]
        if not pr:
            logger.warning("[%s] No proxy assigned", a.pad_code)
            continue

        parts = pr.split(":", 3)
        proxy_host = parts[0]
        proxy_port = int(parts[1])
        proxy_ip = socket.gethostbyname(proxy_host)
        userpart = parts[2]
        password = parts[3]
        session = userpart.split("session_")[1].split(",")[0] if "session_" in userpart else "?"

        logger.info("[%s] Setting proxy session_%s via smartIp...", a.pad_code, session)

        try:
            ck = a.client.check_ip(host=proxy_ip, port=proxy_port,
                                   username=userpart, password=password,
                                   proxy_type="http")
            if not ck.get("proxyWorking"):
                logger.warning("[%s] Proxy check failed, skipping", a.pad_code)
                time.sleep(5)
                continue
        except Exception as e:
            logger.warning("[%s] checkIP error: %s", a.pad_code, e)
            time.sleep(5)
            continue

        time.sleep(3)

        try:
            a.client.set_smart_ip(
                pad_codes=[a.pad_code], host=proxy_ip, port=proxy_port,
                username=userpart, password=password,
                proxy_type="http", mode="proxy"
            )
            logger.info("[%s] smartIp queued", a.pad_code)
        except Exception as e:
            logger.warning("[%s] smartIp error: %s", a.pad_code, e)

        time.sleep(10)

    logger.info("=== Proxy setup done, waiting for devices to restart ===")
    for i, a in enumerate(autos):
        pad = codes[i]
        for attempt in range(24):
            try:
                r = a.client.send_adb(pad, "echo ready")
                if r and r[0].get("taskId"):
                    logger.info("[%s] Back online after ~%ds", pad, attempt * 5)
                    break
            except:
                pass
            time.sleep(5)
        else:
            logger.warning("[%s] Not back within 120s", pad)

    time.sleep(30)

    pkg = "com.match.android.matchmobile"
    logger.info("Launching app on all devices...")
    for a in autos:
        a.client.start_app(a.pad_code, pkg)
    logger.info("Wait 12s for app load...")
    time.sleep(12)

    sms = SyncSMS()

    step_idx = 0
    total = len(all_actions)

    def run_actions(actions):
        nonlocal step_idx
        for action in actions:
            atype = action["type"]
            x = action.get("x")
            y = action.get("y")
            label = action.get("label", "")
            raw_label = label

            logger.info("Step %d/%d: %s (%s) at (%s, %s) — ALL",
                        step_idx + 1, total,
                        atype, label or "—", x or "—", y or "—")

            if atype == "tap":
                if x is not None and y is not None:
                    burst_tap(autos, x, y)

            elif atype == "text":
                if x is not None and y is not None:
                    burst_tap(autos, x, y)
                    time.sleep(1.5)
                    text_cmds = [""] * len(autos)
                    if raw_label == "{SMS_CODE}":
                        sms_codes = sms.wait_all_codes(len(autos))
                        for i in range(len(autos)):
                            if i < len(sms_codes) and sms_codes[i]:
                                text_cmds[i] = f"input text {sms_codes[i]}"
                    elif raw_label == "{RENT_NUMBER}":
                        for i in range(len(autos)):
                            txt = sms.ensure_rented(i, profiles[i], codes[i])
                            if txt:
                                text_cmds[i] = f"input text {txt}"
                            time.sleep(6)
                    else:
                        for i in range(len(autos)):
                            txt = resolve_label(raw_label, profiles[i])
                            if txt:
                                text_cmds[i] = f"input text {txt}"
                    valid = [(i, c) for i, c in enumerate(text_cmds) if c]
                    if valid:
                        idxs, cmds = zip(*valid)
                        burst_adb([autos[i] for i in idxs], [codes[i] for i in idxs], list(cmds))
                    if not action.get("keep_keyboard"):
                        burst_adb(autos, codes, ["input keyevent 111"] * len(autos))
                    time.sleep(5)

            elif atype == "swipe":
                direction = action.get("direction", "TOP_TO_BOTTOM")
                burst_swipe(autos, direction)

            elif atype == "wait":
                secs = action.get("seconds", 2)
                time.sleep(secs)

            step_idx += 1
            time.sleep(10.0)

    run_actions(main_actions)

    if loop_actions:
        logger.info("Swipe loop running until %.1f min cycle end", CYCLE_SECONDS / 60)
        while time.time() - t0 < CYCLE_SECONDS:
            run_actions(loop_actions)

    logger.info("Flow completed — clearing app data and photos on all devices")
    for pc in codes:
        clear_app_data(api, pc)
        clear_device_photos(api, pc)

    elapsed = time.time() - start
    logger.info("Cycle done — %.1fs (%.1f min)", elapsed, elapsed / 60)
    return True


def main():
    logger.info("run_all.py started")
    cycle_num = 0
    while True:
        cycle_num += 1
        logger.info("\n### CYCLE %d ###", cycle_num)
        t0 = time.time()
        try:
            ok = cycle(t0)
            if not ok:
                logger.error("Cycle %d failed", cycle_num)
        except Exception as e:
            logger.exception("Cycle %d crashed: %s", cycle_num, e)
        wait = max(0, CYCLE_SECONDS - (time.time() - t0))
        logger.info("Waiting %.1fs (%.1f min) until next cycle", wait, wait / 60)
        if wait > 0:
            time.sleep(wait)


if __name__ == "__main__":
    main()
