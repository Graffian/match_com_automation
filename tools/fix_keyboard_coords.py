"""
Click on the keyboard-visible screenshot to get corrected coordinates
for the "Continue" buttons that are hidden behind the keyboard.

Shows each text→tap sequence, you click where the button actually appears
with the keyboard open, and it updates flow.json.

Usage:
    python tools/fix_keyboard_coords.py screenshots/image.png
"""
import json
import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk

def main():
    import sys
    screenshot_path = sys.argv[1] if len(sys.argv) > 1 else "screenshots/image.png"
    flow_path = "flow.json"

    flow = json.loads(Path(flow_path).read_text(encoding="utf-8"))

    # Find text→tap sequences that need fixing
    entries = []
    for screen in flow["screenshots"]:
        actions = screen["actions"]
        for j, action in enumerate(actions):
            if action["type"] == "text" and j + 1 < len(actions) and actions[j + 1]["type"] == "tap":
                nxt = actions[j + 1]
                entries.append({
                    "screen_file": screen["file"],
                    "tap_idx": j + 1,
                    "old_x": nxt["x"],
                    "old_y": nxt["y"],
                    "action": nxt,
                })

    if not entries:
        print("No text→tap sequences found.")
        return

    print(f"Found {len(entries)} buttons hidden by keyboard:")
    for e in entries:
        print(f"  {e['screen_file']}: tap at ({e['old_x']}, {e['old_y']})")

    img = Image.open(screenshot_path)
    results = []
    current = 0

    root = tk.Tk()
    root.title(f"Click button 1/{len(entries)} — Close window when done")

    iw, ih = img.size
    screen_w = root.winfo_screenwidth() - 100
    screen_h = root.winfo_screenheight() - 100
    scale = min(screen_w / iw, screen_h / ih, 1.0)
    dw, dh = int(iw * scale), int(ih * scale)
    img_resized = img.resize((dw, dh), Image.LANCZOS)
    photo = ImageTk.PhotoImage(img_resized)

    canvas = tk.Canvas(root, width=dw, height=dh, cursor="crosshair")
    canvas.pack()
    canvas.create_image(0, 0, anchor="nw", image=photo)

    status = tk.Label(root, text=f"Click where '{entries[0]['screen_file']}' button appears")
    status.pack()

    def on_click(event):
        nonlocal current
        if current >= len(entries):
            return
        ox = int(event.x / scale)
        oy = int(event.y / scale)
        e = entries[current]
        results.append({"x": ox, "y": oy, "entry": e})
        print(f"  {e['screen_file']}: ({e['old_x']}, {e['old_y']}) -> ({ox}, {oy})")
        current += 1
        if current < len(entries):
            status.config(text=f"Click where '{entries[current]['screen_file']}' button appears ({current+1}/{len(entries)})")
            root.title(f"Click button {current+1}/{len(entries)}")
        else:
            status.config(text="All done! Close window.")
            root.title("Done!")

    canvas.bind("<Button-1>", on_click)
    root.mainloop()

    if not results:
        print("No clicks recorded.")
        return

    print(f"\nUpdating {flow_path}...")
    for r in results:
        e = r["entry"]
        e["action"]["x"] = r["x"]
        e["action"]["y"] = r["y"]

    Path(flow_path).write_text(json.dumps(flow, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Done! Updated {len(results)} coordinates.")

if __name__ == "__main__":
    main()
