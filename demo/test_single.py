#!/usr/bin/env python3
"""
Single-device test: run the full pipeline on one cloud phone.
Useful for verifying that the VMOS + Appium + Match.com flow works
before scaling up.

Usage:
    python demo/test_single.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.logger import setup_logging
from engine.orchestrator import Orchestrator


def main():
    setup_logging("DEBUG")

    print("=" * 50)
    print("SINGLE DEVICE TEST")
    print("=" * 50)

    orch = Orchestrator(
        device_count=1,
        accounts_per_device=1,
    )

    try:
        result = orch.run_batch()

        print()
        print("=" * 40)
        print("TEST RESULT")
        print("=" * 40)
        print(f"  Success: {result.succeeded}")
        print(f"  Failed:  {result.failed}")
        print(f"  Time:    {result.duration_seconds:.1f}s")

        if result.accounts:
            acc = result.accounts[0]
            print(f"\n  Account: {acc.email} / {acc.password}")
            print(f"  Status:  {acc.status.value}")
        if result.errors:
            print(f"\n  Errors: {result.errors}")

    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        orch.shutdown()


if __name__ == "__main__":
    main()
