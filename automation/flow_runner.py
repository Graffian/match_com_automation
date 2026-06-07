"""
Flow executor — reads a recorded flow JSON and runs it on a VMOS phone.

Special placeholders:
  {RENT_NUMBER}  — calls GetAText to rent a number, stores rental info
  {SMS_CODE}     — polls GetAText for the SMS verification code
  {WAIT_SMS}     — waits but does NOT type (for auto-fill scenarios)

Usage:
    python -m automation.flow_runner flow.json --pad APP5BC... --profile profiles.csv --index 0
"""
import json
import time
import logging
import argparse
import csv
import sys
from pathlib import Path
from typing import Optional
from vmos.automation import VmosAutomation
from vmos.client import VMOSClient, VMOSAPIError
from utils.getatext import GetATextClient
from config.settings import config

logger = logging.getLogger(__name__)

PLACEHOLDER_MAP = {
    "{EMAIL}": "email",
    "{PASSWORD}": "password",
    "{PHONE}": "phone",
    "{FIRST_NAME}": "first_name",
    "{BIRTHDAY}": "birthday",
    "{ZIP}": "zip",
    "{CITY_NAME}": "city_name",
    "{CITY_STATE}": "city_state",
    "{CITY_FULL}": "city_full",
    "{BIO}": "about_me",
    "{JOB}": "job",
    "{COMPANY}": "company",
    "{GENDER}": "gender",
    "{LOOKING_FOR}": "looking_for",
}


def load_profiles(csv_path: str) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def resolve_label(label: str, profile: dict) -> str:
    if not label:
        return ""
    for ph, key in PLACEHOLDER_MAP.items():
        if ph == label or ph.lower() == label.lower():
            return profile.get(key, "")
    return label


class FlowRunner:
    def __init__(self, flow_path: str, vmos_auto: VmosAutomation,
                 profile: dict, dry_run: bool = False):
        self.flow = json.loads(Path(flow_path).read_text(encoding="utf-8"))
        self.v = vmos_auto
        self.profile = profile
        self.dry_run = dry_run
        self.res_w = self.flow.get("resolution", {}).get("width", 540)
        self.res_h = self.flow.get("resolution", {}).get("height", 960)
        self.screenshots = self.flow.get("screenshots", [])
        self._step_index = 0
        self._total_steps = sum(len(s["actions"]) for s in self.screenshots)
        self._sms = None  # GetAText client
        self._rental_id = None
        self._rented_number = None

    def _write_progress(self, screen, action):
        label = action.get("label", "")
        atype = action["type"]
        x = action.get("x", "")
        y = action.get("y", "")
        direction = action.get("direction", "")
        secs = action.get("seconds", "")
        fname = screen["file"]
        info = (f"step={self._step_index + 1}\nfile={fname}\ntype={atype}\n"
                f"x={x}\ny={y}\nlabel={label}\ndirection={direction}\nseconds={secs}\n")
        with open("_step_progress.txt", "w") as f:
            f.write(info)

    def _ensure_sms(self) -> GetATextClient:
        if not self._sms:
            self._sms = GetATextClient(api_key=config.SMS_API_KEY)
        return self._sms

    def _handle_rent_number(self) -> Optional[str]:
        sms = self._ensure_sms()
        area_codes = "502,859,606"
        logger.info("Renting Match.com number (area: %s)...", area_codes)
        result = sms.rent_number(service="match", area_codes=area_codes)
        if result:
            self._rental_id = result.get("id")
            self._rented_number = result.get("number")
            logger.info("Rented %s (ID: %s, $%.2f)",
                        self._rented_number, self._rental_id, result.get("price", 0))

            # Update the in-memory profile so {PHONE} also resolves
            self.profile["phone"] = self._rented_number
            return self._rented_number
        logger.error("Failed to rent number!")
        return None

    def _handle_sms_code(self) -> Optional[str]:
        if not self._rental_id:
            logger.error("No rental ID — call {RENT_NUMBER} first!")
            return None
        sms = self._ensure_sms()
        logger.info("Waiting for SMS code (rental %s)...", self._rental_id)
        code = sms.get_sms_code(rental_id=self._rental_id, timeout=180, poll_interval=3)
        if code:
            logger.info("SMS code: %s", code)
            return code
        logger.error("SMS code not received within timeout")
        return None

    def run(self) -> bool:
        logger.info("Starting flow run (%d steps)", self._total_steps)
        self._step_index = 0

        # Set the VmosAutomation resolution to match flow's recorded resolution
        self.v.w = self.res_w
        self.v.h = self.res_h

        # Launch the Match.com app first
        pkg = config.MATCH_APP_PACKAGE
        if pkg and not self.dry_run:
            logger.info("Launching app: %s", pkg)
            self.v.client.start_app(self.v.pad_code, pkg)
            logger.info("Waiting 12s for app to fully load...")
            time.sleep(12)

        # Build flat list of (screen, action) tuples
        all_actions = []
        for screen in self.screenshots:
            for action in screen["actions"]:
                all_actions.append((screen, action))

        loop_cfg = self.flow.get("flow_loop", {})
        loop_start = loop_cfg.get("start_step")
        loop_end = loop_cfg.get("end_step")

        if loop_start and loop_end:
            # Loop start/end are 1-indexed
            loop_start_idx = loop_start - 1
            loop_end_idx = loop_end - 1
            loop_actions = all_actions[loop_start_idx:loop_end_idx + 1]
            main_actions = all_actions[:loop_start_idx]
        else:
            loop_actions = []
            main_actions = all_actions

        # Run the non-loop portion once
        for screen, action in main_actions:
            self._write_progress(screen, action)
            ok = self._execute(action)
            self._step_index += 1
            if not ok:
                logger.warning("Step %d/%d failed, aborting flow",
                               self._step_index, self._total_steps)
                return False
            time.sleep(5.0)

        # Loop portion — runs infinitely
        if loop_actions:
            logger.info("Entering infinite loop: steps %d-%d",
                        loop_start, loop_end)
        loop_count = 0
        while loop_actions:
            loop_count += 1
            logger.info("Loop iteration %d (steps %d-%d)",
                        loop_count, loop_start, loop_end)
            for screen, action in loop_actions:
                self._write_progress(screen, action)
                ok = self._execute(action)
                self._step_index += 1
                if not ok:
                    logger.warning("Loop step failed at iteration %d, "
                                   "aborting flow", loop_count)
                    return False
                time.sleep(5.0)

        logger.info("Flow completed successfully (%d steps)", self._total_steps)
        return True

    def _execute(self, action: dict, retries: int = 5) -> bool:
        atype = action["type"]
        x = action.get("x")
        y = action.get("y")
        label = action.get("label", "")
        raw_label = label

        # Resolve normal placeholders first
        resolved = resolve_label(label, self.profile)

        pad = self.v.pad_code
        logger.info("[%s] Step %d/%d: %s (%s) at (%s, %s)",
                    pad, self._step_index + 1, self._total_steps,
                    atype, raw_label or resolved, x or "—", y or "—")

        if self.dry_run:
            time.sleep(0.3)
            return True

        try:
            if atype == "tap":
                if x is not None and y is not None:
                    self._execute_with_retry(self.v.tap, x, y, retries=retries)
                return True

            elif atype == "text":
                if x is not None and y is not None:
                    self._execute_with_retry(self.v.tap, x, y, retries=retries)
                    time.sleep(1.5)  # wait for field focus + keyboard open

                    # Handle special SMS placeholders
                    effective_text = resolved
                    if raw_label == "{RENT_NUMBER}":
                        effective_text = self._handle_rent_number()
                    elif raw_label == "{SMS_CODE}":
                        effective_text = self._handle_sms_code()

                    if effective_text:
                        # Use ADB input text (more reliable than VMOS inputText for numeric fields)
                        adb_cmd = f"input text {effective_text}"
                        try:
                            self.v.client.send_adb(self.v.pad_code, adb_cmd)
                        except Exception:
                            self._execute_with_retry(self.v.text, effective_text, retries=retries)

                        # Dismiss keyboard after text so next tap lands (unless keep_keyboard is set)
                        if not action.get("keep_keyboard"):
                            try:
                                self.v.client.send_adb(self.v.pad_code, "input keyevent 111")
                            except Exception:
                                pass
                        time.sleep(5)  # let app process the entered text before next action
                return True

            elif atype == "swipe":
                direction = action.get("direction", "TOP_TO_BOTTOM")
                self._execute_with_retry(self.v.swipe, direction, retries=retries)
                return True

            elif atype == "wait":
                secs = action.get("seconds", 2)
                time.sleep(secs)
                return True

            else:
                logger.warning("Unknown action type: %s", atype)
                return False

        except Exception as e:
            logger.error("Action failed: %s", e)
            return False

    def _execute_with_retry(self, func, *args, retries=5, **kwargs):
        last_exc = None
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except VMOSAPIError as e:
                wait = 10 + attempt * 10
                logger.warning("API error, retrying in %ds (attempt %d/%d): %s",
                               wait, attempt + 1, retries, e)
                time.sleep(wait)
                last_exc = e
            except Exception as e:
                last_exc = e
                raise
        raise last_exc


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Execute recorded flow on VMOS phone")
    parser.add_argument("flow", help="Path to flow.json")
    parser.add_argument("--pad", required=True, help="VMOS padCode")
    parser.add_argument("--profile", required=True, help="CSV file with account profiles")
    parser.add_argument("--index", type=int, default=0, help="Row index in CSV")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without API calls")
    args = parser.parse_args()

    profiles = load_profiles(args.profile)
    if args.index >= len(profiles):
        print(f"Error: index {args.index} >= {len(profiles)} profiles")
        sys.exit(1)
    profile = profiles[args.index]

    client = VMOSClient()
    v = VmosAutomation(client, args.pad)
    runner = FlowRunner(args.flow, v, profile, dry_run=args.dry_run)
    ok = runner.run()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
