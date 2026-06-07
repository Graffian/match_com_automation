import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from vmos import VMOSClient, VmosAutomation

c = VMOSClient()
automation = VmosAutomation(c, "APP5BC4I5Q21MRYG")

print("=== VMOS Phone Automation Test ===")

# 1. Open Match.com
print("\n1. Opening Match.com app...")
automation.open_app("com.match.android")
time.sleep(3)

# 2. Take screenshot
print("2. Taking screenshot...")
automation.run_adb("screencap -p /sdcard/screen.png && echo DONE")
time.sleep(2)

# 3. Tap center (wake up/click)
print("3. Tapping screen...")
automation.tap(540, 1200)
time.sleep(1)

# 4. Type something in focused field
print("4. Typing text...")
automation.text("Match.com is running on VMOS!")
time.sleep(1)

# 5. Swipe
print("5. Swiping...")
automation.swipe("TOP_TO_BOTTOM")
time.sleep(1)

print("\n=== Test complete ===")
