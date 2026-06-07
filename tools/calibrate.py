"""
Click once on the screenshot to get corrected coords for the tap after {BIRTHDAY}.
Updates flow.json immediately.
"""
import json, tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk
import sys

flow = json.loads(Path("flow.json").read_text("utf-8"))

# Find the tap after {BIRTHDAY}
target = None
for screen in flow["screenshots"]:
    for j, a in enumerate(screen["actions"]):
        if a.get("label") == "{BIRTHDAY}" and j+1 < len(screen["actions"]):
            target = screen["actions"][j+1]
            break
    if target:
        break

if not target:
    print("Could not find {BIRTHDAY} text action in flow.json")
    sys.exit(1)

print(f"Current coords: ({target['x']}, {target['y']})")

img_path = sys.argv[1] if len(sys.argv) > 1 else "screenshots/image.png"
img = Image.open(img_path)
iw, ih = img.size

root = tk.Tk()
root.title("Click where Continue button is (with keyboard visible)")
sw, sh = root.winfo_screenwidth()-100, root.winfo_screenheight()-100
scale = min(sw/iw, sh/ih, 1.0)
dw, dh = int(iw*scale), int(ih*scale)
photo = ImageTk.PhotoImage(img.resize((dw, dh), Image.LANCZOS))
canvas = tk.Canvas(root, width=dw, height=dh, cursor="crosshair")
canvas.pack()
canvas.create_image(0, 0, anchor="nw", image=photo)

def click(event):
    ox, oy = int(event.x/scale), int(event.y/scale)
    target["x"], target["y"] = ox, oy
    Path("flow.json").write_text(json.dumps(flow, indent=2, ensure_ascii=True)+"\n", "utf-8")
    print(f"Updated to ({ox}, {oy}) — flow.json saved")
    root.destroy()

canvas.bind("<Button-1>", click)
root.mainloop()
