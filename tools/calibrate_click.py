import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk
import sys

img_path = sys.argv[1] if len(sys.argv) > 1 else "_calibrate_screen.png"
FLOW_W, FLOW_H = 540, 960

img = Image.open(img_path)
iw, ih = img.size

root = tk.Tk()
root.title(f"Click: ZIP field then 'That\\'s home' — image {iw}x{ih} -> flow {FLOW_W}x{FLOW_H}")
sw, sh = root.winfo_screenwidth()-100, root.winfo_screenheight()-100
scale = min(sw/iw, sh/ih, 1.0)
dw, dh = int(iw*scale), int(ih*scale)
photo = ImageTk.PhotoImage(img.resize((dw, dh), Image.LANCZOS))
canvas = tk.Canvas(root, width=dw, height=dh, cursor="crosshair")
canvas.pack()
canvas.create_image(0, 0, anchor="nw", image=photo)

coords = []
def click(event):
    ix, iy = int(event.x/scale), int(event.y/scale)
    # Scale from image resolution to flow resolution
    fx = int(ix * FLOW_W / iw)
    fy = int(iy * FLOW_H / ih)
    coords.append((fx, fy))
    print(f"[{len(coords)}] Image click ({ix}, {iy}) -> Flow coord ({fx}, {fy})")
    if len(coords) == 1:
        print("  ^ ZIP field — tap here to focus + type")
    elif len(coords) == 2:
        print(f"  ^ 'That\\'s home' button")
        print(f"\nUse these in flow.json:")
        print(f"  ZIP text action: x={coords[0][0]}, y={coords[0][1]}")
        print(f"  That's home tap: x={coords[1][0]}, y={coords[1][1]}")
        root.after(200, root.destroy)

canvas.bind("<Button-1>", click)
print(f"Image: {iw}x{ih}  ->  Flow: {FLOW_W}x{FLOW_H}")
print("Click 1: ZIP text field position")
print("Click 2: 'That\\'s home' button position")
root.mainloop()
