import json
import time
import logging
import argparse
import csv
import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw
from vmos.automation import VmosAutomation
from vmos.client import VMOSClient, VMOSAPIError
from utils.getatext import GetATextClient
from config.settings import config

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PLACEHOLDER_MAP = {
    "{EMAIL}": "email", "{PASSWORD}": "password", "{PHONE}": "phone",
    "{FIRST_NAME}": "first_name", "{BIRTHDAY}": "birthday", "{ZIP}": "zip",
    "{CITY_STATE}": "city_state", "{BIO}": "about_me", "{JOB}": "job",
    "{COMPANY}": "company", "{GENDER}": "gender", "{LOOKING_FOR}": "looking_for",
}

def load_profiles(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def resolve_label(label, profile):
    if not label:
        return ""
    for ph, key in PLACEHOLDER_MAP.items():
        if ph == label or ph.lower() == label.lower():
            return profile.get(key, "")
    return label


class InteractiveRunner:
    def __init__(self, flow_path, pad_code, profile, dry_run=False):
        self.client = VMOSClient()
        self.v = VmosAutomation(self.client, pad_code)
        self.pad_code = pad_code
        self.flow = json.loads(Path(flow_path).read_text(encoding="utf-8"))
        self.profile = profile
        self.dry_run = dry_run
        self.res_w = self.flow.get("resolution", {}).get("width", 540)
        self.res_h = self.flow.get("resolution", {}).get("height", 960)
        self.screenshots = self.flow.get("screenshots", [])
        self._step_index = 0
        self._total_steps = sum(len(s["actions"]) for s in self.screenshots)
        self._sms = None
        self._rental_id = None
        self._rented_number = None
        self._corrections = []  # list of (step, old_x, old_y, new_x, new_y)

    def _ensure_sms(self):
        if not self._sms:
            self._sms = GetATextClient(api_key=config.SMS_API_KEY)
        return self._sms

    def _handle_rent_number(self):
        sms = self._ensure_sms()
        area_codes = "502,859,606"
        logger.info("Renting Match.com number (area: %s)...", area_codes)
        result = sms.rent_number(service="match", area_codes=area_codes)
        if result:
            self._rental_id = result.get("id")
            self._rented_number = result.get("number")
            self.profile["phone"] = self._rented_number
            logger.info("Rented %s (ID: %s)", self._rented_number, self._rental_id)
            return self._rented_number
        logger.error("Failed to rent number!")
        return None

    def _handle_sms_code(self):
        if not self._rental_id:
            logger.error("No rental ID!")
            return None
        sms = self._ensure_sms()
        code = sms.get_sms_code(rental_id=self._rental_id, timeout=180, poll_interval=3)
        if code:
            return code
        return None

    def _show_screenshot_and_get_coord(self, action, step_label):
        """Take screenshot, show it with tap marker, let user confirm/correct."""
        try:
            result = self.client.screenshot(self.pad_code, rotation=0)
            img_data = result.get("img") or result.get("image") or result.get("data")
            if img_data and isinstance(img_data, str):
                import base64, io
                img_bytes = base64.b64decode(img_data)
                img = Image.open(io.BytesIO(img_bytes))
            else:
                logger.warning("No image data in screenshot response")
                return None, None
        except Exception as e:
            logger.warning("Screenshot failed: %s", e)
            return None, None

        # Draw planned tap marker
        planned_x, planned_y = action.get("x", 0), action.get("y", 0)
        sc_w, sc_h = img.size
        draw_x = int(planned_x * sc_w / self.res_w)
        draw_y = int(planned_y * sc_h / self.res_h)

        draw = ImageDraw.Draw(img)
        r = 10
        draw.ellipse([draw_x - r, draw_y - r, draw_x + r, draw_y + r],
                     outline="red", width=3)
        draw.line([draw_x - r - 5, draw_y, draw_x + r + 5, draw_y],
                  fill="red", width=2)
        draw.line([draw_x, draw_y - r - 5, draw_x, draw_y + r + 5],
                  fill="red", width=2)

        # Show in Tkinter window
        root = tk.Tk()
        root.title(f"{step_label} — Click to correct, or press Confirm")
        sw, sh = root.winfo_screenwidth() - 100, root.winfo_screenheight() - 100
        scale = min(sw / sc_w, sh / sc_h, 1.5)
        dw, dh = int(sc_w * scale), int(sc_h * scale)
        photo = ImageTk.PhotoImage(img.resize((dw, dh), Image.LANCZOS))
        canvas = tk.Canvas(root, width=dw, height=dh, cursor="crosshair")
        canvas.pack()
        canvas.create_image(0, 0, anchor="nw", image=photo)

        result_coord = [None, None]  # [new_x, new_y] or None

        def on_click(event):
            ix = int(event.x / scale)
            iy = int(event.y / scale)
            fx = int(ix * self.res_w / sc_w)
            fy = int(iy * self.res_h / sc_h)
            result_coord[0] = fx
            result_coord[1] = fy
            root.destroy()

        def on_confirm():
            root.destroy()

        canvas.bind("<Button-1>", on_click)
        confirm_btn = tk.Button(root, text="Confirm Current", command=on_confirm,
                                bg="#4CAF50", fg="white", font=("", 12))
        confirm_btn.pack(pady=5)

        label_text = f"Planned: ({planned_x}, {planned_y})  |  Click to override or press Confirm"
        tk.Label(root, text=label_text, font=("", 10)).pack()

        root.geometry(f"+{100}+{50}")
        root.wait_window()

        if result_coord[0] is not None:
            return result_coord[0], result_coord[1]
        return None, None  # confirmed, no change

    def run(self):
        logger.info("Starting interactive run (%d steps)", self._total_steps)
        self.v.w = self.res_w
        self.v.h = self.res_h

        pkg = config.MATCH_APP_PACKAGE
        if pkg and not self.dry_run:
            logger.info("Launching app: %s", pkg)
            self.v.client.start_app(self.v.pad_code, pkg)
            time.sleep(12)

        for screen in self.screenshots:
            for action in screen["actions"]:
                ok = self._execute_interactive(screen, action)
                self._step_index += 1
                time.sleep(5.0)

        if self._corrections:
            logger.info("Corrections made:")
            for c in self._corrections:
                logger.info("  Step %d: (%d, %d) -> (%d, %d)", *c)

        logger.info("Flow completed (%d steps)", self._total_steps)
        return True

    def _execute_interactive(self, screen, action):
        atype = action["type"]
        x = action.get("x")
        y = action.get("y")
        label = action.get("label", "")
        raw_label = label
        resolved = resolve_label(label, self.profile)

        step_num = self._step_index + 1
        step_label = f"Step {step_num}/{self._total_steps} — {screen['file']} — {atype}"
        logger.info("[%s] %s (%s)", self.pad_code, step_label, raw_label or resolved)

        if self.dry_run:
            time.sleep(0.3)
            return True

        # For tap actions, show screenshot and let user confirm/correct
        if atype == "tap" and x is not None and y is not None:
            new_x, new_y = self._show_screenshot_and_get_coord(action, step_label)
            if new_x is not None:
                self._corrections.append((step_num, x, y, new_x, new_y))
                action["x"] = new_x
                action["y"] = new_y
                x, y = new_x, new_y
                logger.info("Corrected to (%d, %d)", new_x, new_y)

            self._execute_with_retry(self.v.tap, x, y)
            return True

        elif atype == "text":
            if x is not None and y is not None:
                self._execute_with_retry(self.v.tap, x, y, retries=5)
                time.sleep(1.5)

                effective_text = resolved
                if raw_label == "{RENT_NUMBER}":
                    effective_text = self._handle_rent_number()
                elif raw_label == "{SMS_CODE}":
                    effective_text = self._handle_sms_code()

                if effective_text:
                    adb_cmd = f"input text {effective_text}"
                    try:
                        self.v.client.send_adb(self.v.pad_code, adb_cmd)
                    except Exception:
                        self._execute_with_retry(self.v.text, effective_text)

                    try:
                        self.v.client.send_adb(self.v.pad_code, "input keyevent 111")
                    except Exception:
                        pass
                    time.sleep(5)
            return True

        elif atype == "swipe":
            direction = action.get("direction", "TOP_TO_BOTTOM")
            self._execute_with_retry(self.v.swipe, direction)
            return True

        elif atype == "wait":
            secs = action.get("seconds", 2)
            time.sleep(secs)
            return True

        logger.warning("Unknown action: %s", atype)
        return False

    def _execute_with_retry(self, func, *args, retries=5, **kwargs):
        last_exc = None
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except VMOSAPIError as e:
                wait = 10 + attempt * 10
                logger.warning("API error, retry in %ds (%d/%d): %s",
                               wait, attempt + 1, retries, e)
                time.sleep(wait)
                last_exc = e
            except Exception as e:
                last_exc = e
                raise
        raise last_exc


def main():
    parser = argparse.ArgumentParser(description="Interactive flow runner")
    parser.add_argument("flow", help="Path to flow.json")
    parser.add_argument("--pad", required=True, help="VMOS padCode")
    parser.add_argument("--profile", required=True, help="CSV profiles")
    parser.add_argument("--index", type=int, default=0, help="Row in CSV")
    args = parser.parse_args()

    profiles = load_profiles(args.profile)
    profile = profiles[args.index]

    runner = InteractiveRunner(args.flow, args.pad, profile)
    ok = runner.run()

    if runner._corrections:
        print("\n=== Corrections Made ===")
        for c in runner._corrections:
            print(f"  Step {c[0]}: ({c[1]}, {c[2]}) -> ({c[3]}, {c[4]})")

        # Save corrections to flow.json
        with open(args.flow) as f:
            flow = json.load(f)
        with open(args.flow, 'w') as f:
            json.dump(flow, f, indent=2, ensure_ascii=True)
        print(f"Corrections saved to {args.flow}")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
