"""
Run the recorded flow on all 4 VMOS phones with different profiles.

Usage:
    python demo/run_batch.py flow.json data/profiles.csv

The CSV must have at least 4 rows. Each row is assigned to a device in order.
"""
import sys
import time
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from vmos.client import VMOSClient
from vmos.automation import VmosAutomation
from automation.flow_runner import FlowRunner, load_profiles
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PAD_CODES = [
    "APP5BC4I5Q21MRYG",
    "APP5BN4NR2PRIFWO",
    "APP5BN4NUBXZYN17",
    "ATP5CD4Y1THRE5AI",
]


def run_one(flow_path: str, pad_code: str, profile: dict, index: int) -> bool:
    client = VMOSClient()
    v = VmosAutomation(client, pad_code)
    runner = FlowRunner(flow_path, v, profile, dry_run=False)
    logger.info("[%d/%d] Starting %s on %s", index + 1, len(PAD_CODES),
                profile.get("email", "?"), pad_code)
    return runner.run()


def main():
    parser = argparse.ArgumentParser(description="Run flow on all 4 phones")
    parser.add_argument("flow", help="Path to flow.json")
    parser.add_argument("profiles", help="Path to profiles CSV (at least 4 rows)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate without API calls")
    parser.add_argument("--parallel", action="store_true",
                        help="Run all phones in parallel")
    args = parser.parse_args()

    profiles = load_profiles(args.profiles)
    count = min(len(PAD_CODES), len(profiles))
    if count < 4:
        logger.warning("Only %d profiles, using %d devices", len(profiles), count)

    if args.dry_run:
        for i in range(count):
            logger.info("[DRY] Would run %s on %s",
                        profiles[i].get("email", "?"), PAD_CODES[i])
        return

    if args.parallel:
        with ThreadPoolExecutor(max_workers=count) as pool:
            futs = []
            for i in range(count):
                futs.append(pool.submit(
                    run_one, args.flow, PAD_CODES[i], profiles[i], i
                ))
            for fut in as_completed(futs):
                ok = fut.result()
                if not ok:
                    logger.error("One phone run failed!")
    else:
        for i in range(count):
            ok = run_one(args.flow, PAD_CODES[i], profiles[i], i)
            if not ok:
                logger.error("Run failed for %s", PAD_CODES[i])
            time.sleep(5)  # pause between phones


if __name__ == "__main__":
    main()
