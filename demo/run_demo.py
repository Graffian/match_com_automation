#!/usr/bin/env python3
"""
Demo script: Creates a video-ready demonstration of the system.
- Spins up 2 VMOS Cloud Phone devices
- Creates 1 Match.com account per device
- Shows real-time logs and screenshots
- Saves results with timestamps

Steps to record the demo video:
  1. Have OBS or your screen recorder ready
  2. Run: python demo/run_demo.py
  3. Show the console output as devices boot and accounts are created
  4. Show the SQLite DB entries at the end
  5. Show saved screenshots in screenshots/
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.logger import setup_logging
from engine.orchestrator import Orchestrator


def main():
    setup_logging("INFO")
    print("=" * 60)
    print("MATCH.COM ACCOUNT AUTOMATION — DEMO")
    print("=" * 60)
    print()
    print("This demo will:")
    print("  1. Connect to VMOS Cloud")
    print("  2. Boot 2 cloud phone devices")
    print("  3. Generate synthetic profiles")
    print("  4. Run Match.com signup on each device in parallel")
    print("  5. Save results to data/accounts.db")
    print("  6. Take screenshots during the process")
    print()

    demo_dir = Path("demo_output")
    demo_dir.mkdir(exist_ok=True)
    (demo_dir / "screenshots").mkdir(exist_ok=True)

    input("Press Enter to start the demo (start recording now)...")

    print("\n[1/5] Initializing VMOS Cloud connection...")
    time.sleep(1)

    orch = Orchestrator(
        device_count=2,
        accounts_per_device=1,
    )

    try:
        print("\n[2/5] Preparing cloud phone devices...")
        time.sleep(1)

        print("\n[3/5] Generating profiles and running automation...")
        print("      (watch each device create an account in parallel)")
        print()

        result = orch.run_batch()

        print()
        print("[4/5] Demo complete!")
        print()
        print("=" * 40)
        print("DEMO RESULTS")
        print("=" * 40)
        print(f"  Devices used:   2")
        print(f"  Accounts created: {result.succeeded}")
        print(f"  Failed:         {result.failed}")
        print(f"  Duration:       {result.duration_seconds:.1f}s")

        if result.accounts:
            print(f"\n  Accounts created:")
            for acc in result.accounts:
                print(f"    - {acc.email} ({acc.first_name} {acc.last_name})")
                print(f"      Status: {acc.status.value}")
                print(f"      Device: {acc.device_id}")

        if result.errors:
            print(f"\n  Errors:")
            for err in result.errors[:5]:
                print(f"    - {err}")

        print()
        print("[5/5] Summary")
        orch.print_summary()

        print()
        print("=" * 60)
        print("DEMO FINISHED")
        print("=" * 60)
        print()
        print("To verify the accounts in the database:")
        print(f"  python main.py --summary")
        print()

    except KeyboardInterrupt:
        print("\n\nDemo interrupted.")
    finally:
        orch.shutdown()


if __name__ == "__main__":
    main()
