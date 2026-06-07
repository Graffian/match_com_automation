"""
Click on the ZIP field in the screenshot to update its tap position in flow.json.
"""
import json, tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk
import sys

flow = json.loads(Path("flow.json").read_text("utf-8"))

# Find the text action for {ZIP}
target = None
for screen in flow["screenshots"]:
    for a in screen["actions"]:
        if a.get("label") == "{ZIP}":
            target = a
            break
    if target:
        break

if not target:
    print("Could not find {ZIP} text action in flow.json")
    sys.exit(1)

print(f"Current ZIP field coords: ({target['x']}, {target['y']})")

img_path = sys.argv[1] if len(sys.argv) > 1 else "screenshots/image.png"
img = Image.open(img_path)
iw, ih = img.size

root = tk.Tk()
root.title("Click on the ZIP field")
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
    print(f"ZIP field updated to ({ox}, {oy}) — flow.json saved")
    root.destroy()

canvas.bind("<Button-1>", click)
root.mainloop()
