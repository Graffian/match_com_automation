import tkinter as tk
from tkinter import Label, Frame
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw
import json
import io
import sys
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vmos.client import VMOSClient

PROGRESS_FILE = str(Path(__file__).resolve().parent.parent / "_step_progress.txt")
FLOW_FILE = str(Path(__file__).resolve().parent.parent / "flow.json")

flow = json.loads(Path(FLOW_FILE).read_text(encoding="utf-8"))
RES_W = flow.get("resolution", {}).get("width", 540)
RES_H = flow.get("resolution", {}).get("height", 960)

client = VMOSClient()
pad = sys.argv[1] if len(sys.argv) > 1 else "APP5BC4I5Q21MRYG"

root = tk.Tk()
root.title(f"Monitor — {pad}")
root.geometry("500x700+200+50")
root.attributes("-topmost", True)
root.update()

img_label = Label(root)
img_label.pack()

info_var = tk.StringVar(value="Waiting for step...")
info = Label(root, textvariable=info_var, font=("Consolas", 11),
             fg="white", bg="#222", anchor="w", justify="left")
info.pack(fill="x", padx=5, pady=5)

def fetch():
    try:
        # Read progress
        step_info = {}
        try:
            with open(PROGRESS_FILE) as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        step_info[k] = v
        except:
            pass

        # Take screenshot
        result = client.screenshot(pad, rotation=0)
        url = None
        if isinstance(result, list) and len(result) > 0:
            url = result[0].get("accessUrl")
        elif isinstance(result, dict):
            url = result.get("accessUrl")

        if url:
            resp = requests.get(url, timeout=15)
            img = Image.open(io.BytesIO(resp.content))
            sc_w, sc_h = img.size
            draw = ImageDraw.Draw(img)

            # Parse progress
            step = step_info.get("step", "?")
            fname = step_info.get("file", "?")
            atype = step_info.get("type", "?")
            px = step_info.get("x", "")
            py = step_info.get("y", "")
            label = step_info.get("label", "")
            direction = step_info.get("direction", "")

            # Draw tap marker
            if px and py:
                try:
                    dx = int(int(px) * sc_w / RES_W)
                    dy = int(int(py) * sc_h / RES_H)
                    r = 8
                    draw.ellipse([dx - r, dy - r, dx + r, dy + r], outline="#FF4444", width=3)
                    draw.line([dx - r - 5, dy, dx + r + 5, dy], fill="#FF4444", width=2)
                    draw.line([dx, dy - r - 5, dx, dy + r + 5], fill="#FF4444", width=2)
                    draw.text((dx + 15, dy - 10), f"({px},{py})", fill="#FF4444")
                except:
                    pass

            # Draw current step info at top
            extra = label or direction
            header = f"Step {step}: {fname}  {atype}"
            if extra:
                header += f"  [{extra}]"
            draw.text((10, 10), header, fill="#00FF00")
            draw.text((10, 30), f"Coord: ({px}, {py})", fill="#FFFF00")

            # Info text
            info_var.set(header)

            # Resize
            sw = root.winfo_width() or 480
            scale = min(sw / sc_w, 600 / sc_h, 1.0)
            nw, nh = int(sc_w * scale), int(sc_h * scale)
            photo = ImageTk.PhotoImage(img.resize((nw, nh), Image.LANCZOS))
            img_label.config(image=photo)
            img_label.image = photo

    except Exception as e:
        info_var.set(f"Error: {e}")

    root.after(2000, fetch)

fetch()
root.mainloop()
