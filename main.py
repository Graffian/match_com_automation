#!/usr/bin/env python3
"""
Match.com Account Automation System
-----------------------------------
Automates Match.com account creation via VMOS Cloud + Appium,
running 5-20 cloud phone devices in parallel.

Usage:
    python main.py --devices 5 --accounts 1 --continuous
    python main.py --devices 10 --accounts 2 --batches 5
    python main.py --demo                          # Quick demo mode
    python main.py --summary                       # Show account summary
"""

import argparse
import sys
import time

from config.settings import Config
from engine.orchestrator import Orchestrator
from accounts.store import AccountStore
from utils.logger import setup_logging


def parse_args():
    parser = argparse.ArgumentParser(
        description="Match.com Account Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --devices 5 --accounts 1        # 5 accounts on 5 devices
  python main.py --devices 10 --accounts 2        # 20 accounts on 10 devices
  python main.py --devices 20 --accounts 5        # 100 accounts on 20 devices
  python main.py --demo                           # Quick 2-device demo
  python main.py --continuous --batches 10        # Run 10 batches continuously
  python main.py --summary                        # Print account summary
        """,
    )

    parser.add_argument(
        "--devices", type=int, default=5,
        help="Number of VMOS Cloud Phone devices to use (1-20, default: 5)"
    )
    parser.add_argument(
        "--accounts", type=int, default=1,
        help="Number of accounts to create per device per batch (default: 1)"
    )
    parser.add_argument(
        "--batches", type=int, default=1,
        help="Number of batches to run (default: 1)"
    )
    parser.add_argument(
        "--continuous", action="store_true",
        help="Run in continuous batch mode"
    )
    parser.add_argument(
        "--interval", type=int, default=60,
        help="Seconds between batches in continuous mode (default: 60)"
    )
    parser.add_argument(
        "--profiles", type=str, default=None,
        help="CSV file with profile data"
    )
    parser.add_argument(
        "--proxies", type=str, default=None,
        help="Text file with proxy list (one per line)"
    )
    parser.add_argument(
        "--db", type=str, default=None,
        help="SQLite database path (default: data/accounts.db)"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Run a quick demo with 2 devices"
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Print account summary and exit"
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--workers", type=int, default=None,
        help="Max parallel workers (default: same as --devices)"
    )

    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(args.log_level)

    cfg = Config()

    if args.summary:
        store = AccountStore(args.db or cfg.ACCOUNTS_DB)
        total = store.total_count()
        counts = store.count_by_status()
        print(f"\n{'='*40}")
        print(f"Account Store Summary ({cfg.ACCOUNTS_DB})")
        print(f"{'='*40}")
        print(f"  Total accounts: {total}")
        for status, cnt in sorted(counts.items()):
            print(f"  {status}: {cnt}")
        print(f"{'='*40}\n")
        store.close()
        return

    if args.demo:
        print(">>> Running DEMO mode with 2 devices, 1 account each")
        args.devices = 2
        args.accounts = 1
        args.batches = 1

    orch = Orchestrator(
        device_count=args.devices,
        accounts_per_device=args.accounts,
        profile_source=args.profiles,
        proxy_file=args.proxies,
        db_path=args.db,
        max_workers=args.workers,
    )

    try:
        if args.continuous or args.batches > 1:
            orch.run_continuous(
                batches=args.batches,
                interval_seconds=args.interval,
            )
        else:
            result = orch.run_batch()
            print(f"\n{'='*40}")
            print(f"Batch Results ({result.duration_seconds:.1f}s)")
            print(f"{'='*40}")
            print(f"  Total:    {result.total}")
            print(f"  Succeeded: {result.succeeded}")
            print(f"  Failed:   {result.failed}")
            if result.errors:
                print(f"\n  Errors ({len(result.errors)}):")
                for err in result.errors[:10]:
                    print(f"    - {err}")
                if len(result.errors) > 10:
                    print(f"    ... and {len(result.errors)-10} more")
            print(f"{'='*40}\n")

        orch.print_summary()

    except KeyboardInterrupt:
        print("\nInterrupted. Shutting down...")
        orch.stop()
    finally:
        orch.shutdown()


if __name__ == "__main__":
    main()
